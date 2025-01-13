CREATE TABLE IF NOT EXISTS backup_jobs (
    id TEXT PRIMARY KEY,
    client TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT,
    output TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create a trigger to update the updated_at column on row update
CREATE TRIGGER IF NOT EXISTS update_backup_jobs_updated_at
AFTER UPDATE ON backup_jobs
FOR EACH ROW
BEGIN
    UPDATE backup_jobs
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;