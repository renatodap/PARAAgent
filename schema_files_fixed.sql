-- File Storage Schema for PARA Autopilot Knowledge Management
-- Run this in Supabase SQL Editor

-- ============================================
-- STEP 1: Enable Required Extensions
-- ============================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- STEP 2: Create para_items table (if not exists)
-- ============================================

CREATE TABLE IF NOT EXISTS para_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    notes TEXT,
    para_type TEXT NOT NULL CHECK (para_type IN ('project', 'area', 'resource', 'archive')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STEP 3: Create Files Table
-- ============================================

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    para_item_id UUID REFERENCES para_items(id) ON DELETE SET NULL,

    -- File metadata
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'pdf', 'image', 'link', 'document'
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    storage_path TEXT NOT NULL,
    file_url TEXT,

    -- Content extraction
    extracted_text TEXT,
    ocr_text TEXT,
    page_count INTEGER,

    -- AI processing
    summary TEXT,
    keywords TEXT[],
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',

    -- Status tracking
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STEP 4: Create Indexes
-- ============================================

-- User lookup
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_para_items_user_id ON para_items(user_id);

-- File type filtering
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);

-- Status filtering
CREATE INDEX IF NOT EXISTS idx_files_processing_status ON files(processing_status);

-- Full-text search on extracted content
CREATE INDEX IF NOT EXISTS idx_files_extracted_text_fts ON files USING gin(to_tsvector('english', extracted_text));

-- Vector similarity search (for semantic search)
CREATE INDEX IF NOT EXISTS idx_files_embedding ON files USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- STEP 5: Row Level Security (RLS)
-- ============================================

-- Enable RLS
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE para_items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (if any)
DROP POLICY IF EXISTS "Users can view own files" ON files;
DROP POLICY IF EXISTS "Users can insert own files" ON files;
DROP POLICY IF EXISTS "Users can update own files" ON files;
DROP POLICY IF EXISTS "Users can delete own files" ON files;

DROP POLICY IF EXISTS "Users can view own para_items" ON para_items;
DROP POLICY IF EXISTS "Users can insert own para_items" ON para_items;
DROP POLICY IF EXISTS "Users can update own para_items" ON para_items;
DROP POLICY IF EXISTS "Users can delete own para_items" ON para_items;

-- Files policies
CREATE POLICY "Users can view own files" ON files
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own files" ON files
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own files" ON files
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own files" ON files
    FOR DELETE USING (auth.uid() = user_id);

-- PARA items policies
CREATE POLICY "Users can view own para_items" ON para_items
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own para_items" ON para_items
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own para_items" ON para_items
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own para_items" ON para_items
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- STEP 6: Storage Bucket Setup
-- ============================================

-- Create storage bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('para-files', 'para-files', false)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS policies
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'para-files' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
USING (bucket_id = 'para-files' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (bucket_id = 'para-files' AND auth.uid()::text = (storage.foldername(name))[1]);

-- ============================================
-- STEP 7: Helper Functions
-- ============================================

-- Storage stats function
CREATE OR REPLACE FUNCTION get_user_storage_stats(p_user_id UUID)
RETURNS TABLE (
    total_files BIGINT,
    total_size_bytes BIGINT,
    total_size_mb NUMERIC,
    by_type JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_files,
        SUM(file_size_bytes)::BIGINT as total_size_bytes,
        ROUND(SUM(file_size_bytes) / 1024.0 / 1024.0, 2) as total_size_mb,
        jsonb_agg(
            jsonb_build_object(
                'file_type', file_type,
                'count', count,
                'size_bytes', size_bytes
            )
        ) as by_type
    FROM (
        SELECT
            file_type,
            COUNT(*)::BIGINT as count,
            SUM(file_size_bytes)::BIGINT as size_bytes
        FROM files
        WHERE user_id = p_user_id
        GROUP BY file_type
    ) type_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION
-- ============================================

-- Check if tables were created
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'files') THEN
        RAISE NOTICE 'SUCCESS: files table created';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'para_items') THEN
        RAISE NOTICE 'SUCCESS: para_items table created';
    END IF;

    IF EXISTS (SELECT FROM storage.buckets WHERE id = 'para-files') THEN
        RAISE NOTICE 'SUCCESS: para-files bucket created';
    END IF;
END $$;
