import io
import logging
from typing import Optional, Tuple
from PIL import Image
import mss

from config import config

logger = logging.getLogger(__name__)

class ScreenVision:
    """Fast screen capture and image processing pipeline for multimodal vision."""
    
    def __init__(self, max_width: int = config.SCREENSHOT_MAX_WIDTH, quality: int = config.SCREENSHOT_JPEG_QUALITY):
        self.max_width = max_width
        self.quality = quality
        self._sct = None
        
    def _get_sct(self) -> mss.mss:
        """Lazily initialize mss context."""
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def capture_primary_monitor(self) -> Image.Image:
        """
        Captures the primary monitor as a PIL Image.
        Uses mss for high performance with automatic fallback to PIL ImageGrab,
        and graceful fallback image if display session is headless or locked.
        """
        try:
            sct = self._get_sct()
            # In mss, monitors[1] is the primary screen
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(monitor)
            # Convert mss screen capture (BGRA) to PIL Image (RGB)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
        except Exception as e:
            logger.warning(f"mss screen capture failed ({e}), trying PIL ImageGrab...")
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except Exception as grab_err:
                logger.warning(f"Display capture unavailable ({grab_err}), using status canvas.")
                # Return a diagnostic fallback image with clean message
                from PIL import ImageDraw
                fallback = Image.new("RGB", (1280, 720), color=(15, 23, 42))
                draw = ImageDraw.Draw(fallback)
                msg = "[!] Windows Workstation is Locked or Screen is Off.\nTap 'Auto-Unlock Workstation' to access desktop."
                draw.text((360, 340), msg, fill=(0, 240, 255))
                return fallback

    def process_image(self, img: Image.Image) -> Image.Image:
        """Resizes the image if it exceeds max_width while preserving aspect ratio."""
        width, height = img.size
        if width > self.max_width:
            ratio = self.max_width / float(width)
            new_height = int(float(height) * float(ratio))
            img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
        return img

    def capture_screen_bytes(self) -> bytes:
        """
        Captures the screen and returns compressed JPEG bytes ready for Gemini 2.0 API.
        """
        img = self.capture_primary_monitor()
        img = self.process_image(img)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=self.quality, optimize=True)
        return buffer.getvalue()

    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Returns the primary screen width and height."""
        try:
            sct = self._get_sct()
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            return (monitor["width"], monitor["height"])
        except Exception:
            return (1920, 1080)

# Global singleton
screen_vision = ScreenVision()
