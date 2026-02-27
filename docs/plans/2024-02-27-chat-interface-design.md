# Multi-Modal Chat Interface Design

## Overview
Design for adding a multi-modal chat interface with document upload capabilities to the SigmaHQ RAG system using NiceGUI native implementation.

## Architecture
```
┌───────────────────────────────────────────────────────┐
│                 NiceGUI Web Application                │
├─────────────────┬─────────────────┬────────────────────┤
│   Chat UI       │    API Routes   │  Data Service      │
│  Components     │ (FastAPI)       │ (RAG Pipeline)     │
└─────────────────┴─────────────────┴────────────────────┘
```

### Key Components:
- `chat_page.py`: New page component for the chat interface
- `models/chat_service.py`: Business logic for chat interactions  
- Extended `data_service.py`: Document processing and RAG pipeline

## UI Design

### Layout Structure:
```
┌───────────────────────────────────────────────────────┐
│  ┌─────────────┐  ┌─────────────────────────────────┐ │
│  │ Chat Title  │  │  ┌─────────────┐  ┌───────────┐   │ │
│  └─────────────┘  │  │ Upload      │  │ Clear     │   │ │
│                   │  │ Button      │  │ Chat      │   │ │
│  ┌─────────────────────────────────────────────────┐ │ │
│  │ File Drop Zone (or file selector)               │ │ │
│  └─────────────────────────────────────────────────┘ │ │
│  ┌─────────────────────────────────────────────────┐ │ │
│  │ Chat Messages Area                             │ │ │
│  │  ┌───────────────────────────────────────────┐  │ │ │
│  │  │ User: "What's in this document?"          │  │ │ │
│  │  └───────────────────────────────────────────┘  │ │ │
│  │  ┌───────────────────────────────────────────┐  │ │ │
│  │  │ Assistant: "The document discusses..."    │  │ │ │
│  │  └───────────────────────────────────────────┘  │ │ │
│  └─────────────────────────────────────────────────┘ │ │
│  ┌─────────────────────────────────────────────────┐ │ │
│  │ Input Area with Send Button                     │ │ │
│  └─────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

### Key UI Elements:
- File upload zone with drag-and-drop support
- Chat message history (scrollable)
- Input area for text queries
- Document preview thumbnails in chat messages

## Data Flow

```
User Action → NiceGUI Event → FastAPI Endpoint → RAG Pipeline → Response → NiceGUI Update

1. User uploads document → File uploaded to server
2. Document processed → Extracted text, generated embeddings (SentenceTransformers)
3. Embeddings stored → ChromaDB vector store
4. User sends query → Query embedded using same model
5. Similar documents retrieved → From vector store
6. Context + query sent → To local LLM for generation
7. Response received → Displayed in chat interface
```

## Component Implementation Plan

### New Files:
1. `src/nicegui_app/pages/chat_page.py` - Main chat UI component
2. `src/nicegui_app/components/chat_message.py` - Individual message display
3. `src/nicegui_app/models/chat_service.py` - Chat business logic
4. `src/nicegui_app/components/file_upload.py` - Document upload handler

### Modified Files:
1. `src/nicegui_app/app.py` - Add route for chat page
2. `src/nicegui_app/models/data_service.py` - Extend RAG pipeline

## Error Handling Strategy

```
Error Scenarios:
┌───────────────────────────────────────────────────────┐
│ 1. File Upload Errors                                │
│    - Invalid file type → Show error + allowed types   │
│    - File too large → Show size limit warning         │
│    - Upload failed → Retry option                    │
├───────────────────────────────────────────────────────┤
│ 2. Processing Errors                                 │
│    - Embedding generation fails → Fallback to text   │
│    - LLM generation fails → Show technical error     │
├───────────────────────────────────────────────────────┤
│ 3. Display Errors                                    │
│    - Preview generation fails → Show placeholder     │
│    - Chat history load fails → Clear and restart      │
└───────────────────────────────────────────────────────┘
```

## Requirements Summary
- Multi-modal chat interface using NiceGUI native components
- Document upload with drag-and-drop support
- File preview/thumbnail generation for uploaded documents
- Local LLM integration via SentenceTransformers
- RAG pipeline for contextual document queries
- Comprehensive error handling and user feedback
