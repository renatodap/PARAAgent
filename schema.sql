-- PARA Autopilot Database Schema
-- Run this in your Supabase SQL Editor

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users (managed by Supabase Auth, but add profile)
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  timezone TEXT DEFAULT 'UTC',
  onboarding_completed BOOLEAN DEFAULT FALSE,
  para_preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PARA Items (unified table for Projects, Areas, Resources, Archives)
CREATE TABLE para_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  para_type TEXT NOT NULL CHECK (para_type IN ('project', 'area', 'resource', 'archive')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'on_hold')),
  due_date TIMESTAMPTZ,
  completion_date TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}', -- For custom fields
  embedding vector(1536), -- For semantic search with pgvector
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks (next actions derived from PARA items)
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  para_item_id UUID REFERENCES para_items(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  estimated_duration_minutes INT,
  due_date TIMESTAMPTZ,
  scheduled_start TIMESTAMPTZ, -- For calendar blocking
  scheduled_end TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  source TEXT, -- 'user', 'ai_suggested', 'imported'
  source_metadata JSONB DEFAULT '{}', -- Original task source info
  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Weekly Reviews (summaries and insights)
CREATE TABLE weekly_reviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  week_end_date DATE NOT NULL,
  summary TEXT, -- AI-generated summary
  insights JSONB DEFAULT '{}', -- Structured insights by PARA category
  completed_tasks_count INT DEFAULT 0,
  rollover_tasks JSONB DEFAULT '[]',
  next_week_proposals JSONB DEFAULT '[]',
  user_notes TEXT, -- User's own reflections
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'completed', 'skipped')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, week_start_date)
);

-- Calendar Events (synced from MCP)
CREATE TABLE calendar_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  external_id TEXT, -- ID from Google Calendar, etc.
  external_source TEXT, -- 'google_calendar', 'outlook', etc.
  title TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  location TEXT,
  attendees JSONB DEFAULT '[]',
  is_all_day BOOLEAN DEFAULT FALSE,
  is_autopilot_created BOOLEAN DEFAULT FALSE, -- Did we create this?
  linked_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
  sync_status TEXT DEFAULT 'synced' CHECK (sync_status IN ('synced', 'pending', 'error')),
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MCP Integration Configs (which services user has connected)
CREATE TABLE mcp_integrations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  integration_type TEXT NOT NULL, -- 'google_calendar', 'todoist', 'notion', etc.
  is_enabled BOOLEAN DEFAULT TRUE,
  oauth_token_encrypted TEXT, -- Store encrypted tokens
  refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMPTZ,
  config JSONB DEFAULT '{}', -- Integration-specific config
  last_sync_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, integration_type)
);

-- Agent Actions Log (for debugging and user transparency)
CREATE TABLE agent_actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL, -- 'classify', 'schedule', 'review', 'suggest'
  input_data JSONB,
  output_data JSONB,
  model_used TEXT, -- 'claude-haiku-4.5'
  tokens_used INT,
  cost_usd DECIMAL(10, 6),
  status TEXT DEFAULT 'success' CHECK (status IN ('success', 'error', 'pending')),
  error_message TEXT,
  execution_time_ms INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Approvals (for human-in-the-loop changes)
CREATE TABLE pending_approvals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  approval_type TEXT NOT NULL, -- 'calendar_change', 'task_schedule', 'para_reclassify'
  description TEXT,
  proposed_changes JSONB NOT NULL, -- What will change
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
  expires_at TIMESTAMPTZ,
  responded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_para_items_user_type ON para_items(user_id, para_type);
CREATE INDEX idx_para_items_status ON para_items(user_id, status);
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_scheduled ON tasks(user_id, scheduled_start) WHERE scheduled_start IS NOT NULL;
CREATE INDEX idx_calendar_events_user_time ON calendar_events(user_id, start_time);
CREATE INDEX idx_weekly_reviews_user_week ON weekly_reviews(user_id, week_start_date);

-- Vector similarity search functions
CREATE OR REPLACE FUNCTION match_para_items(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_user_id uuid
)
RETURNS TABLE (
  id uuid,
  title text,
  para_type text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    title,
    para_type,
    1 - (embedding <=> query_embedding) AS similarity
  FROM para_items
  WHERE user_id = filter_user_id
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Row Level Security (RLS) policies
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE para_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;

-- Policies: Users can only access their own data
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own PARA items" ON para_items FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own PARA items" ON para_items FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own PARA items" ON para_items FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own PARA items" ON para_items FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own tasks" ON tasks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own tasks" ON tasks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tasks" ON tasks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own tasks" ON tasks FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own reviews" ON weekly_reviews FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own reviews" ON weekly_reviews FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own reviews" ON weekly_reviews FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own calendar events" ON calendar_events FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own calendar events" ON calendar_events FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own calendar events" ON calendar_events FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own calendar events" ON calendar_events FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own integrations" ON mcp_integrations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own integrations" ON mcp_integrations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own integrations" ON mcp_integrations FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own integrations" ON mcp_integrations FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own agent actions" ON agent_actions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can insert agent actions" ON agent_actions FOR INSERT WITH CHECK (true); -- Backend service role

CREATE POLICY "Users can view own approvals" ON pending_approvals FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own approvals" ON pending_approvals FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service can insert approvals" ON pending_approvals FOR INSERT WITH CHECK (true); -- Backend service role
