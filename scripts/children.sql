CREATE TABLE children (
	id INT PRIMARY KEY AUTO_INCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    parent_id INT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES users (id)
);

ALTER TABLE attendance ADD COLUMN child_id INT DEFAULT NULL;
ALTER TABLE attendance ADD constraint foreign key (child_id) REFERENCES children (id);

-- CREATE TABLE child_attendance (
-- 	id INT PRIMARY KEY AUTO_INCREMENT,
--     child_id INT NOT NULL,
--     date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     class_id INT NOT NULL,
--     class_date DATE NOT NULL,
--     class_time TIME NOT NULL
-- );
UPDATE classes SET age_group_id=2 WHERE id=19;
SELECT * FROM attendance WHERE user_id=13 ORDER BY id DESC;
DELETE FROM attendance WHERE user_id = 13 AND child_id;
DELETE FROM children WHERE parent_id=13;
