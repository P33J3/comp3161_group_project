import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    # MYSQL_DATBASE_URI = os.getenv('DATABASE_URI')
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'your_user'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'your_password'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'your_database'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS') or 1)