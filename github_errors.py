from datetime import datetime, timezone

import requests


class GitHubAPIError(requests.RequestException):
    def __init__(self, message, status_code=None, is_rate_limit=False):
        super().__init__(message)
        self.user_message = message
        self.status_code = status_code
        self.is_rate_limit = is_rate_limit

    @classmethod
    def from_response(cls, response):
        status = response.status_code

        if status == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
            reset_at = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
            minutes = max(
                1,
                int((reset_at - datetime.now(timezone.utc)).total_seconds() / 60),
            )
            return cls(
                f"GitHub API rate limit exceeded. Try again in about {minutes} minute(s).",
                status_code=403,
                is_rate_limit=True,
            )

        if status == 403:
            message = _response_message(response, "Access to GitHub API was denied.")
            return cls(message, status_code=403)

        if status == 404:
            return cls("The requested GitHub resource was not found.", status_code=404)

        message = _response_message(
            response,
            response.reason or f"Unexpected GitHub API error (HTTP {status}).",
        )
        return cls(f"GitHub API error: {message}", status_code=status)


def _response_message(response, fallback):
    try:
        payload = response.json()
        return payload.get("message") or fallback
    except ValueError:
        return fallback


def check_github_response(response):
    if response.ok:
        return
    raise GitHubAPIError.from_response(response)
