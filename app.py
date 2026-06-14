import os
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

from compare_builder import (
    build_compare_summary,
    build_comparison_rows,
    count_wins,
)
from mongodb_cache import (
    format_cached_at,
    get_cached_profile,
    is_configured as cache_is_configured,
    save_profile_cache,
    test_connection,
)
from profile_loader import load_profile_data

load_dotenv()

app = Flask(__name__)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@app.route("/health/db")
def health_db():
    if not cache_is_configured():
        return {"mongodb": "not_configured", "detail": "MONGODB_URI is missing from .env"}, 503

    ok, detail = test_connection()
    status = 200 if ok else 503
    return {"mongodb": "ok" if ok else "error", "detail": detail}, status


def _github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _render_profile(profile_data, from_cache=False, cached_at=None, cache_warning=None):
    warnings = list(profile_data.get("warnings", []))
    if cache_warning:
        warnings.insert(0, cache_warning)

    return render_template(
        "profile.html",
        user=profile_data["user"],
        analytics=profile_data.get("analytics"),
        analytics_error=profile_data.get("analytics_error"),
        contributions=profile_data.get("contributions"),
        contributions_error=profile_data.get("contributions_error"),
        warnings=warnings,
        from_cache=from_cache,
        cached_at=format_cached_at(cached_at) if cached_at else None,
    )


def _load_profile_with_cache(username, force_refresh=False):
    if cache_is_configured() and not force_refresh:
        cached = get_cached_profile(username)
        if cached:
            return cached, True, None

    result = load_profile_data(
        username,
        github_token=GITHUB_TOKEN,
        github_headers=_github_headers(),
    )

    cache_error = None
    if (
        cache_is_configured()
        and not result.get("not_found")
        and not result.get("api_error")
    ):
        saved, cache_error = save_profile_cache(username, result)
        if saved:
            cache_error = None

    return result, False, cache_error


def _load_compare_profile(username):
    try:
        result, _, cache_error = _load_profile_with_cache(username)
        return username, result, cache_error
    except requests.RequestException as exc:
        return username, {"api_error": f"Could not reach GitHub: {exc}"}, None


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form["username"].strip()
        force_refresh = request.form.get("refresh") == "1"

        if not username:
            return render_template(
                "index.html",
                api_error="Please enter a GitHub username.",
            )

        if cache_is_configured() and not force_refresh:
            cached = get_cached_profile(username)
            if cached:
                return _render_profile(
                    cached,
                    from_cache=True,
                    cached_at=cached["cached_at"],
                )

        try:
            result, from_cache, cache_error = _load_profile_with_cache(
                username, force_refresh=force_refresh
            )
        except requests.RequestException as exc:
            return render_template(
                "index.html",
                api_error=f"Could not reach GitHub: {exc}",
            )

        if result.get("not_found"):
            return render_template("notFound.html", user=result["username"])

        if result.get("api_error"):
            return render_template("index.html", api_error=result["api_error"])

        cache_warning = None
        if cache_error:
            cache_warning = (
                f"Results could not be saved to MongoDB. {cache_error} "
                "Showing live data only."
            )

        return _render_profile(
            result,
            from_cache=from_cache,
            cached_at=result.get("cached_at") if from_cache else None,
            cache_warning=cache_warning,
        )

    return render_template("index.html")


@app.route("/compare", methods=["GET", "POST"])
def compare():
    if request.method == "GET":
        return render_template("compare.html")

    username1 = request.form.get("username1", "").strip()
    username2 = request.form.get("username2", "").strip()

    if not username1 or not username2:
        return render_template(
            "compare.html",
            api_error="Please enter both GitHub usernames.",
            username1=username1,
            username2=username2,
        )

    if username1.lower() == username2.lower():
        return render_template(
            "compare.html",
            api_error="Enter two different usernames to compare.",
            username1=username1,
            username2=username2,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(_load_compare_profile, username1)
        future2 = executor.submit(_load_compare_profile, username2)
        _, result1, cache_error1 = future1.result()
        _, result2, cache_error2 = future2.result()

    if result1.get("not_found"):
        return render_template(
            "compare.html",
            api_error=f"User '{username1}' was not found on GitHub.",
            username1=username1,
            username2=username2,
        )

    if result2.get("not_found"):
        return render_template(
            "compare.html",
            api_error=f"User '{username2}' was not found on GitHub.",
            username1=username1,
            username2=username2,
        )

    if result1.get("api_error"):
        return render_template(
            "compare.html",
            api_error=result1["api_error"],
            username1=username1,
            username2=username2,
        )

    if result2.get("api_error"):
        return render_template(
            "compare.html",
            api_error=result2["api_error"],
            username1=username1,
            username2=username2,
        )

    left = build_compare_summary(result1)
    right = build_compare_summary(result2)
    comparison_rows = build_comparison_rows(left, right)
    left_wins, right_wins = count_wins(comparison_rows)

    warnings = []
    warnings.extend(result1.get("warnings", []))
    warnings.extend(result2.get("warnings", []))
    for cache_error in (cache_error1, cache_error2):
        if cache_error:
            warnings.append(f"MongoDB: {cache_error}")

    return render_template(
        "compare.html",
        username1=username1,
        username2=username2,
        left=left,
        right=right,
        comparison_rows=comparison_rows,
        left_wins=left_wins,
        right_wins=right_wins,
        warnings=warnings,
    )


if __name__ == "__main__":
    if cache_is_configured():
        ok, detail = test_connection()
        if ok:
            print(f"MongoDB: {detail}")
        else:
            print(f"MongoDB WARNING: {detail}")
    else:
        print("MongoDB: not configured (MONGODB_URI missing from .env)")

    app.run(debug=True)
