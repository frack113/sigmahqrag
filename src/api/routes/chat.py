"""Chat page and API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from src.core.services.chat_service import ChatService
from src.errors import ValidationError
from src.schemas.chat import ChatMessageRequest, ChatMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
templates = Jinja2Templates(directory="src/front/templates")
chat_service = ChatService()


@router.get("/chat")
async def chat_page(request: Request):
    """Serve the chat page with Jinja2 template."""
    return templates.TemplateResponse(request=request, name="chat.html")


@router.post("/api/v1/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(req: ChatMessageRequest) -> ChatMessageResponse:
    """Process a chat message and return AI response."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        response_text = await chat_service.process_message(req.message, req.mode)
        citations = chat_service.get_last_citations()

        # Format citations as [sigma:rule_id] in response
        if citations and response_text:
            citation_str = "Sources: " + ", ".join(f"[{c}]" for c in citations)
            response_text = f"{response_text}\n\n{citation_str}"

        return ChatMessageResponse(
            response=response_text,
            timestamp=datetime.now(UTC).isoformat(),
            citations=citations,
            mode=req.mode,
        )
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        ) from None


@router.post("/api/v1/chat/upload")
async def upload_sigma_rule(file: UploadFile) -> dict:
    """Upload and validate a Sigma rule YAML file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    valid_extensions = (".yaml", ".yml")
    ext = file.filename[file.filename.rfind(".") :]
    if ext.lower() not in valid_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Expected {valid_extensions}, got {ext}",
        )

    try:
        content = await file.read()
        rule_data = await chat_service.validate_and_store_yaml(content)

        return {
            "rule_name": rule_data.get("name", "Unknown"),
            "rule_id": rule_data.get("id", ""),
            "validated": True,
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        ) from None
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}",
        ) from None


@router.post("/api/v1/chat/message/stream")
async def send_chat_message_stream(req: ChatMessageRequest):
    """Process a chat message and stream the LLM response."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    async def generate():
        """Generate SSE events from LLM stream."""
        try:
            response_text = await chat_service.process_message(req.message, req.mode)
            yield f"data: {response_text}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
