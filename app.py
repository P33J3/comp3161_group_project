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
generate_salt, generate_hashed_password, authenticate_user, get_next_user_id,
get_next_student_id, get_next_lec_id, create_jwt, decode_jwt, token_required)
from .forms import *


### ----------LOAD---------- ###

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']
# app.config['VALID_DEPARTMENTS']

csrf = CSRFProtect(app)

app.register_blueprint(courses_bp)
app.register_blueprint(content_bp)
app.register_blueprint(views_bp)

#  python -m venv venv
# .\venv\Scripts\activate
# flask --app app --debug run


### ----------BACKEND---------- ###


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    token, error = authenticate_user(username, password, app.config)
    if token:
        return jsonify({'token': token}), 200
    else:
        return jsonify({'message': error}), 401



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


@app.route('/forums/<int:course_id>', methods=['GET'])
def get_forums(course_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Forum WHERE CourseId = %s", (course_id,))
        forums = cursor.fetchall()
        return jsonify(forums), 200
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve forums: {str(e)}'}), 500
    finally:
        cnx.close()

@app.route('/create_thread', methods=['POST'])
def create_thread():
    data = request.get_json()
    forum_id = data.get('forum_id')
    user_id = data.get('user_id')
    title = data.get('title')
    post = data.get('post')

    if not forum_id or not user_id or not title or not post:
        return jsonify({'message': 'Missing thread data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT MAX(ThreadId) FROM DiscussionThread")
        next_id = cursor.fetchone()[0] or 0
        thread_id = next_id + 1
        cursor.execute("INSERT INTO DiscussionThread (ThreadId, ForumId, UserId, Title, Post) VALUES (%s, %s, %s, %s, %s)",
                       (thread_id, forum_id, user_id, title, post))
        cnx.commit()
        return jsonify({'message': 'Thread created successfully'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to create thread: {str(e)}'}), 500
    finally:
        cnx.close()

@app.route('/retrieve_thread/<int:thread_id>', methods=['GET'])
def retrieve_thread(thread_id):
    cnx = connect_to_mysql()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM DiscussionThread WHERE ThreadId = %s", (thread_id,))
        thread = cursor.fetchone()
        return jsonify(thread), 200
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve thread: {str(e)}'}), 500
    finally:
        cnx.close()

@app.route('/post_reply', methods=['POST'])
def post_reply():
    data = request.get_json()
    parent_thread_id = data.get('thread_id')
    user_id = data.get('user_id')
    reply_text = data.get('reply_text')

    if not parent_thread_id or not user_id or not reply_text:
        return jsonify({'message': 'Missing reply data'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT MAX(ThreadId) FROM DiscussionThread")
        next_id = cursor.fetchone()[0] or 0
        reply_id = next_id + 1
        cursor.execute("INSERT INTO DiscussionThread (ThreadId, ForumId, UserId, Title, Post) \
                       SELECT %s, ForumId, %s, %s, %s FROM DiscussionThread WHERE ThreadId = %s",
                       (reply_id, user_id, f"Reply to {parent_thread_id}", reply_text, parent_thread_id))
        cnx.commit()
        return jsonify({'message': 'Reply posted successfully'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to post reply: {str(e)}'}), 500
    finally:
        cnx.close()

@app.route('/grade_submission/<int:submission_id>', methods=['POST'])
def grade_submission(submission_id):
    data = request.get_json()
    grade = data.get('grade')
    feedback = data.get('feedback')

    if grade is None:
        return jsonify({'message': 'Grade is required'}), 400

    cnx = connect_to_mysql()
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT MAX(GradeId) FROM Grade")
        next_id = cursor.fetchone()[0] or 0
        grade_id = next_id + 1
        cursor.execute("INSERT INTO Grade (GradeId, SubmissionId, Grade, Feedback) VALUES (%s, %s, %s, %s)",
                       (grade_id, submission_id, grade, feedback))
        cnx.commit()
        return jsonify({'message': 'Grade submitted successfully'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to submit grade: {str(e)}'}), 500
    finally:
        cnx.close()


### ----------FRONTEND---------- ###



@app.route('/', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        token, error = authenticate_user(form.username.data, form.password.data, app.config)
        if token:
            session['token'] = token
            session['user'] = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            return redirect(url_for('dashboard_page'))
        flash(error or 'Login failed.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register_page', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        success, error = register_user(form, app.config)
        if success:
            flash('Registration successful!', 'success')
            return redirect(url_for('login_page'))
        flash(error or 'Registration failed.', 'danger')
    return render_template('register.html', form=form)


@app.route('/create_course_page', methods=['GET', 'POST'])
def create_course_page():
    form = CreateCourseForm()
    if form.validate_on_submit():
        success, error = create_course(form, session['user'], app.config)
        if success:
            flash('Course created successfully.', 'success')
            return redirect(url_for('dashboard_page'))
        flash(error or 'Failed to create course.', 'danger')
    return render_template('create_course.html', form=form)


@app.route('/register_for_course_page', methods=['GET', 'POST'])
def register_for_course_page():
    form = RegisterForCourseForm()
    if form.validate_on_submit():
        success, error = register_for_course(form.course_id.data, session['user'], app.config)
        if success:
            flash('Successfully registered for the course!', 'success')
            return redirect(url_for('dashboard_page'))
        flash(error or 'Failed to register for the course.', 'danger')
    return render_template('register_for_course.html', form=form)


@app.route('/my_courses_page')
def my_courses_page():
    user = session.get('user')
    if not user:
        return redirect(url_for('login_page'))

    user_id = user['UserId']
    role = user['Role']

    if role == 'student':
        response = retrieve_courses_for_student(user_id)
    elif role == 'lecturer':
        response = retrieve_courses_for_lecturer(user_id)
    else:
        response = retrieve_courses()

    courses = response.get_json() if response.status_code == 200 else []
    return render_template('my_courses.html', courses=courses)


@app.route('/course_page/<int:course_id>')
def course_detail_page(course_id):
    response = retrieve_members(course_id)
    members = response.get_json() if response.status_code == 200 else []
    return render_template('course_detail.html', course_id=course_id, members=members)


@app.route('/retrieve_calendar_events_for_student_page')
def retrieve_calendar_events_for_student_page():
    user = session.get('user')
    if not user:
        return redirect(url_for('login_page'))

    data = {
        'user_id': user['UserId'],
        'event_date': datetime.date.today().strftime('%Y-%m-%d')
    }
    response = retrieve_calendar_events_for_student(data)
    events = response.get_json() if response.status_code == 200 else []
    return render_template('calendar_events.html', events=events)


@app.route('/retrieve_calendar_events_page/<int:course_id>')
def retrieve_calendar_events_page(course_id):
    response = retrieve_calendar_events(course_id)
    events = response.get_json() if response.status_code == 200 else []
    return render_template('calendar_events.html', events=events)


@app.route('/submit_assignment_page/<int:assignment_id>', methods=['GET', 'POST'])
def submit_assignment_page(assignment_id):
    form = AssignmentSubmissionForm()
    if form.validate_on_submit():
        success, error = submit_assignment(assignment_id, form.assignment_file.data, session['user']['UserId'], app.config)
        if success:
            flash('Assignment submitted successfully.', 'success')
            return redirect(url_for('dashboard_page'))
        flash(error or 'Failed to submit assignment.', 'danger')
    return render_template('uploadsubmission.html', form=form)


@app.route('/forums_page/<int:course_id>')
def forums_page(course_id):
    response = get_forums(course_id)
    forums = response.get_json() if response.status_code == 200 else []
    return render_template('forums.html', forums=forums)


@app.route('/create_thread_page/<int:forum_id>', methods=['GET', 'POST'])
def create_thread_page(forum_id):
    form = CreateThreadForm()
    if form.validate_on_submit():
        data = {
            'forum_id': forum_id,
            'user_id': session['user']['UserId'],
            'title': form.title.data,
            'post': form.post.data
        }
        response = create_thread(data)
        if response.status_code == 201:
            flash('Thread created.', 'success')
            return redirect(url_for('forums_page', course_id=forum_id))
        flash('Failed to create thread.', 'danger')
    return render_template('create_thread.html', form=form)


@app.route('/thread_page/<int:thread_id>', methods=['GET', 'POST'])
def thread_page(thread_id):
    form = ReplyForm()
    response = retrieve_thread(thread_id)
    thread = response.get_json() if response.status_code == 200 else {}
    if form.validate_on_submit():
        data = {
            'thread_id': thread_id,
            'user_id': session['user']['UserId'],
            'reply_text': form.reply_text.data
        }
        reply_response = post_reply(data)
        if reply_response.status_code == 201:
            flash('Reply posted.', 'success')
            return redirect(url_for('thread_page', thread_id=thread_id))
        flash('Failed to post reply.', 'danger')
    return render_template('thread_detail.html', form=form, replies=[thread] if thread else [])


@app.route('/grade_assignment_page/<int:submission_id>', methods=['GET', 'POST'])
def grade_assignment_page(submission_id):
    form = GradeSubmissionForm()
    if form.validate_on_submit():
        data = {
            'grade': form.grade.data,
            'feedback': form.feedback.data
        }
        response = grade_submission(submission_id, data)
        if response.status_code == 201:
            flash('Grade submitted.', 'success')
            return redirect(url_for('dashboard_page'))
        flash('Failed to submit grade.', 'danger')
    return render_template('grade_assignment.html', form=form)


@app.route('/reports_page')
def reports_page():
    return render_template('reports.html')

### Reports go here ###
