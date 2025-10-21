# AI Agent Use Cases - What Users Will Actually Ask For

**The "Autopilot" Part of PARA Autopilot**

---

## 🎯 Top 20 Real-World Use Cases

### **1. Email Drafting & Sending**

**User:** "Email Alice about the Q4 budget review"

**Agent Flow:**
1. Search PARA for "Q4 budget" → Find project + status
2. Search emails from Alice → Get context
3. Find Alice's email address from contacts
4. Draft email with context
5. Show draft for confirmation
6. Send email
7. Log action, create follow-up task

**Edge Cases:**
- Budget project not found → Ask user to clarify or create
- Multiple Alices → Ask which one
- No recent context → Ask user what to include

---

### **2. Meeting Scheduling**

**User:** "Schedule 30 minutes with Bob to discuss the website redesign next week"

**Agent Flow:**
1. Search calendar for Bob's availability
2. Find "website redesign" project → Get context
3. Check user's availability next week
4. Propose 3 time slots
5. After user confirms → Create calendar event
6. Draft meeting invite email with agenda
7. Send invite to Bob
8. Create task: "Prepare for website redesign meeting"

**Smart Features:**
- Avoids user's focus time blocks
- Suggests times when both are usually available
- Auto-generates agenda from project status

---

### **3. Task Breakdown & Project Planning**

**User:** "Break down the 'Launch new blog' project into tasks"

**Agent Flow:**
1. Find "Launch new blog" project
2. Analyze project description & goals
3. Generate task breakdown:
   - Research hosting platforms
   - Choose CMS (WordPress vs. Ghost)
   - Design logo & branding
   - Write first 3 blog posts
   - Set up SEO & analytics
   - Launch announcement
4. Estimate duration for each task
5. Suggest priorities
6. Create tasks in PARA (with user confirmation)
7. Add to Google Tasks for mobile access

---

### **4. Weekly Review Preparation**

**User:** "Prepare my weekly review"

**Agent Flow:**
1. Fetch last week's data:
   - Completed tasks (from PARA + Google Tasks)
   - Calendar events attended
   - Emails sent/received (key threads)
   - Projects updated
2. Analyze patterns:
   - "You completed 18/22 tasks (82%)"
   - "Most productive: Tuesday morning"
   - "3 meetings ran over time"
   - "Website redesign made significant progress"
3. Generate insights:
   - "You spent 40% of time on Q4 planning"
   - "Marketing project hasn't been touched in 5 days"
   - "Consider delegating email responses"
4. Create weekly review document
5. Suggest next week's focus

---

### **5. Information Retrieval (Context-Aware Search)**

**User:** "What did Alice say about the budget last week?"

**Agent Flow:**
1. Search emails from Alice
2. Filter by date range (last week)
3. Keyword search: "budget"
4. Semantic search for related terms (financial, Q4, expenses)
5. Return:
   - Email snippets
   - Thread context
   - Attachments (if any)
   - Related PARA items

**Response:**
"Alice sent 2 emails about the budget last week:
1. Oct 15: Asked for revenue projections by Friday
   - Mentioned need to cut 10% from marketing
   - Attached: Q3_budget_template.xlsx
2. Oct 17: Confirmed meeting for Oct 25

Related: Your project 'Q4 Financial Planning' (due Oct 31)"

---

### **6. Proactive Reminders**

**Agent (unprompted):** "Hey! You have a task 'Review contract' due in 2 hours, but your calendar shows you're in meetings until 5pm. Should I reschedule it for tomorrow morning?"

**Agent Logic:**
- Monitors upcoming tasks vs. calendar
- Detects conflicts
- Proactively suggests solutions

---

### **7. Research & Summarization**

**User:** "Summarize all my notes about the product launch"

**Agent Flow:**
1. Search PARA items tagged "product launch"
2. Search emails mentioning "product launch"
3. Search Google Drive for related docs
4. Fetch calendar events with "product launch"
5. Use Claude to summarize:
   - Key decisions made
   - Stakeholders involved
   - Timeline & milestones
   - Open questions
   - Next steps
6. Create summary document
7. Ask: "Should I create a Resource with this summary?"

---

### **8. Delegation Assistance**

**User:** "Delegate the 'Design mockups' task to Sarah"

**Agent Flow:**
1. Find task "Design mockups"
2. Find Sarah's contact info
3. Draft delegation email:
   - Task description
   - Context from project
   - Deadline
   - Resources needed
