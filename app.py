from flask import Flask, redirect, render_template, request, url_for, flash, send_file, g, get_flashed_messages
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import mysql.connector
import os
import logging
import qrcode
import vobject
from io import BytesIO
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
import re

# Configure app
app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.urandom(24)  # Use a randomly generated key
Session(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

import secrets

secret_key = secrets.token_hex(32)  # 64 characters long
password_salt = secrets.token_hex(16)

# Configure Flask-Mail
app.config['SECRET_KEY'] = secret_key  # Replace with a real secret key
app.config['SECURITY_PASSWORD_SALT'] = password_salt
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "techoverflow7@gmail.com"  # Your Gmail address
app.config['MAIL_PASSWORD'] = "ccxf jjdp zoev detw"  # Your generated App Password
app.config['MAIL_DEFAULT_SENDER'] = "techoverflow7@gmail.com"  # Your Gmail address

mail = Mail(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

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
        return User(id=user_data[0], username=user_data[1], password=user_data[2])
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
    if not any(message['category'] == 'error' for message in get_flashed_messages(with_categories=True)):
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

        flash('Invalid username or password.', 'error')

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
    email = request.form.get("email")
    address = request.form.get("address")
    user_id = current_user.id

    # Validation with regex

    if not re.match(r'^[\w\s]+$', contact_name):
        flash('Invalid contact name format.', 'error')
        return redirect(url_for('new'))

    if not re.match(r'^\+?\d{10,15}$', contact_number):
        flash('Invalid phone number format.', 'error')
        return redirect(url_for('new'))

    if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        flash('Invalid email format.', 'error')
        return redirect(url_for('new'))

    if address and len(address) > 200:
        flash('Address is too long.', 'error')
        return redirect(url_for('new'))

    g.cursor.execute("SELECT * FROM contacts WHERE user_id = %s AND (contact_name = %s OR contact_number = %s)", (user_id, contact_name, contact_number))
    existing_contacts = g.cursor.fetchall()

    if not existing_contacts:
        g.cursor.execute("INSERT INTO contacts (contact_name, contact_number, email, address, user_id) VALUES (%s, %s, %s, %s, %s)", (contact_name, contact_number, email, address, user_id))
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
        if not any(message['category'] == 'error' for message in get_flashed_messages(with_categories=True)):
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
        email = request.form.get("email")

        # Regex patterns
        username_pattern = r'^[a-zA-Z0-9_]{5,20}$'  # Alphanumeric and underscores, 5-20 characters
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'  # Basic email validation
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@_])[A-Za-z\d@_]{8,}$'  # Minimum 8 chars, at least one letter, one number, one special character (@ or _)

        # Validate username
        if not re.match(username_pattern, username):
            flash('Username must be 5-20 characters long and can only contain letters, numbers, and underscores.', 'error')
        # Validate email
        elif not re.match(email_pattern, email):
            flash('Invalid email format.', 'error')
        # Validate password
        elif not re.match(password_pattern, password_1):
            flash('Password must be at least 8 characters long, contain at least one letter, one number, and one special character (@ or _).', 'error')
        else:
            # Check if username already exists
            g.cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            if g.cursor.fetchone():
                flash('Username already exists, please choose another one.', 'error')
            # Check if email already exists
            else:
                g.cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
                if g.cursor.fetchone():
                    flash('An account with this email already exists.', 'error')
                # Check if passwords match
                elif password_1 != password_2:
                    flash('Passwords do not match, please try again.', 'error')
                else:
                    # All validations passed, create the account
                    hashed_password = generate_password_hash(password_1, method='pbkdf2:sha256')
                    g.cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
                    g.db.commit()
                    flash('Account created successfully! Please log in.', 'success')
                    return redirect(url_for('login'))

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
        new_email = request.form.get('email')
        new_address = request.form.get('address')

        g.cursor.execute("UPDATE contacts SET contact_name = %s, contact_number = %s, email = %s, address = %s WHERE id = %s AND user_id = %s", (new_name, new_number, new_email, new_address, contact_id, user_id))
        g.db.commit()
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('view'))

    return render_template('edit.html', contact=contact)



@app.route('/export_vcards')
@login_required
def export_vcards():
    try:
        user_id = current_user.id
        g.cursor.execute("SELECT contact_name, contact_number, email, address FROM contacts WHERE user_id = %s", (user_id,))
        contacts = g.cursor.fetchall()

        # Create a BytesIO object to hold the vCard data
        output = BytesIO()

        for contact in contacts:
            # Create a vCard object
            vcard = vobject.vCard()

            # Add the name
            vcard.add('n')
            name_parts = contact[0].split(' ', 1)
            family_name = name_parts[1] if len(name_parts) > 1 else ''
            vcard.n.value = vobject.vcard.Name(family=family_name, given=name_parts[0])

            # Add the formatted name (FN)
            vcard.add('fn')
            vcard.fn.value = contact[0]

            # Add the phone number
            vcard.add('tel')
            vcard.tel.value = contact[1]
            vcard.tel.type_param = 'CELL'

            # Add the email
            if contact[2]:
                vcard.add('email')
                vcard.email.value = contact[2]
                vcard.email.type_param = 'INTERNET'

            # Add the address if it exists
            if contact[3]:
                vcard.add('adr')
                vcard.adr.value = vobject.vcard.Address(street=contact[3])

            # Serialize the vCard and write to the output
            output.write(vcard.serialize().encode('utf-8'))

        # Seek to the beginning of the BytesIO object
        output.seek(0)

        # Send the file as a downloadable response
        return send_file(output, as_attachment=True, download_name='contacts.vcf', mimetype='text/vcard')

    except Exception as e:
        logging.error(f"Error exporting vCards: {e}")
        flash('An error occurred while exporting contacts.', 'error')
        return redirect(url_for('view'))

