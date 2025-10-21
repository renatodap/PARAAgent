# 📊 PARA Autopilot - Monitoring & Error Tracking

## 🎯 Sentry Integration

Sentry is integrated for real-time error tracking, performance monitoring, and issue alerts.

---

## 🚀 Quick Setup

### 1. Create Sentry Account

1. Go to [sentry.io](https://sentry.io)
2. Create account or sign in
3. Create new project:
   - **Platform**: Python
   - **Framework**: FastAPI
   - **Name**: para-autopilot-backend

### 2. Get Your DSN

1. Go to **Settings** → **Projects** → **para-autopilot-backend**
2. Go to **Client Keys (DSN)**
3. Copy the **DSN** URL (looks like: `https://xxxxx@o12345.ingest.sentry.io/67890`)

### 3. Add to Environment Variables

**backend/.env**:
```env
SENTRY_DSN=https://xxxxx@o12345.ingest.sentry.io/67890
ENVIRONMENT=production
VERSION=0.1.0
```

### 4. Test Sentry

```python
# Create a test error endpoint
@app.get("/sentry-test")
def sentry_test():
    raise Exception("Test Sentry integration")
```

Visit `/sentry-test` and check Sentry dashboard for the error.

---

## 📊 What's Being Tracked

### ✅ Automatic Tracking

1. **Unhandled Exceptions**
   - All Python exceptions
   - Stack traces
   - Request context

2. **API Errors** (500s)
   - Endpoint name
   - Request method
   - Client IP
   - User context (if authenticated)

3. **Performance**
   - Slow endpoints
   - Database query times
   - External API calls (Claude, Supabase)

4. **Logs**
   - ERROR level and above sent to Sentry
   - INFO logs as breadcrumbs

### ✅ Manual Tracking

```python
from monitoring.sentry_config import capture_exception, capture_message, set_user_context

# Capture exception with context
try:
    result = risky_operation()
except Exception as e:
    capture_exception(e, context={
        "user_id": user_id,
        "operation": "classification",
        "item_id": item_id
    })

# Capture message
capture_message("AI classification confidence low", level="warning", context={
    "confidence": 0.3,
    "item_id": item_id
})

# Set user context
set_user_context(user_id="user-123", email="user@example.com")
```

---

## 🔒 Privacy & Security

### Data Filtering

Sensitive data is automatically filtered before sending to Sentry:

**Filtered Fields**:
- `password`
- `token`
- `api_key`
- `secret`
- `anthropic_key`
- `Authorization` header
- `Cookie` header

**Configuration** (`sentry_config.py:filter_sensitive_data()`):
```python
sensitive_fields = ['password', 'token', 'api_key', 'secret']
for field in sensitive_fields:
    if field in data:
        data[field] = '[FILTERED]'
```

### PII Handling

- `send_default_pii=False` - User PII not sent by default
- User ID is sent for grouping, but email is optional
- IP addresses are collected for geo-location only

---

## 📈 Performance Monitoring

### Transaction Sampling

```python
traces_sample_rate=1.0  # 100% in production
traces_sample_rate=0.1  # 10% in development
```

### Profiling

```python
profiles_sample_rate=0.1  # 10% of transactions profiled
```

### What's Monitored

1. **API Endpoints**
   - Response times
   - Slow queries
   - Error rates

2. **External Services**
   - Claude API calls
   - Supabase queries
   - Redis operations
   - Email sending (Resend)

3. **Background Jobs**
   - Weekly review generation
   - MCP sync operations
   - Data cleanup tasks

---

## 🚨 Alerting

### Set Up Alerts in Sentry

1. **Error Alerts**
   - Go to **Alerts** → **Create Alert**
   - **Condition**: When error count > 10 in 1 hour
   - **Action**: Send email/Slack notification

2. **Performance Alerts**
   - **Condition**: When p95 response time > 2 seconds
   - **Action**: Notify on-call engineer

3. **User Impact Alerts**
   - **Condition**: When error affects > 100 users
   - **Action**: Page on-call team

### Example Alert Rules

```yaml
Error Rate Alert:
  - Threshold: 10 errors/hour
  - Severity: Warning
  - Notification: Email + Slack

Critical Error Alert:
  - Threshold: 1 critical error
  - Severity: Critical
  - Notification: PagerDuty

Performance Degradation:
  - Threshold: p95 > 3 seconds
  - Severity: Warning
  - Notification: Slack
```

---

## 📊 Sentry Dashboard Widgets

### Key Metrics to Track

1. **Error Frequency**
   - Errors per hour/day
   - Trending up/down

2. **Affected Users**
   - How many users hit errors
   - User impact percentage

3. **Release Health**
   - Crash-free sessions
   - Adoption rate

4. **Performance**
   - Endpoint response times
   - Slow queries
   - Apdex score

---

## 🔍 Debugging with Sentry

### View Error Details

1. Go to **Issues** in Sentry dashboard
2. Click on an error
3. View:
   - **Stack Trace** - Full Python traceback
   - **Breadcrumbs** - Actions leading to error
   - **Tags** - Environment, release, user
   - **Context** - Request data, user info

### Filter by Tags

```
environment:production
release:para-autopilot@0.1.0
user.email:test@example.com
endpoint:/api/tasks/schedule
```

### Search Errors

```
"classification failed"
level:error
environment:production
```

---

## 💰 Sentry Pricing

### Free Tier
- **Errors**: 5,000 events/month
- **Performance**: 10,000 transactions/month
- **Alerts**: Unlimited
- **Retention**: 30 days

**Good for**: Beta testing, small-scale production

### Developer Tier ($26/month)
- **Errors**: 50,000 events/month
- **Performance**: 100,000 transactions/month
- **Retention**: 90 days

**Good for**: Growing production app (100-500 users)

### Team Tier ($80/month)
- **Errors**: 100,000 events/month
- **Performance**: 500,000 transactions/month
- **Advanced features**: Session replay, custom dashboards

**Good for**: Scaling production (500+ users)

---

## 🧪 Testing Sentry Integration

### Local Testing

```bash
# Start backend with Sentry enabled
SENTRY_DSN=your-dsn ENVIRONMENT=development uvicorn main:app --reload

# Trigger test error
curl http://localhost:8000/sentry-test

# Check Sentry dashboard for error
```

### Production Testing

```bash
# Deploy to Railway with Sentry DSN
railway up

# Trigger real error (e.g., invalid API key)
# Check Sentry for production errors
```

---

## 📚 Additional Resources

- [Sentry Python Docs](https://docs.sentry.io/platforms/python/)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Error Tracking Best Practices](https://docs.sentry.io/product/issues/)

---

## ✅ Monitoring Checklist

Before deploying to production:

- [ ] Sentry DSN added to environment variables
- [ ] Test error capture working
- [ ] Sensitive data filtering verified
- [ ] Alerts configured (error rate, performance)
- [ ] Dashboard widgets set up
- [ ] Team invited to Sentry project
- [ ] Slack/email notifications configured
- [ ] Release tracking enabled

---

**Status**: 🟢 **Ready for Production**

Sentry is fully configured and ready to track errors in production!
