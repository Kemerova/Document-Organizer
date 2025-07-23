# OCR processing utilities for Document Organizer
import logging
from pathlib import Path
from typing import List, Tuple, Optional

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRError(Exception):
    pass

class OCRProcessor:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if not TESSERACT_AVAILABLE:
            raise OCRError("OCR dependencies not available")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def extract_from_image(self, image_path: str) -> Tuple[str, float]:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text, 0.8
        except Exception as e:
            raise OCRError(f"Failed to extract text: {e}")
    
    def process_file(self, file_path: str) -> Tuple[str, float, List[int], bool]:
        file_path = Path(file_path)
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            text, confidence = self.extract_from_image(str(file_path))
            return text, confidence, [1], True
        else:
            return "", 0.0, [], False

def is_ocr_available() -> bool:
    return TESSERACT_AVAILABLE