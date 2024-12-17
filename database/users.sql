-- Script to create the `users` table
CREATE TABLE users (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    primaryEmail VARCHAR(100) NULL,
    secondaryEmail VARCHAR(100) NULL DEFAULT 'n/a',
    primaryDiscord VARCHAR(100) NULL,
    primaryDiscordId VARCHAR(25) NULL,
    secondaryDiscord VARCHAR(100) NULL DEFAULT 'n/a',
    secondaryDiscordId VARCHAR(25) NULL,
    notifyDiscord VARCHAR(10) NULL DEFAULT 'primary',
    notifyEmail VARCHAR(10) NULL DEFAULT 'primary',
    status VARCHAR(10) NULL,
    server VARCHAR(25) NULL,
    4k ENUM('Yes', 'No') NULL,
    paymentMethod VARCHAR(25) NULL,
    paymentPerson VARCHAR(25) NULL,
    paidAmount DECIMAL(10, 2) NULL,
    joinDate DATE NULL DEFAULT CURDATE(),
    startDate DATE NULL DEFAULT CURDATE(),
    endDate DATE NULL
);
