# 🤖 SigmaHQ RAG Application

A local Retrieval-Augmented Generation application with **zero external API dependencies** - works offline with CPU-based embeddings!

---

## ⚡ Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/frack113/sigmahqrag.git
cd sigmahqrag

# 2. Install with uv (recommended Python package manager)
uv sync

# 3. Run the application
uv run python main.py

# 4. Open your browser
# → http://localhost:8002
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🚀 **Zero Dependencies** | No LM Studio required - CPU embeddings work out of the box |
| 🌐 **Offline Ready** | Works completely offline with local models |
| 💬 **Chat Interface** | Real-time RAG-powered conversations with document context |
| 📄 **Document Management** | Upload, organize, and query your documents |
| 🧠 **Local LLM Support** | Optional LM Studio integration for faster responses |
| ⚡ **Streaming Responses** | Real-time response generation |
| 🔐 **Privacy First** | All processing happens on your machine |

---

## 📖 Documentation

📚 **Full documentation organized by category:**

### 🚀 Getting Started
- 📄 **[Quick Production Setup](docs/GETTING_STARTED/QUICK_START_PRODUCTION.md)** - 5-minute production deployment guide

### 👥 User Guides
- 📘 **[User Manual](docs/USER_DOCUMENTATION/USER_MANUAL.md)** - Complete user guide for all features
- 🔌 **[API Reference](docs/USER_DOCUMENTATION/API_REFERENCE.md)** - REST API documentation and examples

### 🏗️ Deployment & Setup
- 🚢 **[Deployment Guide](docs/DEPLOYMENT/DEPLOYMENT_GUIDE.md)** - Production deployment procedures
- ⚙️ **[LM Studio Setup](docs/SETUP_GUIDES/LM_STUDIO_SETUP_GUIDE.md)** - Optional local LLM configuration

### 🔧 Technical Docs
- 🏛️ **[Architecture](docs/TECHNICAL_DOCS/structure.md)** - Code structure and application architecture

---

## 🎯 Core Features Explained

### 💬 RAG-Powered Chat
Ask questions about your uploaded documents with semantic search:
- **Context-aware responses** based on document content
- **Conversation history** maintained across messages
- **Streaming responses** for real-time feedback
- **Document references** in every response

### 📂 Document Management
Supports multiple file formats:
- 📄 PDF files
- 📝 Word documents (DOCX)
- 📃 Text files (TXT, MD)
- 🖼️ Images (with OCR support)

All documents are indexed for fast semantic search using **ChromaDB**.

### 🔗 Optional LM Studio Integration
For faster responses with local LLMs:
- Load models in LM Studio
- Automatic detection and connection
- Seamless fallback to CPU embeddings if unavailable

---

## 📁 Project Structure

```
sigmahqrag/
├── main.py                          # Application entry point
├── src/
│   ├── application/                 # Main app initialization
│   │   └── application.py          # SigmaHQApplication class
│   ├── components/                  # Gradio UI components
│   │   ├── chat_interface.py       # Chat with RAG
│   │   ├── data_management.py      # Document upload/manage
│   │   ├── file_management.py      # File operations
│   │   ├── github_management.py    # GitHub integration
│   │   ├── config_management.py    # Settings configuration
│   │   └── logs_viewer.py          # System logs viewer
│   ├── core/                        # Core services
│   │   ├── llm_service.py          # Optimized LLM interface
│   │   ├── local_embedding_service.py  # CPU embeddings (no deps!)
│   │   └── rag_service.py          # RAG with ChromaDB
│   ├── infrastructure/              # External integrations
│   │   └── external/
│   │       └── lm_studio_client.py # LM Studio API client
│   ├── models/                      # Business logic layers
│   │   ├── rag_chat_service.py     # RAG chat integration
│   │   ├── data_service.py         # Data processing
│   │   └── config_service.py       # Configuration management
│   └── shared/                      # Shared utilities
├── data/                            # Runtime data
│   ├── models/                      # Local model files
│   ├── chat_history.db              # Chat persistence
│   └── logs/                        # Application logs
└── docs/                           # 📚 Documentation
    ├── GETTING_STARTED/
    ├── USER_DOCUMENTATION/
    ├── DEPLOYMENT/
    ├── SETUP_GUIDES/
    └── TECHNICAL_DOCS/
```

---

## 🛠️ Technical Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | Gradio 6.9+ | Modern web interface with tabs |
| **Embeddings** | sentence-transformers | CPU-based local embeddings (all-MiniLM-L6-v2) |
| **Vector DB** | ChromaDB | Semantic search and document retrieval |
| **LLM API** | OpenAI-compatible | LM Studio integration (optional) |
| **Docs** | Markdown + PyPDF2/DocX | Text extraction from documents |
| **Python** | Python 3.10+ | Core application language |
| **Package Manager** | uv | Fast dependency management |

---

## ⚙️ Configuration

### Default Settings (from `data/config.json`)

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "base_url": "http://127.0.0.1:1234"
  },
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000
  },
  "rag": {
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

### Environment Variables

```bash
# Port configuration
export SERVER_PORT=8002

# LM Studio settings
export LM_STUDIO_BASE_URL="http://localhost:1234"
export LM_STUDIO_API_KEY="lm-studio"
```

---

## 🚀 Advanced Usage

### Programmatic API

```python
from src.models.rag_chat_service import create_rag_chat_service

# Create RAG chat service
rag_service = create_rag_chat_service()

# Get streaming response
for chunk in rag_service.stream_response("What documents do you have?"):
    print(chunk, end="", flush=True)

# Check RAG status
status = rag_service.get_rag_status()
print(f"LLM Connected: {status['llm_connected']}")
```

### LM Studio Integration (Optional)

1. Install [LM Studio](https://lmstudio.ai/)
2. Load models:
   - **Chat**: `qwen/qwen3.5-9b` or `mistralai/ministral-3-14b-reasoning`
   - **Embeddings**: `text-embedding-all-minilm-l6-v2-embedding`
3. Start server on port `1234`
4. The app automatically connects when available

**Fallback behavior**: CPU embeddings → LM Studio API → Error handling (always works!)

---

## 📊 Gradio Interface Tabs

| Tab | Description |
|-----|-------------|
| 💬 **Chat** | Main RAG chat interface with streaming responses |
| 📊 **Data** | Document upload, management, and deletion |
| 📁 **GitHub** | Connect GitHub repos for document indexing |
| 📂 **Files** | File browser and operations |
| ⚙️ **Config** | Application settings and configuration |
| 📋 **Logs** | Real-time system logs and monitoring |

---

## 🐛 Troubleshooting

### Port 8002 Already in Use?

```bash
# Kill existing process (Linux/Mac)
sudo lsof -ti:8002 | xargs kill -9

# Or use different port
uv run python main.py --port 8003
```

### LM Studio Not Connecting?

1. Check if LM Studio is running
2. Verify port 1234 is available
3. CPU embeddings work without LM Studio!

See **[Troubleshooting in User Manual](docs/USER_DOCUMENTATION/USER_MANUAL.md#troubleshooting)** for more details.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🔗 External Resources

- [LM Studio](https://lmstudio.ai/) - Local LLM server
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [sentence-transformers](https://www.sbert.net/) - Embedding models

---

**Built with ❤️ for local-first AI applications**