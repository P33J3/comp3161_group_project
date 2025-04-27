
const fs = require('fs');


// ===============================
// SQL Generation
// ===============================
/**
 * Generates SQL INSERT statements for the given table and data.
 * @param {string} tableName - The name of the table.
 * @param {Array} data - The data to insert.
 * @returns {string} - The SQL INSERT statements.
 */
function generateInsertStatements(tableName, data) {
    if (data.length === 0) return "";
    const columns = Object.keys(data[0]);
    let insertStatements = `INSERT INTO ${tableName} (${columns.join(', ')}) VALUES\n`;
    const values = data.map(item => {
        const valueStrings = columns.map(col => {
            let val = item[col];
            if (col === 'Password' || col === 'Salt' || typeof val === 'string') {
                val = val.replace(/'/g, "''");
                return `'${val}'`;
            } else {
                return val;
            }
        });
        return `(${valueStrings.join(', ')})`;
    }).join(',\n');
    insertStatements += values + ';\n\n';
    return insertStatements;
}

function generateCreateDatabaseStatement() {
    const createDatabaseStatement = `
DROP DATABASE IF EXISTS course_mgmt_db;
CREATE DATABASE IF NOT EXISTS course_mgmt_db;
USE course_mgmt_db;
    `;
    return createDatabaseStatement;
}

/**
 * Generates the CREATE TABLE statements for the database schema.
 * @returns {string} - The CREATE TABLE statements.
 */
function generateCreateTableStatements() {
    const createTableStatements = `


CREATE TABLE User (
    UserId INT PRIMARY KEY,
    Username VARCHAR(255) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL,
    Role VARCHAR(10) NOT NULL CHECK (Role IN ('admin', 'lecturer', 'student')),
    Salt VARCHAR(255) NOT NULL
);

CREATE TABLE Lecturer (
    LecId INT PRIMARY KEY,
    LecFirstName VARCHAR(255) NOT NULL,
    LecLastName VARCHAR(255) NOT NULL,
    Department VARCHAR(255) NOT NULL,
    UserId INT,
    FOREIGN KEY (UserId) REFERENCES User(UserId)
);

CREATE TABLE Course (
    CourseId INT PRIMARY KEY,
    CourseName VARCHAR(255) NOT NULL UNIQUE,
    CourseCode VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE CourseLecturer (
    CourseId INT,
    LecId INT,
    PRIMARY KEY (CourseId, LecId),
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId),
    FOREIGN KEY (LecId) REFERENCES Lecturer(LecId)
);

CREATE TABLE Student (
    StudentID INT PRIMARY KEY,
    FirstName VARCHAR(255) NOT NULL,
    LastName VARCHAR(255) NOT NULL,
    UserId INT,
    FOREIGN KEY (UserId) REFERENCES User(UserId)
);

CREATE TABLE Enrollment (
    StudentID INT,
    CourseId INT,
    Grade INT CHECK (Grade >= 0 AND Grade <= 100),
    PRIMARY KEY (StudentID, CourseId),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID),
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId),
    CHECK (Grade >= 0 AND Grade <= 100)
);

CREATE TABLE Assignment (
    AssignmentId INT PRIMARY KEY,
    CourseId INT,
    Title VARCHAR(255) NOT NULL,
    Description TEXT,
    DueDate DATETIME,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE Forum (
    ForumId INT PRIMARY KEY,
    CourseId INT,
    Title VARCHAR(255) NOT NULL,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE DiscussionThread (
    ThreadId INT PRIMARY KEY,
    ForumId INT,
    UserId INT,
    Title VARCHAR(255) NOT NULL,
    Post TEXT NOT NULL,
    FOREIGN KEY (ForumId) REFERENCES Forum(ForumId),
    FOREIGN KEY (UserId) REFERENCES Student(StudentID)
);

CREATE TABLE CalendarEvent (
    EventId INT PRIMARY KEY,
    CourseId INT,
    EventDate DATETIME NOT NULL,
    EventTime TIME NOT NULL,
    Description TEXT,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE CourseContent (
    ContentId INT PRIMARY KEY,
    CourseId INT,
    Section INT NOT NULL,
    Content BLOB,
    Metadata TEXT,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);


CREATE TABLE Submission (
    SubmissionId INT PRIMARY KEY,
    AssignmentId INT NOT NULL,
    StudentID INT NOT NULL,
    SubmissionContent BLOB, 
    SubmissionDate DATETIME DEFAULT CURRENT_TIMESTAMP, 
    FOREIGN KEY (AssignmentId) REFERENCES Assignment(AssignmentId) ON DELETE CASCADE, -- If assignment is deleted, remove submissions
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE, -- If student is deleted, remove their submissions
    UNIQUE (AssignmentId, StudentID) -- Ensure a student submits an assignment only once
);


CREATE TABLE Grade (
    GradeId INT PRIMARY KEY,
    SubmissionId INT NOT NULL UNIQUE, -- Each submission gets only one grade entry
    Grade INT NOT NULL CHECK (Grade >= 0 AND Grade <= 100), 
    Feedback TEXT, 
    GradingDate DATETIME DEFAULT CURRENT_TIMESTAMP, 
    FOREIGN KEY (SubmissionId) REFERENCES Submission(SubmissionId) ON DELETE CASCADE -- If submission is deleted, remove the grade
);

DELIMITER //

CREATE TRIGGER check_student_enrollment_limit
BEFORE INSERT ON Enrollment
FOR EACH ROW
BEGIN
    DECLARE student_course_count INT;
    SELECT COUNT(*) INTO student_course_count
    FROM Enrollment
    WHERE StudentID = NEW.StudentID;
    IF student_course_count > 6 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Student cannot enroll in more than 6 courses.';
    END IF;
END//

DELIMITER ;

/*
CREATE TRIGGER check_course_member_count
AFTER INSERT ON Enrollment
FOR EACH ROW
BEGIN
    DECLARE course_member_count INT;
    SELECT COUNT(*) INTO course_member_count
    FROM Enrollment
    WHERE CourseId = NEW.CourseId;
    IF course_member_count < 10 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Course must have at least 10 members.';
    END IF;
END;

*/

DELIMITER //

CREATE TRIGGER check_lecturer_course_limit
BEFORE INSERT ON CourseLecturer
FOR EACH ROW
BEGIN
    DECLARE lecturer_course_count INT;
    SELECT COUNT(*) INTO lecturer_course_count
    FROM CourseLecturer
    WHERE LecId = NEW.LecId;
    IF lecturer_course_count > 5 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Lecturer cannot teach more than 5 courses.';
    END IF;
END//

DELIMITER ;

/*
CREATE TRIGGER check_lecturer_teaches_at_least_one_course
AFTER INSERT ON Lecturer
FOR EACH ROW
BEGIN
    DECLARE lecturer_course_count INT;
    SELECT COUNT(*) INTO lecturer_course_count
    FROM CourseLecturer
    WHERE LecId = NEW.LecId;
    IF lecturer_course_count < 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Lecturer must teach at least one course.';
    END IF;
END;

*/
`;
    return createTableStatements;
}

/**
 * Generates the CREATE VIEW statements for the reports.
 * @returns {string} - The CREATE VIEW statements.
 */
function generateViews() {
    const createViewsStatements = `
-- 1. All courses that have 50 or more students
CREATE VIEW CoursesWith50PlusStudents AS
SELECT c.CourseId, c.CourseName, COUNT(e.StudentID) AS NumberOfStudents
FROM Course c
JOIN Enrollment e ON c.CourseId = e.CourseId
GROUP BY c.CourseId, c.CourseName
HAVING COUNT(e.StudentID) >= 50;

-- 2. All students that do 5 or more courses.
CREATE VIEW StudentsWith5PlusCourses AS
SELECT s.StudentID, s.FirstName, s.LastName, COUNT(e.CourseId) AS NumberOfCourses
FROM Student s
JOIN Enrollment e ON s.StudentID = e.StudentID
GROUP BY s.StudentID, s.FirstName, s.LastName
HAVING COUNT(e.CourseId) >= 5;

-- 3. All lecturers that teach 3 or more courses.
CREATE VIEW LecturersWith3PlusCourses AS
SELECT l.LecId, l.LecFirstName, l.LecLastName, COUNT(cl.CourseId) AS NumberOfCourses
FROM Lecturer l
JOIN CourseLecturer cl ON l.LecId = cl.LecId
GROUP BY l.LecId, l.LecFirstName, l.LecLastName
HAVING COUNT(cl.CourseId) >= 3;

-- 4. The 10 most enrolled courses.
CREATE VIEW Top10EnrolledCourses AS
SELECT c.CourseId, c.CourseName, COUNT(e.StudentID) AS NumberOfStudents
FROM Course c
JOIN Enrollment e ON c.CourseId = e.CourseId
GROUP BY c.CourseId, c.CourseName
ORDER BY COUNT(e.StudentID) DESC
LIMIT 10;

-- 5. The top 10 students with the highest overall averages.
CREATE VIEW Top10StudentsByAverage AS
SELECT s.StudentID, s.FirstName, s.LastName, AVG(e.Grade) AS OverallAverage
FROM Student s
JOIN Enrollment e ON s.StudentID = e.StudentID
GROUP BY s.StudentID, s.FirstName, s.LastName
ORDER BY AVG(e.Grade) DESC
LIMIT 10;
`;
    return createViewsStatements;
}

// ===============================
// File Writing
// ===============================

/**
 * Writes the given SQL statements to a file.
 * @param {string} filename - The name of the file.
 * @param {string} data - The SQL statements to write.
 */
function writeSQLFile(filename, data) {
    fs.writeFileSync(filename, data);
    console.log(`SQL file "${filename}" generated successfully.`);
}

module.exports = {
    generateInsertStatements,
    generateCreateDatabaseStatement,
    generateCreateTableStatements,
    generateViews,
    writeSQLFile
};