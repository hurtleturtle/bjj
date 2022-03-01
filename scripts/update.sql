DROP TABLE IF EXISTS attendance;

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