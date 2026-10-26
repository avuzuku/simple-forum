import os
import re
import html
import uuid
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'forum_secret_key_prod_dev')
DATABASE = 'forum.db'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.before_request
def check_valid_user():
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT id, is_admin, avatar FROM users WHERE id = ?',
                          (session['user_id'],)).fetchone()
        if not user:
            session.clear()
        else:
            session['is_admin'] = bool(user['is_admin'])
            session['avatar'] = user['avatar']

def save_media_file(file_storage):
    if not file_storage or file_storage.filename == '':
        return None, None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext in IMAGE_EXTENSIONS:
        media_type = 'image'
    elif ext in AUDIO_EXTENSIONS:
        media_type = 'audio'
    else:
        return None, None
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return filename, media_type

def add_notification(user_id, text, link):
    if 'user_id' in session and session['user_id'] == user_id:
        return
    db = get_db()
    db.execute('INSERT INTO notifications (user_id, text, link) VALUES (?, ?, ?)',
               (user_id, text, link))
    db.commit()

@app.template_filter('format_content')
def format_content(text):
    if not text:
        return ''
    escaped = html.escape(text)
    escaped = re.sub(r'\[spoiler\](.*?)\[/spoiler\]', r'<span class="spoiler">\1</span>', escaped, flags=re.DOTALL)
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'\*(.*?)\*', r'<em>\1</em>', escaped)
    lines = escaped.split('\n')
    processed = []
    for line in lines:
        if line.startswith('&gt; '):
            processed.append(f'<div class="quote-block">{line[5:]}</div>')
        else:
            processed.append(line)
    return Markup('<br>'.join(processed))

@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        db = get_db()
        count = db.execute('SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0',
                           (session['user_id'],)).fetchone()['c']
        return dict(unread_notifications=count)
    return dict(unread_notifications=0)

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                avatar TEXT DEFAULT NULL,
                bio TEXT DEFAULT '',
                custom_status TEXT DEFAULT '',
                is_private INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                is_pinned INTEGER DEFAULT 0,
                is_locked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                media_file TEXT DEFAULT NULL,
                media_type TEXT DEFAULT NULL,
                is_edited INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS topic_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role_name TEXT NOT NULL,
                UNIQUE(topic_id, user_id),
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER UNIQUE NOT NULL,
                question TEXT NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS poll_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(poll_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES poll_options (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                link TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                UNIQUE(user_id, post_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            );
        ''')
        default_categories = [
            ('Главное', 'main'),
            ('Игры', 'games'),
            ('Железо и Софт', 'tech'),
            ('Музыка и Кино', 'media'),
            ('Флудилка', 'flood')
        ]
        for name, slug in default_categories:
            db.execute('INSERT OR IGNORE INTO categories (name, slug) VALUES (?, ?)', (name, slug))
        db.commit()

@app.route('/')
def index():
    db = get_db()
    cat_slug = request.args.get('category')
    search_query = request.args.get('q', '').strip()

    if cat_slug:
        category = db.execute('SELECT * FROM categories WHERE slug = ?', (cat_slug,)).fetchone()
        if not category:
            return abort(404)

        sql = '''
            SELECT t.id, t.title, t.is_pinned, t.is_locked, t.created_at, t.author_id,
                   u.username as author, u.avatar,
                   COUNT(p.id) as reply_count
            FROM topics t
            JOIN users u ON t.author_id = u.id
            LEFT JOIN posts p ON t.id = p.topic_id
            WHERE t.category_id = ?
        '''
        params = [category['id']]

        if search_query:
            sql += ' AND (t.title LIKE ? OR u.username LIKE ?)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])

        sql += ' GROUP BY t.id ORDER BY t.is_pinned DESC, t.created_at DESC'
        topics = db.execute(sql, params).fetchall()

        return render_template('index.html', category=category, topics=topics, search_query=search_query)

    categories = db.execute('''
        SELECT c.*, COUNT(t.id) as topic_count
        FROM categories c
        LEFT JOIN topics t ON c.id = t.category_id
        GROUP BY c.id
    ''').fetchall()

    return render_template('index.html', categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('register.html', error='Заполните поля')

        db = get_db()
        exists = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if exists:
            return render_template('register.html', error='Имя занято')

        user_count = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        is_admin = 1 if user_count == 0 else 0

        hashed = generate_password_hash(password)
        db.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                   (username, hashed, is_admin))
        db.commit()

        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = bool(user['is_admin'])
        session['avatar'] = user['avatar']

        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            session['avatar'] = user['avatar']
            return redirect(url_for('index'))

        return render_template('login.html', error='Неверные данные')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 50
    ''', (session['user_id'],)).fetchall()
    db.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (session['user_id'],))
    db.commit()
    return render_template('notifications.html', notifications=items)

