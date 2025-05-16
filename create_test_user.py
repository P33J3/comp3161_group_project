import hashlib
import mysql.connector
from .config import Config

conn = None
cursor = None

# --- Test user details ---
username = 'testuser'
plain_password = 'abc123'
salt = '3f9d8a379f1c4dcab5e4fd2147201cf4'
hashed_password = hashlib.sha256((plain_password + salt).encode()).hexdigest()
user_id = 999
role = 'student'  # or 'lecturer' / 'admin'

# --- Connect to MySQL ---
try:
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

    cursor = conn.cursor()

    # --- Insert User ---
    query = """
        INSERT INTO User (UserId, Username, Password, Role, Salt)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, username, hashed_password, role, salt))
    conn.commit()

    print(f"✅ User '{username}' created successfully with password '{plain_password}'.")

except mysql.connector.Error as err:
    print(f"❌ Database error: {err}")

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
