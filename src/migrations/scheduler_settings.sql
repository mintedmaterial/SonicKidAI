-- Scheduler Settings Schema
-- This table is used to track when scheduled tasks were last run

CREATE TABLE IF NOT EXISTS scheduler_settings (
    task_name VARCHAR(100) PRIMARY KEY,
    last_run TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create index on task_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_scheduler_settings_task_name ON scheduler_settings(task_name);

-- Trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_scheduler_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_scheduler_settings_updated_at ON scheduler_settings;
CREATE TRIGGER trigger_update_scheduler_settings_updated_at
BEFORE UPDATE ON scheduler_settings
FOR EACH ROW
EXECUTE FUNCTION update_scheduler_settings_updated_at();

-- Insert initial records for the Twitter and website scrapers (if they don't exist)
INSERT INTO scheduler_settings (task_name, last_run)
VALUES ('twitter_scraper', CURRENT_TIMESTAMP - INTERVAL '4 hours')
ON CONFLICT (task_name) DO NOTHING;

INSERT INTO scheduler_settings (task_name, last_run)
VALUES ('website_scraper', CURRENT_TIMESTAMP - INTERVAL '24 hours')
ON CONFLICT (task_name) DO NOTHING;