from flask import Flask, render_template, redirect, url_for,flash,jsonify, session, request, send_from_directory
from flask_mail import Mail, Message
import random
import bcrypt
import os
import json
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequestKeyError
from flask_socketio import SocketIO, join_room, leave_room, emit



app = Flask(__name__)
app.secret_key = "saurabasf"


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'otpverifycodegram@gmail.com'  # Replace with your email address
app.config['MAIL_PASSWORD'] = 'genozvnisnlqdywm'

mail= Mail(app)

UPLOAD_FOLDER = 'pfp/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
socketio = SocketIO(app)
import re
db_path = 'chat.db'
def is_valid_username(username):
    return re.match("^[a-zA-Z0-9_]*$", username) is not None

@app.route('/', methods=['GET', 'POST'])
def signup():
    error = ''
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        email = request.form['email']
        if username == '':
            error = "Please enter your username."
            return render_template('signup.html',error=error)
        if password == '':
            error = "Please enter your password."
            return render_template('signup.html',error=error)
        if email == '':
            error = "Please enter your email."
            return render_template('signup.html',error=error)
        if not is_valid_username(username):
            error = 'Invalid characters in username. Please use only letters, numbers, and underscores.'
        # Check if the username and email are already taken
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        username_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
        email_count = c.fetchone()[0]
        conn.close()

        if username_count > 0:
            error = 'Username already taken. Please choose a different username.'
        elif email_count > 0:
            error = 'Email already taken. Please choose a different email.'
        
        else:
            # Generate a verification code
            verification_code = random.randint(100000, 999999)

            # Send verification email
            msg = Message('Welcome to Cupids Diary! Confirm Your Email', sender='otpverifycodegram@gmail.com', recipients=[email])
            msg.html = f"""
            <html>
            <body>
                <p>Hello {username},</p>
                <p>Welcome to Cupid's Diary! To get started, please verify your email by entering the following code:</p>
                <h2 style="color: #3498db;">{verification_code}</h2>
            </body>
            </html>
            """

            mail.send(msg)  # Pass the Message object as an argument here

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Insert user into the database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password, email, verification_code) VALUES (?, ?, ?, ?)', (username, hashed_password.decode('utf-8'), email, verification_code))
            conn.commit()
            conn.close()

            # Set the username in the session
            session['username'] = username

            return redirect(url_for('verify'))

    return render_template('signup.html', error=error)

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        verification_code = int(request.form['verification_code'])
        username = session.get('username')

        if not username:
            error = 'Invalid verification code. Please try again.'
            return render_template('verify.html', error=error)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT verification_code FROM users WHERE username = ?', (username,))
        stored_code = c.fetchone()[0]

        if verification_code == stored_code:
            # Update the 'verified' flag in the database
            # Connect to the database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()

            # Check if the 'verified' column already exists
            c.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in c.fetchall()]
            if 'verified' not in columns:
                # Add the 'verified' column
                c.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")

            c.execute('UPDATE users SET verified = 1 WHERE username = ?', (username,))
            conn.commit()
            conn.close()

            return redirect(url_for('setup'))
        else:
            error = 'Invalid verification code. Please try again.'
            return render_template('verify.html', error=error)

    return render_template('verify.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form['username'].strip().lower()  # Remove spaces and convert to lowercase
        password = request.form['password']
        if username == '':
            error = "Please enter your username."
            return render_template('login.html',error=error)
        if password == '':
            error = "Please enter your username."
            return render_template('login.html',error=error)
        # Connect to the database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Retrieve the hashed password for the given username
        c.execute('SELECT password FROM users WHERE username = ?', (username,))
        hashed_password = c.fetchone()
        # Close the connection
        conn.close()

        if hashed_password is None or not bcrypt.checkpw(password.encode('utf-8'), hashed_password[0].encode('utf-8')):
            error = 'Invalid username or password. Please try again.'
            return render_template('login.html', error=error)
        else:
            session['username'] = username  # Set the 'username' value in the session

            if is_profile_setup_complete(username):
                return redirect(url_for('home'))
            else:
                return redirect(url_for('setup'))

    return render_template('login.html')

def is_profile_setup_complete(username):
    with open('users_data.txt', 'r') as file:
        for line in file:
            user_data = json.loads(line)
            if "username" in user_data and user_data["username"] == username:
                return True
    # Profile setup is not complete or username not found
    return False


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/setup', methods=['POST', 'GET'])
def setup():
    error =  ""  # Initialize error variable
    
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    if is_profile_setup_complete(username):
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle form submission
        name = request.form['name']
        _class = request.form['class']
        section = request.form['section']
        school = request.form['school']
        age = request.form['age']
        gender = request.form['gender']
        bio = request.form['bio']
        hobbies = request.form['hobbies']
        hobby_likes = request.form['hobbyLikes']
        
        length=len(bio)
        hoblen=len(hobby_likes)
        if name == '':
            error = "Please enter your name."
        if not is_valid_username(name):
            error = 'Invalid characters in username. Please use only letters, numbers, and underscores.'
        elif any(char.isdigit() for char in name):
            error = "Invalid name. Name cannot contain numbers."
        elif school == '':
            error = "Please enter your school name."
        elif any(char.isdigit() for char in school):
            error = "Invalid school name. School name cannot contain numbers."
        elif _class == '':
            error = "Please enter your class."
        elif hoblen>200:
            error="Hobbies length should not be more than 200"
        elif not _class.isdigit():
            error = "Invalid class. Class must be a number."
        elif int(_class) < 1 or int(_class) > 12:
            error = "Invalid class. Class must be between 1 and 12."
        elif section == '':
            error = "Please enter your section."
        elif age == '':
            error = "Please enter your age."
        elif not age.isdigit():
            error = "Invalid age. Age must be a number."
        elif int(age) < 13:
            error = "You must be at least 13 years old to sign up."
        elif gender not in ['male', 'female', 'other']:
            error = "Invalid gender selection."
        elif length > 100:
            error= "bio is too long"
        else:
            # Saving form data to JSON file
            user_data = {
                'username': username,
                'name': name,
                'class': _class,
                'section': section,
                'bio': bio,
                'school': school,
                'age': age,
                'gender': gender,
                'hobbies': hobbies,
                'hobby_likes': hobby_likes
            }
            with open('users_data.txt', 'a') as file:
                file.write(json.dumps(user_data) + '\n')
            
            if 'profilePicInput' in request.files:
                file = request.files['profilePicInput']
                if file.filename != '':
                    if file and allowed_file(file.filename):
                        try:
                            # Constructing the filename using the username and file extension
                            filename = secure_filename(username) + '.' + 'png'
                            destination = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(destination)
                        except Exception as e:
                            error = "An error occurred while saving the profile picture: " + str(e)

                
        # If an error occurred, render the setup page with the error message
        if error:
            return render_template('setup.html', error=error)
        else:
            return redirect(url_for('home'))

    return render_template('setup.html', error=error)


@app.route('/premium')
def premium():
    return render_template('premium.html')


@app.route('/signup')
def redirectsignup():
    return redirect(url_for('signup'))

@app.route('/filtered')
def filter():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Retrieve the username of the logged-in user from the session
    username = session['username']

    # Read user data from the JSON file
    with open('users_data.txt', 'r') as file:
        users_data = [json.loads(line) for line in file]

    # Find the user's data based on the username
    user_data = next((data for data in users_data if data['username'] == username), None)

    if not user_data:
        # Handle the case where user data is not found
        return redirect(url_for('login'))

    # Extract user's interests
    user_interests = user_data.get('hobbies', [])

    # Filter users based on matching interests
    filtered_users_data = []
    for data in users_data:
        # Skip the logged-in user
        if data['username'] == username:
            continue

        # Check if interests match
        if set(data.get('hobbies', [])) == set(user_interests):
            # Add profile picture URL to filtered user data
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f"{data['username']}.png")):
                data['profile_picture_url'] = url_for('pfp', filename=f"{data['username']}.png")
            else:
                data['profile_picture_url'] = url_for('pfp', filename='default.png') if data['gender'] == 'male' else url_for('pfp', filename='default-f.png')
            filtered_users_data.append(data)

    return render_template('filterhome.html', filtered_users_data=filtered_users_data)

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Retrieve the username of the logged-in user from the session
    username = session['username']

    # Read user data from the JSON file
    with open('users_data.txt', 'r') as file:
        users_data = [json.loads(line) for line in file]

    # Find the user's data based on the username
    user_data = next((data for data in users_data if data['username'] == username), None)

    if user_data:
        # Get the gender of the logged-in user
        user_gender = user_data['gender']

        # Determine the opposite gender
        opposite_gender = 'female' if user_gender == 'male' else 'male'

        # Filter users' data based on opposite gender
        opposite_gender_users_data = [data for data in users_data if data['gender'] == opposite_gender]
        for user in opposite_gender_users_data:
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f"{user['username']}.png")):
                user['profile_picture_url'] = url_for('pfp', filename=f"{user['username']}.png")
            else:
                user['profile_picture_url'] = url_for('pfp', filename='default.png') if user['gender'] == 'male' else url_for('pfp', filename='default-f.png')
        # You can now pass the opposite_gender_users_data list to your template and display it as needed
        return render_template('home.html', opposite_gender_users_data=opposite_gender_users_data)
    else:
        # Handle the case where user data is not found
        return redirect(url_for('login'))

