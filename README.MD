# Simple Web Forum

A feature-rich web forum application built with Python (Flask) and SQLite, featuring a modern dark interface.

> **Note:** This is an educational project created for learning purposes. The user interface and localization are in Russian.

## Features

- **Authentication & Roles:**
  - Secure registration and login using salted password hashing (`Werkzeug`).
  - Automatic Administrator status for the first registered user.
- **Profiles & Customization:**
  - Custom avatar upload.
  - User bio ("About me") section.
  - User statistics (total topics and posts count).
  - Privacy toggle: option to hide profile details from guests (unregistered visitors).
- **Multimedia & Attachments:**
  - Support for image attachments (`png`, `jpg`, `jpeg`, `gif`, `webp`).
  - Audio playback support for attached audio files (`mp3`, `wav`, `ogg`, `m4a`).
- **Interactions & Moderation:**
  - Post reaction system (likes).
  - Pinned topics (admin action).
  - Authors can delete their own topics and posts; administrators can moderate any content.
- **Database:** Zero-configuration local storage with SQLite and foreign key constraints enabled.

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite3
- **Frontend:** HTML5, CSS3 (Dark theme, Jinja2 templates)

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

1. Clone this repository:
```bash
git clone https://github.com/avuzuku/simple-forum.git
cd simple-forum
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