@app.route('/profile/<username>')
def profile(username):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        return abort(404)

    is_self = session.get('user_id') == user['id']
    is_admin = session.get('is_admin')
    is_authorized = 'user_id' in session

    if user['is_private'] and not is_self and not is_admin and not is_authorized:
        return render_template('profile.html', user=user, restricted=True)

    topics_count = db.execute('SELECT COUNT(*) as count FROM topics WHERE author_id = ?', (user['id'],)).fetchone()['count']
    posts_count = db.execute('SELECT COUNT(*) as count FROM posts WHERE author_id = ?', (user['id'],)).fetchone()['count']

    return render_template('profile.html', user=user, topics_count=topics_count, posts_count=posts_count, restricted=False)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()
        custom_status = request.form.get('custom_status', '').strip()
        is_private = 1 if request.form.get('is_private') else 0
        file = request.files.get('avatar')

        avatar_name = user['avatar']
        if file and file.filename != '':
            new_avatar, media_type = save_media_file(file)
            if media_type == 'image':
                avatar_name = new_avatar
                session['avatar'] = avatar_name

        db.execute('''
            UPDATE users 
            SET bio = ?, custom_status = ?, is_private = ?, avatar = ? 
            WHERE id = ?
        ''', (bio, custom_status, is_private, avatar_name, session['user_id']))
        db.commit()
        return redirect(url_for('profile', username=session['username']))

    return render_template('settings.html', user=user)

@app.route('/create_topic', methods=['POST'])
def create_topic():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title', '').strip()
    category_id = request.form.get('category_id')
    content = request.form.get('content', '').strip()
    file = request.files.get('attachment')
    poll_question = request.form.get('poll_question', '').strip()
    poll_options_raw = request.form.get('poll_options', '').strip()

    media_file, media_type = save_media_file(file)

    if title and content and category_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO topics (title, category_id, author_id) 
            VALUES (?, ?, ?)
        ''', (title, category_id, session['user_id']))
        topic_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO posts (topic_id, author_id, content, media_file, media_type) 
            VALUES (?, ?, ?, ?, ?)
        ''', (topic_id, session['user_id'], content, media_file, media_type))

        if poll_question and poll_options_raw:
            options = [opt.strip() for opt in poll_options_raw.split('\n') if opt.strip()]
            if len(options) >= 2:
                cursor.execute('INSERT INTO polls (topic_id, question) VALUES (?, ?)',
                               (topic_id, poll_question))
                poll_id = cursor.lastrowid
                for opt in options:
                    cursor.execute('INSERT INTO poll_options (poll_id, text) VALUES (?, ?)',
                                   (poll_id, opt))

        db.commit()
        return redirect(url_for('topic', topic_id=topic_id))

    return redirect(url_for('index'))

