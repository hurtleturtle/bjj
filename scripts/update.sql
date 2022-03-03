SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS memberships;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE memberships (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    membership_type TEXT NOT NULL,
    membership_description TEXT,
    sessions_per_week INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    mobile_number TEXT NOT NULL,
    grade TEXT,
    membership_id INTEGER NOT NULL DEFAULT 1,
    admin TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_coach BOOLEAN NOT NULL DEFAULT false,
    FOREIGN KEY (membership_id) REFERENCES memberships (id)
);

INSERT INTO memberships (membership_type, sessions_per_week) 
VALUES 
    ("pay per session", 0),
    ("basic", 4),
    ("intermediate", 6),
    ("unlimited", (SELECT COUNT(id) FROM classes));

INSERT INTO users (id, email, password, first_name, last_name, mobile_number, grade, admin, created, last_access, is_coach) 
SELECT id, email, password, first_name, last_name, mobile_number, grade, admin, created, last_access, is_coach
FROM users_old;