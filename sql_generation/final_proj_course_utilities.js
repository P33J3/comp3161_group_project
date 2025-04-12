const { faker } = require('@faker-js/faker');
const fs = require('fs');
const crypto = require('crypto'); // For password hashing

const { departments,
    departmentSubjects,
    particulars
} = require('./final_proj_department_data_elements');




// ===============================
// Helper Functions
// ===============================

/**
 * Generates a random department from the 'departments' array.
 * @returns {string} - A randomly selected department.
 */
const universityDepartment = () => {
    const randomIndex = faker.number.int({ min: 0, max: departments.length - 1 });
    return departments[randomIndex];
};

/**
 * Generates a course name and code based on the given department.
 * @param {string} department - The department for which to generate the course.
 * @returns {{courseName: string, courseCode: string}} - An object containing the course name and code.
 */
const course = (department) => {
    const subjects = departmentSubjects[department];
    if (!subjects) {
        console.error(`No subjects found for department: ${department}`);
        return { courseName: "Unknown Course", courseCode: "XXX000" };
    }
    const randomSubjectIndex = faker.number.int({ min: 0, max: subjects.length - 1 });
    const subject = subjects[randomSubjectIndex];
    const randomParticularIndex = faker.number.int({ min: 0, max: particulars.length - 1 });
    const particular = particulars[randomParticularIndex];
    const courseName = `${particular} ${subject}`;
    const deptCode = department.slice(0, 3).toUpperCase();
    const randomNumber = faker.number.int({ min: 100, max: 999 });
    const courseCode = `${deptCode}${randomNumber}`;
    return { courseName, courseCode };
};

// Function to get the next available LecId
function getNextLecId() {
    let maxId = 0;
    for (const lecturer of lecturers) {
        if (lecturer.LecId > maxId) {
            maxId = lecturer.LecId;
        }
    }
    return maxId + 1;
}

let nextUserId = 0;

/**
 * Generates a unique UserId.
 * @returns {number} - A unique UserId.
 */
function generateUserId() {
    return nextUserId++;
}

/**
 * Generates a salt string for password hashing.
 * @returns {string} - A random salt string.
 */
function generateSalt() {
    return crypto.randomBytes(16).toString('hex');
}

/**
 * Generates a hashed password from the given password and salt.
 * @param {string} password - The password to hash.
 * @param {string} salt - The salt string.
 * @returns {string} - The hashed password.
 */
function generateHashedPassword(password, salt) {
    const hash = crypto.createHash('sha256');
    hash.update(password + salt);
    return hash.digest('hex');
}

function generateCourseContent(count, courses) {
    const courseContent = [];
    for (let i = 1; i <= count; i++) {
        const randomCourseIndex = faker.number.int({ min: 0, max: courses.length - 1 });
        const randomCourse = courses[randomCourseIndex];
        const contentType = faker.helpers.arrayElement(['link', 'file', 'slide']);
        let content;
        let metadata = null;

        if (contentType === 'link') {
            content = faker.internet.url();
            metadata = { type: 'link' };
        } else if (contentType === 'file') {
            content =  `file_data_${i}`; // Simulate file data.  **IMPORTANT:** In a real app, you'd read from a file.
            metadata = {
                type: 'file',
                filename: `file_${i}.${faker.system.commonFileType()}`,
                size: faker.number.int({ min: 100, max: 1000000 }),
            };
        } else {
            content = faker.lorem.paragraphs(2);
            metadata = { type: 'slide' };
        }

        courseContent.push({
            ContentId: i,
            CourseId: randomCourse.CourseId,
            Section: faker.number.int({ min: 1, max: 20 }),
            Content: content, // This is the BLOB data
            Metadata: JSON.stringify(metadata),
        });
    }
    return courseContent;
}
module.exports = {
    universityDepartment,
    course,
    getNextLecId,
    generateUserId,
    generateSalt,
    generateHashedPassword,
    generateCourseContent
}