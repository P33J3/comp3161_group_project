from flask import Flask, request, make_response, jsonify
import mysql.connector
import hashlib
import uuid
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

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
                return jsonify({'message': 'Login successful'}), 200
            else:
                return jsonify({'message': 'Invalid credentials'}), 401
        else:
            return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

    finally:
        cnx.close()

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


@app.route('/create_course', methods=['POST'])
def create_course():
    data = request.get_json()
    course_name = data.get('course_name')
    course_description = data.get('course_description')
    created_by = data.get('created_by')  # Admin user ID

    if not course_name or not created_by:
        return jsonify({'message': 'Missing course name or creator ID'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        cursor.execute("SELECT Role FROM User WHERE UserId = %s", (created_by,))
        user = cursor.fetchone()
        if not user or user[0] != 'admin':
            return jsonify({'message': 'Only admins can create courses'}), 403

        cursor.execute("INSERT INTO Courses (CourseName, CourseDescription, CreatedBy) VALUES (%s, %s, %s)",
                       (course_name, course_description, created_by))
        cnx.commit()
        return jsonify({'message': 'Course created successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to create course: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_courses', methods=['GET'])
def retrieve_courses():
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        cursor.execute("SELECT CourseId, CourseName, CourseDescription, CreatedAt FROM Courses WHERE IsActive = TRUE")
        courses = cursor.fetchall()
        return jsonify(courses), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve courses: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_courses_for_student/<int:user_id>', methods=['GET'])
def retrieve_courses_for_student(user_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT c.CourseId, c.CourseName, c.CourseDescription, c.CreatedAt
        FROM Courses c
        JOIN CourseRegistrations cr ON c.CourseId = cr.CourseId
        WHERE cr.UserId = %s AND cr.Role = 'student' AND c.IsActive = TRUE
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return jsonify(courses), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve courses for student: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_courses_for_lecturer/<int:user_id>', methods=['GET'])
def retrieve_courses_for_lecturer(user_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT c.CourseId, c.CourseName, c.CourseDescription, c.CreatedAt
        FROM Courses c
        JOIN CourseRegistrations cr ON c.CourseId = cr.CourseId
        WHERE cr.UserId = %s AND cr.Role = 'lecturer' AND c.IsActive = TRUE
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return jsonify(courses), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve courses for lecturer: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/register_for_course', methods=['POST'])
def register_for_course():
    data = request.get_json()
    course_id = data.get('course_id')
    user_id = data.get('user_id')
    role = data.get('role')  # 'student' or 'lecturer'

    if not course_id or not user_id or not role:
        return jsonify({'message': 'Missing course ID, user ID, or role'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        if role == 'lecturer':
            # Ensure only one lecturer is assigned to a course
            cursor.execute("SELECT COUNT(*) FROM CourseRegistrations WHERE CourseId = %s AND Role = 'lecturer'", (course_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'message': 'A lecturer is already assigned to this course'}), 400

        cursor.execute("INSERT INTO CourseRegistrations (CourseId, UserId, Role) VALUES (%s, %s, %s)",
                       (course_id, user_id, role))
        cnx.commit()
        return jsonify({'message': 'User registered for course successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to register for course: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_members/<int:course_id>', methods=['GET'])
def retrieve_members(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT u.UserId, u.Username, u.FullName, u.Email, cr.Role
        FROM Users u
        JOIN CourseRegistrations cr ON u.UserId = cr.UserId
        WHERE cr.CourseId = %s AND u.IsActive = TRUE
        ORDER BY cr.Role, u.FullName
        """
        cursor.execute(query, (course_id,))
        members = cursor.fetchall()
        return jsonify(members), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve members: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_calendar_events/<int:course_id>', methods=['GET'])
def retrieve_calendar_events(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT EventId, EventName, EventDescription, EventDate, CreatedBy, CreatedAt
        FROM CalendarEvents
        WHERE CourseId = %s
        ORDER BY EventDate
        """
        cursor.execute(query, (course_id,))
        events = cursor.fetchall()
        return jsonify(events), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve calendar events: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/retrieve_calendar_events_for_student', methods=['POST'])
def retrieve_calendar_events_for_student():
    data = request.get_json()
    user_id = data.get('user_id')
    event_date = data.get('event_date')

    if not user_id or not event_date:
        return jsonify({'message': 'Missing user ID or event date'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT ce.EventId, ce.EventName, ce.EventDescription, ce.EventDate, c.CourseName
        FROM CalendarEvents ce
        JOIN Courses c ON ce.CourseId = c.CourseId
        JOIN CourseRegistrations cr ON ce.CourseId = cr.CourseId
        WHERE cr.UserId = %s AND DATE(ce.EventDate) = DATE(%s) AND cr.Role = 'student'
        ORDER BY ce.EventDate
        """
        cursor.execute(query, (user_id, event_date))
        events = cursor.fetchall()
        return jsonify(events), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve calendar events for student: {str(e)}'}), 500

    finally:
        cnx.close()


@app.route('/create_calendar_event', methods=['POST'])
def create_calendar_event():
    data = request.get_json()
    course_id = data.get('course_id')
    event_name = data.get('event_name')
    event_description = data.get('event_description')
    event_date = data.get('event_date')
    created_by = data.get('created_by')

    if not course_id or not event_name or not event_date or not created_by:
        return jsonify({'message': 'Missing required event data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        cursor.execute("INSERT INTO CalendarEvents (CourseId, EventName, EventDescription, EventDate, CreatedBy) VALUES (%s, %s, %s, %s, %s)",
                       (course_id, event_name, event_description, event_date, created_by))
        cnx.commit()
        return jsonify({'message': 'Calendar event created successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to create calendar event: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Forums for a Course
@app.route('/forums/<int:course_id>', methods=['GET'])
def retrieve_forums(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT forum_id, forum_name, forum_description, created_at 
        FROM Forums 
        WHERE course_id = %s AND is_active = TRUE
        """
        cursor.execute(query, (course_id,))
        forums = cursor.fetchall()
        return jsonify(forums), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve forums: {str(e)}'}), 500

    finally:
        cnx.close()


# Create Forum for a Course
@app.route('/forums', methods=['POST'])
def create_forum():
    data = request.get_json()
    course_id = data.get('course_id')
    forum_name = data.get('forum_name')
    forum_description = data.get('forum_description')
    created_by = data.get('created_by')

    if not course_id or not forum_name or not created_by:
        return jsonify({'message': 'Missing required forum data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO Forums (course_id, forum_name, forum_description, created_by) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (course_id, forum_name, forum_description, created_by))
        cnx.commit()
        return jsonify({'message': 'Forum created successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to create forum: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Discussion Threads for a Forum
@app.route('/threads/<int:forum_id>', methods=['GET'])
def retrieve_threads(forum_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT dt.thread_id, dt.title, dt.post, dt.created_at, u.username, u.full_name
        FROM DiscussionThreads dt
        JOIN Users u ON dt.user_id = u.user_id
        WHERE dt.forum_id = %s AND dt.is_active = TRUE
        ORDER BY dt.created_at DESC
        """
        cursor.execute(query, (forum_id,))
        threads = cursor.fetchall()
        return jsonify(threads), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve threads: {str(e)}'}), 500

    finally:
        cnx.close()


# Add Discussion Thread to a Forum
@app.route('/threads', methods=['POST'])
def add_thread():
    data = request.get_json()
    forum_id = data.get('forum_id')
    user_id = data.get('user_id')
    title = data.get('title')
    post = data.get('post')

    if not forum_id or not user_id or not title or not post:
        return jsonify({'message': 'Missing required thread data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO DiscussionThreads (forum_id, user_id, title, post) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (forum_id, user_id, title, post))
        cnx.commit()
        return jsonify({'message': 'Thread added successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to add thread: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Replies for a Thread
@app.route('/replies/<int:thread_id>', methods=['GET'])
def retrieve_replies(thread_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT r.reply_id, r.post, r.parent_reply_id, r.created_at, u.username, u.full_name
        FROM Replies r
        JOIN Users u ON r.user_id = u.user_id
        WHERE r.thread_id = %s AND r.is_active = TRUE
        ORDER BY r.created_at
        """
        cursor.execute(query, (thread_id,))
        replies = cursor.fetchall()
        return jsonify(replies), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve replies: {str(e)}'}), 500

    finally:
        cnx.close()


# Reply to a Thread
@app.route('/replies', methods=['POST'])
def add_reply():
    data = request.get_json()
    thread_id = data.get('thread_id')
    user_id = data.get('user_id')
    parent_reply_id = data.get('parent_reply_id')
    post = data.get('post')

    if not thread_id or not user_id or not post:
        return jsonify({'message': 'Missing required reply data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO Replies (thread_id, user_id, parent_reply_id, post) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (thread_id, user_id, parent_reply_id, post))
        cnx.commit()
        return jsonify({'message': 'Reply added successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to add reply: {str(e)}'}), 500

    finally:
        cnx.close()


# Add Course Content
@app.route('/course_content', methods=['POST'])
def add_course_content():
    data = request.get_json()
    course_id = data.get('course_id')
    section = data.get('section')
    content_type = data.get('content_type')
    content = data.get('content')
    file_path = data.get('file_path')
    uploaded_by = data.get('uploaded_by')

    if not course_id or not section or not content_type or not uploaded_by:
        return jsonify({'message': 'Missing required course content data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO CourseContent (course_id, section, content_type, content, file_path, uploaded_by) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (course_id, section, content_type, content, file_path, uploaded_by))
        cnx.commit()
        return jsonify({'message': 'Course content added successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to add course content: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Course Content
@app.route('/course_content/<int:course_id>', methods=['GET'])
def retrieve_course_content(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT content_id, section, content_type, content, file_path, uploaded_by, created_at
        FROM CourseContent 
        WHERE course_id = %s AND is_active = TRUE
        ORDER BY section, created_at
        """
        cursor.execute(query, (course_id,))
        content = cursor.fetchall()
        return jsonify(content), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve course content: {str(e)}'}), 500

    finally:
        cnx.close()


# Create Assignment
@app.route('/assignments', methods=['POST'])
def create_assignment():
    data = request.get_json()
    course_id = data.get('course_id')
    assignment_name = data.get('assignment_name')
    assignment_description = data.get('assignment_description')
    due_date = data.get('due_date')
    total_points = data.get('total_points')
    created_by = data.get('created_by')

    if not course_id or not assignment_name or not due_date or not total_points or not created_by:
        return jsonify({'message': 'Missing required assignment data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO Assignments (course_id, assignment_name, assignment_description, due_date, total_points, created_by) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (course_id, assignment_name, assignment_description, due_date, total_points, created_by))
        cnx.commit()
        return jsonify({'message': 'Assignment created successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to create assignment: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Assignments for a Course
@app.route('/assignments/<int:course_id>', methods=['GET'])
def retrieve_assignments(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT assignment_id, assignment_name, assignment_description, due_date, total_points, created_at
        FROM Assignments
        WHERE course_id = %s AND is_active = TRUE
        ORDER BY due_date
        """
        cursor.execute(query, (course_id,))
        assignments = cursor.fetchall()
        return jsonify(assignments), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve assignments: {str(e)}'}), 500

    finally:
        cnx.close()


# Submit Assignment
@app.route('/assignment_submissions', methods=['POST'])
def submit_assignment():
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    student_id = data.get('student_id')
    submission_text = data.get('submission_text')
    file_path = data.get('file_path')

    if not assignment_id or not student_id:
        return jsonify({'message': 'Missing required submission data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        INSERT INTO AssignmentSubmissions (assignment_id, student_id, submission_text, file_path) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (assignment_id, student_id, submission_text, file_path))
        cnx.commit()
        return jsonify({'message': 'Assignment submitted successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to submit assignment: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Submissions for an Assignment
@app.route('/assignment_submissions/<int:assignment_id>', methods=['GET'])
def retrieve_submissions(assignment_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT s.submission_id, s.submission_text, s.file_path, s.submission_date, 
               s.grade, s.feedback, u.username, u.full_name
        FROM AssignmentSubmissions s
        JOIN Users u ON s.student_id = u.user_id
        WHERE s.assignment_id = %s
        ORDER BY s.submission_date
        """
        cursor.execute(query, (assignment_id,))
        submissions = cursor.fetchall()
        return jsonify(submissions), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve submissions: {str(e)}'}), 500

    finally:
        cnx.close()


# Retrieve Assignment Grades for a Student
@app.route('/assignment_grades/<int:student_id>', methods=['GET'])
def retrieve_assignment_grades(student_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT a.assignment_name, c.course_name, s.grade, s.feedback, s.submission_date, a.total_points
        FROM AssignmentSubmissions s
        JOIN Assignments a ON s.assignment_id = a.assignment_id
        JOIN Courses c ON a.course_id = c.course_id
        WHERE s.student_id = %s AND s.grade IS NOT NULL
        ORDER BY s.submission_date DESC
        """
        cursor.execute(query, (student_id,))
        grades = cursor.fetchall()
        return jsonify(grades), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve grades: {str(e)}'}), 500

    finally:
        cnx.close()


# Grade Assignment
@app.route('/grade_assignment', methods=['PUT'])
def grade_assignment():
    data = request.get_json()
    submission_id = data.get('submission_id')
    grade = data.get('grade')
    feedback = data.get('feedback')
    graded_by = data.get('graded_by')

    if not submission_id or grade is None or not graded_by:
        return jsonify({'message': 'Missing required grading data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        query = """
        UPDATE AssignmentSubmissions 
        SET grade = %s, feedback = %s, graded_by = %s, graded_at = CURRENT_TIMESTAMP
        WHERE submission_id = %s
        """
        cursor.execute(query, (grade, feedback, graded_by, submission_id))
        cnx.commit()
        return jsonify({'message': 'Assignment graded successfully'}), 200

    except Exception as e:
        return jsonify({'message': f'Failed to grade assignment: {str(e)}'}), 500

    finally:
        cnx.close()