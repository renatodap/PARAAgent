"""OCR text extraction utilities for image files."""

from PIL import Image
import pytesseract
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class OCRExtractor:
    """Extract text from images using OCR (Optical Character Recognition)."""

    @staticmethod
    def extract_text_from_image(image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image file using pytesseract.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing:
                - text: Extracted text content
                - success: Whether extraction succeeded
                - error: Error message if failed
                - confidence: OCR confidence score (if available)
        """
        try:
            # Open image
            image = Image.open(image_path)

            # Convert to RGB if needed (for PNG with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Extract text with configuration
            # --psm 3: Automatic page segmentation
            # --oem 3: Default OCR Engine Mode
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(image, config=custom_config)

            # Get confidence data if available
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except Exception as e:
                logger.warning(f"Could not get OCR confidence: {str(e)}")
                avg_confidence = None

            # Clean up text
            text = text.strip()

            return {
                'text': text,
                'success': True,
                'error': None,
                'confidence': avg_confidence,
                'char_count': len(text),
                'word_count': len(text.split()) if text else 0
            }

        except FileNotFoundError:
            return {
                'text': '',
                'success': False,
                'error': f'Image file not found: {image_path}',
                'confidence': None
            }
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {str(e)}")
            return {
                'text': '',
                'success': False,
                'error': str(e),
                'confidence': None
            }

    @staticmethod
    def preprocess_image(image_path: str, output_path: str = None) -> str:
        """
        Preprocess image for better OCR results.

        Applies:
        - Grayscale conversion
        - Contrast enhancement
        - Noise reduction (optional)

        Args:
            image_path: Path to input image
            output_path: Path to save preprocessed image (optional)

        Returns:
            Path to preprocessed image
        """
        try:
            from PIL import ImageEnhance, ImageFilter

            image = Image.open(image_path)

            # Convert to grayscale
            image = image.convert('L')

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)

            # Save or return path
            if output_path:
                image.save(output_path)
                return output_path
            else:
                # Save to temp file
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                image.save(temp_file.name)
                return temp_file.name

        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            return image_path  # Return original path if preprocessing fails

    @staticmethod
    def detect_language(image_path: str) -> str:
        """
        Detect the primary language in the image.

        Args:
            image_path: Path to image file

        Returns:
            Language code (e.g., 'eng', 'spa', 'fra')
        """
        try:
            image = Image.open(image_path)

            # Get OSD (Orientation and Script Detection)
            osd = pytesseract.image_to_osd(image)

            # Parse language from OSD
            for line in osd.split('\n'):
                if line.startswith('Script:'):
                    script = line.split(':')[1].strip()
                    # Map script to language code
                    script_map = {
                        'Latin': 'eng',
                        'Han': 'chi_sim',
                        'Arabic': 'ara',
                        'Cyrillic': 'rus'
                    }
                    return script_map.get(script, 'eng')

            return 'eng'  # Default to English

        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return 'eng'

    @staticmethod
    def is_text_heavy(image_path: str, threshold: int = 50) -> bool:
        """
        Determine if an image contains substantial text.

        Useful for deciding whether to run OCR on an image.

        Args:
            image_path: Path to image file
            threshold: Minimum character count to consider "text-heavy"

        Returns:
            True if image contains substantial text
        """
        try:
            result = OCRExtractor.extract_text_from_image(image_path)
            return result['success'] and result['char_count'] >= threshold
        except Exception:
            return False

    @staticmethod
    def extract_with_preprocessing(image_path: str) -> Dict[str, Any]:
        """
        Extract text with automatic preprocessing for better results.

        Args:
            image_path: Path to image file

        Returns:
            OCR extraction result dictionary
        """
        # Try extraction without preprocessing first
        result = OCRExtractor.extract_text_from_image(image_path)

        # If low confidence or little text, try with preprocessing
        if result['success'] and (
            (result['confidence'] and result['confidence'] < 60) or
            result['char_count'] < 20
        ):
            logger.info("Low OCR quality detected, retrying with preprocessing...")
            preprocessed_path = OCRExtractor.preprocess_image(image_path)

            try:
                preprocessed_result = OCRExtractor.extract_text_from_image(preprocessed_path)

                # Use preprocessed result if better
                if preprocessed_result['char_count'] > result['char_count']:
                    return preprocessed_result

            except Exception as e:
                logger.warning(f"Preprocessing attempt failed: {str(e)}")

        return result
