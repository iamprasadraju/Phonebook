from cs50 import SQL
from flask import Flask, redirect, render_template, request, url_for, flash
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
# Configure app
app = Flask(__name__)

# Connect to database
db = SQL("sqlite:///database.db")

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
    user_data = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    if user_data:
        user = user_data[0]
        return User(id=user["id"], username=user["username"], password=user["password"])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = db.execute("SELECT * FROM users WHERE username = ?", username)
        
        if user_data:
            user = user_data[0]
            if check_password_hash(user['password'], password):
                user_obj = User(id=user["id"], username=user["username"], password=user["password"])
                login_user(user_obj)
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
    contact_num = request.form.get("contact_number")
    user_id = current_user.id

    existing_contacts = db.execute("SELECT * FROM contacts WHERE user_id = ? AND (contact_name = ? OR contact_number = ?)", user_id, contact_name, contact_num)
    
    # Check if the contact already exists
    if not existing_contacts:
        db.execute("INSERT INTO contacts (contact_name, contact_number, user_id) VALUES (?, ?, ?)", contact_name, contact_num, user_id)
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

    query = """
    SELECT * FROM contacts
    WHERE user_id = ? AND (contact_name LIKE ? OR contact_number LIKE ?)
    ORDER BY contact_name
    LIMIT ? OFFSET ?
    """
    all_contacts = db.execute(query, user_id, f'%{search_query}%', f'%{search_query}%', per_page, (page - 1) * per_page)
    logging.debug(f"All contacts: {all_contacts}")

    total_contacts = db.execute("SELECT COUNT(*) AS count FROM contacts WHERE user_id = ? AND (contact_name LIKE ? OR contact_number LIKE ?)", user_id, f'%{search_query}%', f'%{search_query}%')
    logging.debug(f"Total contacts: {total_contacts}")

    if total_contacts:
        total_pages = (total_contacts[0]['count'] + per_page - 1) // per_page
    else:
        total_pages = 1  # Default to 1 if no contacts are found

    return render_template('view.html', all_contacts=all_contacts, search_query=search_query, current_page=page, total_pages=total_pages)

@app.route('/delete/<int:contact_id>', methods=['POST'])
@login_required
def delete(contact_id):
    user_id = current_user.id
    result = db.execute("DELETE FROM contacts WHERE id = ? AND user_id = ?", contact_id, user_id)
    
    if result.rowcount > 0:  # Check if any rows were affected
        flash('Contact deleted successfully!', 'success')
    else:
        flash('Failed to delete contact or contact does not exist!', 'error')
    
    return redirect(url_for('view'))

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup_process', methods=['POST'])
def signup_process():
    # Get form data
    username = request.form.get("username")
    password_1 = request.form.get("password_1")
    password_2 = request.form.get("password_2")
    
    # Basic validation
    if not username or not password_1 or not password_2:
        flash('All fields are required.', 'error')
        return redirect(url_for('signup'))
    
    # Check if the username already exists
    existing_user = db.execute("SELECT username FROM users WHERE username = ?", username)
    if existing_user:
        flash('Username Already Exists', 'error')
        return redirect(url_for('signup'))
    
    # Check if passwords match
    if password_1 != password_2:
        flash('Passwords do not match, please try again.', 'error')
        return redirect(url_for('signup'))
    
    # Hash the password and create the new user
    hashed_password = generate_password_hash(password_1, method='pbkdf2:sha256')
    db.execute("INSERT INTO users (username, password) VALUES (?, ?)", username, hashed_password)
    
    flash('Account Created Successfully', 'success')
    return redirect(url_for('login'))

@app.route('/edit/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit(contact_id):
    user_id = current_user.id
    contact = db.execute("SELECT * FROM contacts WHERE id = ? AND user_id = ?", contact_id, user_id)
    
    if not contact:
        flash('Contact not found!', 'error')
        return redirect(url_for('view'))
    
    contact = contact[0]  # Unpack the first item in the list

    if request.method == 'POST':
        new_name = request.form.get('contact_name')
        new_number = request.form.get('contact_number')
        db.execute("UPDATE contacts SET contact_name = ?, contact_number = ? WHERE id = ? AND user_id = ?", new_name, new_number, contact_id, user_id)
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('view'))

    return render_template('edit.html', contact=contact)



if __name__ == "__main__":
    app.run(debug=True)