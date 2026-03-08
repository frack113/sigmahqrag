"""
Document Processor for NiceGUI

Handles processing of different file formats including PDF, images, DOCX, and text files.
"""

import base64
import io
import logging
import os

# Import document processing libraries
try:
    import docx
    import easyocr  # For OCR if needed
    from PIL import Image
    from pypdf import PdfReader
except ImportError as e:
    print(f"Warning: Some document processing libraries not available: {e}")


class DocumentProcessor:
    """
    Handles processing of different file formats.

    Methods:
        - process_file: Process a file and extract text content
        - _process_pdf: Process PDF files
        - _process_image: Process image files with OCR
        - _process_docx: Process DOCX files
        - _process_txt: Process text files
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_file(self, file_path: str) -> tuple[str, str | None]:
        """
        Process an uploaded document and extract text content.

        Args:
            file_path: Path to the uploaded file

        Returns:
            Tuple of (extracted_text, preview_base64)
            - extracted_text: Text content from the document
            - preview_base64: Optional base64-encoded image preview

        Raises:
            ValueError: If the file type is unsupported.
            Exception: For any other processing errors.
        """
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".txt":
                return self._process_txt(file_path)
            elif ext == ".pdf":
                return self._process_pdf(file_path)
            elif ext in [".png", ".jpg", ".jpeg"]:
                return self._process_image(file_path)
            elif ext == ".docx":
                return self._process_docx(file_path), None
            else:
                raise ValueError(f"Unsupported file type: {ext}")

        except Exception as e:
            error_msg = f"Error processing document {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise

    def _process_pdf(self, file_path: str) -> tuple[str, str | None]:
        """
        Process PDF file and extract text with optional first page preview.

        Args:
            file_path: Path to PDF file.

        Returns:
            Tuple of (extracted_text, preview_base64).

        Raises:
            ImportError: If pdf2image is not available.
            Exception: For any other processing errors.
        """
        extracted_text = ""
        preview_base64 = None

        try:
            # Extract text using PyPDF2
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"

            # Generate preview (first page as image)
            import pdf2image

            images = pdf2image.convert_from_path(file_path, first_page=1, last_page=1)
            if images:
                img = images[0]
                img.thumbnail((300, 300))

                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                preview_base64 = f"data:image/png;base64,{img_str}"

        except ImportError:
            self.logger.warning(
                "pdf2image not available, skipping PDF preview generation"
            )
        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")

        return extracted_text, preview_base64

    def _process_image(self, file_path: str) -> tuple[str, str | None]:
        """
        Process image file and extract text using OCR.

        Args:
            file_path: Path to image file.

        Returns:
            Tuple of (extracted_text, preview_base64).

        Raises:
            ImportError: If PIL or easyocr is not available.
            Exception: For any other processing errors.
        """
        extracted_text = ""
        preview_base64 = None

        try:
            # Load image and generate preview
            img = Image.open(file_path)
            img.thumbnail((300, 300))

            # Convert to base64 for preview
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            preview_base64 = f"data:image/png;base64,{img_str}"

            # Try OCR to extract text (if easyocr is available)
            try:
                reader = easyocr.Reader(["en"])
                results = reader.readtext(img, detail=0)
                extracted_text = "\n".join(results)
            except Exception as ocr_error:
                self.logger.info(f"OCR not available or failed: {ocr_error}")
                extracted_text = "[Image content - no text extracted]"

        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            extracted_text = "[Image file]"

        return extracted_text, preview_base64

    def _process_docx(self, file_path: str) -> str:
        """
        Process DOCX file and extract text content.

        Args:
            file_path: Path to DOCX file.

        Returns:
            Extracted text from the document.

        Raises:
            ImportError: If docx is not available.
            Exception: For any other processing errors.
        """
        extracted_text = ""

        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                extracted_text += paragraph.text + "\n"

        except Exception as e:
            self.logger.error(f"Error processing DOCX: {e}")
            raise

        return extracted_text

    def _process_txt(self, file_path: str) -> tuple[str, str | None]:
        """
        Process text file and extract content.

        Args:
            file_path: Path to text file.

        Returns:
            Tuple of (extracted_text, None).
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                extracted_text = f.read()
            return extracted_text, None
        except Exception as e:
            self.logger.error(f"Error processing TXT file: {e}")
            raise