@app.route('/matches')
def matches():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_username = session['username']
    
    # Initialize a list to store matched users involving the current user
    filtered_matches = []
    
    # Load matched users' data from the JSON file
    with open('matched_users.json', 'r') as file:
        for line in file:
            matched_user_data = json.loads(line)
            user1 = matched_user_data.get('user1')
            user2 = matched_user_data.get('user2')
            
            # Check if the current user is involved in the match
            if current_username == user1 or current_username == user2:
                filtered_matches.append(matched_user_data)

    return render_template('matches.html', matched_users=filtered_matches)

# Dummy function to fetch user data
def get_user_data(username):
    # Define an empty dictionary to store user data
    user_data = {}
    
    # Open the users_data.txt file to read user data
    with open('users_data.txt', 'r') as file:
        # Iterate through each line in the file
        for line in file:
            # Load JSON data from each line
            data = json.loads(line)
            # Check if the username in the data matches the requested username
            if data['username'] == username:
                # Assign user data to the dictionary
                user_data = data
                break  # Stop iterating if user data is found
    
    return user_data

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'username' in session:
        username = session['username']
        bio = request.form['bio']
        school = request.form['school']
        hobbies = request.form.getlist('hobbies')  # Get list of hobbies from form
        hobby_likes = request.form.get('hobby_likes')  # Get user's likes about hobbies
        profile_picture = request.files['profile_picture']
        
        max_bio_length = 100  # Define the maximum bio length
        if len(bio) > max_bio_length:
            error_message = "Bio length exceeds the maximum limit."
            session['error'] = error_message  # Store the error message in the session
            return redirect(url_for('user_profile', username=username))
        
        save_profile_changes(username, bio, school, hobbies, hobby_likes, profile_picture)
        return redirect(url_for('user_profile', username=username))
    else:
        return redirect(url_for('login'))

