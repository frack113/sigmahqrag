# Worker System Architecture

The `src/worker/` module implements a background task processing system responsible for handling long-running operations such as file discovery, document embedding, and model synchronization. It operates asynchronously from the main FastAPI application thread to prevent blocking HTTP requests.

## Core Components

### 1. TaskDispatcher (`processor.py`)
The `TaskDispatcher` is the central orchestrator of the worker system. It manages a pool of specialized workers and dispatches tasks to them using a `ThreadPoolExecutor`.

**Key Features:**
- **In-Memory State Management:** Maintains a real-time dictionary (`_worker_states`) tracking the status, progress, and current task of each worker type. This eliminates database contention for frequent status updates.
- **Task Queue:** Uses a thread-safe `queue.Queue` to accept tasks from API endpoints.
- **Polling Loop:** Runs in a dedicated background thread, continuously polling the queue and submitting work to the thread pool.
- **Lifecycle Management:** Handles worker initialization, task execution, error recovery, and graceful shutdown.

**Enums:**
Worker types and statuses are defined as Python enums for type safety:
- `WorkerName`: `SIGMAREF_DISCOVERY`, `GITHUB_DISCOVERY`, `LOCAL_DISCOVERY`, `SIGMAREF_EMBEDDINGS`, `GITHUB_EMBEDDINGS`, `LOCAL_EMBEDDINGS`, `MODEL_SYNC`
- `WorkerStatus`: `IDLE`, `RUNNING`, `ERROR`

**State Fields:**
Each worker's state includes:
- `status`: `WorkerStatus.IDLE`, `WorkerStatus.RUNNING`, or `WorkerStatus.ERROR`
- `current_task_id`: UUID of the active task
- `progress_percent`: 0-100 completion percentage
- `current_file`: Name of the file currently being processed
- `error`: Error message if the task failed

### 2. BaseWorker (`base.py`)
`BaseWorker` is an abstract base class that all specialized workers must inherit from. It defines the contract for task execution.

**Interface:**
```python
class BaseWorker:
    def __init__(self, db: DatabaseService, dispatcher: TaskDispatcher):
        self.db = db
        self.dispatcher = dispatcher

    @abstractmethod
    def process(self, task: dict) -> None:
        """Execute the worker's specific logic."""
        pass
```

Workers receive both a database service (for persistent data operations) and a reference to the dispatcher (for reporting progress and state updates).

### 3. Worker Implementations (`workers/`)

The system includes several specialized workers, categorized by their function:

#### Discovery Workers
Scan sources to identify files that need processing:
- **`SigmaRefDiscoveryWorker`**: Discovers Sigma rule references from official repositories.
- **`GithubDiscoveryWorker`**: Scans configured GitHub repositories for relevant files.
- **`LocalDiscoveryWorker`**: Monitors local directories for new or modified files.

#### Embedding Workers
Process discovered files into vector embeddings for the RAG system:
- **`SigmaRefEmbeddingWorker`**: Embeds Sigma rule reference documents.
- **`GithubEmbeddingWorker`**: Embeds files discovered from GitHub repositories.
- **`LocalEmbeddingWorker`**: Embeds files from local directories.

These workers inherit from `EmbeddingWorker` (`embedding_base.py`), which provides shared logic for:
- File reading and text extraction
- Document metadata construction
- Progress tracking and status updates
- Error handling and logging

Each embedding worker defines a `worker_type` class attribute using the `WorkerName` enum (e.g., `worker_type = WorkerName.SIGMAREF_EMBEDDINGS`).

#### Utility Workers
- **`ModelSyncWorker`**: Scans the filesystem for LLM and embedding model files (GGUF format) and updates the internal registry. Uses `WorkerName.MODEL_SYNC` and `WorkerStatus` for state reporting.

## Execution Flow

1. **Task Submission**: An API endpoint calls `dispatcher.queue_task(WorkerName.X, task_dict)`.
2. **Queue Polling**: The dispatcher's background thread picks up the task from the queue.
3. **State Update**: The dispatcher sets the worker's status to `WorkerStatus.RUNNING` and records the task ID.
4. **Execution**: The task is submitted to the `ThreadPoolExecutor`, which invokes `worker.process(task)`.
5. **Progress Reporting**: During execution, the worker calls `self.dispatcher.update_worker_state()` to report progress (e.g., percentage complete, current file).
6. **Completion**: 
   - On success: The worker finishes, and the dispatcher marks the status as `WorkerStatus.IDLE`.
   - On failure: The exception is caught, logged, and the error message is stored in the worker's state.
7. **Database Flush**: After task completion, the dispatcher flushes any cached database writes via `BufferedDatabaseService`.

## API Integration

API routes interact with the worker system through the `TaskDispatcher` instance stored in `app.state.dispatcher`:

- **Triggering Workers**: Routes call `dispatcher.queue_task(WorkerName.X, task_dict)` to start background jobs.
- **Checking Status**: Routes call `dispatcher.is_worker_busy(WorkerName.X)` to prevent concurrent execution of the same worker.
- **Monitoring**: Routes call `dispatcher.get_all_worker_states()` to retrieve the current status of all workers for the frontend dashboard.

## Configuration

- **Poll Interval**: Time in seconds the dispatcher waits between queue checks (default: 1.0s).
- **Max Workers**: Number of concurrent tasks allowed in the thread pool (default: 1).
- **Journal Path**: Location of the crash recovery journal (`data/worker_journal.log`).
