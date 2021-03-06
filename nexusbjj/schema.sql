SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS classes;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS memberships;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE age_groups (
  id INT NOT NULL AUTO_INCREMENT,
  name TEXT NOT NULL,
  min_age INT NOT NULL,
  max_age INT NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE memberships (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    membership_type TEXT NOT NULL,
    membership_description TEXT,
    sessions_per_week INTEGER NOT NULL,
    age_group_id INTEGER,
    FOREIGN KEY (age_group_id) REFERENCES age_groups (id)
);

INSERT INTO memberships (membership_type, sessions_per_week) 
VALUES 
    ("pay per session", 0),
    ("basic", 4),
    ("intermediate", 6),
    ("unlimited", 14);


CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    mobile_number TEXT NOT NULL,
    grade TEXT,
    membership_id INTEGER NOT NULL,
    admin TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_coach BOOLEAN NOT NULL DEFAULT false,
    FOREIGN KEY (membership_id) REFERENCES memberships (id)
);

CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    class_name TEXT NOT NULL,
    class_type TEXT NOT NULL,
    weekday TEXT NOT NULL,
    time TIME NOT NULL,
    duration TIME NOT NULL DEFAULT "1:00:00",
    coach_id INTEGER NOT NULL,
    age_group_id INTEGER NOT NULL,
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

CREATE TABLE password_resets (
	id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    token TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);