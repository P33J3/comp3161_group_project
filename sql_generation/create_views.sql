
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
