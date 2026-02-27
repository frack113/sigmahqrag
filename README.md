# SigmaHQ LLM RAG System with NiceGUI

This project refactors the SigmaHQ LLM RAG system to use NiceGUI exclusively, removing all React/JS code and ensuring local LLM embeddings without remote calls.

## Project Structure
```
src/
  ├── nicegui_app/
  │   ├── components/
  │   │   ├── card.py
  │   │   └── notification.py
  │   ├── models/
  │   │   └── data_service.py
  │   ├── pages/
  │   │   └── dashboard.py
  │   ├── app.py
  │   └── __init__.py
  └── __init__.py
mod/
  └── rag.py
config/
  ├── sigmahqllm.json
  └── github.yml
```

## Features
- Remove all React/JS code from the project.
- Update NiceGUI components for compatibility with NiceGUI 3.x.
- Ensure embeddings are generated locally using `SentenceTransformer`.
- Maintain clean, readable, and modular code throughout the refactoring process.

## Installation
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```