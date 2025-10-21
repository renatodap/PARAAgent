-- Conversation persistence for AI agent
-- Stores chat history so agent remembers context

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT, -- Auto-generated from first message
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  is_archived BOOLEAN DEFAULT FALSE,
  metadata JSONB DEFAULT '{}'::jsonb -- Custom data
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

-- Individual messages in a conversation
CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  tool_calls JSONB, -- Tool invocations if any
  metadata JSONB DEFAULT '{}'::jsonb, -- Tokens used, cost, etc.
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id, created_at);

-- Pending confirmations (for email approvals, etc.)
CREATE TABLE IF NOT EXISTS agent_confirmations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL, -- 'send_email', 'delete_task', etc.
  action_data JSONB NOT NULL, -- What will be executed
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_confirmations_user ON agent_confirmations(user_id, status);
CREATE INDEX idx_confirmations_expires ON agent_confirmations(expires_at);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversations
  SET updated_at = NOW()
  WHERE id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_updated_at
  AFTER INSERT ON conversation_messages
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_updated_at();

-- Auto-generate conversation titles from first message
CREATE OR REPLACE FUNCTION generate_conversation_title()
RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT title FROM conversations WHERE id = NEW.conversation_id) IS NULL THEN
    UPDATE conversations
    SET title = LEFT(NEW.content, 50)
    WHERE id = NEW.conversation_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_title
  AFTER INSERT ON conversation_messages
  FOR EACH ROW
  WHEN (NEW.role = 'user')
  EXECUTE FUNCTION generate_conversation_title();

COMMENT ON TABLE conversations IS 'Conversation threads with AI agent';
COMMENT ON TABLE conversation_messages IS 'Individual messages in conversations';
COMMENT ON TABLE agent_confirmations IS 'Pending user confirmations for agent actions';
