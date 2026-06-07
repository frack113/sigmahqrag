"""Chat API v1."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from src.application.chat.service import ChatService
from src.shared.exceptions import ValidationError
from src.shared.schemas.chat import ChatMessageRequest, ChatMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["v1-chat"])
chat_service = ChatService()


@router.get("/history")
async def get_chat_history() -> list[dict]:
    """Get chat message history."""
    return chat_service.get_history()


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history() -> None:
    """Clear chat history and llama.cpp KV cache."""
    await chat_service.clear_history()


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(req: ChatMessageRequest) -> ChatMessageResponse:
    """Process a chat message and return AI response."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        response_text = await chat_service.process_message(
            req.message, req.mode, req.model, prompt_id=req.prompt_id
        )
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
            detail="Failed to process message",
        ) from None


@router.post("/upload")
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
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")
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
            detail="Failed to process upload",
        ) from None


@router.post("/message/stream")
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
            async for token in chat_service.process_message_stream(
                req.message, req.mode, req.model, prompt_id=req.prompt_id
            ):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield "data: Error: An internal error occurred\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
