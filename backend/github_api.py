import requests
from typing import Any, Dict


class GitHubAPI:
    """Lightweight wrapper around the GitHub REST API for pull requests."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("A GitHub token is required to interact with the API.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def create_pull_request(
        self, owner: str, repo: str, title: str, body: str, head: str, base: str
    ) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        payload = {"title": title, "body": body, "head": head, "base": base}
        response = self.session.post(url, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(self._format_error(response))
        return response.json()

    def _format_error(self, response: requests.Response) -> str:
        details = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        message = details.get("message") if isinstance(details, dict) else None
        errors = details.get("errors") if isinstance(details, dict) else None
        error_suffix = f" Errors: {errors}" if errors else ""
        return f"GitHub API request failed with status {response.status_code}: {message or response.text}{error_suffix}"
