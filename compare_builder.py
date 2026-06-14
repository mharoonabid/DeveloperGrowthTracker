from datetime import datetime

COMPARE_METRICS = [
    ("Total Stars", "total_stars", "higher"),
    ("Total Repositories", "total_repos", "higher"),
    ("Original Repos", "original_repos", "higher"),
    ("Total Forks", "total_forks", "higher"),
    ("Avg Stars / Repo", "average_stars", "higher"),
    ("Followers", "followers", "higher"),
    ("Contributions (1y)", "total_contributions", "higher"),
    ("Current Streak", "current_streak", "higher"),
    ("Longest Streak", "longest_streak", "higher"),
    ("Most Active Month", "most_active_month_count", "higher"),
]


def _format_month(month_key):
    if not month_key:
        return "—"
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%b %Y")
    except ValueError:
        return month_key


def build_compare_summary(profile_data):
    user = profile_data["user"]
    analytics = profile_data.get("analytics") or {}
    contributions = profile_data.get("contributions")
    language_bytes = analytics.get("language_bytes") or {}

    most_active_month = None
    most_active_month_count = 0
    if contributions and contributions.get("monthly"):
        best = max(contributions["monthly"], key=lambda entry: entry["count"])
        most_active_month = best["month"]
        most_active_month_count = best["count"]

    streaks = (contributions or {}).get("streaks") or {}
    top_languages = language_bytes.get("languages", [])[:5]
    top_language = top_languages[0] if top_languages else None

    return {
        "login": user["login"],
        "name": user.get("name") or user["login"],
        "avatar_url": user["avatar_url"],
        "bio": user.get("bio"),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "total_repos": analytics.get("total_repos", 0),
        "original_repos": analytics.get("original_repos", 0),
        "forked_repos": analytics.get("forked_repos", 0),
        "total_stars": analytics.get("total_stars", 0),
        "total_forks": analytics.get("total_forks", 0),
        "total_open_issues": analytics.get("total_open_issues", 0),
        "average_stars": analytics.get("average_stars", 0),
        "total_contributions": (contributions or {}).get("total_contributions", 0),
        "current_streak": streaks.get("current_streak", 0),
        "longest_streak": streaks.get("longest_streak", 0),
        "most_active_month": most_active_month,
        "most_active_month_label": _format_month(most_active_month),
        "most_active_month_count": most_active_month_count,
        "top_language": top_language,
        "top_languages": top_languages,
        "analytics_error": profile_data.get("analytics_error"),
        "contributions_error": profile_data.get("contributions_error"),
        "has_contributions": contributions is not None,
    }


def _display_value(summary, key):
    if key == "most_active_month_count":
        if summary["most_active_month_count"]:
            return (
                f"{summary['most_active_month_label']} "
                f"({summary['most_active_month_count']})"
            )
        return "—"
    if key == "average_stars":
        return summary.get(key, 0)
    return summary.get(key, 0)


def build_comparison_rows(left, right):
    rows = []
    for label, key, direction in COMPARE_METRICS:
        left_val = left.get(key, 0) or 0
        right_val = right.get(key, 0) or 0

        if left_val > right_val:
            winner = "left"
        elif right_val > left_val:
            winner = "right"
        else:
            winner = "tie"

        rows.append(
            {
                "label": label,
                "left_value": _display_value(left, key),
                "right_value": _display_value(right, key),
                "left_raw": left_val,
                "right_raw": right_val,
                "winner": winner,
            }
        )
    return rows


def count_wins(rows):
    left_wins = sum(1 for row in rows if row["winner"] == "left")
    right_wins = sum(1 for row in rows if row["winner"] == "right")
    return left_wins, right_wins
