-- DATA 260 HW7: JWT identities and roles for the cumulative MySQL database.
ALTER TABLE users
  ADD COLUMN username VARCHAR(80) NULL AFTER id,
  ADD COLUMN role ENUM('reader', 'writer', 'moderator') NOT NULL DEFAULT 'reader' AFTER password_hash;

UPDATE users
SET username = LOWER(SUBSTRING_INDEX(email, '@', 1))
WHERE username IS NULL;

ALTER TABLE users
  MODIFY username VARCHAR(80) NOT NULL,
  ADD UNIQUE KEY uq_users_username (username);
