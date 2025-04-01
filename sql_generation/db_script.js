
const mysql = require('mysql2/promise');
const fs = require('fs/promises');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// Function to clean up SQL file for Node.js execution
function cleanSqlForNode(sql) {
  return sql
      .replace(/DELIMITER\s+\S+/g, '')  // Remove DELIMITER lines
      .replace(/END\s*\/\/\s*/g, 'END;') // Replace END// with END;
      .replace(/;\s*\n/g, ';\n') // Ensure proper semicolon handling
      .trim();
}
async function executeSqlFiles(files) {
  // console.log('PROCESS.ENV:', process.env);
  // console.log("DB_USER:", process.env.DB_USER);
  // console.log("DB_PASSWORD:", process.env.DB_PASSWORD);
  // console.log("DB_HOST:", process.env.DB_HOST);
  // console.log("DB_NAME:", process.env.DB_NAME);
  // console.log("DB_PORT:", process.env.DB_PORT);

  let connection;

  try {
    // Execute create_db.sql first (create the database)
    connection = await mysql.createConnection({
      host: process.env.DB_HOST,
      user: process.env.DB_USER,
      password: process.env.DB_PASSWORD,
      port: process.env.DB_PORT,
    });

    // Read the SQL from create_database.sql
    const createDbSql = await fs.readFile('create_database.sql', 'utf8');

    // Split SQL into individual statements
    const queries = createDbSql
        .split(';')  // Split by semicolon
        .map(query => query.trim())  // Trim each query
        .filter(query => query.length > 0);  // Remove empty queries

    // Execute each SQL statement separately
    for (const query of queries) {
      await connection.query(query);
    }

    console.log('Executed create_database.sql (database created)');
    await connection.end(); // Close this connection

    // Establish a new connection *to the created database*
    connection = await mysql.createConnection({
      host: process.env.DB_HOST,
      user: process.env.DB_USER,
      password: process.env.DB_PASSWORD,
      database: process.env.DB_NAME, // Connect to the database
      port: process.env.DB_PORT,
    });

    // Loop through the other SQL files
    for (const file of files) {
      if (file !== 'create_database.sql') { // Skip create_db.sql (already executed)
        let sql = await fs.readFile(file, 'utf8');

        //Clean up sql delimiter
        sql = cleanSqlForNode(sql);

        // Split SQL into individual statements
        const fileQueries = sql
            .split(/;\s*(?!\s*END)/)  // Split by semicolon, but not inside BEGIN...END
            .map(query => query.trim())  // Trim each query
            .filter(query => query.length > 0);  // Remove empty queries

        // Execute each SQL statement separately
        for (const query of fileQueries) {
          await connection.query(query);
        }

        console.log(`Executed ${file}`);
      }
    }
  } catch (error) {
    console.error('Error executing SQL files:', error);
  } finally {
    if (connection) await connection.end();
  }

}

const sqlFiles = [
    'create_database.sql',
   'create_tables.sql',
   'create_views.sql',
   'insert_users.sql',
   'insert_lecturers.sql',
'insert_students.sql',
'insert_courses.sql',
'insert_course_lecturer.sql',
'insert_enrollments.sql',
'insert_assignments.sql',
'insert_forums.sql',
'insert_threads.sql',
'insert_events.sql'
];

executeSqlFiles(sqlFiles).then(
    // r => console.log('All SQL files executed successfully.')
);
