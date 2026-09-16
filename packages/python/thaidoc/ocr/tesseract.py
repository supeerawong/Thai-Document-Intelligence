import pytesseract
from PIL import Image


class TesseractOCRProvider:
    name = "tesseract"

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str:
        return str(pytesseract.image_to_string(image, lang=language))
