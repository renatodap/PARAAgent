# Google OAuth2 Setup Guide

Complete guide to enable Google Calendar integration for ALL your users.

---

## Overview

**What You're Building:**
- You (app owner) get ONE set of Google API credentials
- Each user connects THEIR OWN Google account to your app
- Your app can access each user's calendar/email (with their permission)
- Each user's data is completely private and isolated

**Security:**
- Users grant permission via Google's official consent screen
- Tokens are encrypted in your database
- Each user can revoke access anytime
- You can't see users' passwords (OAuth magic!)

---

## Step 1: Create Google Cloud Project

### 1.1 Go to Google Cloud Console
Visit: https://console.cloud.google.com/

### 1.2 Create New Project
1. Click dropdown at top (next to "Google Cloud")
2. Click "New Project"
3. Name: `PARA Autopilot` (or whatever you want)
4. Click "Create"

### 1.3 Enable APIs
1. Go to "APIs & Services" → "Library"
2. Search and enable these APIs:
   - ✅ **Google Calendar API**
   - ✅ **Gmail API** (if you want email access)
   - ✅ **Google Tasks API** (if you want tasks)
   - ✅ **People API** (for user profile info)

---

## Step 2: Configure OAuth Consent Screen

### 2.1 Go to OAuth Consent Screen
1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Choose **External** (allows any Google user to connect)
3. Click "Create"

### 2.2 Fill Out App Information

**App Information:**
- App name: `PARA Autopilot`
- User support email: `your-email@example.com`
- App logo: Upload your logo (optional, 120x120px)

**App Domain:**
- Application home page: `https://your-app.com`
- Application privacy policy: `https://your-app.com/privacy`
- Application terms of service: `https://your-app.com/terms`

**Authorized Domains:**
- Add: `your-app.com` (your frontend domain)
- Add: `your-backend.com` (if backend is on different domain)

**Developer Contact:**
- Email: `your-email@example.com`

Click "Save and Continue"

### 2.3 Add Scopes

Click "Add or Remove Scopes", then add:

**For Calendar Access:**
- `https://www.googleapis.com/auth/calendar.readonly` - View calendar
- `https://www.googleapis.com/auth/calendar.events` - Create/edit events

**For User Info:**
- `https://www.googleapis.com/auth/userinfo.email` - See email address
- `https://www.googleapis.com/auth/userinfo.profile` - See profile (name, picture)

**Optional - For Gmail (future):**
- `https://www.googleapis.com/auth/gmail.readonly` - Read emails
- `https://www.googleapis.com/auth/gmail.send` - Send emails

Click "Update", then "Save and Continue"

### 2.4 Test Users (Development Only)

While your app is in "Testing" mode, only these users can connect:
- Add your own Gmail address
- Add any beta testers' emails

**To allow ANYONE** (production):
- Click "Publish App" later (requires verification for sensitive scopes)

---

## Step 3: Create OAuth2 Credentials

### 3.1 Create Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: **Web application**
4. Name: `PARA Autopilot Web Client`

### 3.2 Configure Authorized URIs

**Authorized JavaScript origins** (your frontend):
```
http://localhost:3000
https://your-app.vercel.app
https://your-custom-domain.com
```

**Authorized redirect URIs** (where Google sends users back):
```
http://localhost:3000/oauth/callback
https://your-app.vercel.app/oauth/callback
https://your-custom-domain.com/oauth/callback
```

⚠️ **IMPORTANT**: Redirect URI must EXACTLY match what's in your code!

Click "Create"

### 3.3 Save Credentials

Google will show you:
- **Client ID**: `123456789-abc123xyz.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-abc123xyz`

**Copy these immediately!** You'll add them to your `.env` file.

---

## Step 4: Update Backend Environment Variables

### 4.1 Add to `.env`

