import os
from dotenv import load_dotenv

load_dotenv()


class Config(object):
    # MYSQL_DATBASE_URI = os.getenv('DATABASE_URI')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'your_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'your_password')
    MYSQL_DB = os.getenv('MYSQL_DB', 'your_database')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS') or 1)
    COURSE_CODE_PREFIX_LENGTH = 3
    COURSE_CODE_NUMERICE_LENGTH = 3
    VALID_DEPARTMENTS =[ dept.strip() for dept in os.environ.get('DEPARTMENTS', '').split(',')
                        if dept.strip() ]  # Split by comma and remove whitespace
  # Or raise an exception, log an error, etc.