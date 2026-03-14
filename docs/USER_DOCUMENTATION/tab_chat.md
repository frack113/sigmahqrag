# 💬 Chat Interface Tab

The Chat tab provides an RAG (Retrieval Augmented Generation) enhanced chat interface for interacting with your knowledge base.

## Overview

This tab allows you to ask questions and receive intelligent responses powered by the RAG system. You can:
- Chat naturally about indexed documents
- Use special commands for quick actions
- Configure RAG settings in real-time
- Export conversation history

---

## GUI Design

### Layout Structure

The Chat tab uses a main chat area with an adjustable sidebar for configuration.

```
┌───────────────────────────────────────────────────────────────┐
│  ## 🤖 RAG Chat Interface                                     │
├───────────────────────────────────────────────────────────────┤
│  ┌───────────────────────┐    ┌─────────────────────────────┐ │
│  │                       │    │      Configuration          │ │
│  │     Main Chat Area    │    │                             │ │
│  │  ┌─────────────────┐  │    │  [🤖] RAG Settings         │ │
│  │  │ Assistant:      │  │    │  ├───────────────────────┤ │ │
│  │  │ Response...     │  │    │  │ ☑ Enable RAG          │ │ │
│  │  └─────────────────┘  │    │  │ 📊 History Limit      │ │ │
│  │                       │    │  ├───────────────────────┤ │ │
│  │  ┌─────────────────┐  │    │  │ 📈 RAG Results        │ │ │
│  │  │ Input Box       │  │    │  │ 🔢 Min Score         │ │ │
│  │  └─────────────────┘  │    │                             │ │ │
│  │    [Send] [Clear]     │    │  [📊] [💾] Actions         │ │ │
│  │                       │    │                             │ │
│  └───────────────────────┘    └─────────────────────────────┘ │
├───────────────────────────────────────────────────────────────┤
│  Status: Ready                                                │
└───────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="chat-container")
    ├── gr.Markdown("## 🤖 RAG Chat Interface")
    │
    ├── gr.Row() # Main content area
    │   ├── gr.Column(scale=3) # Left side
    │   │   ├── self.chatbot = gr.Chatbot()
    │   │   └── gr.Row() # Input controls
    │   │       ├── self.msg_input = gr.Textbox()
    │   │       ├── self.submit_btn = gr.Button("Send")
    │   │       └── self.clear_btn = gr.Button("Clear")
    │   │   └── self.status_text = gr.Textbox(label="Status")
    │   │
    │   └── gr.Column(scale=1) # Right sidebar
    │       ├── gr.Markdown("### Configuration")
    │       └── gr.Accordion("RAG Settings", open=False)
    │           ├── gr.Row() [Checkbox, Number input]
    │           └── gr.Row() [Number inputs]
    │               └── gr.Row() [Buttons]
    │                   ├── refresh_btn
    │                   └── export_btn
    │
    └── Events: submit_btn.click(), msg_input.submit()
```

### Component Specifications

#### Chat Area (`gr.Column`, scale=3)
- **Width**: 75% of container (scale=3 vs scale=1)
- **Padding**: Standard Gradio padding
- **Background**: Theme background color

##### Chatbot Component (`self.chatbot`)
| Property | Value | Purpose |
|----------|-------|---------|
| `type` | list[dict] | Stores conversation history |
| `show_label` | False | No header, title above |
| `elem_id` | "chat-messages" | Identifier for scripts |

##### Input Controls (`gr.Row`)
| Element | Type | Scale | Description |
|---------|------|-------|-------------|
| Textbox | gr.Textbox | 1 | Message input area |
| Submit Button | gr.Button("Send") | 0 | Primary action trigger |
| Clear Button | gr.Button("Clear") | 0 | Clears conversation |

##### Status Box (`self.status_text`)
| Property | Value |
|----------|-------|
| `label` | "Status" |
| `interactive` | False | Read-only display |
| `max_lines` | 2 | Wraps after 2 lines |

#### Sidebar Area (`gr.Column`, scale=1)
- **Width**: 25% of container (scale=1 vs scale=3)
- **Spacing**: Compact padding for controls

##### RAG Settings Accordion
The collapsible panel contains all RAG-related controls.

| Component | Type | Label | Default/Value | Range | Description |
|-----------|------|-------|---------------|-------|-------------|
| Enable RAG | Checkbox | "Enable RAG" | True (☑) | - | Toggle RAG on/off |
| History Limit | Number | "History Limit" | 10 | 1-100 | Conversation history retention |
| RAG Results | Number | "RAG Results" | 3 | 1-10 | Documents to retrieve per query |
| Min Score | Number | "Min Score" | 0.1 | 0.0-1.0 | Minimum relevance threshold |

