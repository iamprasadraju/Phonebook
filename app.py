from flask import Flask, redirect, render_template, request, url_for, flash, g
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import logging

# Configure app
app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.urandom(24)  # Use a randomly generated key
Session(app)

# Configure Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    g.cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = g.cursor.fetchone()
    if user_data:
        user = User(id=user_data[0], username=user_data[1], password=user_data[2])
        return user
    return None

@app.before_request
def before_request():
    g.db = mysql.connector.connect(
        host="",
        user="",
        password="",
        database=""
    )
    g.cursor = g.db.cursor()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {e}")
    flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        g.cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = g.cursor.fetchone()

        if user_data:
            user = User(id=user_data[0], username=user_data[1], password=user_data[2])
            if check_password_hash(user.password, password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/new')
@login_required
def new():
    return render_template('create.html')

@app.route('/create', methods=["POST"])
@login_required
def create():
    contact_name = request.form.get("contact_name")
    contact_number = request.form.get("contact_number")
    user_id = current_user.id

    g.cursor.execute("SELECT * FROM contacts WHERE user_id = %s AND (contact_name = %s OR contact_number = %s)", (user_id, contact_name, contact_number))
    existing_contacts = g.cursor.fetchall()

    if not existing_contacts:
        g.cursor.execute("INSERT INTO contacts (contact_name, contact_number, user_id) VALUES (%s, %s, %s)", (contact_name, contact_number, user_id))
        g.db.commit()
        flash('Contact Added Successfully', 'success')
    else:
        flash('Contact Already Exists', 'error')

    return redirect(url_for('index'))

@app.route('/view', methods=['GET', 'POST'])
@login_required
def view():
    user_id = current_user.id
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    try:
        query = """
        SELECT * FROM contacts
        WHERE user_id = %s AND (contact_name LIKE %s OR contact_number LIKE %s)
        ORDER BY contact_name LIMIT %s OFFSET %s
        """
        g.cursor.execute(query, (user_id, f'%{search_query}%', f'%{search_query}%', per_page, (page - 1) * per_page))
        all_contacts = g.cursor.fetchall()

        g.cursor.execute("SELECT COUNT(*) AS count FROM contacts WHERE user_id = %s AND (contact_name LIKE %s OR contact_number LIKE %s)", (user_id, f'%{search_query}%', f'%{search_query}%'))
        total_contacts = g.cursor.fetchone()
        total_pages = (total_contacts[0] + per_page - 1) // per_page

        return render_template('view.html', all_contacts=all_contacts, search_query=search_query, current_page=page, total_pages=total_pages)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(url_for('index'))

@app.route('/delete/<int:contact_id>', methods=['POST'])
@login_required
def delete(contact_id):
    user_id = current_user.id
    g.cursor.execute("DELETE FROM contacts WHERE id = %s AND user_id = %s", (contact_id, user_id))
    g.db.commit()

    if g.cursor.rowcount > 0:
        flash('Contact deleted successfully!', 'success')
    else:
        flash('Failed to delete contact or contact does not exist!', 'error')

    return redirect(url_for('view'))

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == 'POST':
        username = request.form.get("username")
        password_1 = request.form.get("password")
        password_2 = request.form.get("confirm_password")
        g.cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if g.cursor.fetchone():
            flash('Username Already Exists', 'error')
        elif password_1 == password_2:
            hashed_password = generate_password_hash(password_1, method='pbkdf2:sha256')
            g.cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            g.db.commit()
            flash('Account Created Successfully', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match, please try again.', 'error')

    return render_template('signup.html')

@app.route('/edit/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit(contact_id):
    user_id = current_user.id
    g.cursor.execute("SELECT * FROM contacts WHERE id = %s AND user_id = %s", (contact_id, user_id))
    contact = g.cursor.fetchone()

    if request.method == 'POST':
        new_name = request.form.get('contact_name')
        new_number = request.form.get('contact_number')
        g.cursor.execute("UPDATE contacts SET contact_name = %s, contact_number = %s WHERE id = %s AND user_id = %s", (new_name, new_number, contact_id, user_id))
        g.db.commit()
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('view'))

    return render_template('edit.html', contact=contact)

if __name__ == "__main__":
    app.run(debug=True)