4. Update task status to "delegated"
5. Create follow-up task: "Check in with Sarah on mockups"
6. Send email after confirmation

---

### **9. Follow-Up Tracking**

**User:** "Did Bob ever reply about the proposal?"

**Agent Flow:**
1. Search sent emails to Bob about "proposal"
2. Check for replies
3. If no reply:
   - Calculate days since sent (e.g., 5 days)
   - Suggest: "Bob hasn't replied in 5 days. Should I draft a follow-up?"
4. If replied:
   - Show reply summary
   - Check if action required

---

### **10. Automatic Task Creation from Context**

**Agent (proactive):** "I noticed you scheduled a meeting with the design team for Thursday. Should I create tasks for:
- Prepare presentation deck
- Review design mockups
- Send agenda to team"

**Agent Logic:**
- Monitors calendar events
- Detects meetings requiring prep
- Suggests relevant tasks

---

### **11. Priority Rebalancing**

**User:** "I'm overwhelmed. What should I focus on today?"

**Agent Flow:**
1. Analyze all pending tasks
2. Consider:
   - Deadlines (urgent)
   - Project importance
   - Estimated duration
   - Dependencies
   - User's energy patterns (historical data)
3. Suggest:
   "Based on your deadlines and work patterns:

   **Morning (high energy):**
   1. Finish Q4 budget (due tomorrow, 2 hours)
   2. Review contract (due Friday, 1 hour)

   **Afternoon:**
   3. Email responses (30 min)
   4. Prep for Thursday meeting (45 min)

   **Defer to tomorrow:**
   - Blog post draft (not urgent)
   - Research new tools (low priority)

   This leaves 2 hours buffer for unexpected tasks."

---

### **12. Email Triage & Categorization**

**User:** "Process my unread emails"

**Agent Flow:**
1. Fetch unread emails (e.g., 47 emails)
2. Categorize with AI:
   - **Urgent action required:** 3 emails
   - **Needs response (not urgent):** 12 emails
   - **FYI only:** 18 emails
   - **Newsletters/marketing:** 14 emails
3. For action-required emails:
   - Extract tasks
   - Suggest creating PARA tasks
4. Auto-label and archive processed emails
5. Present summary:
   "47 unread emails processed:
   - 3 need urgent action (shown below)
   - 12 need responses (scheduled for tomorrow)
   - 32 archived (low priority)"

---

### **13. Meeting Notes & Action Items**

**User:** "Extract action items from the team meeting"

**Agent Flow:**
1. Find "team meeting" calendar event
2. Check for meeting notes (Google Doc linked?)
3. If no notes: "I don't see notes. Should I create a template?"
4. If notes exist:
   - Parse for action items
   - Extract: Who, What, When
   - Create tasks for each action
   - Assign owners (if mentioned)
5. Link tasks to relevant projects

**Example Output:**
"Found 5 action items from Tuesday's team meeting:
1. Alice: Review budget by Friday ✅ (created task)
2. Bob: Design mockups by next Monday ✅ (created task)
3. You: Send proposal to client by EOD ✅ (created task)
4. Sarah: Schedule follow-up meeting (no deadline mentioned)
   → Should I ask Sarah for a deadline?
5. Team: Read new policy doc (assigned to everyone)
   → Should I create a task for you?"

---

### **14. Automatic Project Archiving**

**Agent (proactive):** "Your project 'Q3 Website Redesign' has been marked complete for 30 days with no activity. Should I archive it?"

**Agent Logic:**
- Monitors completed projects
- Suggests archiving after inactivity period
- Preserves all data but moves to Archive

---

### **15. Habit Tracking & Nudges**

**Agent (proactive):** "You haven't worked on your Area 'Health & Fitness' in 10 days. Your goal was 3 workouts per week. Should I schedule gym time this week?"

**Agent Logic:**
- Tracks Areas (ongoing responsibilities)
- Compares against stated goals
- Nudges when falling behind

---

### **16. Context Switching Assistance**

**User:** "What was I working on before the meeting?"

**Agent Flow:**
1. Check calendar for recent meeting
2. Look at tasks/projects updated before meeting
3. Check last-opened files/emails
4. Return:
   "Before your 2pm meeting with Alice, you were:
   - Editing 'Q4_Budget_Draft.xlsx'
   - Working on task 'Revenue projections'
   - Last email sent to finance team at 1:47pm

   Pick up where you left off?"

---

### **17. Duplicate Detection**