def save_profile_changes(username, bio, school, hobbies, hobby_likes, profile_picture):
    # Load user data from JSON file
    users_data = []
    with open('users_data.txt', 'r') as file:
        for line in file:
            users_data.append(json.loads(line))

    # Find the user in the data and update their information
    for user_data in users_data:
        if user_data['username'] == username:
            user_data['bio'] = bio
            user_data['school'] = school
            hobbies_string = ', '.join(hobbies)
            user_data['hobbies'] = hobbies_string
            user_data['hobby_likes'] = hobby_likes  # Update likes about hobbies
            
            # If profile picture is changing, delete the old one and replace it
            if profile_picture:
                old_profile_picture_path = f"pfp/{username}.png"
                if os.path.exists(old_profile_picture_path):
                    os.remove(old_profile_picture_path)
                profile_picture.save(f"pfp/{username}.png")

    # Write the updated user data back to the JSON file
    with open('users_data.txt', 'w') as file:
        for user_data in users_data:
            json.dump(user_data, file)
            file.write('\n')

# Modify the user_profile function
@app.route('/<username>')
def user_profile(username):
    if 'username' in session:
        session_username = session['username']
        error_message = session.pop('error', None)  # Get and remove the error message from the session
        if session_username == username:
            user_data = get_user_data(username)
            if user_data:
                # Concatenate hobbies into a string

                profile_picture_url = f"/pfp/{username}.png"
                return render_template('profile.html', username=username,hobby_likes=user_data['hobby_likes'],bio=user_data['bio'], school=user_data['school'], hobbies=user_data['hobbies'], profile_picture_url=profile_picture_url, error_message=error_message)
            else:
                return "User data not found"
        else:
            return redirect(url_for('user_profile', username=session_username))
    else:
        return redirect(url_for('login'))


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    error = ''
    try:
        if request.method == 'POST':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            username = session['username']

            # Check if the old password matches the one in the database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('SELECT password FROM users WHERE username = ?', (username,))
            hashed_password = c.fetchone()[0]
            conn.close()

            if not bcrypt.checkpw(old_password.encode('utf-8'), hashed_password.encode('utf-8')):
                error = 'Incorrect old password.'
            elif new_password != confirm_password:
                error = 'New password and confirmation password do not match.'
            elif len(new_password) < 8:
                error = 'New password must be at least 8 characters long.'
            else:
                # Update the password in the database
                hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_new_password.decode('utf-8'), username))
                conn.commit()
                conn.close()
                flash('Password changed successfully!', 'success')
                return redirect(url_for('home'))
    except BadRequestKeyError as e:
        error = 'Form submission error: Required key missing in form data.'
        # Log the error for further investigation
        app.logger.error(f'BadRequestKeyError: {str(e)}')

    
    print(error)

    return render_template('settings.html', error=error)


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    # Delete the user's account from the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()

    # Delete the user's data from the users_data.txt file
    with open('users_data.txt', 'r') as file:
        lines = file.readlines()
    with open('users_data.txt', 'w') as file:
        for line in lines:
            user_data = json.loads(line)
            if user_data['username'] != username:
                file.write(json.dumps(user_data) + '\n')

    # Delete the user's profile picture if it exists
    profile_picture_path = f"pfp/{username}.png"
    if os.path.exists(profile_picture_path):
        os.remove(profile_picture_path)

    # Clear the session
    session.clear()
    flash('Your account has been deleted.', 'success')
    return redirect(url_for('login'))



