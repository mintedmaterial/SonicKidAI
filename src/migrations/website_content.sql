-- Create website content data table for storing scraped content
CREATE TABLE IF NOT EXISTS website_content_data (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    markdown_content TEXT,
    source_type TEXT NOT NULL,
    metadata JSONB,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on common query fields
CREATE INDEX IF NOT EXISTS idx_website_content_url ON website_content_data(url);
CREATE INDEX IF NOT EXISTS idx_website_content_title ON website_content_data(title);
CREATE INDEX IF NOT EXISTS idx_website_content_source_type ON website_content_data(source_type);
CREATE INDEX IF NOT EXISTS idx_website_content_scraped_at ON website_content_data(scraped_at);

-- Create Twitter data table for storing scraped tweets
CREATE TABLE IF NOT EXISTS twitter_data (
    id SERIAL PRIMARY KEY,
    tweet_id TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL,
    sentiment TEXT,
    category TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on common query fields
CREATE INDEX IF NOT EXISTS idx_twitter_author ON twitter_data(author);
CREATE INDEX IF NOT EXISTS idx_twitter_sentiment ON twitter_data(sentiment);
CREATE INDEX IF NOT EXISTS idx_twitter_category ON twitter_data(category);
CREATE INDEX IF NOT EXISTS idx_twitter_created_at ON twitter_data(created_at);

-- Create scheduler settings table
CREATE TABLE IF NOT EXISTS scheduler_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create scheduler runs table
CREATE TABLE IF NOT EXISTS scheduler_runs (
    id SERIAL PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    details JSONB
);

-- Create indexes on scheduler tables
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_task_type ON scheduler_runs(task_type);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_status ON scheduler_runs(status);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_started_at ON scheduler_runs(started_at);