@app.route('/topic/<int:topic_id>')
def topic(topic_id):
    db = get_db()
    t = db.execute('''
        SELECT t.*, c.name as category_name, c.slug as category_slug, u.username as author 
        FROM topics t 
        JOIN categories c ON t.category_id = c.id
        JOIN users u ON t.author_id = u.id 
        WHERE t.id = ?
    ''', (topic_id,)).fetchone()

    if not t:
        return abort(404)

    current_uid = session.get('user_id', 0)

    topic_roles_raw = db.execute('''
        SELECT user_id, role_name FROM topic_roles WHERE topic_id = ?
    ''', (topic_id,)).fetchall()
    topic_roles = {r['user_id']: r['role_name'] for r in topic_roles_raw}

    poll = db.execute('SELECT * FROM polls WHERE topic_id = ?', (topic_id,)).fetchone()
    poll_options = []
    user_voted_option_id = None
    total_votes = 0

    if poll:
        poll_id = poll['id']
        total_votes = db.execute('SELECT COUNT(*) as c FROM poll_votes WHERE poll_id = ?', (poll_id,)).fetchone()['c']
        raw_options = db.execute('''
            SELECT po.id, po.text,
                   (SELECT COUNT(*) FROM poll_votes WHERE option_id = po.id) as vote_count
            FROM poll_options po
            WHERE po.poll_id = ?
        ''', (poll_id,)).fetchall()

        if current_uid:
            voted = db.execute('SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?',
                               (poll_id, current_uid)).fetchone()
            if voted:
                user_voted_option_id = voted['option_id']

        for opt in raw_options:
            percent = (opt['vote_count'] / total_votes * 100) if total_votes > 0 else 0
            poll_options.append({
                'id': opt['id'],
                'text': opt['text'],
                'vote_count': opt['vote_count'],
                'percent': round(percent, 1)
            })

    posts = db.execute('''
        SELECT p.*, u.username as author, u.avatar, u.custom_status, u.is_admin as author_is_admin,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id AND user_id = ?) as user_liked
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.topic_id = ? 
        ORDER BY p.created_at ASC
    ''', (current_uid, topic_id)).fetchall()

    all_users = []
    if session.get('is_admin') or (current_uid and current_uid == t['author_id']):
        all_users = db.execute('SELECT id, username FROM users ORDER BY username ASC').fetchall()

    return render_template('topic.html', topic=t, posts=posts, poll=poll,
                           poll_options=poll_options, total_votes=total_votes,
                           user_voted_option_id=user_voted_option_id,
                           topic_roles=topic_roles, all_users=all_users)

