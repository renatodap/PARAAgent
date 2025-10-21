"""PDF text extraction utilities for PARA Autopilot"""

import PyPDF2
import pdfplumber
from typing import Dict, Any, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text and metadata from PDF files"""

    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF file using multiple methods

        Args:
            file_path: Path to PDF file

        Returns:
            Dict with extracted text, metadata, and page count
        """
        try:
            # Try pdfplumber first (better for complex PDFs)
            result = PDFExtractor._extract_with_pdfplumber(file_path)

            if not result['text'] or len(result['text'].strip()) < 50:
                # Fallback to PyPDF2 if pdfplumber fails
                logger.info("pdfplumber extracted minimal text, trying PyPDF2")
                result = PDFExtractor._extract_with_pypdf2(file_path)

            return result

        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            return {
                'text': '',
                'page_count': 0,
                'metadata': {},
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> Dict[str, Any]:
        """Extract using pdfplumber (better for complex layouts)"""
        text_parts = []
        page_count = 0
        metadata = {}

        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            metadata = pdf.metadata or {}

            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = '\n\n'.join(text_parts)

        return {
            'text': full_text,
            'page_count': page_count,
            'metadata': metadata,
            'method': 'pdfplumber',
            'success': True
        }

    @staticmethod
    def _extract_with_pypdf2(file_path: str) -> Dict[str, Any]:
        """Extract using PyPDF2 (fallback method)"""
        text_parts = []
        page_count = 0
        metadata = {}

        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            metadata = pdf_reader.metadata or {}

            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        full_text = '\n\n'.join(text_parts)

        return {
            'text': full_text,
            'page_count': page_count,
            'metadata': {str(k): str(v) for k, v in metadata.items()},
            'method': 'PyPDF2',
            'success': True
        }

    @staticmethod
    def generate_title_from_content(text: str, max_length: int = 100) -> str:
        """
        Generate a meaningful title from PDF content

        Args:
            text: Extracted PDF text
            max_length: Maximum title length

        Returns:
            Generated title string
        """
        if not text or len(text.strip()) < 10:
            return "Untitled Document"

        # Take first meaningful line
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return "Untitled Document"

        # Find first line that looks like a title (not too short, not all caps unless acronym)
        for line in lines[:10]:  # Check first 10 lines
            if 20 <= len(line) <= 200:  # Reasonable title length
                # Truncate if too long
                if len(line) > max_length:
                    return line[:max_length-3] + "..."
                return line

        # Fallback to first line
        first_line = lines[0]
        if len(first_line) > max_length:
            return first_line[:max_length-3] + "..."
        return first_line

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for vector embeddings

        Args:
            text: Full text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk.rfind('. ')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > chunk_size * 0.5:  # Only break if not too far back
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from PDF text (simple TF-IDF approach)

        Args:
            text: Extracted text
            top_n: Number of keywords to return

        Returns:
            List of keywords
        """
        if not text or len(text) < 50:
            return []

        # Simple keyword extraction - count word frequency
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                     'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'can', 'could', 'may', 'might', 'must', 'this', 'that', 'these', 'those'}

        words = text.lower().split()
        word_freq = {}

        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top N
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_n]]

    @staticmethod
    def is_pdf_scanned(file_path: str) -> bool:
        """
        Check if PDF is scanned (image-based) vs text-based

        Args:
            file_path: Path to PDF file

        Returns:
            True if PDF appears to be scanned
        """
        try:
            result = PDFExtractor.extract_text(file_path)
            text = result.get('text', '')
            page_count = result.get('page_count', 0)

            if page_count == 0:
                return True

            # If very little text per page, likely scanned
            avg_chars_per_page = len(text) / page_count if page_count > 0 else 0

            # Scanned PDFs typically have <100 chars per page
            return avg_chars_per_page < 100

        except Exception as e:
            logger.error(f"Error checking if PDF is scanned: {str(e)}")
            return False
