"""File upload and management endpoints for PARA Autopilot"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from auth import get_current_user
from database import supabase
from config import settings
from utils.pdf_extractor import PDFExtractor
from utils.ocr_extractor import OCRExtractor
from utils.web_archiver import WebArchiver
from agents.classifier import classify_item
import uuid
import os
import tempfile
import logging
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
pdf_extractor = PDFExtractor()
ocr_extractor = OCRExtractor()
web_archiver = WebArchiver()

# File size limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_TYPES = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}


class FileMetadata(BaseModel):
    """File metadata model"""
    id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    page_count: Optional[int] = None
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    para_type: Optional[str] = None
    processing_status: str
    uploaded_at: str


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(get_current_user)
):
    """
    Upload a file (PDF, image, etc.) and process it with AI

    Steps:
    1. Validate file type and size
    2. Upload to Supabase Storage
    3. Extract text (PDF) or OCR (images)
    4. AI classify into PARA type
    5. Generate vector embeddings
    6. Create para_item automatically
    """
    user_id = user.id

    try:
        # Validate file
        if not file.content_type:
            raise HTTPException(status_code=400, detail="Could not determine file type")

        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Supported types: {', '.join(ALLOWED_TYPES.values())}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_extension = ALLOWED_TYPES[file.content_type]
        storage_path = f"{user_id}/{file_id}/{file.filename}"

        # Upload to Supabase Storage
        logger.info(f"Uploading file to storage: {storage_path}")
        storage_response = supabase.storage.from_('para-files').upload(
            storage_path,
            content,
            file_options={"content-type": file.content_type}
        )

        # Get file URL
        file_url = supabase.storage.from_('para-files').get_public_url(storage_path)

        # Determine file type category
        if file.content_type == 'application/pdf':
            file_type = 'pdf'
        elif file.content_type.startswith('image/'):
            file_type = 'image'
        else:
            file_type = 'document'

        # Create file record in database
        file_record = {
            "id": file_id,
            "user_id": user_id,
            "file_name": file.filename,
            "file_type": file_type,
            "mime_type": file.content_type,
            "file_size_bytes": file_size,
            "storage_path": storage_path,
            "file_url": file_url,
            "processing_status": "pending",
            "uploaded_at": datetime.utcnow().isoformat()
        }

        result = supabase.table('files').insert(file_record).execute()

        # Process file in background
        if file_type == 'pdf':
            # Process immediately for MVP (can be moved to background for production)
            await process_pdf(file_id, user_id, content, file.filename)
        elif file_type == 'image':
            # Process image with OCR
            await process_image(file_id, user_id, content, file.filename, file.content_type)

        # Get updated file record
        updated_file = supabase.table('files').select('*').eq('id', file_id).single().execute()

        return {
            "success": True,
            "file_id": file_id,
            "file_url": file_url,
            "file": updated_file.data,
            "message": f"File uploaded successfully. Processing {file_type}..."
        }

    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_pdf(file_id: str, user_id: str, content: bytes, filename: str):
    """
    Process uploaded PDF file

    Steps:
    1. Extract text from PDF
    2. Classify with AI
    3. Generate embeddings
    4. Create PARA item
    """
    try:
        # Update status to processing
        supabase.table('files').update({"processing_status": "processing"}).eq('id', file_id).execute()

        # Save PDF to temp file for extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Extract text from PDF
        logger.info(f"Extracting text from PDF: {filename}")
        extraction_result = pdf_extractor.extract_text(tmp_file_path)

        extracted_text = extraction_result.get('text', '')
        page_count = extraction_result.get('page_count', 0)

        # Clean up temp file
        os.unlink(tmp_file_path)

        if not extracted_text or len(extracted_text.strip()) < 50:
            # PDF is likely scanned or empty
            logger.warning(f"PDF has minimal text. May need OCR: {filename}")
            supabase.table('files').update({
                "processing_status": "completed",
                "processing_error": "PDF appears to be scanned or has minimal text. OCR not yet implemented.",
                "page_count": page_count,
                "extracted_text": extracted_text,
                "processed_at": datetime.utcnow().isoformat()
            }).eq('id', file_id).execute()
            return

        # Generate title from content
        title = pdf_extractor.generate_title_from_content(extracted_text)

        # Extract keywords
        keywords = pdf_extractor.extract_keywords(extracted_text)

        # AI Classification
        logger.info(f"Classifying PDF with AI: {title}")
        classification = classify_item(
            title=title,
            description=extracted_text[:500],  # First 500 chars for classification
            context=f"file_type: pdf, page_count: {page_count}"
        )

        para_type = classification.get('para_type', 'resource')  # Default to resource for PDFs
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')

        # Generate AI summary
        from agents.nlp_parser import NaturalLanguageTaskParser
        nlp_parser = NaturalLanguageTaskParser()

        summary_prompt = f"Summarize this document in 2-3 sentences:\n\n{extracted_text[:2000]}"
        # For now, use first paragraph as summary (can enhance with Claude)
        summary = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text

        # Create PARA item for this file
        para_item = {
            "user_id": user_id,
            "title": title,
            "description": summary,
            "notes": extracted_text,  # Full text in notes
            "para_type": para_type,
            "status": "active",
            "tags": keywords[:5],  # Top 5 keywords as tags
            "metadata": {
                "source": "pdf_upload",
                "file_id": file_id,
                "page_count": page_count,
                "classification_confidence": confidence,
                "classification_reasoning": reasoning
            }
        }

        para_result = supabase.table('para_items').insert(para_item).execute()
        para_item_id = para_result.data[0]['id'] if para_result.data else None

        # Update file record with processing results
        supabase.table('files').update({
            "para_item_id": para_item_id,
            "extracted_text": extracted_text,
            "page_count": page_count,
            "summary": summary,
            "keywords": keywords,
            "processing_status": "completed",
            "processed_at": datetime.utcnow().isoformat()
        }).eq('id', file_id).execute()

        # TODO: Generate vector embeddings (implement in next iteration)
        # chunks = pdf_extractor.chunk_text(extracted_text)
        # for chunk in chunks:
        #     embedding = generate_embedding(chunk)
        #     store embedding in database

        logger.info(f"PDF processing completed: {filename} -> {para_type}")

    except Exception as e:
        logger.error(f"PDF processing failed: {str(e)}")
        supabase.table('files').update({
            "processing_status": "failed",
            "processing_error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }).eq('id', file_id).execute()


async def process_image(file_id: str, user_id: str, content: bytes, filename: str, mime_type: str):
    """
    Process uploaded image file with OCR

    Steps:
    1. Extract text using OCR
    2. Classify with AI
    3. Create PARA item
    """
    try:
        # Update status to processing
        supabase.table('files').update({"processing_status": "processing"}).eq('id', file_id).execute()

        # Save image to temp file for OCR
        file_extension = ALLOWED_TYPES.get(mime_type, '.jpg')
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Extract text from image using OCR
        logger.info(f"Extracting text from image with OCR: {filename}")
        ocr_result = ocr_extractor.extract_with_preprocessing(tmp_file_path)

        ocr_text = ocr_result.get('text', '')
        ocr_confidence = ocr_result.get('confidence', 0)

        # Clean up temp file
        os.unlink(tmp_file_path)

        # Generate title from filename or OCR text
        if ocr_text and len(ocr_text.strip()) > 10:
            # Use first meaningful line as title
            title = ocr_text.split('\n')[0][:100].strip()
            if not title:
                title = filename.rsplit('.', 1)[0]
        else:
            # No text found, use filename
            title = filename.rsplit('.', 1)[0]
            logger.info(f"Image has minimal text ({len(ocr_text)} chars). Using filename as title.")

        # Extract keywords from OCR text if available
        keywords = []
        if ocr_text and len(ocr_text.strip()) > 20:
            keywords = pdf_extractor.extract_keywords(ocr_text)  # Reuse PDF keyword extraction

        # AI Classification
        logger.info(f"Classifying image with AI: {title}")
        classification_context = f"file_type: image, ocr_confidence: {ocr_confidence}, has_text: {len(ocr_text) > 20}"

        if ocr_text and len(ocr_text.strip()) > 50:
            # Use OCR text for classification
            classification = classify_item(
                title=title,
                description=ocr_text[:500],
                context=classification_context
            )
        else:
            # Minimal text - classify based on filename
            classification = classify_item(
                title=title,
                description=f"Image file: {filename}",
                context=classification_context
            )

        para_type = classification.get('para_type', 'resource')  # Default to resource for images
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')

        # Generate summary
        if ocr_text and len(ocr_text.strip()) > 100:
            summary = ocr_text[:300] + "..." if len(ocr_text) > 300 else ocr_text
        else:
            summary = f"Image: {filename}" + (f" - Contains: {ocr_text}" if ocr_text else " - No text detected")

        # Create PARA item for this image
        para_item = {
            "user_id": user_id,
            "title": title,
            "description": summary,
            "notes": ocr_text if ocr_text else "Image with no detectable text",
            "para_type": para_type,
            "status": "active",
            "tags": keywords[:5] if keywords else ["image"],
            "metadata": {
                "source": "image_upload",
                "file_id": file_id,
                "ocr_confidence": ocr_confidence,
                "classification_confidence": confidence,
                "classification_reasoning": reasoning,
                "has_ocr_text": bool(ocr_text and len(ocr_text) > 20)
            }
        }

        para_result = supabase.table('para_items').insert(para_item).execute()
        para_item_id = para_result.data[0]['id'] if para_result.data else None

        # Update file record with processing results
        supabase.table('files').update({
            "para_item_id": para_item_id,
            "ocr_text": ocr_text,
            "extracted_text": ocr_text,  # Also store in extracted_text for consistent searching
            "summary": summary,
            "keywords": keywords,
            "processing_status": "completed",
            "processed_at": datetime.utcnow().isoformat()
        }).eq('id', file_id).execute()

        logger.info(f"Image processing completed: {filename} -> {para_type} (OCR confidence: {ocr_confidence:.1f}%)")

    except Exception as e:
        logger.error(f"Image processing failed: {str(e)}")
        supabase.table('files').update({
            "processing_status": "failed",
            "processing_error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }).eq('id', file_id).execute()


@router.post("/archive-link")
async def archive_link(
    url: str,
    user: dict = Depends(get_current_user)
):
    """
    Archive a web page/link

    Request body:
    - url: The URL to archive
    """
    try:
        user_id = user.id

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format. Must start with http:// or https://")

        logger.info(f"Archiving link for user {user_id}: {url}")

        # Generate file ID
        file_id = str(uuid.uuid4())

        # Create file record in database (initial)
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        file_record = {
            "id": file_id,
            "user_id": user_id,
            "file_name": f"{domain}",
            "file_type": "link",
            "mime_type": "text/html",
            "file_size_bytes": 0,  # Will update after archiving
            "storage_path": url,  # Store original URL
            "file_url": url,
            "processing_status": "pending",
            "uploaded_at": datetime.utcnow().isoformat()
        }

        result = supabase.table('files').insert(file_record).execute()

        # Process link in background
        await process_link(file_id, user_id, url)

        # Get updated file record
        updated_file = supabase.table('files').select('*').eq('id', file_id).single().execute()

        return {
            "success": True,
            "file_id": file_id,
            "file_url": url,
            "file": updated_file.data,
            "message": "Link archived successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link archival failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Archival failed: {str(e)}")


async def process_link(file_id: str, user_id: str, url: str):
    """
    Process archived link

    Steps:
    1. Archive web page content
    2. Extract metadata
    3. Classify with AI
    4. Create PARA item
    """
    try:
        # Update status to processing
        supabase.table('files').update({"processing_status": "processing"}).eq('id', file_id).execute()

        # Archive the web page
        logger.info(f"Archiving web page: {url}")
        archive_result = await web_archiver.archive_url(url)

        if not archive_result['success']:
            raise Exception(archive_result.get('error', 'Failed to archive page'))

        title = archive_result['title']
        description = archive_result.get('description', '')
        content_text = archive_result['content_text']
        content_markdown = archive_result['content_markdown']
        metadata = archive_result['metadata']
        word_count = archive_result.get('word_count', 0)

        # Generate keywords from content
        keywords = pdf_extractor.extract_keywords(content_text)  # Reuse PDF keyword extraction

        # AI Classification
        logger.info(f"Classifying link with AI: {title}")
        classification = classify_item(
            title=title,
            description=description or content_text[:500],
            context=f"file_type: link, url: {url}, word_count: {word_count}, site_name: {metadata.get('site_name')}"
        )

        para_type = classification.get('para_type', 'resource')  # Default to resource for links
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')

        # Generate summary
        summary = web_archiver.generate_summary(content_text, max_length=500)

        # Create PARA item for this link
        para_item = {
            "user_id": user_id,
            "title": title,
            "description": summary,
            "notes": content_markdown,  # Store markdown version for readability
            "para_type": para_type,
            "status": "active",
            "tags": keywords[:5] if keywords else ["link", "web"],
            "metadata": {
                "source": "link_archive",
                "file_id": file_id,
                "url": url,
                "archived_url": archive_result.get('url'),  # Final URL after redirects
                "site_name": metadata.get('site_name'),
                "author": metadata.get('author'),
                "published_date": metadata.get('published_date'),
                "favicon": metadata.get('favicon'),
                "image": metadata.get('image'),
                "word_count": word_count,
                "classification_confidence": confidence,
                "classification_reasoning": reasoning
            }
        }

        para_result = supabase.table('para_items').insert(para_item).execute()
        para_item_id = para_result.data[0]['id'] if para_result.data else None

        # Update file record with processing results
        supabase.table('files').update({
            "para_item_id": para_item_id,
            "file_name": title,
            "extracted_text": content_text,
            "summary": summary,
            "keywords": keywords,
            "file_size_bytes": len(content_text.encode('utf-8')),
            "processing_status": "completed",
            "processed_at": datetime.utcnow().isoformat(),
            "metadata": {
                "favicon": metadata.get('favicon'),
                "site_name": metadata.get('site_name'),
                "author": metadata.get('author'),
                "published_date": metadata.get('published_date'),
                "image": metadata.get('image'),
                "word_count": word_count,
                "archived_content": content_markdown  # Store full markdown content
            }
        }).eq('id', file_id).execute()

        logger.info(f"Link processing completed: {title} -> {para_type}")

    except Exception as e:
        logger.error(f"Link processing failed: {str(e)}")
        supabase.table('files').update({
            "processing_status": "failed",
            "processing_error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }).eq('id', file_id).execute()


@router.get("/")
async def list_files(
    file_type: Optional[str] = None,
    para_type: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """
    List user's uploaded files

    Query params:
    - file_type: Filter by pdf, image, document
    - para_type: Filter by project, area, resource, archive
    - limit: Max results (default 50)
    """
    user_id = user.id

    query = supabase.table('files')\
        .select('*, para_items(id, title, para_type)')\
        .eq('user_id', user_id)\
        .order('uploaded_at', desc=True)\
        .limit(limit)

    if file_type:
        query = query.eq('file_type', file_type)

    result = query.execute()

    # Filter by para_type if specified
    files = result.data
    if para_type:
        files = [f for f in files if f.get('para_items') and f['para_items'].get('para_type') == para_type]

    return {
        "files": files,
        "total": len(files)
    }


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Get file details by ID"""
    user_id = user.id

    result = supabase.table('files')\
        .select('*, para_items(*)')\
        .eq('id', file_id)\
        .eq('user_id', user_id)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")

    return result.data


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a file and its associated data"""
    user_id = user.id

    try:
        # Get file record
        file_record = supabase.table('files')\
            .select('*')\
            .eq('id', file_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()

        if not file_record.data:
            raise HTTPException(status_code=404, detail="File not found")

        storage_path = file_record.data['storage_path']

        # Delete from storage
        supabase.storage.from_('para-files').remove([storage_path])

        # Delete file record (cascade will handle para_items if needed)
        supabase.table('files').delete().eq('id', file_id).execute()

        return {"success": True, "message": "File deleted successfully"}

    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/stats/storage")
async def get_storage_stats(user: dict = Depends(get_current_user)):
    """Get user's storage statistics"""
    user_id = user.id

    try:
        # Use the SQL function we created
        result = supabase.rpc('get_user_storage_stats', {'p_user_id': user_id}).execute()

        if result.data:
            stats = result.data[0] if isinstance(result.data, list) else result.data
            return stats
        else:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "file_types": {}
            }

    except Exception as e:
        logger.error(f"Failed to get storage stats: {str(e)}")
        # Fallback calculation
        files = supabase.table('files').select('file_type, file_size_bytes').eq('user_id', user_id).execute()

        total_size = sum(f.get('file_size_bytes', 0) for f in files.data)

        return {
            "total_files": len(files.data),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "file_types": {}
        }