@app.route('/topic/<int:topic_id>/reply', methods=['POST'])
def reply(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    t = db.execute('SELECT * FROM topics WHERE id = ?', (topic_id,)).fetchone()
    if not t:
        return abort(404)
    if t['is_locked'] and not session.get('is_admin'):
        return abort(403)

    content = request.form.get('content', '').strip()
    file = request.files.get('attachment')
    media_file, media_type = save_media_file(file)

    if content or media_file:
        db.execute('''
            INSERT INTO posts (topic_id, author_id, content, media_file, media_type) 
            VALUES (?, ?, ?, ?, ?)
        ''', (topic_id, session['user_id'], content, media_file, media_type))
        db.commit()

        add_notification(
            t['author_id'],
            f"Пользователь {session['username']} оставил ответ в вашей теме «{t['title']}»",
            url_for('topic', topic_id=topic_id)
        )

    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        return abort(404)

    is_author = session.get('user_id') == post['author_id']
    is_admin = session.get('is_admin')

    if not is_author and not is_admin:
        return abort(403)

    if request.method == 'POST':
        new_content = request.form.get('content', '').strip()
        if new_content:
            db.execute('UPDATE posts SET content = ?, is_edited = 1 WHERE id = ?',
                       (new_content, post_id))
            db.commit()
            return redirect(url_for('topic', topic_id=post['topic_id']))

    return render_template('edit_post.html', post=post)

@app.route('/topic/<int:topic_id>/poll_vote', methods=['POST'])
def poll_vote(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    raw_option_id = request.form.get('option_id')
    db = get_db()
    poll = db.execute('SELECT id FROM polls WHERE topic_id = ?', (topic_id,)).fetchone()

    if poll and raw_option_id:
        try:
            option_id = int(raw_option_id)
            user_id = int(session['user_id'])
            db.execute('''
                INSERT OR IGNORE INTO poll_votes (poll_id, option_id, user_id) 
                VALUES (?, ?, ?)
            ''', (poll['id'], option_id, user_id))
            db.commit()
        except (ValueError, TypeError):
            pass

    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/topic/<int:topic_id>/assign_role', methods=['POST'])
def assign_topic_role(topic_id):
    if 'user_id' not in session:
        return abort(403)

    db = get_db()
    t = db.execute('SELECT author_id FROM topics WHERE id = ?', (topic_id,)).fetchone()
    if not t:
        return abort(404)

    if not session.get('is_admin') and session.get('user_id') != t['author_id']:
        return abort(403)

    target_user_id = request.form.get('user_id')
    role_name = request.form.get('role_name', '').strip()

    if target_user_id and role_name:
        db.execute('''
            INSERT INTO topic_roles (topic_id, user_id, role_name) 
            VALUES (?, ?, ?) 
            ON CONFLICT(topic_id, user_id) DO UPDATE SET role_name = excluded.role_name
        ''', (topic_id, target_user_id, role_name))
        db.commit()
    elif target_user_id and not role_name:
        db.execute('DELETE FROM topic_roles WHERE topic_id = ? AND user_id = ?',
                   (topic_id, target_user_id))
        db.commit()

    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/topic/<int:topic_id>/lock', methods=['POST'])
def toggle_lock_topic(topic_id):
    if 'user_id' not in session:
        return abort(403)

    db = get_db()
    t = db.execute('SELECT author_id, is_locked FROM topics WHERE id = ?', (topic_id,)).fetchone()
    if not t:
        return abort(404)

    if not session.get('is_admin') and session.get('user_id') != t['author_id']:
        return abort(403)

    db.execute('UPDATE topics SET is_locked = 1 - is_locked WHERE id = ?', (topic_id,))
    db.commit()
    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/post/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    existing = db.execute('SELECT id FROM likes WHERE user_id = ? AND post_id = ?',
                          (session['user_id'], post_id)).fetchone()

    post = db.execute('SELECT topic_id, author_id FROM posts WHERE id = ?', (post_id,)).fetchone()

    if existing:
        db.execute('DELETE FROM likes WHERE id = ?', (existing['id'],))
    else:
        db.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)',
                   (session['user_id'], post_id))
        if post:
            add_notification(
                post['author_id'],
                f"Пользователю {session['username']} понравился ваш ответ.",
                url_for('topic', topic_id=post['topic_id'])
            )
    db.commit()

    return redirect(url_for('topic', topic_id=post['topic_id']))

@app.route('/topic/<int:topic_id>/pin', methods=['POST'])
def pin_topic(topic_id):
    if not session.get('is_admin'):
        return abort(403)
    db = get_db()
    db.execute('UPDATE topics SET is_pinned = 1 - is_pinned WHERE id = ?', (topic_id,))
    db.commit()
    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/topic/<int:topic_id>/delete', methods=['POST'])
def delete_topic(topic_id):
    if 'user_id' not in session:
        return abort(403)

    db = get_db()
    topic = db.execute('''
        SELECT t.author_id, c.slug as category_slug 
        FROM topics t 
        JOIN categories c ON t.category_id = c.id 
        WHERE t.id = ?
    ''', (topic_id,)).fetchone()

    if not topic:
        return abort(404)

    if session.get('is_admin') or session.get('user_id') == topic['author_id']:
        cat_slug = topic['category_slug']
        db.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
        db.commit()
        return redirect(url_for('index', category=cat_slug))

    return abort(403)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return abort(403)

    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        return abort(404)

    topic_id = post['topic_id']
    topic = db.execute('''
        SELECT t.author_id, c.slug as category_slug 
        FROM topics t 
        JOIN categories c ON t.category_id = c.id 
        WHERE t.id = ?
    ''', (topic_id,)).fetchone()

    is_topic_author = bool(topic and session.get('user_id') == topic['author_id'])

    if session.get('is_admin') or session.get('user_id') == post['author_id'] or is_topic_author:
        db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        db.commit()

        remaining = db.execute('SELECT COUNT(*) as c FROM posts WHERE topic_id = ?', (topic_id,)).fetchone()['c']
        if remaining == 0:
            cat_slug = topic['category_slug']
            db.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
            db.commit()
            return redirect(url_for('index', category=cat_slug))

        return redirect(url_for('topic', topic_id=topic_id))

    return abort(403)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)