@app.route('/import_vcf', methods=['GET', 'POST'])
@login_required
def import_vcf():
    if request.method == 'POST':
        file = request.files.get('vcf_file')
        if not file or not file.filename.endswith('.vcf'):
            flash('Please upload a valid vCard file.', 'error')
            return redirect(url_for('view'))

        try:
            # Parse the vCard file
            vcard_data = file.read().decode('utf-8')
            vcards = vobject.readComponents(vcard_data)

            for vcard in vcards:
                # Extract contact details
                name = vcard.fn.value if hasattr(vcard, 'fn') else ''
                tel = vcard.tel.value if hasattr(vcard, 'tel') else ''
                email = vcard.email.value if hasattr(vcard, 'email') else ''
                adr = vcard.adr.value.street if hasattr(vcard, 'adr') else ''

                # Insert into database
                g.cursor.execute("""
                    INSERT INTO contacts (contact_name, contact_number, email, address, user_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, tel, email, adr, current_user.id))
                g.db.commit()

            flash('Contacts imported successfully.', 'success')
            return redirect(url_for('view'))

        except Exception as e:
            logging.error(f"Error importing vCards: {e}")
            flash('An error occurred while importing contacts.', 'error')

    return render_template('import.html')

@app.route('/generate_vcard_qr/<int:contact_id>')
@login_required
def generate_vcard_qr(contact_id):
    user_id = current_user.id
    g.cursor.execute("SELECT contact_name, contact_number, email, address FROM contacts WHERE id = %s AND user_id = %s", (contact_id, user_id))
    contact = g.cursor.fetchone()

    if contact:
        contact_name, contact_number, email, address = contact

        # Create the vCard string
        vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{contact_name};;;
FN:{contact_name}
TEL;TYPE=CELL:{contact_number}
EMAIL;TYPE=INTERNET:{email}
ADR;TYPE=HOME:;;{address};;;
REV:{datetime.now().isoformat()}
END:VCARD"""

        # Generate the QR code
        qr_object = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_object.add_data(vcard, optimize=0)
        qr_object.make(fit=True)

        img = qr_object.make_image(fill_color="black", back_color="white").convert("RGBA")

        # Serve the QR code as an image
        byte_io = BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)
        return send_file(byte_io, mimetype='image/png')

    return "Contact not found", 404

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        g.cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = g.cursor.fetchone()

        if user:
            user_id = user[0]
            token = generate_password_reset_token(user_id)
            send_reset_email(email, token)
            flash('Password reset email sent!', 'info')
        else:
            flash('No account associated with this email.', 'error')

    return render_template('forgot_password.html')



def generate_password_reset_token(user_id):
    # Generate a unique token
    token = secrets.token_urlsafe()
    expiration_time = datetime.now() + timedelta(hours=1)  # Token valid for 1 hour

    # Store the token and its expiration in the database
    g.cursor.execute("""
        INSERT INTO password_reset_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE token = VALUES(token), expires_at = VALUES(expires_at)
    """, (user_id, token, expiration_time))
    g.db.commit()

    return token

def verify_password_reset_token(token):
    # Check if the token exists and is valid
    g.cursor.execute("""
        SELECT user_id FROM password_reset_tokens
        WHERE token = %s AND expires_at > %s
    """, (token, datetime.now()))
    result = g.cursor.fetchone()

    if result:
        user_id = result[0]

        # Optionally, delete the token after it's used
        g.cursor.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))
        g.db.commit()

        return user_id

    return None


def send_reset_email(user_email, token):
    reset_url = url_for('reset_password', token=token, _external=True)

    # HTML content of the email
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                width: 100%;
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                text-align: center;
                padding: 20px;
                background: #007bff;
                color: #ffffff;
                border-radius: 8px 8px 0 0;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                padding: 20px;
            }}
            .button {{
                display: block;
                width: 100%;
                max-width: 200px;
                margin: 20px auto;
                padding: 15px;
                text-align: center;
                background-color: #007bff;
                color: #ffffff;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
            }}
            .footer {{
                text-align: center;
                padding: 10px;
                font-size: 12px;
                color: #666666;
            }}
            .footer a {{
                color: #007bff;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Phonebook</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>We received a request to reset your password. Please click the button below to reset it:</p>
                <a href="{reset_url}" class="button">Reset Password</a>
                <p>If you did not request this change, please ignore this email.</p>
                <p>Best regards,<br>Our Team</p>
            </div>
            <div class="footer">
                <p>Created by Prasad Raju G | <a href="mailto:g.leelasaiprasadraju@gmail.com">Contact Us</a> | <a href="https://github.com/iamprasadraju" target="_blank">GitHub</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = Message(
        subject='Password Reset Request',
        recipients=[user_email],
        html=html_content
    )
    mail.send(msg)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Password validation
        password_pattern = re.compile(r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[@,_])[A-Za-z\d@,_]{8,}$')
        if not password_pattern.match(new_password):
            flash('Password must be at least 8 characters long, include letters, numbers, and one special character (@ or _).', 'error')
            return redirect(url_for('reset_password', token=token))

        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_password', token=token))

        user_id = verify_password_reset_token(token)
        if user_id:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            g.cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
            g.db.commit()
            flash('Password reset successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired token.', 'error')
            return redirect(url_for('reset_password_request'))

    return render_template('reset_password.html', token=token)



@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        g.cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = g.cursor.fetchone()
        if user:
            user_id = user[0]
            token = generate_password_reset_token(user_id)
            send_reset_email(email, token)
            flash('Check your email for a password reset link.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email address not found.', 'error')

    return render_template('reset_password_request.html')


if __name__ == '__main__':
    app.run(debug=True)

