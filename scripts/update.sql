CREATE TABLE age_groups (
  id INT NOT NULL AUTO_INCREMENT,
  name TEXT NOT NULL,
  min_age INT NOT NULL,
  max_age INT NOT NULL,
  PRIMARY KEY (id)
);

ALTER TABLE memberships ADD COLUMN age_group_id INTEGER AFTER sessions_per_week;
ALTER TABLE classes ADD COLUMN age_group_id INTEGER AFTER coach_id;

INSERT INTO age_groups (name, min_age, max_age) VALUES ('junior', 5, 15), ('senior', 16, 200);

UPDATE classes SET age_group_id=1 WHERE class_name='Junior BJJ';
UPDATE classes SET age_group_id=2 WHERE class_name<>'Junior BJJ';