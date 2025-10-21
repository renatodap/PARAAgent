"""Quick capture endpoints for PARA Autopilot - natural language & voice input."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from auth import get_current_user_id
from database import db, supabase
from config import settings
import logging
import httpx
import base64

router = APIRouter()
logger = logging.getLogger(__name__)


class QuickCaptureRequest(BaseModel):
    """Request model for quick capture."""
    input: str = Field(..., min_length=1, max_length=2000, description="Natural language input")
    capture_type: Optional[str] = Field(None, description="Force type: 'task', 'note', 'auto'")
    context: Optional[str] = Field(None, description="Additional context for classification")


class QuickCaptureResponse(BaseModel):
    """Response model for quick capture."""
    created: Dict[str, Any]
    classification: Dict[str, Any]
    parsed: Dict[str, Any]
    suggestions: Dict[str, Any]
    usage: Dict[str, Any]


class VoiceTranscriptionResponse(BaseModel):
    """Response model for voice transcription."""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None


@router.post("/quick", response_model=QuickCaptureResponse)
async def quick_capture(
    request: QuickCaptureRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Universal quick capture endpoint - parse natural language and create appropriate items.

    Examples:
    - "Buy groceries tomorrow" → Task with due date
    - "Python tutorial collection" → Resource
    - "Finish Q4 report by Friday high priority" → Project + Task
    - "Health and fitness routine" → Area

    The AI will:
    1. Parse the natural language to extract task details
    2. Classify into PARA categories
    3. Create the appropriate item(s)
    4. Suggest next actions
    """
    try:
        # Step 1: Parse natural language
        from agents.nlp_parser import NaturalLanguageTaskParser
        parser = NaturalLanguageTaskParser()

        logger.info(f"Parsing input: {request.input[:100]}...")
        parsed = await parser.parse(request.input, user_id)
        logger.info(f"Parsed result: {parsed}")

        # Step 2: Classify into PARA
        from agents.classifier import classify_item

        classification = classify_item(
            title=parsed['title'],
            description=parsed.get('description', '') or request.input,
            context=request.context or f"keywords: {', '.join(parsed.get('keywords', []))}"
        )
        logger.info(f"Classification: {classification['para_type']} (confidence: {classification['confidence']})")

        # Step 3: Determine what to create based on type and parsed data
        created_items = []

        # Force type if specified
        if request.capture_type:
            if request.capture_type == "task":
                classification['para_type'] = 'project'  # Tasks usually belong to projects
            elif request.capture_type == "note":
                classification['para_type'] = 'resource'

        # Create PARA item if it's not just a standalone task
        para_item_id = None
        if classification['para_type'] in ['project', 'area', 'resource']:
            para_item = db.insert_record("para_items", {
                "user_id": user_id,
                "title": parsed['title'],
                "description": parsed.get('description', ''),
                "para_type": classification['para_type'],
                "status": "active",
                "metadata": {
                    "ai_confidence": classification['confidence'],
                    "ai_reasoning": classification['reasoning'],
                    "suggested_next_actions": classification['suggested_next_actions'],
                    "source": "quick_capture",
                    "original_input": request.input
                }
            })
            para_item_id = para_item['id']
            created_items.append({
                "type": "para_item",
                "id": para_item_id,
                "title": parsed['title'],
                "para_type": classification['para_type']
            })
            logger.info(f"Created PARA item: {para_item_id}")

        # Create task if there's actionable info (due date, duration, priority)
        task_id = None
        if (parsed.get('due_date') or
            parsed.get('estimated_duration_minutes') or
            parsed.get('priority', 'medium') in ['high', 'urgent'] or
            request.capture_type == "task"):

            task = db.insert_record("tasks", {
                "user_id": user_id,
                "title": parsed['title'],
                "description": parsed.get('description', ''),
                "para_item_id": para_item_id,
                "due_date": parsed.get('due_date'),
                "priority": parsed.get('priority', 'medium'),
                "estimated_duration_minutes": parsed.get('estimated_duration_minutes'),
                "status": "pending",
                "source": "ai_suggested",
                "source_metadata": {
                    "original_input": request.input,
                    "confidence": parsed.get('confidence', 0.8),
                    "linked_para_item": para_item_id
                }
            })
            task_id = task['id']
            created_items.append({
                "type": "task",
                "id": task_id,
                "title": parsed['title'],
                "due_date": parsed.get('due_date'),
                "priority": parsed.get('priority', 'medium')
            })
            logger.info(f"Created task: {task_id}")

        # If nothing was created (shouldn't happen), create a resource as fallback
        if not created_items:
            fallback_item = db.insert_record("para_items", {
                "user_id": user_id,
                "title": parsed['title'],
                "description": request.input,
                "para_type": "resource",
                "status": "active",
                "metadata": {
                    "source": "quick_capture_fallback",
                    "original_input": request.input
                }
            })
            created_items.append({
                "type": "para_item",
                "id": fallback_item['id'],
                "title": parsed['title'],
                "para_type": "resource"
            })

        # Step 4: Log the action
        db.log_agent_action(
            user_id=user_id,
            action_type="quick_capture",
            input_data={
                "input": request.input,
                "capture_type": request.capture_type
            },
            output_data={
                "created_items": created_items,
                "classification": classification['para_type']
            },
            model_used=settings.CLAUDE_MODEL,
            tokens_used=classification['usage']['input_tokens'] + classification['usage']['output_tokens'],
            cost_usd=classification['usage']['cost_usd']
        )

        # Step 5: Build suggestions
        suggestions = {
            "next_actions": classification.get('suggested_next_actions', []),
            "linked_to": parsed.get('linked_to'),
            "schedule_suggestion": None,
            "auto_schedule_available": False
        }

        if parsed.get('due_date') and task_id:
            suggestions['schedule_suggestion'] = f"Schedule for {parsed.get('due_date')}"
            suggestions['auto_schedule_available'] = True

        # Step 6: Return comprehensive response
        return {
            "created": {
                "items": created_items,
                "primary_id": created_items[0]['id'],
                "primary_type": created_items[0]['type']
            },
            "classification": {
                "para_type": classification['para_type'],
                "confidence": classification['confidence'],
                "reasoning": classification['reasoning'],
                "estimated_duration_weeks": classification.get('estimated_duration_weeks')
            },
            "parsed": {
                "title": parsed['title'],
                "description": parsed.get('description'),
                "due_date": parsed.get('due_date'),
                "priority": parsed.get('priority'),
                "duration_minutes": parsed.get('estimated_duration_minutes'),
                "keywords": parsed.get('keywords', [])
            },
            "suggestions": suggestions,
            "usage": {
                "tokens": classification['usage']['input_tokens'] + classification['usage']['output_tokens'],
                "cost_usd": classification['usage']['cost_usd']
            }
        }

    except Exception as e:
        logger.error(f"Quick capture error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process capture: {str(e)}"
        )


