from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    SelectField, IntegerField, FileField, DateField, TimeField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email
from flask_wtf.file import FileAllowed


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=255)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=255)])
    password = PasswordField('Password', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=255)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=255)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('student', 'Student'), ('lecturer', 'Lecturer')], validators=[DataRequired()])
    department = StringField('Department (if Lecturer)', validators=[Optional()])
    submit = SubmitField('Register')


class CreateCourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired(), Length(max=255)])
    department = StringField('Department', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Create Course')


class RegisterForCourseForm(FlaskForm):
    course_code = StringField('Course Code', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Register')


class AssignmentSubmissionForm(FlaskForm):
    assignment_file = FileField('Upload Submission', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'zip', 'txt'], 'Allowed file types: pdf, doc, docx, zip, txt'),
        DataRequired()
    ])
    submit = SubmitField('Submit Assignment')


class CreateEventForm(FlaskForm):
    event_date = DateField('Event Date', validators=[DataRequired()])
    event_time = TimeField('Event Time', validators=[DataRequired()])
    description = TextAreaField('Event Description', validators=[DataRequired()])
    submit = SubmitField('Create Event')


class AddContentForm(FlaskForm):
    section = IntegerField('Section Number', validators=[DataRequired()])
    content_file = FileField('Upload File (Optional)', validators=[
        FileAllowed(['pdf', 'ppt', 'pptx', 'docx', 'mp4', 'jpg', 'png'], 'Unsupported file type')
    ])
    metadata = TextAreaField('Metadata or Description', validators=[Optional()])
    submit = SubmitField('Add Content')


class CreateThreadForm(FlaskForm):
    title = StringField('Thread Title', validators=[DataRequired(), Length(max=255)])
    post = TextAreaField('Initial Post', validators=[DataRequired()])
    submit = SubmitField('Create Thread')


class ReplyForm(FlaskForm):
    reply_text = TextAreaField('Your Reply', validators=[DataRequired()])
    submit = SubmitField('Post Reply')


class GradeSubmissionForm(FlaskForm):
    grade = IntegerField('Grade (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    feedback = TextAreaField('Feedback (Optional)', validators=[Optional()])
    submit = SubmitField('Submit Grade')
