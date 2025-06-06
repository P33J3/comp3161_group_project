from functools import wraps # Import wraps for decorator
import mysql.connector
import hashlib
import uuid
from .config import Config
import jwt
import datetime
from flask import Flask, request, make_response, jsonify, current_app


def connect_to_mysql(config):
    try:
        con = mysql.connector.connect(
            host=config['MYSQL_HOST'],
            user=config['MYSQL_USER'],
            password=config['MYSQL_PASSWORD'],
            database=config['MYSQL_DB'],
            port=config['MYSQL_PORT']
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
#     cnx = connect_to_mysql()
    cursor = cnx.cursor()
    cursor.execute(f"SELECT MAX({id_column}) FROM {table_name}")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 1
    else:
        return max_id + 1

def get_next_student_id(cnx):
    """Helper function to get the next StudentID."""
#     cnx = connect_to_mysql()
    cursor = cnx.cursor()
    cursor.execute("SELECT MAX(StudentID) FROM Student")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 62001
    else:
        return max_id + 1

def get_next_lec_id(cnx):
    """Helper function to get the next LecId."""
#     cnx = connect_to_mysql()
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
        secret_key = current_app.config['SECRET_KEY']
        payload = decode_jwt(token, secret_key)

        if not payload:
            return jsonify({'message': 'Invalid token'}), 401

        # Make the user information available to the route
        return f(payload, *args, **kwargs)

    return decorated_function

def get_next_course_code(cnx, department):
  """
  Gets the next available course code for a department.
  Assumes course codes are like 'ABC101', and increments the numeric part.
  """
  cursor = cnx.cursor()
  cursor.execute(
    "SELECT MAX(CourseCode) FROM Course WHERE LEFT(CourseCode, 3) = %s",
    (department[:3].upper(),)
    )
  last_code = cursor.fetchone()[0]
  if not last_code:
    next_number = 101 # Default starting number
  else:
    try:
        next_number = int(last_code[3:]) + 1 # Increment the numeric part
    except ValueError:
        next_number = 101 # Default if the numeric part isn't an integer

  return f"{department[:3].upper()}{next_number:03d}" # Format the next code

def get_next_course_id(cnx):
    """Helper function to get the next CourseID."""
    cursor = cnx.cursor()
    cursor.execute("SELECT MAX(CourseID) FROM Course")
    max_id = cursor.fetchone()[0]
    cursor.close()

    if max_id is None:
        return 1
    else:
        return int(max_id) + 1