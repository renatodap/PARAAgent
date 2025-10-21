-- PARA Detail Pages Schema
-- Adds support for tasks, notes, files, and relationships

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TASKS TABLE (Link tasks to PARA items)
-- ============================================================
CREATE TABLE IF NOT EXISTS para_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    para_item_id UUID NOT NULL REFERENCES para_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    priority TEXT CHECK (priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_para_tasks_item ON para_tasks(para_item_id);
CREATE INDEX idx_para_tasks_user ON para_tasks(user_id);
CREATE INDEX idx_para_tasks_due_date ON para_tasks(due_date) WHERE completed = FALSE;

-- ============================================================
-- NOTES TABLE (Markdown notes for PARA items)
-- ============================================================
CREATE TABLE IF NOT EXISTS para_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    para_item_id UUID NOT NULL REFERENCES para_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_para_notes_item ON para_notes(para_item_id);
CREATE INDEX idx_para_notes_user ON para_notes(user_id);
CREATE INDEX idx_para_notes_created ON para_notes(created_at DESC);

-- ============================================================
-- FILES TABLE (Attachments for PARA items)
-- ============================================================
CREATE TABLE IF NOT EXISTS para_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    para_item_id UUID NOT NULL REFERENCES para_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_para_files_item ON para_files(para_item_id);
CREATE INDEX idx_para_files_user ON para_files(user_id);

-- ============================================================
-- RELATIONSHIPS TABLE (Link any PARA item to any other)
-- ============================================================
CREATE TABLE IF NOT EXISTS para_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_item_id UUID NOT NULL REFERENCES para_items(id) ON DELETE CASCADE,
    to_item_id UUID NOT NULL REFERENCES para_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'related',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent linking item to itself
    CHECK (from_item_id != to_item_id),

    -- Prevent duplicate relationships
    UNIQUE(from_item_id, to_item_id)
);

-- Index for fast queries
CREATE INDEX idx_para_relationships_from ON para_relationships(from_item_id);
CREATE INDEX idx_para_relationships_to ON para_relationships(to_item_id);
CREATE INDEX idx_para_relationships_user ON para_relationships(user_id);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE para_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE para_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE para_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE para_relationships ENABLE ROW LEVEL SECURITY;

-- Tasks Policies
CREATE POLICY "Users can view own tasks"
    ON para_tasks FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tasks"
    ON para_tasks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tasks"
    ON para_tasks FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tasks"
    ON para_tasks FOR DELETE
    USING (auth.uid() = user_id);

-- Notes Policies
CREATE POLICY "Users can view own notes"
    ON para_notes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notes"
    ON para_notes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notes"
    ON para_notes FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notes"
    ON para_notes FOR DELETE
    USING (auth.uid() = user_id);

-- Files Policies
CREATE POLICY "Users can view own files"
    ON para_files FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own files"
    ON para_files FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own files"
    ON para_files FOR DELETE
    USING (auth.uid() = user_id);

-- Relationships Policies
CREATE POLICY "Users can view own relationships"
    ON para_relationships FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own relationships"
    ON para_relationships FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own relationships"
    ON para_relationships FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tasks
CREATE TRIGGER update_para_tasks_updated_at
    BEFORE UPDATE ON para_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to notes
CREATE TRIGGER update_para_notes_updated_at
    BEFORE UPDATE ON para_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- HELPER VIEWS (Optional - for easier querying)
-- ============================================================

-- View to get PARA items with task counts and completion %
CREATE OR REPLACE VIEW para_items_with_stats AS
SELECT
    p.*,
    COUNT(t.id) FILTER (WHERE t.completed = FALSE) as active_tasks_count,
    COUNT(t.id) FILTER (WHERE t.completed = TRUE) as completed_tasks_count,
    COUNT(t.id) as total_tasks_count,
    CASE
        WHEN COUNT(t.id) = 0 THEN 0
        ELSE ROUND((COUNT(t.id) FILTER (WHERE t.completed = TRUE)::NUMERIC / COUNT(t.id)::NUMERIC) * 100)
    END as completion_percentage
FROM para_items p
LEFT JOIN para_tasks t ON p.id = t.para_item_id
GROUP BY p.id;

-- ============================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================

-- Example: Insert a test project with tasks and notes
-- COMMENT OUT THIS SECTION IN PRODUCTION

/*
INSERT INTO para_items (user_id, title, description, para_type, status)
VALUES (
    (SELECT id FROM auth.users LIMIT 1),
    'Example Project',
    'This is a test project with tasks and notes',
    'project',
    'active'
) RETURNING id;

-- Use the returned ID to add tasks and notes
*/