@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if request.form['action'] == 'delete_account':
            # Delete the user's account
            return redirect(url_for('delete_account'))
        elif request.form['action'] == 'change_password':
            # Change the user's password
            return redirect(url_for('change_password'))

    return render_template('settings.html')



@app.route('/pfp/<path:filename>')
def pfp(filename):
    return send_from_directory('pfp', filename)
def check_and_write_match(user1, user2):
    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if table exists for user1
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (user1,))
    user1_table = c.fetchone()

    if not user1_table:
        # Create table for user1
        c.execute(f"CREATE TABLE IF NOT EXISTS {user1} (username TEXT)")

    # Check if user2 is already present in user1's table
    c.execute(f"SELECT * FROM {user1} WHERE username=?", (user2,))
    existing_user = c.fetchone()
    
    if existing_user:
        conn.close()
        return

    # Insert user2 into user1's table
    c.execute(f"INSERT INTO {user1} (username) VALUES (?)", (user2,))

    # Check if table exists for user2
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (user2,))
    user2_table = c.fetchone()

    if user2_table:
        # Check if user1 is present in user2's table
        c.execute(f"SELECT * FROM {user2} WHERE username=?", (user1,))
        user1_in_user2_table = c.fetchone()
        
        if user1_in_user2_table:
            # Write both usernames to a JSON file
            matched_users = {'user1': user1, 'user2': user2}
            with open('matched_users.json', 'a') as file:
                json.dump(matched_users, file)
                file.write('\n')

    # Commit changes and close connection
    conn.commit()
    conn.close()

