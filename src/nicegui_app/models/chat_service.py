"""
Chat Service Layer

Handles message history management, document processing pipeline,
LLM query interface, and error handling for the multi-modal chat system.
"""
from typing import List, Dict, Any, Optional, Tuple, NoReturn
from datetime import datetime
import logging
import os
import tempfile
import asyncio
from pathlib import Path
import markdown2
import base64  # Added for proper base64 encoding

# Import document processing libraries
try:
    from PyPDF2 import PdfReader
    import docx
    from PIL import Image
    import pytesseract  # For OCR if needed
except ImportError as e:
    print(f"Warning: Some document processing libraries not available: {e}")


class ChatMessage:
    """
    Data structure representing a chat message.
    
    Attributes:
        id: Unique identifier for the message
        role: Either 'user' or 'assistant'
        content: Text content of the message
        timestamp: When the message was created
        document_path: Optional path to uploaded document
        metadata: Additional message metadata
    """
    
    def __init__(
        self,
        role: str,
        content: str,
        document_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if role not in ('user', 'assistant'):
            raise ValueError("Role must be either 'user' or 'assistant'")
        
        self.id = str(datetime.now().timestamp()) + f"_{hash(content) % 1000}"
        self.role = role
        self.content = content
        self.timestamp = datetime.now()
        self.document_path = document_path
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'document_path': self.document_path,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create message from dictionary."""
        msg = cls(
            role=data['role'],
            content=data['content'],
            document_path=data.get('document_path'),
            metadata=data.get('metadata', {})
        )
        msg.id = data['id']
        msg.timestamp = datetime.fromisoformat(data['timestamp'])
        return msg


class ChatService:
    """
    Core chat service that manages conversation state and document processing.
    
    Attributes:
        message_history: List of ChatMessage objects in the current session
        max_history: Maximum number of messages to keep in history
        logger: Logging instance for debugging
    """
    
    def __init__(self, max_history: int = 50) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be a positive integer")
        
        self.message_history: List[ChatMessage] = []
        self.max_history = max_history
        self.logger = logging.getLogger(__name__)
        
        # Configure logger with a more descriptive format
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def add_message(self, role: str, content: str, document_path: Optional[str] = None) -> ChatMessage:
        """
        Add a message to the conversation history.
        
        Args:
            role: Either 'user' or 'assistant'
            content: Message text content
            document_path: Optional path to uploaded document
            
        Returns:
            The created ChatMessage object
        """
        message = ChatMessage(role, content, document_path)
        self.message_history.append(message)
        
        # Trim history if it exceeds max size
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        return message
    
    def get_message_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get the conversation history.
        
        Args:
            limit: Maximum number of messages to return (None for all)
            
        Returns:
            List of ChatMessage objects
        """
        if limit is None:
            return self.message_history.copy()
        return self.message_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear the entire conversation history."""
        self.message_history = []
    
    async def process_document(self, file_path: str) -> Tuple[str, Optional[str]]:
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
        extracted_text = ""
        preview_base64 = None
        
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            elif ext == '.pdf':
                extracted_text, preview_base64 = self._process_pdf(file_path)
            elif ext in ['.png', '.jpg', '.jpeg']:
                extracted_text, preview_base64 = self._process_image(file_path)
            elif ext == '.docx':
                extracted_text = self._process_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        
        except Exception as e:
            error_msg = f"Error processing document {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise
        
        return extracted_text, preview_base64
    
    def _process_pdf(self, file_path: str) -> Tuple[str, Optional[str]]:
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
                import io
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                preview_base64 = f"data:image/png;base64,{img_str}"
        
        except ImportError:
            self.logger.warning("pdf2image not available, skipping PDF preview generation")
        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")
        
        return extracted_text, preview_base64
    
    def _process_image(self, file_path: str) -> Tuple[str, Optional[str]]:
        """
        Process image file and extract text using OCR.
        
        Args:
            file_path: Path to image file.
            
        Returns:
            Tuple of (extracted_text, preview_base64).
            
        Raises:
            ImportError: If PIL or pytesseract is not available.
            Exception: For any other processing errors.
        """
        extracted_text = ""
        preview_base64 = None
        
        try:
            # Load image and generate preview
            from PIL import Image  # Import here to avoid circular dependency
            img = Image.open(file_path)
            img.thumbnail((300, 300))
            
            # Convert to base64 for preview
            import io
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            preview_base64 = f"data:image/png;base64,{img_str}"
            
            # Try OCR to extract text (if tesseract is available)
            try:
                import pytesseract  # Import here to avoid circular dependency
                extracted_text = pytesseract.image_to_string(img)
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
    
    async def generate_response(
        self,
        user_message: str,
        document_content: Optional[str] = None,
        context_documents: Optional[List[str]] = None
    ) -> str:
        """
        Generate an assistant response using the LLM.
        
        Args:
            user_message: The user's message text.
            document_content: Optional content from uploaded documents.
            context_documents: Optional list of additional context documents.
            
        Returns:
            Generated response text.
            
        Raises:
            Exception: If the LLM generation fails or times out.
        """
        # In a real implementation, this would call the LLM API
        # For now, we'll return a mock response
        
        self.logger.info(f"Generating response for: {user_message[:50]}...")
        
        # Build context from document content if provided
        context = []
        if document_content:
            context.append(f"Document content:\n{document_content[:200]}...")
        if context_documents:
            for i, doc in enumerate(context_documents):
                context.append(f"Context document {i+1}:\n{doc[:200]}...")
        
        # Simulate processing delay
        await asyncio.sleep(1)
        
        # Generate mock response based on input
        if "hello" in user_message.lower() or "hi" in user_message.lower():
            response = "Hello! How can I assist you today?"
        elif document_content and len(document_content) > 0:
            response = f"I've analyzed the document. It contains {len(document_content.split()):,} words. Based on the content, here's my analysis: [analysis would go here]"
        else:
            response = f"Thank you for your message: '{user_message}'. I'm a chat assistant that can help with document analysis and questions about the content."
        
        return response
    
    async def process_chat_turn(
        self,
        user_input: str,
        file_paths: Optional[List[str]] = None
    ) -> Tuple[ChatMessage, ChatMessage]:
        """
        Process a complete chat turn (user input + optional files).
        
        Args:
            user_input: The user's text input.
            file_paths: Optional list of uploaded file paths.
            
        Returns:
            Tuple of (user_message, assistant_message).
            
        Raises:
            ValueError: If the provided inputs are invalid.
        """
        # Add user message to history
        if file_paths and len(file_paths) > 0:
            # Process documents first
            document_contents = []
            previews = []
            
            for file_path in file_paths:
                try:
                    doc_content, preview = await self.process_document(file_path)
                    document_contents.append(doc_content)
                    if preview:
                        previews.append(preview)
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    self.logger.error(error_msg)
            
            # Combine all document contents
            combined_doc_content = "\n\n".join(document_contents)
        else:
            combined_doc_content = None
        
        user_message = self.add_message('user', user_input, file_paths[0] if file_paths else None)
        
        # Generate assistant response
        assistant_response = await self.generate_response(
            user_input,
            combined_doc_content
        )
        
        assistant_message = self.add_message('assistant', assistant_response)
        
        return user_message, assistant_message
    
    def export_conversation(self) -> Dict[str, Any]:
        """
        Export the entire conversation history as a dictionary.
        
        Returns:
            Dictionary containing conversation data
        """
        return {
            'messages': [msg.to_dict() for msg in self.message_history],
            'exported_at': datetime.now().isoformat(),
            'message_count': len(self.message_history)
        }
    
    @classmethod
    def import_conversation(cls, data: Dict[str, Any]) -> 'ChatService':
        """
        Import conversation from exported data.
        
        Args:
            data: Dictionary containing exported conversation data
            
        Returns:
            ChatService instance with imported messages
        """
        service = cls()
        service.message_history = [ChatMessage.from_dict(msg_data) for msg_data in data['messages']]
        return service