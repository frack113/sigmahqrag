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
    SPEC_DISCOVERY = "spec_discovery"
    MODEL_SYNC = "model_sync"
    LOCAL_REPO_SYNC = "local_repo_sync"
    DOC_GC = "doc_gc"
