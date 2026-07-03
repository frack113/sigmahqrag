"""Chat API v1."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from src.application.chat.service import ChatService
from src.shared.exceptions import ValidationError
from src.api.v1.chat.schemas import ChatMessageRequest, ChatMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["v1-chat"])
_chat_service: ChatService | None = None


def _get_session_id(x_session_id: str | None = Header(None)) -> str | None:
    """Extract session ID from ``X-Session-ID`` header."""
    return x_session_id


def _get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


@router.get("/history")
async def get_chat_history(
    session_id: str | None = Depends(_get_session_id),
) -> list[dict]:
    """Get chat message history."""
    return _get_chat_service().get_history(session_id)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history(
    session_id: str | None = Depends(_get_session_id),
) -> None:
    """Clear chat history and llama.cpp KV cache."""
    await _get_chat_service().clear_history(session_id)


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    req: ChatMessageRequest,
    session_id: str | None = Depends(_get_session_id),
) -> ChatMessageResponse:
    """Process a chat message and return AI response."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        svc = _get_chat_service()
        response_text = await svc.process_message(
            req.message,
            req.mode,
            req.model,
            prompt_id=req.prompt_id,
            session_id=session_id,
        )
        citations = svc.get_last_citations(session_id)

        # Format citations as [sigma:rule_id] in response
        if citations and response_text:
            citation_str = "Sources: " + ", ".join(f"[{c}]" for c in citations)
            response_text = f"{response_text}\n\n{citation_str}"

        return ChatMessageResponse(
            response=response_text,
            timestamp=datetime.now(UTC).isoformat(),
            citations=[{"id": c} for c in citations] if citations else [],
            mode=req.mode,
        )
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        ) from None


@router.post("/upload")
async def upload_sigma_rule(
    file: UploadFile,
    session_id: str | None = Depends(_get_session_id),
) -> dict:
    """Upload and validate a Sigma rule YAML file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    valid_extensions = (".yaml", ".yml")
    if "." not in file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Expected {valid_extensions}, got no extension",
        )
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
        rule = await _get_chat_service().validate_and_store_yaml(content, session_id)

        return {
            "rule_name": rule.name,
            "rule_id": rule.id,
            "validated": True,
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.message,
        ) from None
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload",
        ) from None


@router.post("/message/stream")
async def send_chat_message_stream(
    req: ChatMessageRequest,
    session_id: str | None = Depends(_get_session_id),
):
    """Process a chat message and stream the LLM response."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    async def generate():
        """Generate SSE events from LLM stream."""
        try:
            async for token in _get_chat_service().process_message_stream(
                req.message,
                req.mode,
                req.model,
                prompt_id=req.prompt_id,
                session_id=session_id,
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
