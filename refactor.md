# Refactor Plan: SigmaHQ RAG

## 1. Critical: Complete Core Implementation
The core RAG functionality is currently a skeleton.
- [ ] Implement `LlamaClient.complete` and `LlamaClient.chat` in `src/back/llamacpp/client.py` to interface with the Llama.cpp server.
- [ ] Implement `RAGPipeline.search` and `RAGPipeline.index` in `src/back/rag/pipeline.py` to perform actual vector searches and indexing.

## 2. High Priority: Performance & Stability
- [ ] **Fix Memory Leak in Log Reading**: Refactor `SubprocessManager.get_logs` in `src/shared/subprocess_manager.py` to use a streaming approach (e.g., reading from the end of the file) instead of `f.readlines()` to prevent OOM errors on large logs.
- [ ] **Prevent Event Loop Blocking**: 
    - Move `yaml.dump` in `src/back/backend/services/rag_pipeline.py` to a thread pool using `loop.run_in_executor`.
    - Identify and wrap other synchronous I/O operations in `async` methods with executors.

## 3. Medium Priority: Reliability & Maintenance
- [ ] **Robust Service Recovery**: Enhance `SubprocessManager` to better handle service crashes and ensure clean state transitions.
- [ ] **Error Handling**: Standardize error propagation from the backend services to the API layer to provide more meaningful feedback to the user.