@app.route('/match', methods=['POST'])
def match():
    if 'username' in session:
        user1 = session['username']
        user2 = request.form.get('user_id')

        check_and_write_match(user1, user2)

    return redirect(url_for('home'))

@app.route('/anonymouschat')
def anonymouschat():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Connect to the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Fetch the list of usernames from the "users" table
    cursor.execute('SELECT username FROM users')
    users = [row[0] for row in cursor.fetchall()]
    user_count = len(users)  # Use len() function instead of users.length

    # Close the database connection
    conn.close()

    return render_template('anonymous.html', users=users, user_count=user_count)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'feedback': request.form['feedback']
        }
        save_feedback(feedback_data)
        return redirect(url_for('home'))  # Redirect to home after submitting feedback
    return render_template('feedback.html')
                                       
def save_feedback(feedback_data):
    with open('feedback.txt', 'a') as file:
        json.dump(feedback_data, file)
        file.write('\n')  # Add a newline for better readability

@app.route('/logout', methods=['GET', 'POST'])  # Allow both GET and POST requests
def logout():
    if 'username' in session:
        session.pop('username')
    return redirect(url_for('login'))


# Read data from the users_data.txt file
def read_classroom_data():
    with open('users_data.txt', 'r') as file:
        data = file.readlines()
        classrooms = [json.loads(line.strip()) for line in data]
    return classrooms


@app.route('/groups')
def groups():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Read classroom data from the file
    classrooms = read_classroom_data()
    
    # Extract unique class and section combinations
    unique_class_sections = {(classroom["class"], classroom["section"]) for classroom in classrooms}
    
    # Convert unique class and section combinations to list of tuples
    class_sections_list = list(unique_class_sections)
    
    return render_template('groups.html', class_sections=class_sections_list)
