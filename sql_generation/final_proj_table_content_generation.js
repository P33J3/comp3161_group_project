// ===============================
// Data Generation Functions
// ===============================

const {
    course,
    generateHashedPassword,
    generateSalt,
    generateUserId,
    universityDepartment
} = require("./final_proj_course_utilities");

const {faker} = require('@faker-js/faker');


/**
 * Generates an array of lecturer objects.
 * @param {number} count - The number of lecturers to generate.
 * @param allUsers
 * @returns {{allUsers, lecturers: *[]}} - An array of lecturer objects.
 */
function generateLecturers(count, allUsers) {
    const lecturers = [];
    // const users = []; // Array for User table data
    for (let i = 1; i <= count; i++) {
        const firstName = faker.person.firstName();
        const lastName = faker.person.lastName();
        let username = `${firstName.toLowerCase()}.${lastName.toLowerCase()}`;
        let originalUsername = username;
        let suffix = 1;
        const salt = generateSalt();
        const password = generateHashedPassword("password", salt);
        const userId = generateUserId(); // Get unique UserId

        while (allUsers.some(user => user.Username === username)) {
            username = `${originalUsername}${suffix}`;
            suffix++;
        }

        allUsers.push({  // Populate User table data
            UserId: userId,
            Username: username,
            Password: password,
            Role: 'lecturer', // Set role to 'lecturer'
            Salt: salt
        });
        lecturers.push({
            LecId: 10000000 + i,
            LecFirstName: firstName,
            LecLastName: lastName,
            Department: universityDepartment(),
            UserId: userId, // Use generated UserId
        });
    }
    return { lecturers, allUsers }; // Return both lecturers and users data
}

/**
 * Generates an array of course objects.
 * @param {number} count - The number of courses to generate.
 * @returns {Array} - An array of course objects.
 */
function generateCourses(count) {
    const courses = [];
    const generatedCourseNames = new Set();
    const generatedCourseCodes = new Set();
    for (let i = 1; i <= count; i++) {
        let courseName, courseCode, identifier;
        let attempts = 0; // Add an attempt counter to prevent infinite loops
        do {
            const department = universityDepartment();
            const { courseName: newName, courseCode: newCode } = course(department);
            courseName = newName;
            courseCode = newCode;
            // identifier = `${courseName}-${courseCode}`; // Combine name and code
            attempts++;

            if (attempts > 1000) {
                // If we've tried many times, it's likely there's an issue with the data
                console.error("Could not generate unique course after 1000 attempts.");
                return courses; // Return what we have to avoid an infinite loop
            }
        } while (generatedCourseNames.has(courseName) || generatedCourseCodes.has(courseCode));
        generatedCourseNames.add(courseName);
        generatedCourseCodes.add(courseCode);
        courses.push({
            CourseId: i,
            CourseName: courseName,
            CourseCode: courseCode
        });
    }
    return courses;
}

/**
 * Generates an array of student objects.
 * @param {number} count - The number of students to generate.
 * @param allUsers
 * @returns {{allUsers, students: *[]}} - An array of student objects.
 */
function generateStudents(count, allUsers) {
    const students = [];
    // const users = []; // Array for User table data
    for (let i = 1; i <= count; i++) {
        const firstName = faker.person.firstName();
        const lastName = faker.person.lastName();
        let username = `${firstName.toLowerCase()}.${lastName.toLowerCase()}`;
        let originalUsername = username;
        let suffix = 1;
        const salt = generateSalt();
        const password = generateHashedPassword("password", salt);
        const userId = generateUserId(); // Get unique UserId

        while (allUsers.some(user => user.Username === username)) {
            username = `${originalUsername}${suffix}`;
            suffix++;
        }

        allUsers.push({ // Populate User table data
            UserId: userId,
            Username: username,
            Password: password,
            Role: 'student', // Set role to 'student'
            Salt: salt
        });
        students.push({
            StudentID: 620000000 + i,
            FirstName: firstName,
            LastName: lastName,
            UserId: userId, // Use generated UserId
        });
    }
    return { students, allUsers }; // Return both students and users data
}

/**
 * Generates an array of assignment objects.
 * @param {number} count - The number of assignments to generate.
 * @param {Array} courses - The array of courses.
 * @returns {Array} - An array of assignment objects.
 */
function generateAssignments(count, courses) {
    const assignments = [];
    for (let i = 1; i <= count; i++) {
        const randomCourseIndex = faker.number.int({ min: 0, max: courses.length - 1 });
        const randomCourse = courses[randomCourseIndex];
        const dueDate = faker.date.future();
        const mysqlDateString = dueDate.toISOString().slice(0, 19).replace('T', ' '); // Format for MySQL DATETIME

        assignments.push({
            AssignmentId: i,
            CourseId: randomCourse.CourseId,
            Title: `Assignment ${i} - ${randomCourse.CourseName}`,
            Description: faker.lorem.sentence(),
            DueDate: mysqlDateString
        });
    }
    return assignments;
}

/**
 * Generates an array of forum objects.
 * @param {number} count - The number of forums to generate.
 * @param {Array} courses - The array of courses.
 * @returns {Array} - An array of forum objects.
 */
function generateForums(count, courses) {
    const forums = [];
    for (let i = 1; i <= count; i++) {
        const randomCourseIndex = faker.number.int({ min: 0, max: courses.length - 1 });
        const randomCourse = courses[randomCourseIndex];
        forums.push({
            ForumId: i,
            CourseId: randomCourse.CourseId,
            Title: `Forum ${i} - ${randomCourse.CourseName}`,
        });
    }
    return forums;
}

/**
 * Generates an array of discussion thread objects.
 * @param {number} count - The number of threads to generate.
 * @param {Array} forums - The array of forums.
 * @param {Array} students - The array of students.
 * @returns {Array} - An array of thread objects.
 */
function generateThreads(count, forums, students) {
    const threads = [];
    for (let i = 1; i <= count; i++) {
        const randomForumIndex = faker.number.int({ min: 0, max: forums.length - 1 });
        const randomForum = forums[randomForumIndex];
        const randomStudentIndex = faker.number.int({ min: 0, max: students.length - 1 });
        const randomStudent = students[randomStudentIndex];
        threads.push({
            ThreadId: i,
            ForumId: randomForum.ForumId,
            UserId: randomStudent.StudentID,
            Title: `Thread ${i}`,
            Post: faker.lorem.paragraph(),
        });
    }
    return threads;
}

/**
 * Generates an array of calendar event objects.
 * @param {number} count - The number of events to generate.
 * @param {Array} courses - The array of courses.
 * @returns {Array} - An array of calendar event objects.
 */
function generateCalendarEvents(count, courses) {
    const events = [];
    for (let i = 1; i <= count; i++) {
        const randomCourseIndex = faker.number.int({ min: 0, max: courses.length - 1 });
        const randomCourse = courses[randomCourseIndex];
        const eventDateTime = faker.date.future(); // Generate a combined date and time
        const mysqlDateTimeString = eventDateTime.toISOString()
            .slice(0, 19).replace('T', ' '); // Format for MySQL DATETIME
        events.push({
            EventId: i,
            CourseId: randomCourse.CourseId,
            EventDate: mysqlDateTimeString.split(' ')[0], // Extract date part
            EventTime: mysqlDateTimeString.split(' ')[1], // Extract the time
            Description: faker.lorem.sentence(),
        });
    }
    return events;
}

module.exports = {
    generateLecturers,
    generateCourses,
    generateStudents,
    generateAssignments,
    generateForums,
    generateThreads,
    generateCalendarEvents
}