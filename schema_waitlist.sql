-- Waitlist table for Phase 2 market validation
-- Stores email signups from landing page

CREATE TABLE IF NOT EXISTS waitlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Position in waitlist (auto-incremented)
    position INTEGER,

    -- Where they came from (organic, reddit_ad, facebook_ad, referral)
    source TEXT DEFAULT 'organic',

    -- UTM tracking
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,

    -- Status tracking
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'invited', 'converted', 'unsubscribed')),

    -- When they were invited to early access
    invited_at TIMESTAMPTZ,

    -- When they became a paying customer
    converted_at TIMESTAMPTZ,

    -- Referral tracking (for "refer 3 friends, skip the line")
    referral_code TEXT UNIQUE,
    referred_by TEXT REFERENCES waitlist(referral_code),
    referral_count INTEGER DEFAULT 0,

    -- Email engagement
    welcome_email_sent_at TIMESTAMPTZ,
    last_email_sent_at TIMESTAMPTZ,
    email_open_count INTEGER DEFAULT 0,
    email_click_count INTEGER DEFAULT 0
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist(email);
CREATE INDEX IF NOT EXISTS idx_waitlist_status ON waitlist(status);
CREATE INDEX IF NOT EXISTS idx_waitlist_created_at ON waitlist(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_waitlist_source ON waitlist(source);
CREATE INDEX IF NOT EXISTS idx_waitlist_referral_code ON waitlist(referral_code);

-- Function to auto-assign position
CREATE OR REPLACE FUNCTION assign_waitlist_position()
RETURNS TRIGGER AS $$
BEGIN
    NEW.position = (SELECT COALESCE(MAX(position), 0) + 1 FROM waitlist);

    -- Generate unique referral code (6 chars)
    NEW.referral_code = UPPER(SUBSTRING(MD5(NEW.email || NOW()::TEXT) FROM 1 FOR 6));

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-assign position on insert
DROP TRIGGER IF EXISTS set_waitlist_position ON waitlist;
CREATE TRIGGER set_waitlist_position
    BEFORE INSERT ON waitlist
    FOR EACH ROW
    EXECUTE FUNCTION assign_waitlist_position();

-- Function to increment referral count when someone signs up with referral code
CREATE OR REPLACE FUNCTION increment_referral_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.referred_by IS NOT NULL THEN
        UPDATE waitlist
        SET referral_count = referral_count + 1
        WHERE referral_code = NEW.referred_by;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_referral_count ON waitlist;
CREATE TRIGGER update_referral_count
    AFTER INSERT ON waitlist
    FOR EACH ROW
    EXECUTE FUNCTION increment_referral_count();

-- View for analytics
CREATE OR REPLACE VIEW waitlist_analytics AS
SELECT
    DATE(created_at) as signup_date,
    COUNT(*) as signups,
    COUNT(*) FILTER (WHERE status = 'converted') as conversions,
    source,
    utm_campaign
FROM waitlist
GROUP BY DATE(created_at), source, utm_campaign
ORDER BY signup_date DESC;

-- Sample query: Get conversion rate by source
-- SELECT
--     source,
--     COUNT(*) as total_signups,
--     COUNT(*) FILTER (WHERE status = 'converted') as conversions,
--     ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'converted') / COUNT(*), 2) as conversion_rate_pct
-- FROM waitlist
-- GROUP BY source
-- ORDER BY conversion_rate_pct DESC;