@router.post("/voice", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    audio: UploadFile = File(..., description="Audio file (mp3, wav, m4a, etc.)"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Transcribe voice input to text using OpenRouter's Whisper API.

    Supports common audio formats: mp3, wav, m4a, webm, ogg
    Max file size: 25MB
    """
    try:
        # Validate file type
        allowed_types = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/webm', 'audio/ogg', 'audio/x-m4a']
        if audio.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format: {audio.content_type}. Allowed: mp3, wav, m4a, webm, ogg"
            )

        # Validate file size (25MB max)
        content = await audio.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large. Maximum size: 25MB"
            )

        logger.info(f"Transcribing audio file: {audio.filename} ({len(content)} bytes)")

        # Call OpenRouter Whisper API
        async with httpx.AsyncClient(timeout=60.0) as client:
            # OpenRouter uses OpenAI-compatible API
            files = {
                'file': (audio.filename, content, audio.content_type)
            }
            data = {
                'model': 'openai/whisper-large-v3',  # OpenRouter model name
                'response_format': 'json'
            }

            response = await client.post(
                'https://openrouter.ai/api/v1/audio/transcriptions',
                headers={
                    'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                    'HTTP-Referer': settings.APP_URL,
                    'X-Title': 'PARA Autopilot'
                },
                files=files,
                data=data
            )

            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Transcription service error: {response.text}"
                )

            result = response.json()
            transcription = result.get('text', '')

            if not transcription:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No speech detected in audio"
                )

            logger.info(f"Transcription successful: {transcription[:100]}...")

            # Log the transcription
            db.log_agent_action(
                user_id=user_id,
                action_type="voice_transcription",
                input_data={
                    "filename": audio.filename,
                    "content_type": audio.content_type,
                    "size_bytes": len(content)
                },
                output_data={
                    "text": transcription,
                    "language": result.get('language')
                },
                model_used="openai/whisper-large-v3",
                tokens_used=0,  # Whisper doesn't use tokens
                cost_usd=0.006 * (len(content) / 1_000_000)  # ~$0.006/minute estimate
            )

            return {
                "text": transcription,
                "language": result.get('language'),
                "duration": result.get('duration'),
                "confidence": 0.95  # Whisper typically has high confidence
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice transcription error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@router.post("/voice-quick", response_model=QuickCaptureResponse)
async def voice_quick_capture(
    audio: UploadFile = File(..., description="Audio file to transcribe and capture"),
    context: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Combined endpoint: transcribe voice → quick capture in one call.

    This is a convenience endpoint that chains voice transcription with quick capture.
    Use this for the fastest voice-to-PARA workflow.
    """
    try:
        # Step 1: Transcribe
        transcription = await transcribe_voice(audio, user_id)

        # Step 2: Quick capture
        capture_request = QuickCaptureRequest(
            input=transcription['text'],
            capture_type="auto",
            context=context or f"voice input (language: {transcription.get('language', 'unknown')})"
        )

        result = await quick_capture(capture_request, user_id)

        # Add transcription info to response
        result['transcription'] = {
            "text": transcription['text'],
            "language": transcription.get('language'),
            "confidence": transcription.get('confidence')
        }

        return result

    except Exception as e:
        logger.error(f"Voice quick capture error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process voice capture: {str(e)}"
        )
