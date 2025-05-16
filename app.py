from flask import (
    Flask, render_template, redirect, url_for,
    session, flash, request
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import requests
import mysql.connector
import hashlib
import uuid
from .config import Config
import jwt
import os
import datetime
from functools import wraps # Import wraps for decorator
from .courses_routes import courses_bp
from .content_routes import content_bp
from .views_routes import views_bp
from .utilities import (connect_to_mysql,
generate_salt, generate_hashed_password, get_next_user_id,
get_next_student_id, get_next_lec_id, create_jwt, decode_jwt, token_required)
from .forms import (
    LoginForm, RegisterForm, CreateCourseForm, AssignmentSubmissionForm,
    CreateEventForm, AddContentForm, CreateForumForm, CreateThreadForm,
    ReplyForm, GradeSubmissionForm
)


### ----------LOAD---------- ###

API_BASE_URL = "http://localhost:5000"
app = Flask(__name__)
app.config.from_object(Config)
# app.config['VALID_DEPARTMENTS']

csrf = CSRFProtect(app)

app.register_blueprint(courses_bp)
app.register_blueprint(content_bp)
app.register_blueprint(views_bp)

#  python -m venv venv
# .\venv\Scripts\activate
# flask --app app --debug run


### ----------BACKEND---------- ###


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
    if role == 'admin' and department is None:
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
        cursor.close()
        cnx.close()


@app.route('/retrieve_members/<int:course_id>', methods=['GET'])
def retrieve_members(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)

    try:
        query = """
        SELECT u.UserId, u.Username, CONCAT(u.FirstName, ' ', u.LastName) AS FullName, u.Email, cr.Role
        FROM Users u
        JOIN CourseRegistrations cr ON u.UserId = cr.UserId
        WHERE cr.CourseId = %s AND u.IsActive = TRUE
        ORDER BY cr.Role, FullName
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


@app.route('/retrieve_calendar_events_for_student', methods=['GET'])
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

    try:
        datetime.strptime(event_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid event date format. Use YYYY-MM-DD.'}), 400

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


@app.route('/submit_assignment', methods=['POST'])
def submit_assignment():
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    student_id = data.get('student_id')
    submission_content = data.get('submission_content')

    if not assignment_id or not student_id or not submission_content:
        return jsonify({'message': 'Missing required data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM Assignment WHERE AssignmentId = %s", (assignment_id,))
        if cursor.fetchone()[0] == 0:
            return jsonify({'message': 'Invalid AssignmentId'}), 400

        cursor.execute("""
            INSERT INTO Submission (AssignmentId, StudentID, SubmissionContent)
            VALUES (%s, %s, %s)
        """, (assignment_id, student_id, submission_content))
        cnx.commit()
        return jsonify({'message': 'Assignment submitted successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'Failed to submit assignment: {str(e)}'}), 500

    finally:
        cursor.close()
        cnx.close()


### ----------FRONTEND---------- ###


@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        response = requests.post(f"{API_BASE_URL}/login", json={
            'username': form.username.data,
            'password': form.password.data
        })
        if response.status_code == 200:
            token = response.json().get('token')
            session['token'] = token
            session['user'] = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            return redirect(url_for('dashboard_page'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register_page', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        data = {
            'username': form.username.data,
            'password': form.password.data,
            'role': form.role.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'department': form.department.data if form.role.data == 'lecturer' else None
        }
        response = requests.post(f"{API_BASE_URL}/register", json=data)
        if response.status_code == 201:
            flash('Registration successful!', 'success')
            return redirect(url_for('login_page'))
        flash('Registration failed.', 'danger')
    return render_template('register.html', form=form)


@app.route('/logout_page')
def logout_page():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login_page'))


@app.route('/dashboard_page')
def dashboard_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')


@app.route('/create_course_page', methods=['GET', 'POST'])
def create_course_page():
    form = CreateCourseForm()
    if form.validate_on_submit():
        headers = {'Authorization': f"Bearer {session['token']}"}
        data = {
            'course_name': form.course_name.data,
            'course_description': form.course_description.data,
            'created_by': session['user']['UserId']
        }
        response = requests.post(f"{API_BASE_URL}/create_course", json=data, headers=headers)
        if response.status_code == 201:
            flash('Course created successfully.', 'success')
            return redirect(url_for('dashboard_page'))
        flash(response.json().get('message', 'Failed to create course'), 'danger')
    return render_template('create_course.html', form=form)


@app.route('/my_courses_page')
def my_courses_page():
    user = session.get('user')
    if not user:
        return redirect(url_for('login_page'))
    
    headers = {'Authorization': f"Bearer {session['token']}"}
    role = user['Role']
    user_id = user['UserId']

    if role == 'student':
        url = f"{API_BASE_URL}/retrieve_courses_for_student/{user_id}"
    elif role == 'lecturer':
        url = f"{API_BASE_URL}/retrieve_courses_for_lecturer/{user_id}"
    else:
        url = f"{API_BASE_URL}/retrieve_courses"

    response = requests.get(url, headers=headers)
    courses = response.json() if response.status_code == 200 else []
    return render_template('my_courses.html', courses=courses)


@app.route('/course_page/<int:course_id>')
def course_detail_page(course_id):
    headers = {'Authorization': f"Bearer {session['token']}"}
    response = requests.get(f"{API_BASE_URL}/retrieve_members/{course_id}", headers=headers)
    if response.status_code == 200:
        members = response.json()
    else:
        members = []
        flash('Failed to retrieve course members.', 'danger')
    return render_template('course_detail.html', course_id=course_id, members=members)


@app.route('/submit_assignment_page/<int:assignment_id>', methods=['GET', 'POST'])
def submit_assignment_page(assignment_id):
    form = AssignmentSubmissionForm()
    if form.validate_on_submit():
        headers = {'Authorization': f"Bearer {session['token']}"}
        data = {
            'assignment_id': assignment_id,
            'student_id': session['user']['UserId'],
            'submission_content': form.assignment_file.data
        }
        response = requests.post(f"{API_BASE_URL}/submit_assignment", json=data, headers=headers)
        if response.status_code == 201:
            flash('Assignment submitted successfully.', 'success')
            return redirect(url_for('dashboard_page'))
        flash(response.json().get('message', 'Failed to submit assignment'), 'danger')
    return render_template('uploadsubmission.html', form=form)


@app.route('/create_event_page/<int:course_id>', methods=['GET', 'POST'])
def create_event_page(course_id):
    form = CreateEventForm()
    if form.validate_on_submit():
        headers = {'Authorization': f"Bearer {session['token']}"}
        data = {
            'course_id': course_id,
            'event_name': form.event_name.data,
            'event_description': form.event_description.data,
            'event_date': str(form.event_date.data),
            'created_by': session['user']['UserId']
        }
        response = requests.post(f"{API_BASE_URL}/create_calendar_event", json=data, headers=headers)
        if response.status_code == 201:
            flash('Event created.', 'success')
            return redirect(url_for('course_detail_page', course_id=course_id))
        flash(response.json().get('message', 'Failed to create event'), 'danger')
    return render_template('create_event.html', form=form)


@app.route('/add_content_page/<int:course_id>', methods=['GET', 'POST'])
def add_content_page(course_id):
    form = AddContentForm()
    if form.validate_on_submit():
        flash('Content added (simulated).', 'success')
        return redirect(url_for('course_detail_page', course_id=course_id))
    return render_template('add_content.html', form=form)


@app.route('/forums_page/<int:course_id>')
def forums_page(course_id):
    headers = {'Authorization': f"Bearer {session['token']}"}
    response = requests.get(f"{API_BASE_URL}/forums/{course_id}", headers=headers)
    
    if response.status_code == 200:
        forums = response.json()
    else:
        forums = []
        flash('Failed to retrieve forums.', 'danger')
    
    return render_template('forums.html', forums=forums)


@app.route('/create_forum_page/<int:course_id>', methods=['GET', 'POST'])
def create_forum_page(course_id):
    form = CreateForumForm()
    if form.validate_on_submit():
        flash('Forum created.', 'success')
        return redirect(url_for('forums_page', course_id=course_id))
    return render_template('create_forum.html', form=form)


@app.route('/create_thread_page/<int:forum_id>', methods=['GET', 'POST'])
def create_thread_page(forum_id):
    form = CreateThreadForm()
    if form.validate_on_submit():
        flash('Thread created.', 'success')
        return redirect(url_for('forum_detail_page', forum_id=forum_id))
    return render_template('create_thread.html', form=form)


@app.route('/thread_page/<int:thread_id>', methods=['GET', 'POST'])
def thread_page(thread_id):
    form = ReplyForm()
    if form.validate_on_submit():
        flash('Reply posted.', 'success')
        return redirect(url_for('thread_page', thread_id=thread_id))
    return render_template('thread_detail.html', form=form, replies=[])


@app.route('/grade_assignment_page/<int:submission_id>', methods=['GET', 'POST'])
def grade_assignment_page(submission_id):
    form = GradeSubmissionForm()
    if form.validate_on_submit():
        flash('Grade submitted.', 'success')
        return redirect(url_for('dashboard_page'))
    return render_template('grade_assignment.html', form=form)


@app.route('/reports_page')
def reports_page():
    return render_template('reports.html')


@app.route('/reports/high_enrollment_page')
def high_enrollment_report_page():
    response = requests.get(f"{API_BASE_URL}/courses/high-enrollment", headers={'Authorization': f"Bearer {session['token']}"})
    data = response.json() if response.status_code == 200 else []
    return render_template('report_high_enrollment.html', data=data)


@app.route('/reports/top_students_page')
def top_students_report_page():
    response = requests.get(f"{API_BASE_URL}/students/top-performers", headers={'Authorization': f"Bearer {session['token']}"})
    data = response.json() if response.status_code == 200 else []
    return render_template('report_top_students.html', data=data)
