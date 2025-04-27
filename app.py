from flask import Flask, request, make_response, jsonify
import mysql.connector
import hashlib
import uuid
from .config import Config
import jwt
import datetime
from functools import wraps # Import wraps for decorator
from .courses_routes import courses_bp
from .content_routes import content_bp
from .views_routes import views_bp
from .utilities import (connect_to_mysql,
generate_salt, generate_hashed_password, get_next_user_id,
get_next_student_id, get_next_lec_id, create_jwt, decode_jwt, token_required)

app = Flask(__name__)
app.config.from_object(Config)
# app.config['VALID_DEPARTMENTS']


app.register_blueprint(courses_bp)
app.register_blueprint(content_bp)
app.register_blueprint(views_bp)

#  python -m venv venv
# .\venv\Scripts\activate
# flask --app app --debug run




@app.route('/hello_world', methods=['GET'])
def hello_world():
    return "hello world"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        cursor.execute("SELECT * FROM User WHERE Username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            stored_salt = user[4]
            stored_hashed_password = user[2]
            print(stored_salt)
            print(stored_hashed_password)

            # Hash the provided password with the stored salt
            provided_hashed_password = generate_hashed_password(password, stored_salt)

            if provided_hashed_password == stored_hashed_password:
                user_data = {  # Create a dictionary for JWT payload
                                'UserId': user[0],  # Access by integer index
                                'Username': user[1],
                                'Role': user[3]
                            }
                 # Conversion to dictionary was needed because string index did not work on tuples
                token = create_jwt(user_data, app.config['SECRET_KEY'], app.config['JWT_EXPIRATION_HOURS'])
                print(f"Login Successful: {token}")
                return jsonify({'token': token}), 200
            else:
                return jsonify({'message': 'Invalid credentials'}), 401
        else:
            return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

    finally:
        cnx.close()

@app.route('/logout', methods=['POST'])
def logout():
    # Invalidate the JWT token (this can be done by simply not sending it in future requests)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/protected', methods=['GET'])
@token_required
def protected(user_data):  # Receive user data from the decorator
    return jsonify({'message': f'Hello, {user_data["username"]}! Your role is {user_data["role"]}'})



@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')  # 'admin', 'lecturer', or 'student'
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    department = data.get('department')

    # Enforce the rule: Only lecturers can be admins
    if role == 'admin' and role != 'lecturer':
        return jsonify({'message': 'Only lecturers can be admins'}), 400

    if not username or not password or not role or role not in ('admin', 'lecturer', 'student') or not first_name or not last_name:
        return jsonify({'message': 'Missing or invalid registration data'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # 1. Generate Salt and Hashed Password
        salt = generate_salt()
        hashed_password = generate_hashed_password(password, salt)

        # 2. Insert into User table (generate UserId)
        user_id = get_next_user_id(cnx)
        cursor.execute("INSERT INTO User (UserId, Username, Password, Role, Salt) VALUES ( %s,  %s,  %s,  %s,  %s)",
             (user_id, username, hashed_password, role, salt))

        # 3. Insert into Student or Lecturer table if applicable
        if role == 'student':
            student_id = get_next_student_id(cnx)
            cursor.execute("INSERT INTO Student (StudentID, FirstName, LastName, UserId) VALUES ( %s,  %s,  %s,  %s)",
                           (student_id, first_name, last_name, user_id))
        elif role == 'lecturer' or role == 'admin':  # Allow admins to be created if they are lecturers
            lec_id = get_next_lec_id(cnx)  # Get next LecId
            cursor.execute("INSERT INTO Lecturer (LecId, LecFirstName, LecLastName, Department, UserId) VALUES ( %s,  %s,  %s,  %s,  %s)",
                           (lec_id, first_name, last_name, department, user_id))

        cnx.commit()
        print(f"User registered successfully: {username} with role {role}")
        return jsonify({'message': 'User registered successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

    finally:
        cnx.close()