# Create table if not exists
def create_table(cursor, table_name):
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL
        )
    ''')
# Flask route handling the chat page
@app.route('/chat/<class_section>')
def chat(class_section):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']

    # Fetch existing chat messages from the database
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        table_name = f"class_{class_section.replace('-', '_')}"
        create_table(c, table_name)
        c.execute(f"SELECT username, message FROM {table_name}")
        old_chats = c.fetchall()
        # Create a list of existing usernames for which profile pictures exist
        existing_usernames = []
        pfp_dir = os.path.join(app.root_path, 'pfp')  # Assuming 'pfp' directory is in the root of your Flask app
        for filename in os.listdir(pfp_dir):
            if filename.endswith('.png'):
                username = filename[:-4]  # Remove the file extension
                existing_usernames.append(username)
        return render_template('classroom.html', username=username, class_section=class_section, old_chats=old_chats, existing_usernames=existing_usernames)


@socketio.on('join')
def on_join(data):
    username = session['username']
    class_section = data['class_section']
    room = class_section
    join_room(room)
    emit('status', {'msg': username + ' has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = session['username']
    class_section = data['class_section']
    room = class_section
    leave_room(room)
    emit('status', {'msg': username + ' has left the room.'}, room=room)

@socketio.on('message')
def handle_message(data):
    username = session['username']
    class_section = data['class_section']
    room = class_section
    message = data['message']
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        table_name = f"class_{class_section.replace('-', '_')}"
        create_table(c, table_name)
        c.execute(f"INSERT INTO {table_name} (username, message) VALUES (?, ?)", (username, message))
        conn.commit()
    emit('message', {'username': username, 'message': message}, room=room)


# Function to check credentials for moderators
def check_moderator_credentials(username, password):
    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mods WHERE username=? AND password=?", (username, password))
    moderator = cursor.fetchone()
    conn.close()
    return moderator is not None

# Function to check credentials for group admins
def check_group_admin_credentials(username, password):
    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groupadmin WHERE username=? AND password=?", (username, password))
    group_admin = cursor.fetchone()
    conn.close()
    return group_admin is not None

# Function to check credentials for admin
def check_admin_credentials(username, password):
    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
    admin = cursor.fetchone()
    conn.close()
    return admin is not None

@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        if not username or not password:
            error = "Please enter both username and password."
            return render_template('adminlogin.html', error=error)
        
        if username.startswith('mod'):
            if check_moderator_credentials(username, password):
                return redirect(url_for('moderator_route'))
        elif username.startswith('groupadmin'):
            if check_group_admin_credentials(username, password):
                return redirect(url_for('groupadmin_route'))
        elif check_admin_credentials(username, password):
            return redirect(url_for('admin_panel'))
        session['username'] = username
        error = "Invalid username or password. Please try again."
        
        return render_template('adminlogin.html', error=error)
        
    return render_template('adminlogin.html')



def get_classroom_names():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Retrieve table names (assuming they start with "class_" prefix)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'class_%'")
        table_names = [row[0] for row in cursor.fetchall()]

        # Extract classroom names from table names
        classroom_names = [name.split('_')[1:] for name in table_names]  # Adjust split index if necessary

        return classroom_names

@app.route('/groupadmin')
def groupadmin_route():
    if 'username' not in session:
        return redirect(url_for('adminlogin'))

    classroom_names = get_classroom_names()

    return render_template('groupadmin.html', classrooms=classroom_names)


@app.route('/groupadmin/chat/<class_name>')
def groupadmin_chat(class_name):
  if 'username' not in session:
    return redirect(url_for('adminlogin'))

  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()

    table_name = f"class_{class_name}"
    cursor.execute(f"SELECT * FROM {table_name}")
    chat_messages = cursor.fetchall()

    usernames = [message[1] for message in chat_messages]
    message_ids = [message[0] for message in chat_messages]  # Assuming message ID is the first element
    messages = [message[2] if message[2] else "" for message in chat_messages]  # No sanitization
    message_lengths = [len(message) for message in messages]  # Calculate message lengths

  return render_template('groupadmin_chat.html', class_name=class_name, usernames=usernames, message_ids=message_ids, messages=messages, message_lengths=message_lengths)


@app.route('/groupadmin/chat/<class_name>/delete/<int:message_id>', methods=['POST'])
def delete_message(class_name, message_id):
    if 'username' not in session:
        return redirect(url_for('adminlogin'))

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        table_name = f"class_{class_name}"
        cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (message_id,))
        conn.commit()

    flash('Message deleted successfully', 'success')
    return redirect(url_for('groupadmin_chat', class_name=class_name))


@app.route('/moderator')
def moderator_route():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('adminlogin'))
    
    # Read data from users_data.txt
    with open('users_data.txt', 'r') as file:
        user_data = [json.loads(line) for line in file]
    
    # Render the template with the user data
    return render_template('moderator.html', user_data=user_data)


from datetime import datetime

def log_change(username, field, old_value, new_value):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp}: User '{username}' changed '{field}' from '{old_value}' to '{new_value}'\n"
    
    with open('change_logs.txt', 'a') as log_file:
        log_file.write(log_entry)

@app.route('/moderator/edit_user_info', methods=['POST'])
def edit_user_info():
    if 'username' not in session:
        return redirect(url_for('adminlogin'))

    # Get form data
    username = request.form['username']
    bio = request.form['bio']
    school = request.form['school']
    hobby_likes = request.form['hobby_likes']

    # Read data from users_data.txt
    with open('users_data.txt', 'r') as file:
        user_data = [json.loads(line) for line in file]

    # Find the user in user_data
    for user in user_data:
        if user['username'] == username:
            # Log old values
            old_bio = user['bio']
            old_school = user['school']
            old_hobby_likes = user['hobby_likes']

            # Update user info
            user['bio'] = bio
            user['school'] = school
            user['hobby_likes'] = hobby_likes

            # Log changes
            log_change(username, 'bio', old_bio, bio)
            log_change(username, 'school', old_school, school)
            log_change(username, 'hobby_likes', old_hobby_likes, hobby_likes)
            
            break

    # Write updated data back to users_data.txt
    with open('users_data.txt', 'w') as file:
        for user in user_data:
            file.write(json.dumps(user) + '\n')

    flash('User info updated successfully', 'success')
    return redirect(url_for('moderator_route'))


@app.route('/delete_profile_picture', methods=['POST'])
def delete_profile_picture():
    # Get the username from the form data
    username = request.form.get('username')

    # Construct the file path to the profile picture
    profile_picture_path = os.path.join( 'pfp', username + '.png')

    # Check if the file exists and delete it
    if os.path.exists(profile_picture_path):
        os.remove(profile_picture_path)
        print(f"Profile picture for {username} deleted successfully.")
    else:
        print(f"Profile picture for {username} not found.")

    # Redirect to the admin panel or any other page
    return redirect(url_for('admin_panel'))

@app.route('/admin_panel')
def admin_panel():
    # Check if the user is logged in as admin
    if 'username' not in session:
        return redirect(url_for('adminlogin'))  # Redirect to admin login if not logged in
    
    # Connect to the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Fetch all users from the database
    cursor.execute("SELECT * FROM users")
    db_users = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Read matched users from matched_users.json
    with open('matched_users.json', 'r') as match_file:
        matched_users = json.load(match_file)

    # Read user data from users_data.txt
    with open('users_data.txt', 'r') as users_data_file:
        users_data = [json.loads(line) for line in users_data_file]

    # Render the admin panel template with the list of users, matched users, and user data
    return render_template('admin_panel.html', db_users=db_users, matched_users=matched_users, users_data=users_data)

@app.route('/delete_user', methods=['POST'])
def delete_user():
    # Check if the user is logged in as admin
    if 'username' not in session:
        return redirect(url_for('admin_login'))  # Redirect if not logged in as admin
    
    # Get the user ID to be deleted from the form data
    user_id = request.form.get('user_id')

    # Connect to the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Delete the user from the database
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

    # Close the database connection
    conn.close()

    # Redirect to the admin panel after deletion
    return redirect(url_for('admin_panel'))
@app.route('/edit_user_data', methods=['POST', 'GET'])
def edit_user_data():
    # Check if the user is logged in as admin
    if 'username' not in session:
        return redirect(url_for('admin_login'))  # Redirect if not logged in as admin
    
    # Retrieve the form data
    username = request.form.get('username')
    new_name = request.form.get('new_name')
    new_school = request.form.get('new_school')
    new_bio = request.form.get('new_bio')

    # Read the existing user data from the users_data.txt file
    with open('users_data.txt', 'r') as file:
        users_data = [json.loads(line) for line in file]

    # Update the user data with the new information
    for user_data in users_data:
        if user_data['username'] == username:
            user_data['name'] = new_name
            user_data['school'] = new_school
            user_data['bio'] = new_bio
            break

    # Write the updated user data back to the file
    with open('users_data.txt', 'w') as file:
        for user_data in users_data:
            file.write(json.dumps(user_data) + '\n')

    # Redirect back to the admin panel
    return redirect('/admin_panel')
@app.route('/delete_user_data', methods=['POST'])
def delete_user_data():
    username = request.form.get('username')
    print("Username to delete:", username)  # Debugging statement

    if username:
        delete_user_from_file(username)
    return redirect(url_for('admin_panel'))
def delete_user_from_file(username):
    # Read lines from the file
    with open('users_data.txt', 'r') as file:
        lines = file.readlines()

    # Initialize an empty list to store parsed JSON data
    data = []

    # Iterate over each line and parse JSON data
    for line in lines:
        # Ignore empty lines
        if line.strip():
            try:
                user_data = json.loads(line)
                data.append(user_data)
            except json.JSONDecodeError as e:
                print("Error parsing JSON:", e)

    # Search for the user and remove if found
    for user in data:
        if user.get('username') == username:
            data.remove(user)
            break

    # Write back modified data to the file
    with open('users_data.txt', 'w') as file:
        for user in data:
            file.write(json.dumps(user) + '\n')

if __name__ == '__main__':
    socketio.run(app,debug=True,host='192.168.1.34')
