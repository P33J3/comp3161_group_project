from flask import Blueprint, jsonify, request, current_app as app
from .utilities import connect_to_mysql, token_required
from .config import Config

views_bp = Blueprint('views', __name__)

#Courses with 50 or more students
@views_bp.route('/courses/high-enrollment', methods=['GET'])
@token_required
def get_high_enrollment_courses(user_data):
    """
    Retrieves a list of courses with 50 or more students enrolled,
    based on the 'courseswith50plusstudents' database view.
    Accessible by admins and lecturers.
    """
    # Define roles allowed to access this view/report
    allowed_roles = ['admin', 'lecturer']
    if user_data['role'] not in allowed_roles:
        return jsonify({'message': 'Access denied: Insufficient privileges'}), 403

    cnx = None
    cursor = None
    try:
        cnx = connect_to_mysql(app.config)
        cursor = cnx.cursor(dictionary=True) # Use dictionary cursor

        cursor.execute("""
            SELECT *
            FROM `courseswith50plusstudents`
        """)

        courses_raw = cursor.fetchall()
        courses_list = []

        for course_row in courses_raw:

            # Append formatted data to the list
            courses_list.append({
                "course_id": course_row.get('CourseId'),
                "course_name": course_row.get('CourseName'),
                "student_count": course_row.get('NumberOfStudents')
            })

        return jsonify(courses_list), 200

    except Exception as e:
        # Check for specific error like table/view not found (MySQL error code 1146)
        if "1146" in str(e):
             app.logger.error(f"Error accessing view 'courseswith50plusstudents': View might not exist. {e}", exc_info=True)
             return jsonify({'message': "Database view 'courseswith50plusstudents' not found or inaccessible."}), 500
        else:
             app.logger.error(f"Error retrieving high enrollment courses: {e}", exc_info=True)
             return jsonify({'message': f'Failed to retrieve high enrollment courses: {str(e)}'}), 500
    finally:
        # Ensure resources are closed even if errors occur
        if cursor: cursor.close()
        if cnx: cnx.close()


#Lecturers with 3 or more courses
@views_bp.route('/lecturers/high-workload', methods=['GET'])
@token_required
def get_high_workload_lecturers(user_data):
    """
    Retrieves a list of lecturers teaching 3 or more courses,
    based on the 'lecturerswith3pluscourses' database view.
    Accessible by admins.
    """

    allowed_roles = ['admin']
    if user_data['role'] not in allowed_roles:
        return jsonify({'message': 'Access denied: Insufficient privileges'}), 403

    cnx = None
    cursor = None
    try:
        cnx = connect_to_mysql(app.config)
        cursor = cnx.cursor(dictionary=True) # Use dictionary cursor

        cursor.execute("""
            SELECT *
            FROM `lecturerswith3pluscourses`
        """)

        lecturers_raw = cursor.fetchall()
        lecturers_list = []

        for lec_row in lecturers_raw:

            # Append formatted data to the list
            lecturers_list.append({
                "lecturer_id": lec_row.get('LecId'),
                "first_name": lec_row.get('LecFirstName'),
                "last_name": lec_row.get('LecLastName'),
                "course_count": lec_row.get('NumberOfCourses')
            })

        return jsonify(lecturers_list), 200

    except Exception as e:
        # Check for specific error like table/view not found (MySQL error code 1146)
        if "1146" in str(e):
             app.logger.error(f"Error accessing view 'lecturerswith3pluscourses': View might not exist. {e}", exc_info=True)
             return jsonify({'message': "Database view 'lecturerswith3pluscourses' not found or inaccessible."}), 500
        else:
             app.logger.error(f"Error retrieving high workload lecturers: {e}", exc_info=True)
             return jsonify({'message': f'Failed to retrieve high workload lecturers: {str(e)}'}), 500
    finally:
        # Ensure resources are closed even if errors occur
        if cursor: cursor.close()
        if cnx: cnx.close()

#Students with 5 or more courses
@views_bp.route('/students/high-load', methods=['GET'])
@token_required
def get_high_load_students(user_data):
    """
    Retrieves a list of students enrolled in 5 or more courses,
    based on the 'studentswith5pluscourses' database view.
    Accessible by admins and lecturers.
    """
    # Define roles allowed to access this view/report
    allowed_roles = ['admin', 'lecturer']
    if user_data['role'] not in allowed_roles:
        return jsonify({'message': 'Access denied: Insufficient privileges'}), 403

    cnx = None
    cursor = None
    try:
        cnx = connect_to_mysql(app.config)
        cursor = cnx.cursor(dictionary=True) # Use dictionary cursor

        cursor.execute("""
            SELECT *
            FROM `studentswith5pluscourses`

        """)

        students_raw = cursor.fetchall()
        students_list = []

        for student_row in students_raw:

           # Append formatted data to the list
            students_list.append({
                "student_id": student_row.get('StudentID'),
                "first_name": student_row.get('FirstName'),
                "last_name": student_row.get('LastName'),
                "course_count": student_row.get('NumberOfCourses')
            })

        return jsonify(students_list), 200

    except Exception as e:
        # Check for specific error like table/view not found (MySQL error code 1146)
        if "1146" in str(e):
             app.logger.error(f"Error accessing view 'studentswith5pluscourses': View might not exist. {e}", exc_info=True)
             return jsonify({'message': "Database view 'studentswith5pluscourses' not found or inaccessible."}), 500
        else:
             app.logger.error(f"Error retrieving high load students: {e}", exc_info=True)
             return jsonify({'message': f'Failed to retrieve high load students: {str(e)}'}), 500
    finally:
        # Ensure resources are closed even if errors occur
        if cursor: cursor.close()
        if cnx: cnx.close()

#Top 10 Enrolled Courses
@views_bp.route('/courses/top-enrolled', methods=['GET'])
@token_required
def get_top_10_enrolled_courses(user_data):
    """
    Retrieves the top 10 courses based on student enrollment count,
    based on the 'top10enrolledcourses' database view.
    Accessible by admins and lecturers.
    """
    # Define roles allowed to access this view/report
    allowed_roles = ['admin', 'lecturer']
    if user_data['role'] not in allowed_roles:
        return jsonify({'message': 'Access denied: Insufficient privileges'}), 403

    cnx = None
    cursor = None
    try:
        cnx = connect_to_mysql(app.config)
        cursor = cnx.cursor(dictionary=True) # Use dictionary cursor

        cursor.execute("""
            SELECT *
            FROM `top10enrolledcourses`
        """) # The view should already be ordered and limited

        top_courses_raw = cursor.fetchall()
        top_courses_list = []

        for course_row in top_courses_raw:

            # Append formatted data to the list
            top_courses_list.append({
                "course_id": course_row.get('CourseId'),
                "course_name": course_row.get('CourseName'),
                "enrollment_count": course_row.get('NumberOfStudents')
            })

        return jsonify(top_courses_list), 200

    except Exception as e:
        # Check for specific error like table/view not found (MySQL error code 1146)
        if "1146" in str(e):
             app.logger.error(f"Error accessing view 'top10enrolledcourses': View might not exist. {e}", exc_info=True)
             return jsonify({'message': "Database view 'top10enrolledcourses' not found or inaccessible."}), 500
        else:
             app.logger.error(f"Error retrieving top 10 enrolled courses: {e}", exc_info=True)
             return jsonify({'message': f'Failed to retrieve top 10 enrolled courses: {str(e)}'}), 500
    finally:
        # Ensure resources are closed even if errors occur
        if cursor: cursor.close()
        if cnx: cnx.close()


#Top 10 Students
@views_bp.route('/students/top-performers', methods=['GET'])
@token_required
def get_top_10_students(user_data):
    """
    Retrieves the top 10 students based on their average grade across all courses,
    based on the 'top10studentsbyaverage' database view.
    Accessible by admins and lecturers.
    """
    # Define roles allowed to access this performance view/report
    allowed_roles = ['admin', 'lecturer']
    if user_data['role'] not in allowed_roles:
        return jsonify({'message': 'Access denied: Insufficient privileges'}), 403

    cnx = None
    cursor = None
    try:
        cnx = connect_to_mysql(app.config)
        cursor = cnx.cursor(dictionary=True) # Use dictionary cursor


        cursor.execute("""
            SELECT *
            FROM `top10studentsbyaverage`
        """)

        top_students_raw = cursor.fetchall()
        top_students_list = []

        for student_row in top_students_raw:

            # Append formatted data to the list
            top_students_list.append({
                "student_id": student_row.get('StudentID'),
                "first_name": student_row.get('FirstName'),
                "last_name": student_row.get('LastName'),
                "average_grade": student_row.get('OverallAverage')
            })

        return jsonify(top_students_list), 200

    except Exception as e:
        # Check for specific error like table/view not found (MySQL error code 1146)
        if "1146" in str(e):
             app.logger.error(f"Error accessing view 'top10studentsbyaverage': View might not exist. {e}", exc_info=True)
             return jsonify({'message': "Database view 'top10studentsbyaverage' not found or inaccessible."}), 500
        else:
             app.logger.error(f"Error retrieving top 10 students: {e}", exc_info=True)
             return jsonify({'message': f'Failed to retrieve top 10 students: {str(e)}'}), 500
    finally:
        # Ensure resources are closed even if errors occur
        if cursor: cursor.close()
        if cnx: cnx.close()