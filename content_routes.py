from flask import Blueprint, jsonify, request, current_app as app
from .utilities import connect_to_mysql, token_required
from .config import Config
from datetime import datetime

content_bp = Blueprint('content', __name__)


@content_bp.route('/course/<int:course_id>/content', methods=['POST'])
@token_required
def add_course_content(user_data, course_id):
    """
    Adds course content to a specific course.

    Content can be links, files, or slides.
    Content is organized by sections.
    """
    if user_data['role'] not in ['admin', 'lecturer']:
        return jsonify({'message': 'Access denied: Only lecturers and admins can add course content'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'message': 'No content data provided'}), 400

    section = data.get('section')
    content = data.get('content')  # Can be a link, file data, or slides data
    metadata = data.get('metadata')  # Additional info (e.g., file type, description)

    if not section or not content:
        return jsonify({'message': 'Section and content are required'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the course exists
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        # Get the next available ContentId
        cursor.execute("SELECT MAX(ContentId) FROM CourseContent")
        max_content_id = cursor.fetchone()[0]
        next_content_id = 1 if max_content_id is None else max_content_id + 1

        cursor.execute("""
            INSERT INTO CourseContent (ContentId, CourseId, Section, Content, Metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (next_content_id, course_id, section, str(content), str(metadata)))

        cnx.commit()
        return jsonify({'message': 'Course content added successfully', 'content_id': next_content_id}), 201

    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to add course content: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()


@content_bp.route('/course/<int:course_id>/content', methods=['GET'])
@token_required
def get_course_content(user_data, course_id):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    # Use a dictionary cursor for easier access by column name
    cursor = cnx.cursor(dictionary=True) # <-- Change: Use dictionary cursor

    try:
        # Check if the course exists
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        cursor.execute("""
            SELECT ContentId, Section, Content, Metadata
            FROM CourseContent
            WHERE CourseId = %s
        """, (course_id,))

        content_list = []
        content_data = cursor.fetchall()

        for content_row in content_data: # Renamed loop variable for clarity
            section_value = content_row.get('Section')
            content_value = content_row.get('Content')
            metadata_value = content_row.get('Metadata')

            # Decode Section if it's bytes (might be VARCHAR/TEXT)
            if isinstance(section_value, bytes):
                try:
                    section_string = section_value.decode('utf-8')
                except UnicodeDecodeError:
                    section_string = f"[Binary data Section: {len(section_value)} bytes]"
            else:
                # Use str() for other types (like INT) or if already a string
                section_string = str(section_value) if section_value is not None else None

            # Decode Content if it's bytes (likely BLOB/TEXT)
            if isinstance(content_value, bytes):
                 try:
                     # Attempt to decode assuming UTF-8, adjust if needed
                     content_string = content_value.decode('utf-8')
                 except UnicodeDecodeError:
                     # Fallback if decoding fails (e.g., binary data)
                     content_string = f"[Binary data Content: {len(content_value)} bytes]"
            else:
                 # Use str() for other types or if already a string
                 content_string = str(content_value) if content_value is not None else None

            # Decode Metadata if it's bytes (likely TEXT)
            if isinstance(metadata_value, bytes):
                try:
                    metadata_string = metadata_value.decode('utf-8')
                except UnicodeDecodeError:
                    metadata_string = f"[Binary data Metadata: {len(metadata_value)} bytes]"
            else:
                metadata_string = str(metadata_value) if metadata_value is not None else None

            content_list.append({
                "content_id": content_row.get('ContentId'),
                "section": section_string,
                "content": content_string,
                "metadata": metadata_string
            })

        return jsonify(content_list), 200

    except Exception as e:
        # Log the full error for debugging
        app.logger.error(f"Error retrieving course content for course {course_id}: {e}", exc_info=True)
        return jsonify({'message': f'Failed to retrieve course content: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()


@content_bp.route('/course/<int:course_id>/assignments', methods=['POST'])
@token_required
def create_assignment(user_data, course_id):
    """
    Creates a new assignment for a specific course.
    """
    if user_data['role'] not in ['admin', 'lecturer']:
        return jsonify({'message': 'Access denied: Only lecturers and admins can create assignments'}), 403

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    due_date_str = data.get('due_date')

    if not title or not description or not due_date_str:
        return jsonify({'message': 'Title, description, and due date are required'}), 400

    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({'message': 'Invalid due date format. Use YYYY-MM-DD HH:MM:SS'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the course exists
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        # Get the next available AssignmentId
        cursor.execute("SELECT MAX(AssignmentId) FROM Assignment")
        max_assignment_id = cursor.fetchone()[0]
        next_assignment_id = 1 if max_assignment_id is None else max_assignment_id + 1

        cursor.execute("""
            INSERT INTO Assignment (AssignmentId, CourseId, Title, Description, DueDate)
            VALUES (%s, %s, %s, %s, %s)
        """, (next_assignment_id, course_id, title, description, due_date))

        cnx.commit()
        return jsonify({'message': 'Assignment created successfully', 'assignment_id': next_assignment_id}), 201

    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to create assignment: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()

@content_bp.route('/course/<int:course_id>/assignments', methods=['GET'])
@token_required
def get_assignments(user_data, course_id):
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the course exists
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        cursor.execute("""
            SELECT AssignmentId, Title, Description, DueDate
            FROM Assignment
            WHERE CourseId = %s
        """, (course_id,))
        assignment_list = []
        assignment_data = cursor.fetchall()
        for assignment in assignment_data:
            assignment_list.append({
                "assignment_id": assignment[0],
                "title": assignment[1],
                "description": assignment[2],
                "due_date": assignment[3].strftime('%Y-%m-%d %H:%M:%S') # Convert datetime to string
            })

        return jsonify(assignment_list), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve assignments: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()

@content_bp.route('/assignment/<int:assignment_id>/submit', methods=['POST'])
@token_required
def submit_assignment(user_data, assignment_id):
    """
    Allows a student to submit an assignment.
    """
    if user_data['role'] != 'student':
        return jsonify({'message': 'Access denied: Only students can submit assignments'}), 403

    data = request.get_json()
    student_id = data.get('student_id')
    submission_content = data.get('submission')  # This can be a link, file data, etc.

    if not student_id or not submission_content:
        return jsonify({'message': 'Student ID and submission content are required'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the assignment exists
        cursor.execute("SELECT AssignmentId FROM Assignment WHERE AssignmentId = %s", (assignment_id,))
        assignment = cursor.fetchone()
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        # Check if the student exists
        cursor.execute("SELECT StudentID FROM Student WHERE StudentID = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        # Check if the student is enrolled in the course related to the assignment
        cursor.execute("""
            SELECT COUNT(*)
            FROM Enrollment E
            JOIN Assignment A ON E.CourseId = A.CourseId
            WHERE E.StudentID = %s AND A.AssignmentId = %s
        """, (student_id, assignment_id))

        is_enrolled = cursor.fetchone()[0]
        if not is_enrolled:
            return jsonify({'message': 'Student is not enrolled in the course associated with this assignment'}), 400


        # Check if a submission already exists for this assignment and student
        cursor.execute("SELECT * FROM Submission WHERE AssignmentId = %s AND StudentID = %s", (assignment_id, student_id))
        existing_submission = cursor.fetchone()
        if existing_submission:
            return jsonify({'message': 'Submission already exists for this assignment and student'}), 400


        # Get the next available SubmissionId
        cursor.execute("SELECT MAX(SubmissionId) FROM Submission")
        max_submission_id = cursor.fetchone()[0]
        next_submission_id = 1 if max_submission_id is None else max_submission_id + 1

        # Add the submission
        cursor.execute("""
            INSERT INTO Submission (SubmissionId, AssignmentId, StudentID, SubmissionContent)
            VALUES (%s, %s, %s, %s)
        """, (next_submission_id, assignment_id, student_id, submission_content))

        cnx.commit()
        return jsonify({'message': 'Assignment submitted successfully', 'submission_id': next_submission_id}), 201

    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to submit assignment: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()


@content_bp.route('/submission/<int:submission_id>/grade', methods=['POST'])
@token_required
def grade_submission(user_data, submission_id):
    """
    Allows a lecturer to grade a student's assignment submission.
    """
    if user_data['role'] not in ['admin', 'lecturer']:
        return jsonify({'message': 'Access denied: Only lecturers and admins can grade submissions'}), 403

    data = request.get_json()
    grade = data.get('grade')

    if grade is None:
        return jsonify({'message': 'Grade is required'}), 400
    if not 0 <= grade <= 100:
        return jsonify({'message': 'Grade must be between 0 and 100'}), 400

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the submission exists
        cursor.execute("SELECT SubmissionId FROM Submission WHERE SubmissionId = %s", (submission_id,))
        submission = cursor.fetchone()
        if not submission:
            return jsonify({'message': 'Submission not found'}), 404

        # Check if a grade already exists for this submission
        cursor.execute("SELECT * FROM Grade WHERE SubmissionId = %s", (submission_id,))
        existing_grade = cursor.fetchone()
        if existing_grade:
            return jsonify({'message': 'Grade already exists for this submission'}), 400

        # Get the next available GradeId
        cursor.execute("SELECT MAX(GradeId) FROM Grade")
        max_grade_id = cursor.fetchone()[0]
        next_grade_id = 1 if max_grade_id is None else max_grade_id + 1

        # Add the grade
        cursor.execute("""
            INSERT INTO Grade (GradeId, SubmissionId, Grade)
            VALUES (%s, %s, %s)
        """, (next_grade_id, submission_id, grade))

        cnx.commit()
        return jsonify({'message': 'Submission graded successfully', 'grade_id': next_grade_id}), 201

    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to grade submission: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()

@content_bp.route('/student/<int:student_id>/grades', methods=['GET'])
@token_required
def get_student_grades(user_data, student_id):
    """
    Retrieves all grades for a specific student.
    """
    if user_data['role'] not in ['admin', 'lecturer', 'student']:
        return jsonify({'message': 'Access denied'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the student exists
        cursor.execute("SELECT StudentID FROM Student WHERE StudentID = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        # Retrieve all grades for the student, including assignment details
        cursor.execute("""
            SELECT G.GradeId, A.Title, G.Grade, C.CourseName, E.StudentID
            FROM Grade G
            JOIN Submission S ON G.SubmissionId = S.SubmissionId
            JOIN Assignment A ON S.AssignmentId = A.AssignmentId
            JOIN Course C ON A.CourseId = C.CourseId
            JOIN Enrollment E ON C.CourseId = E.CourseId
            WHERE E.StudentID = %s
            ORDER BY C.CourseName, S.StudentID
        """, (student_id,))

        grades_list = []
        grades_data = cursor.fetchall()
        for grade in grades_data:
            grades_list.append({
                "grade_id": grade[0],
                "assignment_title": grade[1],
                "grade": grade[2],
                "course_name": grade[3],
                "student_id": grade[4]
            })

        return jsonify(grades_list), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve student grades: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()

#use new grades from grades tables to calculate or adjust grade in enrollments
@content_bp.route('/course/<int:course_id>/calculate-grades', methods=['POST'])
@token_required
def calculate_course_grades(user_data, course_id):
    """
    Calculates and updates grades in Enrollment table based on submitted assignments.
    Averages new assignment grades with existing enrollment grade if present.
    """
    if user_data['role'] not in ['admin', 'lecturer']:
        return jsonify({'message': 'Access denied: Only lecturers and admins can calculate grades'}), 403

    cnx = connect_to_mysql(app.config)
    cursor = cnx.cursor()

    try:
        # Check if the course exists
        cursor.execute("SELECT CourseID FROM Course WHERE CourseID = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            return jsonify({'message': 'Course not found'}), 404

        # Get all students enrolled in the course
        cursor.execute("SELECT StudentID FROM Enrollment WHERE CourseID = %s", (course_id,))
        student_ids = [row[0] for row in cursor.fetchall()]

        # Track students whose grades were updated
        updated_students = []

        for student_id in student_ids:
            # Calculate average grade for this student in this course from assignments
            cursor.execute("""
                SELECT AVG(G.Grade)
                FROM Grade G
                JOIN Submission S ON G.SubmissionId = S.SubmissionId
                JOIN Assignment A ON S.AssignmentId = A.AssignmentId
                WHERE S.StudentID = %s AND A.CourseID = %s
            """, (student_id, course_id))

            new_avg_grade = cursor.fetchone()[0]

            # If student has assignment grades
            if new_avg_grade is not None:
                # Check if there's an existing grade in Enrollment
                cursor.execute("""
                    SELECT Grade FROM Enrollment
                    WHERE StudentID = %s AND CourseID = %s
                """, (student_id, course_id))

                existing_grade_row = cursor.fetchone()
                existing_grade = existing_grade_row[0] if existing_grade_row and existing_grade_row[0] is not None else None

                if existing_grade is not None:
                    # Average the existing grade with the new grade
                    final_grade = (existing_grade + new_avg_grade) / 2
                else:
                    # Use the new grade directly if no existing grade
                    final_grade = new_avg_grade

                # Update the Enrollment record
                cursor.execute("""
                    UPDATE Enrollment
                    SET Grade = %s
                    WHERE StudentID = %s AND CourseID = %s
                """, (final_grade, student_id, course_id))

                updated_students.append(student_id)

        cnx.commit()
        return jsonify({
            'message': 'Grades calculated and updated successfully',
            'updated_students': updated_students,
            'total_updated': len(updated_students)
        }), 200

    except Exception as e:
        cnx.rollback()
        return jsonify({'message': f'Failed to calculate grades: {str(e)}'}), 500
    finally:
        cursor.close()
        cnx.close()