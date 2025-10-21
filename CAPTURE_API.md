# Quick Capture API Documentation

The Quick Capture API provides natural language and voice input for effortless capture into your PARA system.

## Endpoints

### 1. **POST `/api/capture/quick`** - Natural Language Quick Capture

Capture anything in natural language and let AI classify and organize it.

#### Request Body
```json
{
  "input": "Buy groceries tomorrow at 3pm",
  "capture_type": "auto",  // Optional: "auto", "task", "note"
  "context": ""            // Optional: Additional context for classification
}
```

#### Response
```json
{
  "created": {
    "items": [
      {
        "type": "task",
        "id": "uuid",
        "title": "Buy groceries",
        "due_date": "2025-10-22T15:00:00",
        "priority": "medium"
      }
    ],
    "primary_id": "uuid",
    "primary_type": "task"
  },
  "classification": {
    "para_type": "project",
    "confidence": 0.92,
    "reasoning": "This is an actionable item with a specific due date",
    "estimated_duration_weeks": null
  },
  "parsed": {
    "title": "Buy groceries",
    "description": null,
    "due_date": "2025-10-22T15:00:00",
    "priority": "medium",
    "duration_minutes": null,
    "keywords": ["groceries", "shopping"]
  },
  "suggestions": {
    "next_actions": ["Create shopping list", "Set reminder"],
    "linked_to": null,
    "schedule_suggestion": "Schedule for 2025-10-22T15:00:00",
    "auto_schedule_available": true
  },
  "usage": {
    "tokens": 450,
    "cost_usd": 0.00225
  }
}
```

#### Examples

**Capture a Task:**
```bash
curl -X POST https://your-api.com/api/capture/quick \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Call mom tomorrow at 3pm"}'
```

**Capture a Project:**
```bash
curl -X POST https://your-api.com/api/capture/quick \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Launch new blog by end of Q1 high priority"}'
```

**Capture a Resource:**
```bash
curl -X POST https://your-api.com/api/capture/quick \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Python machine learning tutorials collection"}'
```

**Capture an Area:**
```bash
curl -X POST https://your-api.com/api/capture/quick \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Health and fitness routine maintenance"}'
```

---

### 2. **POST `/api/capture/voice`** - Voice Transcription

Transcribe audio to text using OpenRouter's Whisper API.

#### Request
- **Content-Type**: `multipart/form-data`
- **Body**: Audio file (mp3, wav, m4a, webm, ogg)
- **Max Size**: 25MB

#### Response
```json
{
  "text": "Buy groceries tomorrow at three PM",
  "language": "en",
  "duration": 3.5,
  "confidence": 0.95
}
```

#### Example
```bash
curl -X POST https://your-api.com/api/capture/voice \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@recording.mp3"
```

---

### 3. **POST `/api/capture/voice-quick`** - Voice → Quick Capture (Combined)

Transcribe audio and immediately process it with quick capture in one call.

#### Request
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `audio`: Audio file
  - `context`: Optional context string

#### Response
Same as `/api/capture/quick` with additional `transcription` field:
```json
{
  "created": { ... },
  "classification": { ... },
  "parsed": { ... },
  "suggestions": { ... },
  "usage": { ... },
  "transcription": {
    "text": "Buy groceries tomorrow at three PM",
    "language": "en",
    "confidence": 0.95
  }
}
```

#### Example
```bash
curl -X POST https://your-api.com/api/capture/voice-quick \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@recording.mp3" \
  -F "context=morning grocery run"
```

---

## Natural Language Parsing Examples

The NLP parser understands:

### Time References
- "tomorrow" → Next day
- "next week" → 7 days from now
- "Friday" → Next Friday
- "at 3pm" → 15:00:00

### Priority Keywords
- "urgent", "asap" → urgent priority
- "high priority", "important" → high priority
- "low priority" → low priority

### Duration
- "for 2 hours" → 120 minutes
- "30 minute meeting" → 30 minutes

### Context Linking
- Keywords automatically link to existing projects/areas
- "Q4 budget review" → Links to existing "Q4" project

---

## Setup

### 1. Add OpenRouter API Key
```bash
# .env
OPENROUTER_API_KEY=sk-or-your-key-here
```

Get your key from: https://openrouter.ai/keys

### 2. Voice Input Cost
- OpenRouter Whisper: ~$0.006 per minute of audio
- Very affordable for voice capture

---

## Frontend Integration

### Quick Capture Hook (React)
```typescript
import { useState } from 'react';

export function useQuickCapture() {
  const [loading, setLoading] = useState(false);

  const capture = async (input: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/capture/quick', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ input })
      });
      return await response.json();
    } finally {
      setLoading(false);
    }
  };

  return { capture, loading };
}
```

### Voice Capture Hook
```typescript
export function useVoiceCapture() {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks: BlobPart[] = [];

    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');

      const response = await fetch('/api/capture/voice-quick', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      return await response.json();
    };

    recorder.start();
    setMediaRecorder(recorder);
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorder?.stop();
    setRecording(false);
  };

  return { startRecording, stopRecording, recording };
}
```

---

## Best Practices

1. **Always provide context**: More context = better classification
2. **Use natural language**: Write/speak naturally, AI will parse it
3. **Review suggestions**: AI provides next actions - consider them!
4. **Link to existing items**: Keywords automatically link to projects/areas
5. **Trust the confidence scores**: <0.7 = review manually, >0.9 = very confident

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid auth token
- `413 Request Entity Too Large` - Audio file >25MB
- `500 Internal Server Error` - Server error (check logs)

Example error response:
```json
{
  "detail": "Audio file too large. Maximum size: 25MB"
}
```

---

## Rate Limits

- Quick capture: 100 requests/minute
- Voice transcription: 20 requests/minute (due to processing time)
- Voice-quick: 20 requests/minute

---

## Testing

Run the test suite:
```bash
pytest tests/test_capture.py -v
```

---

**Built with ❤️ using Claude Haiku 4.5 + OpenRouter Whisper**
