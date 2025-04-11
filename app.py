from flask import Flask, request, make_response, jsonify
import mysql.connector
import hashlib
import uuid
from config import Config
from user import User
import jwt
import datetime
from functools import wraps # Import wraps for decorator

app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 7. Start the flask development server with `flask --app app --debug run`

def connect_to_mysql():
    try:
        con = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            port=app.config['MYSQL_PORT']
        )
        print("Successfully connected to MYSQL")
        return con
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

# github.com/MoTechStore/Vue-JS-3-Flask-2-REST-API-and-MYSQL---CRUD-App
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def generate_salt():
    """Generates a random salt as a hexadecimal string."""
    return uuid.uuid4().hex

def generate_hashed_password(password, salt):
    """Hashes the password with the salt using SHA256."""
    hash_object = hashlib.sha256()
    hash_object.update((password + salt).encode('utf-8')) # Ensure UTF-8 encoding
    return hash_object.hexdigest()

def get_next_id(cnx, table_name, id_column):
    """Helper function to get the next available ID."""
    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    cursor.execute(f"SELECT MAX({id_column}) FROM {table_name}")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 1
    else:
        return max_id + 1

def get_next_student_id(cnx):
    """Helper function to get the next StudentID."""
    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    cursor.execute("SELECT MAX(StudentID) FROM Student")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 62001
    else:
        return max_id + 1

def get_next_lec_id(cnx):
    """Helper function to get the next LecId."""
    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    cursor.execute("SELECT MAX(LecId) FROM Lecturer")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 1
    else:
        return max_id + 1

def get_next_user_id(cnx):
    """Helper function to get the next UserId."""
    return get_next_id(cnx, "User", "UserId")

def create_jwt(user, secret_key, expiration_hours):
    """Creates a JWT token for the user."""
    payload = {
        'user_id': user['UserId'],  # Use keys from the database result
        'username': user['Username'],
        'role': user['Role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def decode_jwt(token, secret_key):
    """Decodes and verifies a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
    except jwt.DecodeError:
        return None  # Invalid token format


def token_required(f):
    """Decorator to protect routes and get user info from the token."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Token is missing or invalid'}), 401

        token = auth_header.split(' ')[1]
        payload = decode_jwt(token, app.config['SECRET_KEY'])

        if not payload:
            return jsonify({'message': 'Invalid token'}), 401

        # Make the user information available to the route
        return f(payload, *args, **kwargs)

    return decorated_function


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

    cnx = connect_to_mysql()
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

    cnx = connect_to_mysql()
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
        return jsonify({'message': 'User registered successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

    finally:
        cnx.close()