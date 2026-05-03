# Admin UI Migration - Complete

## Pages

| Path | Description |
|------|-------------|
| GET /admin | Dashboard (status + services) |
| GET /admin/models | Models management |
| GET /admin/settings | Settings |
| GET /admin/health | Health check |
| GET /admin/logs | Logs |
| GET /admin/llama | llama.cpp management |
| GET /admin/qdrant | Qdrant management |
| GET /admin/prompts | System prompts |

## API Endpoints Used

### Admin Service
- `/admin/health` - Get all services status
- `/admin/services/?action=start|stop|logs&service=llama|qdrant`

### llama.cpp
- `/admin/llama/config` (GET/POST)
- `/admin/llama/info` (GET)
- `/admin/llama/download` (POST)
- `/admin/llama/update` (POST)

### Backend
- `/admin/backend/?action=download&service=llama|qdrant`
- `/admin/backend/?action=status`

### Models
- `/api/v1/admin/models` (GET)
- `/api/v1/admin/models/delete` (POST)
- `/admin/llm/?action=list|installed`

### Prompts
- `/admin/prompts/` (GET/POST)
- `/admin/prompts/active` (GET)