USE nexusbjj;

CREATE TABLE password_resets (
	id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    token TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);