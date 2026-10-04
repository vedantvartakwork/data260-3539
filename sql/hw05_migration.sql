USE s3539_rel;

CREATE TABLE IF NOT EXISTS manufacturers (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(160) NOT NULL,
  contact_name VARCHAR(160) NOT NULL,
  contact_email VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_manufacturers_contact_email (contact_email)
) ENGINE=InnoDB;

-- This migration is intentionally applied once by scripts/seed_hw05.py.
ALTER TABLE recall_notices
  ADD COLUMN recall_code VARCHAR(32) NULL AFTER product_name,
  ADD COLUMN units_affected INT NOT NULL DEFAULT 0 AFTER recall_code,
  ADD COLUMN manufacturer_id INT NULL AFTER units_affected,
  ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

INSERT INTO manufacturers (name, contact_name, contact_email)
VALUES ('Legacy Recall Manufacturer', 'Recall Coordinator', 'legacy-manufacturer@example.edu');

SET @default_manufacturer_id = LAST_INSERT_ID();

UPDATE recall_notices
SET recall_code = CONCAT('REC-', LPAD(id, 6, '0')),
    manufacturer_id = @default_manufacturer_id
WHERE recall_code IS NULL OR manufacturer_id IS NULL;

ALTER TABLE recall_notices
  MODIFY recall_code VARCHAR(32) NOT NULL,
  MODIFY manufacturer_id INT NOT NULL,
  ADD CONSTRAINT uq_recall_notices_code UNIQUE (recall_code),
  ADD CONSTRAINT fk_recall_notices_manufacturer
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE RESTRICT;
