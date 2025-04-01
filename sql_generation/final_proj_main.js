// ===============================
// Data Generation
// ===============================

// Generate data using the functions
const {
    generateCreateTableStatements,
    generateInsertStatements,
    generateViews,
    writeSQLFile, generateCreateDatabaseStatement
} = require('./final_proj_generate_sql');

const {
    generateAssignments, generateCalendarEvents,
    generateCourses, generateForums,
    generateLecturers,
    generateStudents, generateThreads
} = require('./final_proj_table_content_generation');

const { generateHashedPassword, generateSalt,
    generateUserId,universityDepartment, getNextLecId,
    generateCourseContent
} = require('./final_proj_course_utilities');

const { faker } = require('@faker-js/faker');
const fs = require('fs');
const crypto = require('crypto');

// Number of records to generate
const numLecturers = 40; // Increased to ensure enough lecturers can cover 200 courses
const numCourses = 200;
const numStudents = 100000;
const numAssignments = 600;
const numForums = 80;
const numThreads = 200;
const numEvents = 150;

let allUsers = []
const { lecturers} = generateLecturers(numLecturers, allUsers); // Destructure lecturer and user data
const courses = generateCourses(numCourses);
const { students } = generateStudents(numStudents, allUsers);   // Destructure student and user data
const assignments = generateAssignments(numAssignments, courses);
const forums = generateForums(numForums, courses);
const threads = generateThreads(numThreads, forums, students);
const events = generateCalendarEvents(numEvents, courses);
const courseContent = generateCourseContent(numCourses * 3, courses);
// allUsers = [...lecturerUsers, ...studentUsers];


// Generate data using the functions
// Assign lecturers to courses
const courseLecturerAssignments =[];
const lecturerCourseCounts = {};

// Initialize lecturer course counts
lecturers.forEach(lecturer => {
    lecturerCourseCounts[lecturer.LecId] = 0;
});

// // Function to get the next available LecId
// function getNextLecId() {
//     let maxId = 0;
//     for (const lecturer of lecturers) {
//         if (lecturer.LecId > maxId) {
//             maxId = lecturer.LecId;
//         }
//     }
//     return maxId + 1;
// }

// Function to assign a lecturer to a course
function assignLecturerToCourse(course,lecturers,allUsers) {
    // Try to find an existing lecturer with less than 5 courses
    for (const lecturerId in lecturerCourseCounts) {
        if (lecturerCourseCounts[lecturerId] < 5) {
            courseLecturerAssignments.push({
                CourseId: course.CourseId,
                LecId: parseInt(lecturerId)
            });
            lecturerCourseCounts[lecturerId]++;
            return;
        }
    }

    // If no existing lecturer is available, create a new one
    const newFirstName = faker.person.firstName();
    const newLastName = faker.person.lastName();
    const username = `${newFirstName.toLowerCase()}.${newLastName.toLowerCase()}`
    const salt = generateSalt();
    const password = generateHashedPassword("password", salt);
    const userId = generateUserId(); // Get unique UserId

    allUsers.push({  // Populate User table data
        UserId: userId,
        Username: username,
        Password: password,
        Role: 'lecturer', // Set role to 'lecturer'
        Salt: salt
    });

    const newLecturer = {
        LecId: getNextLecId(), // Get the next available LecId
        LecFirstName: newFirstName,
        LecLastName: newLastName,
        Department: universityDepartment(),
        UserId: userId, // Use generated UserId
    }

    lecturers.push(newLecturer);



    // const newLecturerSalt = generateSalt();
    // const newLecturer = {
    //     LecId: getNextLecId(), // Get the next available LecId
    //     LecFirstName: newFirstName,
    //     LecLastName: newLastName,
    //     Department: universityDepartment(),
    //     UserId: getNextLecId(),
    //     ,
    //     Password: generateHashedPassword("password", newLecturerSalt),
    //     Salt: newLecturerSalt
    // };
    //
    // lecturers.push(newLecturer);
    lecturerCourseCounts[newLecturer.LecId] = 1;
    courseLecturerAssignments.push({
        CourseId: course.CourseId,
        LecId: newLecturer.LecId
    });
}

courses.forEach(course => {
    assignLecturerToCourse(course,lecturers,allUsers);
});


// Assign courses to students
const enrollments =[];

students.forEach(student => {
    const numCoursesToEnroll = faker.number.int({ min: 3, max: 6 }); // Enroll between 3 and 6 courses
    const studentCourses = new Set();
    for (let i = 0; i < numCoursesToEnroll; i++) {
        let randomCourse;
        do {
            randomCourse = courses[faker.number.int({ min: 0, max: courses.length - 1 })];
        } while (studentCourses.has(randomCourse.CourseId)); // Avoid duplicate courses for the same student
        studentCourses.add(randomCourse.CourseId);
        enrollments.push({
            StudentID: student.StudentID,
            CourseId: randomCourse.CourseId,
            Grade: faker.number.int({ min: 0, max: 100 })
        });
    }
});

