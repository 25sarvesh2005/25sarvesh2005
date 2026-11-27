"""Unit tests for fail-closed API error handling and self-star filtering."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts import fetch_github_data


def _mock_response(status_code: int, payload: object, url: str = "https://api.github.com/test") -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("GET", url),
    )


def test_fetch_repo_signals_fails_closed_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(client, method, url, **kwargs):  # noqa: ARG001
        if url.endswith("/languages"):
            return _mock_response(403, {"message": "API rate limit exceeded"}, url)
        return _mock_response(200, {}, url)

    monkeypatch.setattr(fetch_github_data, "_request_with_retry", fake_request)
    repo = {
        "name": "VeriRAG",
        "full_name": "25sarvesh2005/VeriRAG",
        "html_url": "https://github.com/25sarvesh2005/VeriRAG",
        "size": 67,
        "stargazers_count": 1,
    }
    with httpx.Client() as client, pytest.raises(httpx.HTTPStatusError):
        fetch_github_data._fetch_repo_signals(client, "25sarvesh2005", repo, {})


def test_fetch_repo_signals_computes_external_stars_unauthenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(client, method, url, **kwargs):  # noqa: ARG001
        if url.endswith("/languages"):
            return _mock_response(200, {"Python": 1000}, url)
        if url.endswith("/readme"):
            return _mock_response(404, {"message": "Not Found"}, url)
        if url.endswith("/contents/.github/workflows"):
            return _mock_response(404, {"message": "Not Found"}, url)
        raise AssertionError(f"Unexpected call: {url}")

    monkeypatch.setattr(fetch_github_data, "_request_with_retry", fake_request)
    repo = {
        "name": "telephony_ai",
        "full_name": "25sarvesh2005/telephony_ai",
        "html_url": "https://github.com/25sarvesh2005/telephony_ai",
        "size": 235,
        "stargazers_count": 2,
    }
    with httpx.Client() as client:
        signals = fetch_github_data._fetch_repo_signals(
            client,
            "25sarvesh2005",
            repo,
            {},
            user_starred={"25sarvesh2005/telephony_ai"},
        )
    assert signals["external_stars"] == 1
    assert signals["has_readme"] is False
    assert signals["has_ci"] is False


def test_main_preserves_fallback_metrics_on_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fallback_file = tmp_path / "cached.json"
    out_file = tmp_path / "metrics.json"
    cached_payload = {"schema_version": 1, "preserved": True}
    fallback_file.write_text(json.dumps(cached_payload), encoding="utf-8")

    def boom(**kwargs):  # noqa: ARG001
        raise RuntimeError("API rate limit exceeded")

    monkeypatch.setattr(fetch_github_data, "collect_github_metrics", boom)
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_github_data.py", "--out", str(out_file), "--fallback", str(fallback_file)],
    )
    fetch_github_data.main()
    assert json.loads(out_file.read_text(encoding="utf-8")) == cached_payload


def test_fetch_user_starred_set_retries_without_auth_on_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    def fake_request(client, method, url, headers=None, **kwargs):  # noqa: ARG001
        calls.append(dict(headers or {}))
        if "Authorization" in (headers or {}):
            return _mock_response(403, {"message": "Resource not accessible by integration"}, url)
        return _mock_response(200, [{"full_name": "25sarvesh2005/VeriRAG"}], url)

    monkeypatch.setattr(fetch_github_data, "_request_with_retry", fake_request)
    with httpx.Client() as client:
        starred = fetch_github_data._fetch_user_starred_set(
            client,
            "25sarvesh2005",
            {"Authorization": "Bearer installation-token"},
        )
    assert starred == {"25sarvesh2005/verirag"}
    assert len(calls) == 2
    assert "Authorization" not in calls[1]


def test_extract_manifest_packages_parses_python_js_and_gradle() -> None:
    req = "# comment\nfastapi==0.115.0\ngoogle_genai>=2.0.0\npydantic[email]>=2.9\n"
    assert {"fastapi", "google-genai", "pydantic"} <= fetch_github_data._extract_manifest_packages(
        "requirements.txt", req
    )

    pyp = '[project]\ndependencies = ["httpx>=0.27", "pytest>=8.0"]\n[tool.ruff]\nline-length = 100\n'
    assert {"httpx", "pytest", "ruff"} <= fetch_github_data._extract_manifest_packages(
        "pyproject.toml", pyp
    )

    pkg_json = '{"dependencies": {"react": "^19.0.0", "electron": "^32.0.0"}, "devDependencies": {"typescript": "^5.6.0"}}'
    assert {"react", "electron", "typescript"} == fetch_github_data._extract_manifest_packages(
        "package.json", pkg_json
    )

    gradle = '[libraries]\ncompose = { group = "androidx.compose.ui", name = "ui" }\n'
    assert "androidx.compose.ui" in fetch_github_data._extract_manifest_packages(
        "gradle/libs.versions.toml", gradle
    )
