from collections import Counter

import requests

GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"

CONTRIBUTION_LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def _api_headers(token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_all_repos(username, token=None):
    repos = []
    page = 1
    headers = _api_headers(token)

    while True:
        response = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers,
            params={
                "per_page": 100,
                "page": page,
                "type": "owner",
                "sort": "updated",
            },
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repos


def fetch_repo_languages(full_name, token=None):
    response = requests.get(
        f"{GITHUB_API}/repos/{full_name}/languages",
        headers=_api_headers(token),
        timeout=30,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def format_bytes(byte_count):
    size = float(byte_count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024


def compute_language_usage_by_bytes(repos, token=None):
    byte_totals = Counter()
    repos_analyzed = 0

    for repo in repos:
        if repo.get("fork"):
            continue

        languages = fetch_repo_languages(repo["full_name"], token=token)
        if not languages:
            continue

        repos_analyzed += 1
        for language, byte_count in languages.items():
            byte_totals[language] += byte_count

    total_bytes = sum(byte_totals.values())
    if total_bytes == 0:
        return {
            "languages": [],
            "total_bytes": 0,
            "repos_analyzed": repos_analyzed,
        }

    language_stats = []
    for language, byte_count in byte_totals.most_common():
        language_stats.append(
            {
                "name": language,
                "bytes": byte_count,
                "bytes_label": format_bytes(byte_count),
                "percentage": round(byte_count / total_bytes * 100, 1),
            }
        )

    return {
        "languages": language_stats,
        "total_bytes": total_bytes,
        "total_bytes_label": format_bytes(total_bytes),
        "repos_analyzed": repos_analyzed,
    }


def fetch_contribution_graph(username, token):
    if not token:
        raise ValueError("GITHUB_TOKEN is required for contribution data")

    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                contributionLevel
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        GITHUB_GRAPHQL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": {"username": username}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        message = payload["errors"][0].get("message", "GraphQL error")
        raise requests.RequestException(message)

    user = payload.get("data", {}).get("user")
    if not user:
        raise requests.RequestException("User not found")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    days = []
    weeks = []

    for week in calendar["weeks"]:
        week_days = []
        for day in week["contributionDays"]:
            day_data = {
                "date": day["date"],
                "count": day["contributionCount"],
                "level": CONTRIBUTION_LEVELS.get(day["contributionLevel"], 0),
            }
            days.append(day_data)
            week_days.append(day_data)
        weeks.append({"days": week_days})

    monthly_totals = Counter()
    for day in days:
        monthly_totals[day["date"][:7]] += day["count"]

    return {
        "total_contributions": calendar["totalContributions"],
        "days": days,
        "weeks": weeks,
        "monthly": [
            {"month": month, "count": count}
            for month, count in sorted(monthly_totals.items())
        ],
    }


def compute_repo_analytics(repos):
    if not repos:
        return {
            "total_repos": 0,
            "original_repos": 0,
            "forked_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "total_open_issues": 0,
            "total_watchers": 0,
            "average_stars": 0,
            "most_starred": None,
            "languages": [],
            "repos": [],
        }

    original = [repo for repo in repos if not repo.get("fork")]
    forked = [repo for repo in repos if repo.get("fork")]

    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    total_forks = sum(repo.get("forks_count", 0) for repo in repos)
    total_open_issues = sum(repo.get("open_issues_count", 0) for repo in repos)
    total_watchers = sum(repo.get("watchers_count", 0) for repo in repos)

    sorted_repos = sorted(
        repos,
        key=lambda repo: (
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0),
        ),
        reverse=True,
    )

    language_counts = Counter(
        repo.get("language") or "Unknown" for repo in original
    )

    return {
        "total_repos": len(repos),
        "original_repos": len(original),
        "forked_repos": len(forked),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "total_open_issues": total_open_issues,
        "total_watchers": total_watchers,
        "average_stars": round(total_stars / len(repos), 1),
        "most_starred": sorted_repos[0],
        "languages": language_counts.most_common(),
        "repos": sorted_repos,
    }