**Agent (proactive):** "I noticed you have similar tasks:
- 'Email Bob about proposal' (created Oct 15)
- 'Follow up with Bob on project proposal' (created Oct 20)

These seem like duplicates. Should I merge them?"

---

### **18. Smart Suggestions from Patterns**

**Agent (proactive):** "I noticed you always schedule 'Deep work' on Tuesday mornings and you're most productive then. Should I block Tuesday 9am-12pm as recurring focus time?"

**Agent Logic:**
- Analyzes historical patterns
- Suggests optimizations

---

### **19. Goal Progress Tracking**

**User:** "How am I doing on my Q4 goals?"

**Agent Flow:**
1. Find Q4 goals (Areas or Projects)
2. Calculate progress:
   - Tasks completed vs. total
   - Time spent (from calendar)
   - Milestones hit
3. Compare to timeline (Q4 ends Dec 31)
4. Return:
   "Q4 Goals Progress:

   **On track:**
   - Product launch: 75% complete (ahead of schedule!)

   **At risk:**
   - Blog redesign: 40% complete (behind schedule)
     → You have 10 weeks left. Need to complete 6% per week.
     → Should I schedule more time for this?

   **Needs attention:**
   - Marketing campaign: 0% complete (not started!)
     → This is due Dec 15. Should we defer or prioritize?"

---

### **20. Natural Language Queries**

**User:** "What's on my plate this week?"

**Agent:**
"Here's your week ahead:

**Tasks (18 total):**
- 5 high priority
- 8 medium priority
- 5 low priority

**Top 3 urgent:**
1. Q4 budget review (due Friday)
2. Client proposal (due Thursday)
3. Team presentation prep (due Wednesday)

**Meetings (12 total):**
- Monday: 3 meetings (4 hours)
- Tuesday: Focus day (no meetings!)
- Wednesday: 2 meetings (2 hours)
- Thursday: 4 meetings (5 hours) ⚠️ Heavy day!
- Friday: 3 meetings (3 hours)