```bash
# Google OAuth Credentials
GOOGLE_CLIENT_ID=123456789-abc123xyz.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123xyz

# Frontend URL (for OAuth redirects)
FRONTEND_URL=https://your-app.vercel.app

# App URL (for Google to verify)
APP_URL=https://your-app.vercel.app

# Encryption Key (IMPORTANT - generate a secure key!)
ENCRYPTION_KEY=your-32-byte-base64-encoded-key-here
```

### 4.2 Generate Encryption Key

The `ENCRYPTION_KEY` is used to encrypt user tokens in the database.

**Generate a secure key:**

```python
# Run this in Python ONCE, then paste result into .env
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Output example:
```
jQd7mP9k2L4nR8sT1vW5xZ6aB3cD4eF5gH6iJ7kL8mN=
```

Paste this into your `.env`:
```bash
ENCRYPTION_KEY=jQd7mP9k2L4nR8sT1vW5xZ6aB3cD4eF5gH6iJ7kL8mN=
```

⚠️ **NEVER commit this to Git!** Keep it secret!

---

## Step 5: Test OAuth Flow

### 5.1 Start Your Backend

```bash
cd backend
uvicorn main:app --reload
```

### 5.2 Test Endpoints

**Get OAuth URL:**
```bash
curl http://localhost:8000/api/oauth/google/init \
  -H "Authorization: Bearer YOUR_SUPABASE_TOKEN"
```

Response:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "random-state-token",
  "expires_in": 600
}
```

**Open the `auth_url` in browser:**
- You'll see Google's consent screen
- Click "Allow"
- Google redirects to your callback URL
- Backend stores encrypted tokens
- User is redirected to frontend with success message

### 5.3 Verify in Database

```sql
-- Check Supabase database
SELECT id, user_id, integration_type, is_enabled, last_sync_at, config
FROM mcp_integrations
WHERE integration_type = 'google_calendar';
```

You should see:
- Encrypted tokens (can't read them - that's good!)
- User's Google email in `config` JSON
- `is_enabled = true`

---

## Step 6: Frontend Integration

### 6.1 Create OAuth Button Component

```typescript
// components/integrations/GoogleCalendarButton.tsx

import { useState } from 'react';

export function GoogleCalendarButton() {
  const [loading, setLoading] = useState(false);

  const connectGoogle = async () => {
    setLoading(true);
    try {
      // Step 1: Get OAuth URL from backend
      const response = await fetch('/api/oauth/google/init', {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      });
      const data = await response.json();

      // Step 2: Redirect to Google consent screen
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Failed to initiate Google OAuth:', error);
      setLoading(false);
    }
  };

  return (
    <button
      onClick={connectGoogle}
      disabled={loading}
      className="btn-primary"
    >
      {loading ? 'Connecting...' : '🔗 Connect Google Calendar'}
    </button>
  );
}
```

### 6.2 Create OAuth Callback Page

```typescript
// app/oauth/callback/page.tsx

'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export default function OAuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');

    if (success === 'google_calendar_connected') {
      // Show success message
      alert('✅ Google Calendar connected successfully!');
      router.push('/settings/integrations');
    } else if (error) {
      // Show error message
      alert(`❌ Connection failed: ${error}`);
      router.push('/settings/integrations');
    }
  }, [searchParams, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p>Processing Google OAuth callback...</p>
    </div>
  );
}
```

### 6.3 Display Connected Status

```typescript
// components/integrations/IntegrationStatus.tsx

import { useEffect, useState } from 'react';

export function IntegrationStatus() {
  const [integrations, setIntegrations] = useState([]);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    const response = await fetch('/api/integrations', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    const data = await response.json();
    setIntegrations(data);
  };

  const disconnect = async (type: string) => {
    await fetch(`/api/oauth/google/revoke`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    fetchIntegrations();
  };

  return (
    <div>
      {integrations.map(integration => (
        <div key={integration.id} className="card">
          <h3>{integration.integration_type}</h3>
          <p>Connected as: {integration.config.google_user_email}</p>
          <p>Last synced: {integration.last_sync_at}</p>
          <button onClick={() => disconnect(integration.integration_type)}>
            Disconnect
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## Step 7: Automatic Token Refresh (Already Built!)

Your `mcp/sync_service.py` already handles token refresh automatically:

```python
# Before each API call, check if token expired
if token_expires_at < datetime.now():
    # Use refresh_token to get new access_token
    new_tokens = refresh_token_with_google(refresh_token)
    # Update database with new tokens
