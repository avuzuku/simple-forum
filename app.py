import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_default_key_123')
DATABASE = 'forum.db'

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

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            );
        ''')
        db.commit()

@app.route('/')
def index():
    db = get_db()
    topics = db.execute('''
        SELECT t.id, t.title, t.created_at, t.author_id, u.username as author,
               COUNT(p.id) as reply_count
        FROM topics t
        JOIN users u ON t.author_id = u.id
        LEFT JOIN posts p ON t.id = p.topic_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    ''').fetchall()
    return render_template('index.html', topics=topics)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('register.html', error='Заполните все поля')

        db = get_db()
        exists = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if exists:
            return render_template('register.html', error='Пользователь уже существует')

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
            return redirect(url_for('index'))

        return render_template('login.html', error='Неверный логин или пароль')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/create_topic', methods=['POST'])
def create_topic():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if title and content:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO topics (title, author_id) VALUES (?, ?)',
                       (title, session['user_id']))
        topic_id = cursor.lastrowid
        cursor.execute('INSERT INTO posts (topic_id, author_id, content) VALUES (?, ?, ?)',
                       (topic_id, session['user_id'], content))
        db.commit()
        return redirect(url_for('topic', topic_id=topic_id))

    return redirect(url_for('index'))

@app.route('/topic/<int:topic_id>')
def topic(topic_id):
    db = get_db()
    t = db.execute('''
        SELECT t.*, u.username as author 
        FROM topics t 
        JOIN users u ON t.author_id = u.id 
        WHERE t.id = ?
    ''', (topic_id,)).fetchone()

    if not t:
        return abort(404)

    posts = db.execute('''
        SELECT p.*, u.username as author, u.is_admin as author_is_admin 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.topic_id = ? 
        ORDER BY p.created_at ASC
    ''', (topic_id,)).fetchall()

    return render_template('topic.html', topic=t, posts=posts)

@app.route('/topic/<int:topic_id>/reply', methods=['POST'])
def reply(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form.get('content', '').strip()
    if content:
        db = get_db()
        db.execute('INSERT INTO posts (topic_id, author_id, content) VALUES (?, ?, ?)',
                   (topic_id, session['user_id'], content))
        db.commit()

    return redirect(url_for('topic', topic_id=topic_id))

@app.route('/topic/<int:topic_id>/delete', methods=['POST'])
def delete_topic(topic_id):
    if 'user_id' not in session:
        return abort(403)

    db = get_db()
    topic = db.execute('SELECT author_id FROM topics WHERE id = ?', (topic_id,)).fetchone()
    if not topic:
        return abort(404)

    if session.get('is_admin') or session.get('user_id') == topic['author_id']:
        db.execute('DELETE FROM posts WHERE topic_id = ?', (topic_id,))
        db.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
        db.commit()
        return redirect(url_for('index'))

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
    if session.get('is_admin') or session.get('user_id') == post['author_id']:
        db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        db.commit()

        remaining_posts = db.execute('SELECT COUNT(*) as count FROM posts WHERE topic_id = ?', (topic_id,)).fetchone()['count']
        if remaining_posts == 0:
            db.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
            db.commit()
            return redirect(url_for('index'))

        return redirect(url_for('topic', topic_id=topic_id))

    return abort(403)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
