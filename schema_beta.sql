-- Beta waitlist table for PARA Autopilot
-- Run this in Supabase SQL Editor to add beta waitlist functionality

CREATE TABLE IF NOT EXISTS beta_waitlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    source TEXT DEFAULT 'landing_page',
    signed_up_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'invited', 'registered')),
    invited_at TIMESTAMP WITH TIME ZONE,
    registered_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster email lookups
CREATE INDEX IF NOT EXISTS idx_beta_waitlist_email ON beta_waitlist(email);
CREATE INDEX IF NOT EXISTS idx_beta_waitlist_status ON beta_waitlist(status);
CREATE INDEX IF NOT EXISTS idx_beta_waitlist_signed_up_at ON beta_waitlist(signed_up_at);

-- RLS policies for beta_waitlist
ALTER TABLE beta_waitlist ENABLE ROW LEVEL SECURITY;

-- Allow anyone to sign up
CREATE POLICY "Anyone can sign up for beta" ON beta_waitlist
    FOR INSERT
    WITH CHECK (true);

-- Only service role can read (for admin purposes)
CREATE POLICY "Only service role can read waitlist" ON beta_waitlist
    FOR SELECT
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_beta_waitlist_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_beta_waitlist_updated_at_trigger
    BEFORE UPDATE ON beta_waitlist
    FOR EACH ROW
    EXECUTE FUNCTION update_beta_waitlist_updated_at();

-- Grant permissions
GRANT SELECT, INSERT ON beta_waitlist TO authenticated;
GRANT SELECT, INSERT ON beta_waitlist TO anon;

COMMENT ON TABLE beta_waitlist IS 'Beta waitlist signups for PARA Autopilot';
