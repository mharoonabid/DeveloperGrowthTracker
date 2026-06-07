from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def home():

    if request.method == "POST":
        username = request.form["username"]
        res = requests.get(f"https://api.github.com/users/{username}")
        user = res.json()

        if res.status_code != 200:
             return render_template("notFound.html", user=username)

        return render_template("profile.html", user=user)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
