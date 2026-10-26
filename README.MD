# Simple Web Forum

A full-featured web forum application built with Python (Flask) and SQLite, featuring a modern dark UI, section-based discussions, multimedia attachments, and in-depth moderation tools.

> **Note:** This is an educational project created for learning purposes. The user interface and localization are in Russian.

## Features

### Categories & Navigation
- **Section-Based Structure:** Discussion threads are organized into distinct categories (Main, Games, Tech, Media, Off-topic).
- **Welcome Dashboard:** The root page displays active categories, topic counters, and an overview before diving into specific sections.
- **Search:** Search topics and authors within sections.
- **Global Navigation Bar:** Fast access to notifications, profile, settings, and authentication from any page.

### Discussions & Formatting
- **Rich Post Formatting:** Supports bold (`**bold**`), italics (`*italic*`), spoilers (`[spoiler]text[/spoiler]`), and quotes (`> quote`).
- **Interactive Quoting:** One-click quoting that automatically quotes a user's post into the reply editor.
- **Post Editing:** Authors and administrators can edit existing posts with an automatic `(изменено)` status indicator.
- **Multimedia Attachments:**
  - Image attachments (`png`, `jpg`, `jpeg`, `gif`, `webp`) with inline image display.
  - Audio attachments (`mp3`, `wav`, `ogg`, `m4a`) with a native HTML5 audio player.

### Polls & Engagement
- **Interactive Polls:** Attach multi-option polls to threads with live vote percentage bars and vote counters.
- **Post Reactions:** Like system with like counters on every message.
- **Notification System:** In-app notification center alerting users when their posts are liked or their threads receive replies.

### Moderation & Roles
- **Hierarchical Access:**
  - The first registered user automatically becomes a global Administrator.
  - Topic creators have moderation permissions in their own threads (delete any post, lock/unlock the thread).
  - Administrators have global moderation rights (pin/unpin topics, delete/lock any thread, edit/remove any post).
- **Topic-Level Roles:** Topic owners and admins can assign custom role badges to participants inside specific threads (e.g., "Куратор", "Спикер", "Эксперт").

### User Profiles & Privacy
- **Profile Customization:** Upload custom avatars, set a bio, and define a custom status text shown next to your username.
- **Activity Stats:** View registered date, total topics created, and total messages sent.
- **Privacy Controls:** Option to hide profile details from guests (unregistered visitors).

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite3 (with foreign key constraints enabled)
- **Frontend:** HTML5, CSS3 (Custom Dark Theme), Jinja2 templates
- **Security:** Salted password hashing (`werkzeug.security`), session validation against active database records

## Project Structure

```text
mini_forum/
│
├── app.py                  # Application logic, database models, and routes
├── forum.db                # SQLite database (auto-generated on launch)
├── static/
│   ├── style.css           # Global stylesheet
│   └── uploads/            # Uploaded avatars, images, and audio files
└── templates/
    ├── index.html          # Welcome screen and category topic lists
    ├── topic.html          # Thread view, replies, polls, and thread moderation
    ├── profile.html        # User profile view
    ├── settings.html       # Profile and privacy settings
    ├── notifications.html  # In-app notifications center
    ├── edit_post.html      # Message editing form
    ├── login.html          # Authentication
    └── register.html       # User registration
```

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

1. Clone the repository:
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