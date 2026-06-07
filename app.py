import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

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
            result = load_profile_data(
                username,
                github_token=GITHUB_TOKEN,
                github_headers=_github_headers(),
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
        if cache_is_configured():
            saved, cache_error = save_profile_cache(username, result)
            if not saved:
                cache_warning = (
                    f"Results could not be saved to MongoDB. {cache_error} "
                    "Showing live data only."
                )

        return _render_profile(result, cache_warning=cache_warning)

    return render_template("index.html")


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
