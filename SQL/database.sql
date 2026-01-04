CREATE TABLE IF NOT EXISTS users (
    user_id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
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
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    date_last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    img_link VARCHAR(255),
    original_api_id VARCHAR(255),
    summary VARCHAR(1024),
    PRIMARY KEY (id),
    FOREIGN KEY (media_type)
        REFERENCES media_types(id)
);

CREATE TABLE IF NOT EXISTS creators (
    creator_id INT NOT NULL AUTO_INCREMENT,
    creator_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (creator_id),
    UNIQUE KEY (creator_name)
);

CREATE TABLE IF NOT EXISTS item_creators (
    item_id INT NOT NULL,
    creator_id INT NOT NULL,
    PRIMARY KEY (item_id, creator_id),
    FOREIGN KEY (item_id)
        REFERENCES items(id),
    FOREIGN KEY (creator_id)
        REFERENCES creators(creator_id)
);

CREATE TABLE IF NOT EXISTS genres (
    genre_id INT NOT NULL AUTO_INCREMENT,
    genre_name VARCHAR(64) NOT NULL,
    PRIMARY KEY (genre_id),
    UNIQUE KEY (genre_name)
);

CREATE TABLE IF NOT EXISTS item_genres (
    item_id INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (item_id, genre_id),
    FOREIGN KEY (item_id)
        REFERENCES items(id),
    FOREIGN KEY (genre_id)
        REFERENCES genres(genre_id)
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
    duration SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS video_games (
    id INT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS board_games (
    id INT NOT NULL,
    min_players TINYINT,
    max_players TINYINT,
    duration SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS rpgs (
    id INT NOT NULL,
    isbn VARCHAR(16),
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS anime (
    id INT NOT NULL,
    episodes SMALLINT,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS albums (
    id INT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (id)
        REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS album_tracks (
    album_id INT NOT NULL,
    track_number TINYINT NOT NULL,
    track_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (album_id, track_number),
    FOREIGN KEY (album_id)
        REFERENCES albums(id)
);

CREATE TABLE IF NOT EXISTS collection_items (
    item_id INT NOT NULL,
    user_id INT NOT NULL,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
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
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (list_id),
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS list_items (
    item_id INT NOT NULL,
    list_id INT NOT NULL,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
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