##### Action Buttons (`gr.Row` under accordion)
| Button | Variant | Purpose |
|--------|---------|---------|
| Stats | secondary | Displays system statistics |
| Export | secondary | Exports chat to JSON file |

---

## Commands Reference

### Special Commands (Start with `/`)

Type commands directly in the chat input box to access quick actions.

#### `/help` - Show Command Reference
Shows all available commands and features.

**Output:**
```
**Available Commands:**

/help - Show this help message
/stats - Show system statistics  
/clear - Clear chat history
/export - Export chat to file

**RAG Features:**
- Automatic document retrieval for context
- Conversation history management
```

#### `/stats` - System Statistics
Displays current system statistics.

**Output:**
```
**System Statistics**:
**Total Conversations:** X
```

#### `/clear` - Clear Chat History
Clears the conversation and shows welcome message.

**Effect:**
- Removes all chat history
- Shows: "Chat history cleared. How can I help you today?"

#### `/export` - Export Conversation
Triggers export of conversation history to JSON file.

**File Location:** `exports/chat_export_YYYYMMDD_HHMMSS.json`

---

## RAG Configuration Options

### Enable RAG (Checkbox)
- **Purpose**: Toggle RAG retrieval on/off
- **Default**: ✅ Enabled
- **Effect**: When disabled, responses come from the LLM only without document context

### History Limit (Number Input)
- **Range**: 1 to 100 messages
- **Default**: 10 messages
- **Purpose**: Controls how many recent messages are considered in context window

### RAG Results (Number Input)
- **Range**: 1 to 10 documents
- **Default**: 3 documents
- **Purpose**: Number of relevant document chunks to retrieve for each query

### Min Score (Number Input)
- **Range**: 0.0 to 1.0
- **Step**: 0.01 precision
- **Default**: 0.1
- **Purpose**: Minimum relevance score threshold for document retrieval

---

## Event Handlers

### Message Submission (`submit_btn.click()` / `msg_input.submit()`)
Two event handlers trigger on message submission:
1. **Button click** - User presses "Send" button
2. **Text submit** - User presses Enter in input box

**Flow:**
```python
_handle_send_message(message: str) -> Generator[...]:
    1. Check for empty/whitespace-only messages
    2. Handle special commands (start with /)
    3. For regular messages:
       a. Add user message to history
       b. Stream response chunk by chunk
       c. Yield updates on each chunk
       d. Update assistant response in chat history
    4. Return complete conversation state
```

### Chat Clear (`clear_btn.click()`)
**Flow:**
```python
_clear_chat_handler():
    1. Set status to "Ready"
    2. Clear Gradio's internal chatbot state
    3. Show welcome message
```

### Stats Command (`/stats`)
**Flow:**
```python
_get_stats():
    1. Count conversations from chatbot history
    2. Return formatted statistics string
```

### Export Command (`/export`)
**Flow:**
```python
_export_chat_handler():
    1. Generate timestamp: YYYYMMDD_HHMMSS
    2. Create filepath in exports/ directory
    3. Serialize chatbot history to JSON
    4. Write file to disk
    5. Return success message with filepath
```

---

## Conversation Flow Example

### Step-by-Step Interaction

1. **User sends:** "What does the RAG service do?"
2. **System retrieves:** Document chunks about RAG from indexed knowledge base
3. **LLM generates:** Response combining retrieved context with language understanding
4. **Output displays:** Streamed response in chat history

### Chat History Structure
```python
conversation = [
    {"role": "user", "content": "What is RAG?"},
    {"role": "assistant", "content": "RAG stands for..."},
    {"role": "user", "content": "How does it work?"},
    {"role": "assistant", "content": "The workflow includes..."}
]
```

---

## Export Format

Exported files are JSON with the following structure:

```json
{
  [0]: {
    "role": "user",
    "content": "Question text here..."
  },
  [1]: {
    "role": "assistant", 
    "content": "Answer text here..."
  }
}
```

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Empty message | No text entered | Type a question and press Send |
| Invalid JSON export | Corrupted chat history | Refresh the tab and try again |
| RAG timeout | Large document index | Reduce "RAG Results" or increase timeout |
| Connection error | LLM server unavailable | Check network and model server status |

---

## Best Practices

1. **Be specific in queries** - The more context you provide, the better responses
2. **Use /help first** - Familiarize yourself with available commands
3. **Adjust RAG settings per task** - Fewer results for quick questions, more for research
4. **Export important conversations** - Use /export to save key discussions
5. **Clear history when needed** - Use /clear to start fresh topics

---

## Related Documentation

- [📊 Data Tab](./tab_data.md) - Update the knowledge base
- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview