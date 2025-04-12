from flask import Blueprint, jsonify, request, current_app as app
from .utilities import connect_to_mysql, token_required
from .config import Config
from .utilities import get_next_course_code, get_next_course_id

courses_bp = Blueprint('courses', __name__)



@courses_bp.route('/courses', methods=['POST'])
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