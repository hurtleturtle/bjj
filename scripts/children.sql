CREATE TABLE children (
	id INT PRIMARY KEY AUTO_INCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    parent_id INT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES users (id)
);

ALTER TABLE attendance ADD COLUMN child_id INT DEFAULT NULL;
ALTER TABLE attendance ADD constraint foreign key (child_id) REFERENCES children (id);