```

**This happens automatically** every time the sync service runs (every 5 minutes).

---

## Step 8: Publishing Your App (Production)

### 8.1 When to Publish

While in "Testing" mode:
- Only test users you manually add can connect
- Good for development and beta testing

To allow ANY Google user:
- You must publish the app

### 8.2 Publishing Process

1. Go to OAuth consent screen
2. Click "Publish App"
3. If you're requesting sensitive scopes (Calendar, Gmail):
   - Google will review your app (takes 3-7 days)
   - They'll check your privacy policy
   - They'll verify you're using scopes appropriately

4. Once approved:
   - ANY Google user can connect
   - Your app shows as "verified by Google"

---

## Security Best Practices

### ✅ DO:
- Store `ENCRYPTION_KEY` in environment variables, never in code
- Use HTTPS in production (required by Google)
- Revoke tokens when user disconnects
- Refresh tokens before they expire
- Log OAuth attempts for security monitoring

### ❌ DON'T:
- Commit `.env` file to Git
- Share `CLIENT_SECRET` publicly
- Use same encryption key for dev/staging/prod
- Skip CSRF protection (we use `state` parameter)

---

## Troubleshooting

### Error: "redirect_uri_mismatch"
**Cause**: Redirect URI in Google Console doesn't match your code
**Fix**: Make sure redirect URI EXACTLY matches (case-sensitive, no trailing slash)

### Error: "access_denied"
**Cause**: User clicked "Deny" on consent screen
**Fix**: This is normal - user declined access

### Error: "invalid_grant"
**Cause**: Authorization code already used or expired
**Fix**: Codes expire after 10 minutes - user needs to try again

### Error: "Token refresh failed"
**Cause**: Refresh token is invalid or revoked
**Fix**: User needs to reconnect (click "Connect Google Calendar" again)

### Error: "App not verified"
**Cause**: App still in testing mode or under Google review
**Fix**: Add user as test user, or wait for Google verification

---

## Cost

**Google Calendar API:**
- **FREE** up to 1 million requests/day per project
- That's ~11.5 requests/second sustained
- **You'll never hit this limit** for a normal app

**What counts as a request:**
- Fetching events: 1 request
- Creating event: 1 request
- Updating event: 1 request

**Typical usage per user:**
- Sync every 5 minutes = 288 syncs/day
- 1000 users = 288,000 requests/day
- **Still well under the free tier!** 🎉

---

## Next Steps

Once Google Calendar works, you can add:
- **Gmail Integration** - Read/send emails
- **Google Tasks** - Sync tasks
- **Google Drive** - Access files
- **Google Contacts** - Sync contacts

All use the same OAuth2 flow! Just add scopes.

---

## Summary

**What you set up:**
1. ✅ Google Cloud Project with Calendar API enabled
2. ✅ OAuth consent screen (tells users what your app does)
3. ✅ OAuth2 credentials (Client ID + Secret)
4. ✅ Authorized redirect URIs (where Google sends users back)
5. ✅ Environment variables in backend
6. ✅ Encryption key for token storage
7. ✅ Frontend OAuth button + callback page

**What happens when user connects:**
1. User clicks "Connect Google Calendar"
2. Redirected to Google consent screen
3. User approves access
4. Google gives you encrypted tokens
5. You store tokens (encrypted) in database
6. Background sync fetches their calendar every 5 minutes
7. User sees their Google events in your PARA app

**Each user's data is completely isolated!** ✅

---

**Built with ❤️ for PARA Autopilot**
