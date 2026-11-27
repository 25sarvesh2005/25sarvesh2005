"""Resilient GitHub API & contribution calendar collector for @25sarvesh2005.

Supports authenticated GraphQL+REST (used in GitHub Actions via GITHUB_TOKEN or
optional PROFILE_READ_TOKEN) as well as unauthenticated REST + public calendar
HTML fallback for local testing without secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from scripts.config import API_BASE, GITHUB_USERNAME, GRAPHQL_URL

USER_AGENT = "25sarvesh2005-profile-telemetry/1.0"

GRAPHQL_USER_CONTRIBS = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

GRAPHQL_MERGED_PRS = """
query($q: String!) {
  search(query: $q, type: ISSUE, first: 100) {
    issueCount
    nodes {
      ... on PullRequest {
        url
        merged
        repository {
          nameWithOwner
          owner {
            login
          }
        }
      }
    }
  }
}
"""


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    max_attempts: int = 3,
) -> httpx.Response:
    """Execute an HTTP request with bounded exponential backoff on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            resp = client.request(method, url, headers=headers, json=json_body, timeout=20.0)
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts - 1:
                time.sleep(1.5 * (2**attempt))
                continue
            return resp
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(1.5 * (2**attempt))
    raise RuntimeError(f"HTTP request failed for {url}: {last_exc}")


def _api_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_owned_repos(client: httpx.Client, username: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Fetch owned, non-fork public repositories cleanly via paginated REST."""
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{username}/repos?type=owner&per_page=100&page={page}&sort=updated"
        resp = _request_with_retry(client, "GET", url, headers=headers)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for repo in batch:
            owner_login = (repo.get("owner") or {}).get("login", "")
            if owner_login.lower() == username.lower() and not repo.get("fork", False):
                repos.append(repo)
        if len(batch) < 100:
            break
        page += 1
    return repos


def _fetch_user_starred_set(client: httpx.Client, username: str, headers: dict[str, str]) -> set[str]:
    """Fetch lowercase full_names of repositories starred by the user (fallback when unauthenticated)."""
    starred: set[str] = set()
    page = 1
    while page <= 10:
        resp = _request_with_retry(
            client,
            "GET",
            f"{API_BASE}/users/{username}/starred?per_page=100&page={page}",
            headers=headers,
        )
        if resp.status_code != 200:
            resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for item in batch:
            if isinstance(item, dict) and item.get("full_name"):
                starred.add(item["full_name"].lower())
        if len(batch) < 100:
            break
        page += 1
    return starred


def _fetch_repo_signals(
    client: httpx.Client,
    username: str,
    repo: dict[str, Any],
    headers: dict[str, str],
    user_starred: set[str] | None = None,
) -> dict[str, Any]:
    """Collect verified language bytes, non-self stars, README, and CI workflow status."""
    full_name = repo["full_name"]
    is_empty = repo.get("size", 0) == 0

    languages: dict[str, int] = {}
    has_readme = False
    has_ci = False
    external_stars = 0

    if not is_empty:
        lang_resp = _request_with_retry(client, "GET", f"{API_BASE}/repos/{full_name}/languages", headers=headers)
        if lang_resp.status_code == 200:
            languages = lang_resp.json()
        elif lang_resp.status_code != 404:
            lang_resp.raise_for_status()

        readme_resp = _request_with_retry(client, "GET", f"{API_BASE}/repos/{full_name}/readme", headers=headers)
        if readme_resp.status_code == 200:
            has_readme = True
        elif readme_resp.status_code != 404:
            readme_resp.raise_for_status()

        wf_resp = _request_with_retry(
            client,
            "GET",
            f"{API_BASE}/repos/{full_name}/contents/.github/workflows",
            headers=headers,
        )
        if wf_resp.status_code == 200 and isinstance(wf_resp.json(), list):
            has_ci = any(
                item.get("name", "").endswith((".yml", ".yaml"))
                for item in wf_resp.json()
                if isinstance(item, dict)
            )
        elif wf_resp.status_code != 404:
            wf_resp.raise_for_status()

        total_stars = int(repo.get("stargazers_count", 0))
        if total_stars > 0:
            if user_starred is not None:
                self_starred = 1 if full_name.lower() in user_starred else 0
                external_stars = max(0, total_stars - self_starred)
            else:
                star_page = 1
                while True:
                    star_resp = _request_with_retry(
                        client,
                        "GET",
                        f"{API_BASE}/repos/{full_name}/stargazers?per_page=100&page={star_page}",
                        headers=headers,
                    )
                    if star_resp.status_code != 200:
                        star_resp.raise_for_status()
                    stargazers = star_resp.json()
                    if not stargazers:
                        break
                    external_stars += sum(
                        1
                        for sg in stargazers
                        if sg.get("login", "").lower() != username.lower()
                    )
                    if len(stargazers) < 100:
                        break
                    star_page += 1

    return {
        "name": repo["name"],
        "full_name": full_name,
        "html_url": repo["html_url"],
        "description": repo.get("description") or "",
        "homepage": repo.get("homepage") or "",
        "size_kb": repo.get("size", 0),
        "is_empty": is_empty,
        "stargazers_count": repo.get("stargazers_count", 0),
        "external_stars": external_stars,
        "has_readme": has_readme,
        "has_ci": has_ci,
        "languages": languages,
        "pushed_at": repo.get("pushed_at"),
        "created_at": repo.get("created_at"),
    }


def _parse_contributions_html(html: str) -> dict[str, int]:
    """Parse date -> count map from GitHub's public contributions fragment."""
    id_to_date = {
        match.group(2): match.group(1)
        for match in re.finditer(
            r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="(contribution-day-component-[^"]+)"',
            html,
        )
    }
    if not id_to_date:
        id_to_date = {
            match.group(1): match.group(2)
            for match in re.finditer(
                r'id="(contribution-day-component-[^"]+)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"',
                html,
            )
        }
    daily: dict[str, int] = {}
    for tt in re.finditer(
        r'<tool-tip[^>]*for="(contribution-day-component-[^"]+)"[^>]*>(.*?)</tool-tip>',
        html,
        re.S,
    ):
        comp_id, text = tt.group(1), re.sub(r"<[^>]+>", "", tt.group(2)).strip()
        day = id_to_date.get(comp_id)
        if not day:
            continue
        cnt_match = re.match(r"^(\d+)\s+contribution", text)
        daily[day] = int(cnt_match.group(1)) if cnt_match else 0
    return daily