**Projects requiring attention:**
- Website Redesign (hasn't been updated in 5 days)
- Q4 Planning (on track)

**Recommendations:**
- Your Thursday is packed. Consider moving 1-2 meetings.
- Tuesday is your best day for deep work on the website.
- You're at 80% capacity this week (sustainable).

Want me to schedule your Tuesday deep work?"

---

## 🧠 How The Agent Works (Technical)

### **Architecture: Claude with Tool Use**

```python
# Agent system prompt
AGENT_SYSTEM_PROMPT = """
You are PARA Autopilot - an AI assistant that helps users manage their work and life using the PARA method (Projects, Areas, Resources, Archive).

You have access to the user's:
- PARA items (projects, areas, resources, archives)
- Tasks (with due dates, priorities, status)
- Calendar events
- Emails (Gmail integration)
- Google Tasks
- Contact list
- Historical data (what they worked on, when)

When the user asks you to do something:

1. UNDERSTAND INTENT
   - What does the user want?
   - What information do you need?

2. GATHER CONTEXT
   - Search their PARA system
   - Search their emails
   - Check their calendar
   - Use semantic search if needed

3. REASON & PLAN
   - Break down multi-step tasks
   - Identify missing information
   - Consider edge cases

4. CONFIRM BEFORE ACTING
   - Always show drafts before sending emails
   - Always confirm before creating/deleting items
   - Explain your reasoning

5. EXECUTE & LOG
   - Perform the action
   - Log what you did
   - Suggest follow-up actions

6. HANDLE ERRORS GRACEFULLY
   - If info not found, ask clarifying questions
   - Suggest alternatives
   - Never guess or make up information

TOOLS AVAILABLE:
- search_para_items(query) - Semantic search
- search_emails(query, from, date_range)
- search_contacts(name)
- get_calendar_events(start, end)
- create_task(title, due_date, priority, project_id)
- send_email(to, subject, body)
- create_calendar_event(title, start, end, attendees)
- get_project_status(project_id)
- analyze_productivity(date_range)

Be proactive, context-aware, and helpful!
"""

# User message
user_message = "Email Alice about the Q4 budget review"

# Agent thinks + uses tools
response = claude.messages.create(
    model="claude-sonnet-4",
    max_tokens=4000,
    system=AGENT_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_message}],
    tools=[
        {
            "name": "search_para_items",
            "description": "Search user's PARA items semantically",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "para_type": {"type": "string", "enum": ["project", "area", "resource", "archive"]}
                }
            }
        },
        {
            "name": "search_emails",
            "description": "Search user's emails",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "from": {"type": "string"},
                    "after": {"type": "string"}
                }
            }
        },
        # ... more tools
    ]
)

# Claude responds with tool calls:
# 1. search_para_items({"query": "Q4 budget"})
# 2. search_emails({"query": "budget", "from": "alice"})
# 3. search_contacts({"name": "Alice"})

# Execute tools, feed results back to Claude
# Claude drafts email with context
# Shows to user for confirmation
# User approves → send_email() tool called
```

---

## 🎯 Key Capabilities

### **1. Context-Aware Reasoning**
- Knows user's projects, tasks, emails
- Understands relationships (this task belongs to that project)
- Remembers past interactions

### **2. Tool Use (Function Calling)**
- Claude decides which tools to call
- Chains tools together (search → analyze → draft → send)
- Handles tool errors gracefully

### **3. Confirmation Loops**
- Never performs destructive actions without confirmation
- Shows drafts/plans before executing
- Explains reasoning

### **4. Proactive Suggestions**
- Monitors for patterns
- Suggests optimizations
- Nudges when needed

### **5. Natural Language Understanding**
- "Email Alice" → Finds Alice's email, drafts contextual email
- "What's on my plate?" → Summarizes tasks + calendar
- "I'm overwhelmed" → Analyzes and suggests priorities

---

## 🚀 Implementation Roadmap

**Phase 1: Conversational Interface** (Week 1)
- Chat endpoint with Claude
- System prompt with user context
- Basic tool definitions

**Phase 2: Core Tools** (Week 2)
- search_para_items
- search_emails
- create_task
- send_email

**Phase 3: Advanced Tools** (Week 3)
- Calendar management
- Meeting scheduling
- Task delegation
- Project breakdown

**Phase 4: Proactive Agent** (Week 4)
- Background monitoring
- Pattern detection
- Automatic suggestions
- Smart reminders

---

## 💬 Example Conversations

### **Complex Multi-Step Request**

**User:** "I need to present our Q4 progress to the board next week. Help me prepare."

**Agent:**
"I'll help you prepare for the board presentation. Let me gather the information:

[Uses tools to search Q4 projects, analyze completion rates, check calendar]

Here's what I found:

**Q4 Progress Summary:**
- 4 major projects (3 on track, 1 at risk)
- 87% of planned tasks completed
- Key wins: Product launch, new partnerships
- Challenges: Marketing campaign delayed

**Suggested Presentation Outline:**
1. Executive Summary (1 slide)
2. Project Status Dashboard (1 slide)
3. Key Achievements (2 slides)
4. Challenges & Mitigation (1 slide)
5. Q1 Roadmap Preview (1 slide)

**Next Steps:**
1. Should I create a Google Doc with detailed talking points?
2. Should I schedule prep time on your calendar?
3. Should I draft an email to the board with pre-read materials?

What would you like me to do first?"

---

### **Handling Ambiguity**

**User:** "Schedule a call with the team"

**Agent:**
"I need a bit more information:

**Which team?**
- Engineering Team (8 people, last meeting: Oct 15)
- Marketing Team (5 people, last meeting: Oct 10)
- Leadership Team (4 people, last meeting: Oct 18)

**When?**
- This week (I see you have availability Wed 2-4pm, Fri 10-12pm)
- Next week (more flexibility)

**What's it about?**
I can suggest an agenda based on:
- Recent project updates
- Outstanding action items
- Upcoming deadlines

Just let me know which team and when, and I'll handle the rest!"

---

## 🎨 Frontend: Agent Chat Interface

```typescript
// components/agent/AgentChat.tsx

function AgentChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    // Add user message
    setMessages([...messages, {role: 'user', content: input}]);

    // Call agent
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: input,
        context: {
          user_id: currentUser.id,
          timezone: 'America/New_York'
        }
      })
    });

    const data = await response.json();

    // Add agent response
    setMessages([...messages, {
      role: 'user',
      content: input
    }, {
      role: 'assistant',
      content: data.message,
      tool_calls: data.tool_calls,
      actions: data.suggested_actions
    }]);

    setInput('');
  };

  return (
    <div className="chat-interface">
      <div className="messages">
        {messages.map((msg, i) => (
          <Message key={i} {...msg} />
        ))}
      </div>

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask me anything... 'Email Alice about the budget'"
      />
    </div>
  );
}
```

---

**This is what transforms PARA Autopilot from a "smart organizer" into a true "AI assistant".** 🤖

Want me to build the conversational agent system now?
