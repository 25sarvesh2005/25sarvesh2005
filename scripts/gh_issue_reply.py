"""Post combat result reply to the triggering GitHub Issue and close it."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

from scripts.config import API_BASE


def main() -> None:
    parser = argparse.ArgumentParser(description="Comment on and close a raid issue.")
    parser.add_argument("--reply-file", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    issue_num = os.environ["EVENT_ISSUE_NUMBER"]
    body = args.reply_file.read_text(encoding="utf-8")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "25sarvesh2005-raid-bot/1.0",
    }

    with httpx.Client(timeout=20.0) as client:
        c_resp = client.post(
            f"{API_BASE}/repos/{repo}/issues/{issue_num}/comments",
            headers=headers,
            json={"body": body},
        )
        c_resp.raise_for_status()

        p_resp = client.patch(
            f"{API_BASE}/repos/{repo}/issues/{issue_num}",
            headers=headers,
            json={"state": "closed", "state_reason": "completed"},
        )
        p_resp.raise_for_status()

    print(f"Replied and closed issue #{issue_num}")


if __name__ == "__main__":
    main()
