-- Initialize PostgreSQL database for Steel.run
-- This script runs during container initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create additional indexes for performance
-- (These will be run after migrations, so we check if tables exist)

-- Optimize common queries
DO $$
BEGIN
    -- Index on user email for faster lookups
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;
    END IF;

    -- Index on stored actions for user queries
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stored_actions') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stored_actions_user_active ON stored_actions(user_id, is_active);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stored_actions_public ON stored_actions(is_public) WHERE is_public = true;
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stored_actions_type ON stored_actions(action_type);
    END IF;

    -- Index on execution runs for monitoring queries
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'execution_runs') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_runs_user_created ON execution_runs(user_id, created_at DESC);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_runs_status ON execution_runs(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_runs_action_created ON execution_runs(stored_action_id, created_at DESC);
    END IF;

    -- Index on API keys for authentication
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'api_keys') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
    END IF;

    -- Index on credentials for user queries
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'credentials') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credentials_user_active ON credentials(user_id, is_active);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credentials_service ON credentials(service_name);
    END IF;
END $$;