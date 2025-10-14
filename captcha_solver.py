import logging
import io
from typing import Optional
from PIL import Image
import pytesseract

from logger import logger


class OCRCaptchaSolver:
    """OCR-based CAPTCHA solver using Tesseract"""
    
    def solve_captcha_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to grayscale and enhance contrast
            image = image.convert('L')

            # Use pytesseract to extract text
            captcha_text = pytesseract.image_to_string(
                image,
                config='--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            )

            # Clean up the text
            captcha_text = captcha_text.strip().replace(' ', '').replace('\n', '')

            if len(captcha_text) >= 4:  # Most CAPTCHAs are 4-6 characters
                logger.info(f"OCR extracted CAPTCHA: {captcha_text}")
                return captcha_text
            else:
                logger.warning(f"OCR extracted too short text: {captcha_text}")
                return None

        except Exception as e:
            logger.error(f"OCR CAPTCHA solving failed: {e}")
            return None


class SimpleCaptchaSolver:
    
    def solve_manual_captcha(self, image_bytes: bytes) -> Optional[str]:
        try:
            # For now, just return placeholder
            logger.info("Manual CAPTCHA solving not implemented - using placeholder")
            return "1234"  # Replace with GUI/input logic if needed
        except Exception as e:
            logger.error(f"Manual CAPTCHA solving failed: {e}")
            return None


class HybridCaptchaSolver:

    def __init__(self):
        self.ocr_solver = OCRCaptchaSolver()
        self.manual_solver = SimpleCaptchaSolver()

    def solve_captcha(self, image_bytes: bytes) -> Optional[str]:
        
        logger.info("Attempting to solve CAPTCHA...")

        
        solution = self.ocr_solver.solve_captcha_from_bytes(image_bytes)
        if solution:
            logger.info("CAPTCHA solved using OCR")
            return solution

        logger.info("OCR failed, trying manual CAPTCHA solving...")
        solution = self.manual_solver.solve_manual_captcha(image_bytes)
        if solution:
            logger.info("CAPTCHA solved manually")
            return solution

        logger.error("Both OCR and manual CAPTCHA solving failed")
        return None


_captcha_solver: Optional[HybridCaptchaSolver] = None


def get_captcha_solver() -> HybridCaptchaSolver:
    """Get the global CAPTCHA solver instance"""
    global _captcha_solver
    if _captcha_solver is None:
        _captcha_solver = HybridCaptchaSolver()
    return _captcha_solver


def solve_captcha(image_bytes: bytes) -> Optional[str]:
    
    solver = get_captcha_solver()
    return solver.solve_captcha(image_bytes)
