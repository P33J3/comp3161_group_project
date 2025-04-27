


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
    SubmissionContent BLOB, -- Or TEXT/VARCHAR if storing links/text only
    SubmissionDate DATETIME DEFAULT CURRENT_TIMESTAMP, -- Track when it was submitted
    FOREIGN KEY (AssignmentId) REFERENCES Assignment(AssignmentId) ON DELETE CASCADE, -- If assignment is deleted, remove submissions
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE, -- If student is deleted, remove their submissions
    UNIQUE (AssignmentId, StudentID) -- Ensure a student submits an assignment only once
);


CREATE TABLE Grade (
    GradeId INT PRIMARY KEY,
    SubmissionId INT NOT NULL UNIQUE, -- Each submission gets only one grade entry
    Grade INT NOT NULL CHECK (Grade >= 0 AND Grade <= 100), -- The numerical grade
    Feedback TEXT, -- Optional field for lecturer feedback
    GradingDate DATETIME DEFAULT CURRENT_TIMESTAMP, -- Track when it was graded
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
