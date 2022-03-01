SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS stories;
DROP TABLE IF EXISTS chapters;
DROP TABLE IF EXISTS challenges;
DROP TABLE IF EXISTS challenge_descriptions;
DROP TABLE IF EXISTS challenge_files;
DROP TABLE IF EXISTS challenge_answers;
DROP TABLE IF EXISTS classes;
DROP TABLE IF EXISTS attendance;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    admin TEXT NOT NULL,
    access_approved BOOLEAN NOT NULL DEFAULT false,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submission_approval_requested BOOLEAN NOT NULL DEFAULT false,
    submission_approved BOOLEAN NOT NULL DEFAULT false,
    is_coach BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    author TEXT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    rating INTEGER,
    uploader_id INTEGER NOT NULL,
    FOREIGN KEY (uploader_id) REFERENCES users (id)
);

CREATE TABLE chapters (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    story_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chapter_number INTEGER NOT NULL,
    chapter_title TEXT,
    chapter_content TEXT,
    uploader_id INTEGER NOT NULL,
    FOREIGN KEY (story_id) REFERENCES stories (id),
    FOREIGN KEY (uploader_id) REFERENCES users (id)
);

CREATE TABLE challenges (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    short_description TEXT NOT NULL,
    verifier_filename TEXT NOT NULL
);

CREATE TABLE challenge_descriptions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    challenge_id INTEGER NOT NULL,
    sequence_num INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id)
);

CREATE TABLE challenge_files (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    challenge_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE challenge_answers (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    challenge_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    pass BOOLEAN NOT NULL DEFAULT false,
    evaluation_result TEXT
);

CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    class_name TEXT NOT NULL,
    class_type TEXT NOT NULL,
    weekday TEXT NOT NULL,
    time TIME NOT NULL,
    duration TIME NOT NULL DEFAULT "1:00:00",
    coach_id INTEGER NOT NULL,
    FOREIGN KEY (coach_id) REFERENCES users (id)
);

CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    class_id INTEGER NOT NULL,
    class_date DATE NOT NULL,
    class_time TIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (class_id) REFERENCES classes (id)
);