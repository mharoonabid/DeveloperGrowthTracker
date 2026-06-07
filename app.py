import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

from github_analytics import (
    compute_language_usage_by_bytes,
    compute_repo_analytics,
    fetch_all_repos,
    fetch_contribution_graph,
)

load_dotenv()

app = Flask(__name__)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form["username"].strip()
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        res = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
            timeout=30,
        )
        user = res.json()

        if res.status_code != 200:
            return render_template("notFound.html", user=username)

        analytics = None
        analytics_error = None
        contributions = None
        contributions_error = None

        try:
            repos = fetch_all_repos(username, token=GITHUB_TOKEN)
            analytics = compute_repo_analytics(repos)
            analytics["language_bytes"] = compute_language_usage_by_bytes(
                repos, token=GITHUB_TOKEN
            )
        except requests.RequestException as exc:
            analytics_error = str(exc)

        if GITHUB_TOKEN:
            try:
                contributions = fetch_contribution_graph(username, GITHUB_TOKEN)
            except (requests.RequestException, ValueError) as exc:
                contributions_error = str(exc)
        else:
            contributions_error = (
                "Set GITHUB_TOKEN in .env to load contribution data."
            )

        return render_template(
            "profile.html",
            user=user,
            analytics=analytics,
            analytics_error=analytics_error,
            contributions=contributions,
            contributions_error=contributions_error,
        )

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
