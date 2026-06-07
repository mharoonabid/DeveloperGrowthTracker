import requests

from github_analytics import (
    compute_language_usage_by_bytes,
    compute_repo_analytics,
    fetch_all_repos,
    fetch_contribution_graph,
)
from github_errors import GitHubAPIError


def load_profile_data(username, github_token=None, github_headers=None):
    headers = github_headers or {"Accept": "application/vnd.github+json"}
    if github_token:
        headers = {**headers, "Authorization": f"Bearer {github_token}"}

    res = requests.get(
        f"https://api.github.com/users/{username}",
        headers=headers,
        timeout=30,
    )

    if res.status_code == 404:
        return {"not_found": True, "username": username}

    if not res.ok:
        error = GitHubAPIError.from_response(res)
        return {"api_error": error.user_message}

    user = res.json()
    warnings = []
    analytics = None
    analytics_error = None
    contributions = None
    contributions_error = None
    repos = None

    try:
        repos = fetch_all_repos(username, token=github_token)
    except GitHubAPIError as exc:
        analytics_error = exc.user_message
    except requests.RequestException as exc:
        analytics_error = f"Could not load repositories: {exc}"

    if repos is not None:
        analytics = compute_repo_analytics(repos)

        if analytics["total_repos"] == 0:
            warnings.append("This user has no public repositories to analyze.")
        else:
            language_bytes = compute_language_usage_by_bytes(
                repos, token=github_token
            )
            analytics["language_bytes"] = language_bytes
            warnings.extend(language_bytes.get("warnings", []))

    if github_token:
        try:
            contributions = fetch_contribution_graph(username, github_token)
            if contributions["total_contributions"] == 0:
                warnings.append("No public contributions recorded in the last year.")
        except GitHubAPIError as exc:
            contributions_error = exc.user_message
        except requests.RequestException as exc:
            contributions_error = f"Could not load contributions: {exc}"
    else:
        contributions_error = "Set GITHUB_TOKEN in .env to load contribution data."

    return {
        "user": user,
        "analytics": analytics,
        "analytics_error": analytics_error,
        "contributions": contributions,
        "contributions_error": contributions_error,
        "warnings": warnings,
    }
