from flask import Blueprint, jsonify, request, current_app as app
from .utilities import connect_to_mysql, token_required
from .config import Config
from .utilities import get_next_course_code, get_next_course_id

courses_bp = Blueprint('courses', __name__)



@courses_bp.route('/createcourse', methods=['POST'])
@token_required
def create_course(user_data):
    if user_data['role'] != 'admin':
        return jsonify({'message': 'Only admins can create courses'}), 403

    data = request.get_json()
    course_name = data.get('course_name')
    department = data.get('department')

    if not course_name or not department:
        return jsonify({'message': 'Course name and department are required'}), 400

#     print(app.config['VALID_DEPARTMENTS'])
    if department not in app.config['VALID_DEPARTMENTS']:
        return jsonify({'message': 'Invalid department'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
      next_course_code = get_next_course_code(cnx, department)
      next_course_id = get_next_course_id(cnx)

      cursor.execute("INSERT INTO Course (CourseID, CourseName, CourseCode) VALUES (%s, %s, %s)",
      (next_course_id, course_name, next_course_code))
      cnx.commit()
      return jsonify({'message': 'Course created successfully', 'course_code': next_course_code}), 201
    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Course creation failed: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()



@courses_bp.route('/courses', methods=['GET'])
@token_required
def get_courses(user_data):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()



    try:
        cursor.execute("SELECT CourseID, CourseName, CourseCode FROM Course")
        courses = cursor.fetchall()
        courses_list = [{'CourseID': course[0], 'CourseName': course[1], 'CourseCode': course[2]} for course in courses]
        return jsonify(courses_list), 200
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve courses: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()


@courses_bp.route('/student/<int:student_id>/courses', methods=['GET'])
@token_required
def get_student_courses(user_data, student_id):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403


    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:

#         if user_data['role'] == 'student':
#                 cursor.execute("SELECT StudentID FROM Student WHERE UserId = %s", (user_data['user_id'],))
#                 result = cursor.fetchone()
#                 if not result:
#                     return jsonify({'message': 'Student not found'}), 404
#                 user_student_id = result[0]
#                 if user_student_id != student_id:
#                     return jsonify({'message': 'Access denied'}), 403

        cursor.execute("""SELECT Course.CourseID, CourseName, CourseCode FROM Course
        JOIN Enrollment ON Course.CourseID = Enrollment.CourseID WHERE StudentID = %s""", (student_id,))
        courses = cursor.fetchall()
        courses_list = [{'CourseID': course[0], 'CourseName': course[1], 'CourseCode': course[2]} for course in courses]
        return jsonify(courses_list), 200
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve student courses: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()

@courses_bp.route('/lecturer/<int:lecturer_id>/courses', methods=['GET'])
@token_required
def get_lecturer_courses(user_data, lecturer_id):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        cursor.execute("""SELECT Course.CourseID, CourseName, CourseCode FROM Course
        JOIN CourseLecturer ON Course.CourseID = CourseLecturer.CourseID WHERE LecID = %s""", (lecturer_id,))
        courses = cursor.fetchall()
        courses_list = [{'CourseID': course[0], 'CourseName': course[1], 'CourseCode': course[2]} for course in courses]
        return jsonify(courses_list), 200
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve lecturer courses: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()


@courses_bp.route('/course/<int:course_id>/lecturer/<int:lecturer_id>', methods=['POST'])
@token_required
def assign_lecturer_to_course(user_data, course_id, lecturer_id):
    if user_data['role'] not in ['admin', 'lecturer']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404
        course_result = cursor.fetchall() # Consume the result

        cursor.execute("SELECT LecId FROM Lecturer WHERE LecId = %s", (lecturer_id,))
        lecturer = cursor.fetchone()
        if not lecturer:
            return jsonify({'message': 'Lecturer not found'}), 404
        lecturer_result = cursor.fetchall() # Consume the result

        # Check if any lecturer is already assigned to the course
        cursor.execute("SELECT LecId FROM CourseLecturer WHERE CourseID = %s", (course_id,))
        existing_lecturer = cursor.fetchone()
        if existing_lecturer:
            return jsonify({'message': 'Course already has a lecturer assigned'}), 400
        existing_lecturer_result = cursor.fetchall() # Consume the result


        # Assign the lecturer to the course
        cursor.execute("INSERT INTO CourseLecturer (CourseID, LecID) VALUES (%s, %s)", (course_id, lecturer_id))
        cnx.commit()
        return jsonify({'message': 'Lecturer assigned to course successfully'}), 201
    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to assign lecturer to course: {str(e)}'}), 500
    finally:
#         cursor.close()
        cnx.close()

#students should be able to enroll in courses
@courses_bp.route('/student/<int:student_id>/course/<int:course_id>', methods=['POST'])
@token_required
def enroll_student_in_course(user_data, student_id, course_id):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        cursor.execute("SELECT StudentID FROM Student WHERE StudentID = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        # Check if the student is already enrolled in the course
        cursor.execute("SELECT * FROM Enrollment WHERE StudentID = %s AND CourseID = %s", (student_id, course_id))
        enrollment = cursor.fetchone()
        if enrollment:
            return jsonify({'message': 'Student is already enrolled in this course'}), 400

        #Check if the student is doing more than 6 courses
        cursor.execute("SELECT COUNT(*) FROM Enrollment WHERE StudentID = %s", (student_id,))
        count = cursor.fetchone()[0]
        if count >= 6:
            return jsonify({'message': 'Student cannot enroll in more than 6 courses'}), 400

        # Enroll the student in the course
        cursor.execute("INSERT INTO Enrollment (StudentID, CourseID) VALUES (%s, %s)", (student_id, course_id))
        cnx.commit()
        return jsonify({'message': 'Student enrolled in course successfully'}), 201
    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to enroll student in course: {str(e)}'}), 500
    finally:
        cnx.close()