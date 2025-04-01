


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
    CourseId VARCHAR(20) PRIMARY KEY,
    CourseName VARCHAR(255) NOT NULL UNIQUE,
    CourseCode VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE CourseLecturer (
    CourseId VARCHAR(20),
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
    CourseId VARCHAR(20),
    Grade INT CHECK (Grade >= 0 AND Grade <= 100),
    PRIMARY KEY (StudentID, CourseId),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID),
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId),
    CHECK (Grade >= 0 AND Grade <= 100)
);

CREATE TABLE Assignment (
    AssignmentId VARCHAR(20) PRIMARY KEY,
    CourseId VARCHAR(20),
    Title VARCHAR(255) NOT NULL,
    Description TEXT,
    DueDate DATETIME,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE Forum (
    ForumId VARCHAR(20) PRIMARY KEY,
    CourseId VARCHAR(20),
    Title VARCHAR(255) NOT NULL,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE DiscussionThread (
    ThreadId VARCHAR(20) PRIMARY KEY,
    ForumId VARCHAR(20),
    UserId INT,
    Title VARCHAR(255) NOT NULL,
    Post TEXT NOT NULL,
    FOREIGN KEY (ForumId) REFERENCES Forum(ForumId),
    FOREIGN KEY (UserId) REFERENCES Student(StudentID)
);

CREATE TABLE CalendarEvent (
    EventId VARCHAR(20) PRIMARY KEY,
    CourseId VARCHAR(20),
    EventDate DATETIME NOT NULL,
    EventTime DATETIME NOT NULL,
    Description TEXT,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
);

CREATE TABLE CourseContent (
    ContentId VARCHAR(20) PRIMARY KEY,
    CourseId VARCHAR(20),
    Section VARCHAR(255) NOT NULL,
    Content BLOB,
    Metadata TEXT,
    FOREIGN KEY (CourseId) REFERENCES Course(CourseId)
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
