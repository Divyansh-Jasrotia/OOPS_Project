-- Create database
CREATE DATABASE IF NOT EXISTS habit_db;
USE habit_db;

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE
);

-- Habits table
CREATE TABLE habits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100),
    type ENUM('good','bad'),
    importance ENUM('low','medium','high'),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Reports table
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    habit_id INT NOT NULL,
    report_date DATE NOT NULL,
    result ENUM('completed','failed'),
    FOREIGN KEY (habit_id) REFERENCES habits(id),
    UNIQUE (habit_id, report_date)
);

-- Stats table
CREATE TABLE stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_points INT DEFAULT 0,
    current_streak_weeks INT DEFAULT 0,
    current_goal INT DEFAULT 100,
    last_processed_week_start DATE NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Rewards table
CREATE TABLE rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reward_type VARCHAR(50),
    details TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
