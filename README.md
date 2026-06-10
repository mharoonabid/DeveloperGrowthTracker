# DeveloperGrowthTracker 🚀

A full-stack GitHub Developer Analytics Dashboard that showcases real-time repository analytics, language distribution visualizations, contribution insights, and user profile metrics.

**Live Demo:** [https://developergrowthtracker.onrender.com/](https://developergrowthtracker.onrender.com/)

---

## 📋 Features

- **GitHub Profile Metrics:** Real-time display of user profile details (avatar, bio, followers, following, public repositories, and organization affiliations).
- **Repository Analytics:** Aggregate stats across public repositories including total stars, forks, open issues, watchers, average stars per repository, and the user's most starred repository.
- **Language Distribution:** Detailed breakdown of programming languages used across public repositories, calculated in bytes and percentages, utilizing multi-threaded API fetching.
- **Contribution Graph:** Visual contribution calendar mapping weekly and monthly activity levels (requires a GitHub API Token).
- **Contribution Streaks:** Automatically computes and displays **Current Streak** 🔥 (consecutive days with ≥ 1 contribution, tolerating today with zero) and **Longest Streak** 🏆 (the all-time longest run of consecutive contribution days) with start/end dates, animated icons, and styled streak cards. Streak data is derived from the GitHub GraphQL contribution calendar.
- **TTL Caching:** MongoDB-backed cache that stores user profiles for a configurable duration (default: 6 hours) to minimize API requests and avoid GitHub rate limiting.
- **Robust Error Handling:** Detects invalid usernames, rate-limiting, and missing database configs, fallback gracefully to live fetching with clear UI warnings.
- **Premium Responsive Design:** Custom dark-themed layout built with vanilla CSS, subtle micro-animations, glassmorphism, responsive grid layouts, and support for all device sizes.

---

## 🛠️ Tech Stack & Technologies Used

- **Backend Framework:** [Flask 3.1.3](https://flask.palletsprojects.com/) (Python-based microframework)
- **WSGI Server:** [Gunicorn 23.0.0](https://gunicorn.org/) (for production deployment)
- **Database / Cache:** [MongoDB](https://www.mongodb.com/) (using [pymongo 4.17.0](https://pymongo.readthedocs.io/))
- **APIs Integrated:**
  - [GitHub REST API v3](https://docs.github.com/en/rest) (for user info, repositories, and language stats)
  - [GitHub GraphQL API v4](https://docs.github.com/en/graphql) (for contribution calendar data)
- **Frontend Technologies:**
  - Semantic HTML5 & Jinja2 Templates
  - Vanilla CSS3 (Custom styling, Flexbox/Grid layouts, Glassmorphism, animations)
  - Vanilla JavaScript (Dynamic loading states, error handling animations)
  - Icons: FontAwesome v6
  - Typography: Google Fonts (Inter)
- **Containerization:** Docker & Docker Compose
- **Hosting Platform:** Render

---

## 📁 Project Structure

```text
DeveloperGrowthTracker/
├── static/
│   ├── css/
│   │   └── style.css          # Main stylesheet containing layout, design tokens, and responsiveness
│   └── js/
│       └── loading.js         # JavaScript to trigger and handle application loading states
├── templates/
│   ├── base.html              # Base Jinja2 layout (includes HTML head, CSS/JS links, and structural container)
│   ├── index.html             # The landing page with the username search interface
│   ├── notFound.html          # Custom error page for when a GitHub user does not exist
│   └── profile.html           # Dashboard layout featuring analytics panels, charts, and graphs
├── app.py                     # Main Flask application serving endpoints and routing logic
├── github_analytics.py        # Logic for fetching repositories, language bytes, and contribution calendar
├── github_errors.py           # Custom exception handling wrappers for API-specific errors
├── mongodb_cache.py           # MongoDB connection pooling, caching operations, and TTL indexes management
├── profile_loader.py          # Orchestrates data loading by fetching and combining profile, repo, and GraphQL data
├── requirements.txt           # Python application package dependencies
├── render.yaml                # Render Infrastructure-as-Code (IaC) deployment configuration file
├── Dockerfile                 # Multi-stage Docker image definition
├── docker-compose.yml         # Local development orchestration with MongoDB service
├── .env.example               # Template file for environment variables configuration
├── .gitignore                 # Files and folders ignored by git
└── README.md                  # Project documentation (this file)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MongoDB (running locally or via MongoDB Atlas)
- GitHub Personal Access Token (PAT) (Optional but highly recommended to prevent rate limits and load contribution graphs)
- Docker & Docker Compose (Optional, for containerized run)

### Installation & Local Setup (Without Docker)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/DeveloperGrowthTracker.git
   cd DeveloperGrowthTracker
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Copy the example environment file and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   FLASK_DEBUG=True
   GITHUB_TOKEN=your_github_personal_access_token
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB_NAME=developer_growth_tracker
   CACHE_TTL_HOURS=6
   ```

5. **Run the application:**
   ```bash
   flask run
   ```
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

### Run with Docker Compose 🐳

To run the full stack (Flask + MongoDB) inside isolated Docker containers:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update the environment variables in `.env` (Set `MONGODB_URI=mongodb://mongodb:27017/` for internal docker networking).
3. Build and launch the containers:
   ```bash
   docker-compose up --build
   ```
4. Access the web app at [http://localhost:5000](http://localhost:5000).

---

## ☁️ Deployment on Render

This repository includes a `render.yaml` blueprint file for easy deployment on [Render](https://render.com/).

### Deployment Steps:
1. Connect your GitHub repository to Render.
2. Render will automatically parse the `render.yaml` file.
3. Configure the following **Environment Variables** in the Render Dashboard:
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token (for fetching user contributions and high rate limits).
   - `MONGODB_URI`: Your MongoDB Atlas connection string.
   - `MONGODB_DB_NAME`: The database name (defaults to `developer_growth_tracker`).
   - `CACHE_TTL_HOURS`: Cache expiration time in hours (defaults to `6`).
4. Click deploy and your app will be online.
