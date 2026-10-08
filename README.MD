# Simple Web Forum

A lightweight web forum application built with Python (Flask) and SQLite.

> **Note:** This is an educational project created for learning purposes. The user interface and localization are currently in Russian.

## Features

- **Authentication:** User registration and login with secure password hashing (`Werkzeug`).
- **Role System:**
  - The first registered user automatically receives Administrator privileges.
  - Regular users can manage only their own topics and posts.
  - Administrators can delete any topic or post.
- **Topics & Posts:** Create discussion threads, write replies, and manage discussions.
- **Database:** Zero-configuration local database using SQLite.

## Tech Stack

- Python 3, Flask
- SQLite
- HTML5, CSS3 (Jinja2)

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

1. Clone this repository:
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install flask
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```text
http://127.0.0.1:5000
```