from enum import Enum


class WorkerStatus(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    ERROR = "error"


class WorkerName(Enum):
    SIGMAREF_DISCOVERY = "sigmaref_discovery"
    GITHUB_DISCOVERY = "github_discovery"
    LOCAL_DISCOVERY = "local_discovery"
    SIGMAREF_EMBEDDINGS = "sigmaref_embeddings"
    GITHUB_EMBEDDINGS = "github_embeddings"
    LOCAL_EMBEDDINGS = "local_embeddings"
    MODEL_SYNC = "model_sync"
    LOCAL_REPO_SYNC = "local_repo_sync"
    DOC_GC = "doc_gc"