def _fetch_calendar_graphql(
    client: httpx.Client,
    username: str,
    start_year: int,
    end_year: int,
    headers: dict[str, str],
) -> tuple[dict[str, int], int]:
    """Fetch exact daily contribution calendar across all years since account creation."""
    daily: dict[str, int] = {}
    restricted_total = 0
    for year in range(start_year, end_year + 1):
        payload = {
            "query": GRAPHQL_USER_CONTRIBS,
            "variables": {
                "login": username,
                "from": f"{year}-01-01T00:00:00Z",
                "to": f"{year}-12-31T23:59:59Z",
            },
        }
        resp = _request_with_retry(client, "POST", GRAPHQL_URL, headers=headers, json_body=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        col = body["data"]["user"]["contributionsCollection"]
        restricted_total += int(col.get("restrictedContributionsCount") or 0)
        for week in col["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                daily[day["date"]] = int(day["contributionCount"])
    return daily, restricted_total


def _fetch_calendar_public_html(
    client: httpx.Client,
    username: str,
    start_year: int,
    end_year: int,
) -> tuple[dict[str, int], int]:
    """Fallback calendar collector using GitHub's public contributions HTML fragment."""
    daily: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        url = f"https://github.com/users/{username}/contributions?from={year}-01-01&to={year}-12-31"
        resp = _request_with_retry(client, "GET", url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        daily.update(_parse_contributions_html(resp.text))
    return daily, 0


def _fetch_merged_prs(
    client: httpx.Client,
    username: str,
    headers: dict[str, str],
    token: str | None,
) -> tuple[int, int]:
    """Return (total_merged_prs, external_merged_prs)."""
    query_str = f"author:{username} type:pr is:merged"
    if token:
        resp = _request_with_retry(
            client,
            "POST",
            GRAPHQL_URL,
            headers=headers,
            json_body={"query": GRAPHQL_MERGED_PRS, "variables": {"q": query_str}},
        )
        if resp.status_code == 200 and not resp.json().get("errors"):
            search_data = resp.json()["data"]["search"]
            nodes = search_data.get("nodes") or []
            total = int(search_data.get("issueCount") or len(nodes))
            external = sum(
                1
                for node in nodes
                if ((node.get("repository") or {}).get("owner") or {}).get("login", "").lower()
                != username.lower()
            )
            return total, external

    resp = _request_with_retry(
        client,
        "GET",
        f"{API_BASE}/search/issues?q=author:{username}+type:pr+is:merged&per_page=100",
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items") or []
    total = int(data.get("total_count") or len(items))
    prefix = f"/repos/{username.lower()}/"
    external = sum(
        1 for it in items if prefix not in (it.get("repository_url") or "").lower()
    )
    return total, external


def collect_github_metrics(username: str = GITHUB_USERNAME, token: str | None = None) -> dict[str, Any]:
    """Collect normalized public/authenticated metrics for the target GitHub user."""
    headers = _api_headers(token)
    now = datetime.now(UTC)

    with httpx.Client() as client:
        user_resp = _request_with_retry(client, "GET", f"{API_BASE}/users/{username}", headers=headers)
        user_resp.raise_for_status()
        user = user_resp.json()

        created_at = user["created_at"]
        start_year = int(created_at[:4])
        end_year = now.year

        repos = _fetch_owned_repos(client, username, headers)
        user_starred = None if token else _fetch_user_starred_set(client, username, headers)
        repo_signals = [
            _fetch_repo_signals(client, username, repo, headers, user_starred=user_starred)
            for repo in repos
        ]

        if token:
            daily_calendar, restricted_count = _fetch_calendar_graphql(
                client, username, start_year, end_year, headers
            )
        else:
            daily_calendar, restricted_count = _fetch_calendar_public_html(
                client, username, start_year, end_year
            )

        merged_prs, external_merged_prs = _fetch_merged_prs(client, username, headers, token)

    return {
        "schema_version": 1,
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": {
            "login": user["login"],
            "name": user.get("name") or user["login"],
            "created_at": created_at,
            "followers": int(user.get("followers") or 0),
            "following": int(user.get("following") or 0),
            "public_repos_count": int(user.get("public_repos") or len(repo_signals)),
        },
        "contributions": {
            "daily": dict(sorted(daily_calendar.items())),
            "restricted_count_reported": restricted_count,
        },
        "pull_requests": {
            "merged_total": merged_prs,
            "merged_external": external_merged_prs,
        },
        "owned_repositories": repo_signals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch normalized GitHub profile metrics.")
    parser.add_argument("--username", default=GITHUB_USERNAME)
    parser.add_argument("--out", type=Path, required=True, help="Output metrics JSON path.")
    parser.add_argument(
        "--fallback",
        type=Path,
        default=None,
        help="Optional existing metrics JSON to preserve if GitHub API is degraded.",
    )
    args = parser.parse_args()

    token = os.getenv("PROFILE_READ_TOKEN") or os.getenv("GITHUB_TOKEN") or None
    args.out.parent.mkdir(parents=True, exist_ok=True)

    try:
        payload = collect_github_metrics(username=args.username, token=token)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote fresh metrics snapshot to {args.out}")
    except Exception as exc:
        if args.fallback and args.fallback.exists():
            args.out.write_text(args.fallback.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"WARN: Live fetch failed ({exc}); preserved cached fallback metrics.")
            return
        raise


if __name__ == "__main__":
    main()