// Ensure each course has at least 10 students
courses.forEach(course => {
    //essentially filtering the enrollments array to get the number of students enrolled in a course
    let courseEnrollmentCount = enrollments.filter(enrollment => enrollment.CourseId === course.CourseId).length;
    //keeps running until there are 10 students enrolled in the course
    while (courseEnrollmentCount < 10) {
        // Find a student with the fewest enrollments
        const studentEnrollmentCounts = {};
        //finds the number of courses each student is enrolled in
        students.forEach(student => {
            studentEnrollmentCounts[student.StudentID] = enrollments.filter(enrollment => enrollment.StudentID === student.StudentID).length;
        });
        //Infinity so initially first value compared will always be less
        let minEnrollment = Infinity;
        let fewestEnrollmentsID = null;
        for (const studentId in studentEnrollmentCounts) {
            if (studentEnrollmentCounts[studentId] < minEnrollment) {
                minEnrollment = studentEnrollmentCounts[studentId];
                fewestEnrollmentsID = studentId;
            }
        }

        // **Check if the student is already enrolled**
        const alreadyEnrolled = enrollments.some(
            enrollment => enrollment.StudentID === parseInt(fewestEnrollmentsID) && enrollment.CourseId === course.CourseId
        );

        // Check if the student has less than 6 enrollments before enrolling
        const currentStudentEnrollmentCount = studentEnrollmentCounts[fewestEnrollmentsID] || 0; //Default to 0 if not present in the object



        // Enroll the student with the fewest courses in the current course
        if (!alreadyEnrolled && currentStudentEnrollmentCount < 6) { // Only enroll if not already enrolled
            enrollments.push({
                StudentID: parseInt(fewestEnrollmentsID),
                CourseId: course.CourseId,
                Grade: faker.number.int({ min: 0, max: 100 })
            });
            courseEnrollmentCount++;
        } else {
            // If the student is already enrolled, we don't increment the count
            // but we still need to try to find another student to enroll
            // so we don't get stuck in an infinite loop if all students are enrolled
            // In a real-world scenario, you might want to add a counter to prevent infinite loops here as well.
            if (alreadyEnrolled) {
                console.log(`Student ${fewestEnrollmentsID} is already enrolled in Course ${course.CourseId}`);
            } else if (currentStudentEnrollmentCount >= 6) {
                console.log(`Student ${fewestEnrollmentsID} has reached the maximum of 6 enrollments.`);
            }

            // If the student is already enrolled or has 6 enrollments, find another eligible student
            let foundEligibleStudent = false;
            for (const studentId in studentEnrollmentCounts) {
                const checkEnrolled = enrollments.some(enrollment => enrollment.StudentID === parseInt(studentId) && enrollment.CourseId === course.CourseId);
                if (!checkEnrolled && studentEnrollmentCounts[studentId] < 6) {
                    fewestEnrollmentsID = studentId;
                    foundEligibleStudent = true;
                    break;
                }
            }

            if(foundEligibleStudent){
                enrollments.push({
                    StudentID: parseInt(fewestEnrollmentsID),
                    CourseId: course.CourseId,
                    Grade: faker.number.int({ min: 0, max: 100 })
                });
                courseEnrollmentCount++;
            }else{
                //if no eligible student is found, break the while loop to prevent infinite loop
                console.log(`No eligible student found for Course ${course.CourseId}`);
                courseEnrollmentCount = 10; //force the while loop to end.
            }

        }
        // Recalculate the enrollment count after potentially adding a new enrollment
        courseEnrollmentCount = enrollments.filter(enrollment => enrollment.CourseId === course.CourseId).length;
    }
});




//Generate and Write CREATE DATABASE statement to a file
const createDatabaseStatement = generateCreateDatabaseStatement();
writeSQLFile('create_database.sql', createDatabaseStatement);

// Generate and write CREATE TABLE statements to a file
const createTableStatements = generateCreateTableStatements();
writeSQLFile('create_tables.sql', createTableStatements);

// Generate and write CREATE VIEW statements to a file
const createViewsStatements = generateViews();
writeSQLFile('create_views.sql', createViewsStatements);

// Generate and write INSERT statements to separate files
const adminSalt = generateSalt();
writeSQLFile('insert_users.sql', generateInsertStatements("User", [...allUsers, { UserId: generateUserId(), Username: 'admin', Password: generateHashedPassword('admin', adminSalt), Role: 'admin', Salt: adminSalt }]));
writeSQLFile('insert_lecturers.sql', generateInsertStatements("Lecturer", lecturers));
writeSQLFile('insert_courses.sql', generateInsertStatements("Course", courses));
writeSQLFile('insert_course_lecturer.sql', generateInsertStatements("CourseLecturer", courseLecturerAssignments));
writeSQLFile('insert_course_content.sql', generateInsertStatements("CourseContent", courseContent));
writeSQLFile('insert_students.sql', generateInsertStatements("Student", students));
writeSQLFile('insert_enrollments.sql', generateInsertStatements("Enrollment", enrollments));
writeSQLFile('insert_assignments.sql', generateInsertStatements("Assignment", assignments));
writeSQLFile('insert_forums.sql', generateInsertStatements("Forum", forums));
writeSQLFile('insert_threads.sql', generateInsertStatements("DiscussionThread", threads));
writeSQLFile('insert_events.sql', generateInsertStatements("CalendarEvent", events));

console.log('SQL files generated successfully.');