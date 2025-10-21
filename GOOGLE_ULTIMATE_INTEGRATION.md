# 🔥 ULTIMATE Google Integration Guide

**Transform PARA Autopilot into a Google Ecosystem Powerhouse**

---

## 🎯 What You Just Got

With ONE OAuth connection, users can now connect:

- ✅ **Gmail** - Email parsing, search, task extraction
- ✅ **Google Calendar** - Event sync, scheduling
- ✅ **Google Tasks** - Bidirectional task sync
- ✅ **User Profile** - Name, email, avatar

### **The Magic: ONE Click, Everything Connected**

Users click "Connect Google" → Authorize once → Get access to ALL services!

---

## 🚀 Killer Features

### **1. Email → PARA Tasks (AI-Powered)**

**Use Case:** "Hey, can you review the Q4 budget by Friday?"

**What Happens:**
1. Email arrives in Gmail
2. PARA detects unread emails
3. Claude parses email body
4. Extracts: Task = "Review Q4 budget", Due = Friday
5. Creates PARA task
6. Creates Google Task (syncs to user's phone!)
7. Labels email as "PARA/Processed"

**Endpoint:**
```bash
POST /api/google/gmail/email-to-task
{
  "email_id": "msg_123",
  "create_google_task": true
}
```

---

### **2. PARA Tasks ↔ Google Tasks (Bidirectional Sync)**

**Use Case:** User creates task in PARA, wants it on their phone

**What Happens:**
- Task created in PARA → Instantly appears in Google Tasks
- Completed in Google Tasks → Marked done in PARA
- Edited in PARA → Updated in Google Tasks
- Every 5 minutes: Full bidirectional sync

**Endpoints:**
```bash
# Sync all tasks
POST /api/google/tasks/sync
{
  "sync_to_google": true,
  "sync_from_google": true
}

# Get Google Tasks
GET /api/google/tasks/google
```

---

### **3. Gmail Search → PARA Resources**

**Use Case:** "Find all emails about the website redesign"

**What Happens:**
1. Search Gmail with natural language
2. Find relevant emails + threads
3. AI summarizes with Claude
4. Create Resource with email links
5. Link to relevant Project

**Endpoint:**
```bash
POST /api/google/gmail/search
{
  "query": "subject:website redesign",
  "max_results": 50,
  "after": "2025-01-01T00:00:00Z"
}
```

---

### **4. Unread Email Processing**

**Use Case:** Process inbox automatically

**What Happens:**
- Fetch unread emails
- Parse for tasks/deadlines
- Create PARA items
- Label as processed
- Mark as read

**Endpoint:**
```bash
GET /api/google/gmail/unread?max_results=100
```

---

## 📡 API Reference

### **Gmail Endpoints**

#### GET `/api/google/gmail/unread`
Get unread emails

**Query Params:**
- `max_results` - Max emails to fetch (default: 100)

**Response:**
```json
{
  "count": 5,
  "emails": [
    {
      "id": "msg_123",
      "subject": "Q4 Budget Review",
      "from": "alice@company.com",
      "to": "you@company.com",
      "date": "Mon, 21 Oct 2025 10:00:00",
      "body": "Can you review this by Friday?...",
      "snippet": "Can you review...",
      "is_unread": true,
      "is_important": false
    }
  ]
}
```

---

#### POST `/api/google/gmail/search`
Search emails with Gmail query syntax

**Request:**
```json
{
  "query": "from:alice subject:budget after:2025/01/01",
  "max_results": 50,
  "after": "2025-01-01T00:00:00Z"
}
```

**Gmail Query Syntax:**
- `from:alice@example.com` - From specific sender
- `subject:budget` - Subject contains "budget"
- `has:attachment` - Has attachments
- `is:important` - Marked as important
- `is:unread` - Unread only
- `after:2025/01/01` - After date
- `label:work` - Has label

---

#### POST `/api/google/gmail/email-to-task`
Convert email to PARA task using AI

**Request:**
```json
{
  "email_id": "msg_123",
  "create_google_task": true
}
```

**What It Does:**
1. Fetches email by ID
2. Parses with Claude NLP
3. Extracts task details (title, due date, priority)
4. Creates PARA task
5. Creates Google Task (if requested)
6. Labels email as "PARA/Processed"
7. Marks as read

**Response:**
```json
{
  "message": "Email converted to task successfully",
  "task": {
    "id": "task-uuid",
    "title": "Review Q4 budget",
    "due_date": "2025-10-25T17:00:00Z",
    "priority": "high",
    "source": "gmail",
    "source_metadata": {
      "email_id": "msg_123",
      "email_from": "alice@company.com",
      "google_task_id": "gtask_456"
    }
  },
  "google_task": {
    "id": "gtask_456",
    "title": "Review Q4 budget",
    "status": "needsAction"
  }
}
```

---

### **Google Tasks Endpoints**

#### GET `/api/google/tasks/google`
Get all Google Tasks for user

**Response:**
```json
{
  "count": 12,
  "tasks": [
    {
      "id": "gtask_123",
      "title": "Buy groceries",
      "notes": "Milk, eggs, bread",
      "status": "needsAction",
      "due": "2025-10-22T00:00:00Z",
      "is_completed": false
    }
  ]
}
```

---

#### POST `/api/google/tasks/sync`
Bidirectional sync between PARA and Google Tasks

**Request:**
```json
{
  "task_ids": ["task-1", "task-2"],  // Optional - if null, syncs all
  "sync_to_google": true,            // PARA → Google Tasks
  "sync_from_google": true           // Google Tasks → PARA
}
```

**Sync Logic:**

**To Google (PARA → Google Tasks):**
- New PARA task → Create in Google Tasks
- Updated PARA task → Update Google Task
- Completed PARA task → Mark completed in Google
- Stores `google_task_id` in PARA for tracking

**From Google (Google Tasks → PARA):**
- New Google Task → Create PARA task
- Updated Google Task → Update PARA task
- Completed Google Task → Mark PARA task complete
- Stores `google_task_id` in metadata

**Response:**
```json
{
  "message": "Sync completed successfully",
  "synced_to_google": 8,
  "synced_from_google": 3,
  "tasks_to_google": [...],      // First 5 for preview
  "tasks_from_google": [...]     // First 5 for preview
}
```

---

## 🔧 Setup Instructions

### Step 1: Update Google OAuth Scopes

Already done! Your OAuth now requests:
- `calendar.readonly` + `calendar.events`
- `gmail.readonly` + `gmail.modify`
- `tasks`
- `userinfo.email` + `userinfo.profile`

### Step 2: Users Connect Google

1. User clicks "Connect Google"
2. Frontend calls `GET /api/oauth/google/init`
3. Redirects to Google consent screen
4. User sees: "PARA Autopilot wants to access your Calendar, Gmail, and Tasks"
5. User clicks "Allow"
6. OAuth callback stores tokens
7. All services now accessible!

### Step 3: Background Sync (Optional)

Add to your scheduler for automatic email processing:

```python
# jobs/scheduler.py

@scheduler.scheduled_job('interval', minutes=15)
async def process_unread_emails():
    """Process unread emails every 15 minutes"""
    users = get_users_with_google_connected()

    for user in users:
        # Get unread emails
        emails = fetch_unread_emails(user['id'])

        for email in emails:
            # Parse for tasks
            if contains_task_keywords(email):
                # Auto-create task from email
                await convert_email_to_task(email['id'], user['id'])
```

---

## 🎨 Frontend Integration Examples

### Email Search Component

```typescript
// components/gmail/EmailSearch.tsx

import { useState } from 'react';

export function EmailSearch() {
  const [query, setQuery] = useState('');
  const [emails, setEmails] = useState([]);

  const searchEmails = async () => {
    const response = await fetch('/api/google/gmail/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({
        query,
        max_results: 50
      })
    });

    const data = await response.json();
    setEmails(data.emails);
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="from:alice subject:budget"
      />
      <button onClick={searchEmails}>Search Gmail</button>

      {emails.map(email => (
        <EmailCard key={email.id} email={email} />
      ))}
    </div>
  );
}
```

### Task Sync Button

```typescript
// components/tasks/SyncWithGoogle.tsx

export function SyncWithGoogleButton() {
  const [syncing, setSyncing] = useState(false);

  const syncTasks = async () => {
    setSyncing(true);
    try {
      const response = await fetch('/api/google/tasks/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({
          sync_to_google: true,
          sync_from_google: true
        })
      });

      const data = await response.json();
      alert(`✅ Synced! ${data.synced_to_google} → Google, ${data.synced_from_google} ← Google`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <button onClick={syncTasks} disabled={syncing}>
      {syncing ? 'Syncing...' : '🔄 Sync with Google Tasks'}
    </button>
  );
}
```

### Unread Emails Widget

```typescript
// components/dashboard/UnreadEmailsWidget.tsx

export function UnreadEmailsWidget() {
  const [emails, setEmails] = useState([]);

  useEffect(() => {
    fetchUnreadEmails();
  }, []);

  const fetchUnreadEmails = async () => {
    const response = await fetch('/api/google/gmail/unread?max_results=10', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    const data = await response.json();
    setEmails(data.emails);
  };

  const convertToTask = async (emailId: string) => {
    await fetch('/api/google/gmail/email-to-task', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({
        email_id: emailId,
        create_google_task: true
      })
    });

    // Refresh emails
    fetchUnreadEmails();
  };

  return (
    <div className="widget">
      <h3>📧 Unread Emails ({emails.length})</h3>
      {emails.map(email => (
        <div key={email.id} className="email-card">
          <p><strong>{email.from}</strong></p>
          <p>{email.subject}</p>
          <button onClick={() => convertToTask(email.id)}>
            ✅ Create Task
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔥 Advanced Use Cases

### 1. Auto-Process Emails from Boss

```python
# Background job
def process_boss_emails():
    emails = search_emails(query="from:boss@company.com is:unread")

    for email in emails:
        # Auto-create high-priority task
        convert_email_to_task(
            email['id'],
            priority_override="high",
            create_google_task=True
        )
```

### 2. Weekly Email Digest → PARA Resource

```python
def create_weekly_email_digest():
    # Search emails from past week
    emails = search_emails(
        query="is:important after:7daysago",
        max_results=100
    )

    # Group by thread
    threads = group_by_thread(emails)

    # Create Resource with summary
    create_para_resource(
        title=f"Email Digest - Week of {week_start}",
        description=claude_summarize(threads),
        metadata={"email_ids": [e['id'] for e in emails]}
    )
```

### 3. Smart Task Distribution

```python
def smart_task_creation(email):
    """Decide where to create task based on context"""

    parsed = parse_email_with_claude(email)

    # Create in PARA
    para_task = create_para_task(parsed)

    # Sync to Google Tasks if user prefers mobile
    if user_preferences['sync_to_google_tasks']:
        google_tasks.create_task(para_task)

    # Add to calendar if has specific time
    if parsed['has_specific_time']:
        calendar.create_event(para_task)

    # Link to existing project
    if parsed['project_match']:
        link_to_project(para_task, parsed['project_match'])
```

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  USER'S GOOGLE ECOSYSTEM                                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Gmail                Calendar              Google Tasks     │
│  ├─ Inbox              ├─ Events            ├─ My Tasks      │
│  ├─ Sent               ├─ Reminders         ├─ Work          │
│  └─ Labels             └─ Shared            └─ Personal      │
│                                                               │
│         ↓ OAuth2 (ONE authorization) ↓                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PARA AUTOPILOT BACKEND                                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Encrypted Tokens (per user)                                 │
│  ├─ access_token (refreshed hourly)                          │
│  └─ refresh_token (permanent)                                │
│                                                               │
│  Services:                                                    │
│  ├─ GmailMCP          → Read/search/label emails             │
│  ├─ GoogleTasksMCP    → Create/sync/complete tasks           │
│  ├─ GoogleCalendarMCP → Read/create/update events            │
│  └─ NLPParser         → Parse emails with Claude             │
│                                                               │
│  Background Jobs:                                             │
│  ├─ Email processor   → Check unread emails every 15 min     │
│  ├─ Task sync         → Bidirectional sync every 5 min       │
│  └─ Calendar sync     → Fetch events every 5 min             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PARA DATABASE (Supabase)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  tables:                                                      │
│  ├─ tasks                                                     │
│  │  ├─ source_metadata.email_id                              │
│  │  └─ source_metadata.google_task_id                        │
│  │                                                            │
│  ├─ para_items                                                │
│  │  └─ metadata.email_thread_ids                             │
│  │                                                            │
│  └─ calendar_events                                           │
│     └─ external_source = "google_calendar"                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security

- ✅ Tokens encrypted at rest (Fernet AES128)
- ✅ Per-user token isolation
- ✅ Automatic token refresh (hourly)
- ✅ CSRF protection (state parameter)
- ✅ Scope-limited (only requested permissions)
- ✅ User can revoke anytime

---

## 💰 Cost (Still FREE!)

**Google API Quotas (Free Tier):**
- Gmail API: 1 billion quota units/day
  - Read email: 5 units
  - Search: 5 units
  - **You can process 200M emails/day!**

- Google Tasks API: 50,000 requests/day
  - Create/update task: 1 request
  - **You can sync 50,000 tasks/day!**

- Calendar API: 1M requests/day (already covered)

**For 1000 users:**
- 1000 users × 100 emails/day = 100,000 emails = 500,000 units
- **Still 0.05% of free quota!** 🎉

---

## 🚀 What's Next?

### Future Enhancements:

1. **Gmail Sending**
   - Send emails from PARA
   - Weekly review → Email to yourself

2. **Google Drive Integration**
   - Upload files to Drive
   - Link Drive files to PARA items
   - Search Drive from PARA

3. **Smart Inbox Zero**
   - Auto-archive processed emails
   - Auto-label by PARA type
   - Suggest email → Task conversions

4. **Meeting Notes**
   - Calendar event → Google Doc
   - Auto-populate with attendees
   - Link to PARA project

---

## 📚 Summary

**What You Built:**
- ✅ Gmail integration (read, search, parse to tasks)
- ✅ Google Tasks (bidirectional sync)
- ✅ Email → Task conversion (AI-powered)
- ✅ Automatic background processing

**What Users Get:**
- 📧 Never miss an email task again
- ✅ Tasks sync everywhere (PARA + Google Tasks + Phone)
- 🔍 Semantic email search
- 🤖 AI-powered inbox processing
- 📱 Mobile access via Google Tasks

**ONE OAuth, THREE Services, INFINITE Possibilities!** 🔥

---

**Built with ❤️ for PARA Autopilot**
