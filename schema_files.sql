-- File Storage Schema for PARA Autopilot Knowledge Management
-- Run this in Supabase SQL Editor

-- ============================================
-- 1. Enable Storage (if not already enabled)
-- ============================================

-- Create storage bucket for user files
INSERT INTO storage.buckets (id, name, public)
VALUES ('para-files', 'para-files', false)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 2. Files Metadata Table
-- ============================================

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    para_item_id UUID REFERENCES para_items(id) ON DELETE SET NULL,

    -- File metadata
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'pdf', 'image', 'document', etc.
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    storage_path TEXT NOT NULL, -- Path in Supabase Storage
    file_url TEXT, -- Public or signed URL

    -- Content extraction
    extracted_text TEXT, -- Full text extracted from file
    ocr_text TEXT, -- OCR text for images
    page_count INTEGER, -- For PDFs

    -- AI processing
    summary TEXT, -- AI-generated summary
    keywords TEXT[], -- Extracted keywords
    embedding vector(1536), -- Vector embedding for search

    -- Metadata
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE, -- When AI processing completed
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 3. Indexes for Performance
-- ============================================

CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_para_item_id ON files(para_item_id);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_uploaded_at ON files(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_processing_status ON files(processing_status);

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS idx_files_embedding ON files USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_files_extracted_text_fts ON files USING gin(to_tsvector('english', extracted_text));

-- ============================================
-- 4. RLS Policies for Security
-- ============================================

ALTER TABLE files ENABLE ROW LEVEL SECURITY;

-- Users can only see their own files
CREATE POLICY "Users can view own files" ON files
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can upload files
CREATE POLICY "Users can upload files" ON files
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own files
CREATE POLICY "Users can update own files" ON files
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own files
CREATE POLICY "Users can delete own files" ON files
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================
-- 5. Storage Bucket Policies
-- ============================================

-- Allow authenticated users to upload files to their own folder
CREATE POLICY "Users can upload to own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'para-files' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow users to read their own files
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'para-files' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow users to delete their own files
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'para-files' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- ============================================
-- 6. Add file_url column to para_items
-- ============================================

ALTER TABLE para_items ADD COLUMN IF NOT EXISTS file_id UUID REFERENCES files(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_para_items_file_id ON para_items(file_id);

-- ============================================
-- 7. Functions for File Processing
-- ============================================

-- Function to update file updated_at timestamp
CREATE OR REPLACE FUNCTION update_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_files_updated_at_trigger
    BEFORE UPDATE ON files
    FOR EACH ROW
    EXECUTE FUNCTION update_files_updated_at();

-- Function to get file storage stats
CREATE OR REPLACE FUNCTION get_user_storage_stats(p_user_id UUID)
RETURNS TABLE (
    total_files BIGINT,
    total_size_bytes BIGINT,
    total_size_mb NUMERIC,
    file_types JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_files,
        COALESCE(SUM(file_size_bytes), 0)::BIGINT as total_size_bytes,
        ROUND(COALESCE(SUM(file_size_bytes), 0)::NUMERIC / 1024 / 1024, 2) as total_size_mb,
        jsonb_object_agg(file_type, count) as file_types
    FROM (
        SELECT
            file_type,
            COUNT(*)::INTEGER as count
        FROM files
        WHERE user_id = p_user_id
        GROUP BY file_type
    ) type_counts;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 8. Grant Permissions
-- ============================================

GRANT SELECT, INSERT, UPDATE, DELETE ON files TO authenticated;
GRANT USAGE ON SEQUENCE files_id_seq TO authenticated;

-- ============================================
-- Comments for Documentation
-- ============================================

COMMENT ON TABLE files IS 'Stores metadata and extracted content for uploaded files (PDFs, images, documents)';
COMMENT ON COLUMN files.extracted_text IS 'Full text extracted from PDFs or OCR from images';
COMMENT ON COLUMN files.embedding IS 'Vector embedding for semantic search across file content';
COMMENT ON COLUMN files.processing_status IS 'Status of AI processing: pending, processing, completed, failed';
COMMENT ON COLUMN files.storage_path IS 'Path in Supabase Storage bucket (format: {user_id}/{file_id}/{filename})';

-- ============================================
-- Success Message
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'File storage schema created successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Verify storage bucket "para-files" exists';
    RAISE NOTICE '2. Test file upload via API';
    RAISE NOTICE '3. Configure PDF extraction and AI processing';
END $$;
