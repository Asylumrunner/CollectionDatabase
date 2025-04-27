CREATE TABLE IF NOT EXISTS users (
    user_id INT NOT NULL AUTO_INCREMENT,
  	cognito_id VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    register_date DATETIME,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS media_types (
    id INT NOT NULL AUTO_INCREMENT,
    type_name VARCHAR(32) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS items (
    id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255),
    media_type INT,
    release_year SMALLINT,
    date_added DATETIME,
    created_by VARCHAR(255),
    img_link VARCHAR(255),
    original_api_id VARCHAR(255),
    PRIMARY KEY (id),
    FOREIGN KEY (media_type)
        REFERENCES media_types(id)
);

CREATE TABLE IF NOT EXISTS books (
    id INT NOT NULL,
    isbn VARCHAR(16),
    printing_year SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS movies (
    id INT NOT NULL,
    lang VARCHAR(6),
    summary VARCHAR(512),
    duration SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS video_games (
    id INT NOT NULL,
    summary VARCHAR(512),
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS board_games (
    id INT NOT NULL,
    minimum_players TINYINT,
    maximum_players TINYINT,
    summary VARCHAR(512),
    duration SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS rpgs (
    id INT NOT NULL,
    isbn VARCHAR(16),
    summary VARCHAR(512),
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS anime (
    id INT NOT NULL,
    episodes SMALLINT,
    summary VARCHAR(512),
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS albums (
    id INT NOT NULL,
    summary VARCHAR(512),
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS collection_items (
    item_id INT NOT NULL,
    user_id INT NOT NULL,
    date_added DATETIME,
    PRIMARY KEY (item_id, user_id),
    FOREIGN KEY (item_id)
        REFERENCES items(id),
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS user_lists (
    list_id INT NOT NULL AUTO_INCREMENT,
    list_name VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    date_create DATETIME,
    PRIMARY KEY (list_id),
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS list_items (
    item_id INT NOT NULL,
    list_id INT NOT NULL,
    date_added DATETIME,
    PRIMARY KEY(item_id, list_id),
    FOREIGN KEY (item_id)
        REFERENCES items(id),
    FOREIGN KEY (list_id)
        REFERENCES user_lists(list_id)
);

CREATE TABLE IF NOT EXISTS video_game_platforms (
    platform_id INT NOT NULL AUTO_INCREMENT,
    platform_name VARCHAR(64) NOT NULL,
    PRIMARY KEY (platform_id)
);

CREATE TABLE IF NOT EXISTS game_platform_availabilities (
    game_id INT NOT NULL,
    platform_id INT NOT NULL,
    PRIMARY KEY (game_id, platform_id),
    FOREIGN KEY (game_id)
        REFERENCES items(id),
    FOREIGN KEY (platform_id)
        REFERENCES video_game_platforms(platform_id)
);

INSERT INTO media_types (type_name) VALUES ('book');
INSERT INTO media_types (type_name) VALUES ('movie');
INSERT INTO media_types (type_name) VALUES ('video_game');
INSERT INTO media_types (type_name) VALUES ('board_game');
INSERT INTO media_types (type_name) VALUES ('rpg');
INSERT INTO media_types (type_name) VALUES ('anime');
INSERT INTO media_types (type_name) VALUES ('album');