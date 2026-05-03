# Admin Panel: Backend Configuration

## 1. Configuration
- **OS and GPU Choices**
  - Detected OS: Windows
  - Supported GPUs:
    - `cpu`
    - `cuda`
    - `hip`
    - `vulkan`
  
  ### Config Management
  - Get current config:
    ```bash
    GET /admin/llama/config
    ```
  - Set config:
    ```json
    {
      "os": "windows",
      "gpu": "cuda"
    }
    ```

## 2. llama.cpp Management
- **Status** (from System Dashboard):
  - Endpoint: `GET /admin/health`
  
  ### Version
  - Installed Version:
    ```json
    {
      "current_version": "b3084",
      "update_available": true,
      "latest_version": "b3090"
    }
    ```
  - **Download/Update Commands:**
    - `POST /admin/llama/download`
    - `POST /admin/llama/update`

## 3. Qdrant Management
- **Status** (from System Dashboard):
  - Endpoint: `GET /admin/health`
  
  ### Version
  - Installed Version:
    - (Placeholder: Add actual version details)
  - Get status:
    ```bash
    GET /admin/backend/?action=status&service=qdrant
    ```

## Backend Integration
- **Merged Endpoints:**
  - Get backend status:
    ```bash
    GET /admin/backend/?action=status
    ```
  - Download service (llama.cpp or Qdrant):
    ```bash
    POST /admin/backend/?action=download&service=llama|qdrant&version=latest
    ```
  
  - Start/Stop services:
    ```bash
    POST /admin/services/?action=start|stop&service=llama|qdrant
    ```
  - Retrieve logs:
    ```bash
    GET /admin/services/?action=logs&service=llama|qdrant
    ```

## API References
- **Llama.cpp Management:**
  - `/admin/llama/info` (GET)
  - `/admin/llama/config` (GET/POST)
  - `/admin/llama/download` (POST)
  - `/admin/llama/update` (POST)

- **Qdrant Management:**
  - `/admin/backend/?action=status&service=qdrant` (GET)
  - `/admin/services/?action=start|stop&service=qdrant` (POST/GET)