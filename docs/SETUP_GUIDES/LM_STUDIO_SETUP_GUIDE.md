# LM Studio Setup Guide

Complete setup instructions for LM Studio integration with the SigmaHQ RAG application.

## Alternative: CPU-based Embeddings (Recommended)

**Note**: The SigmaHQ RAG application now supports CPU-based embeddings that work without any external dependencies. This is the recommended approach for most users.

### Quick Start (No Setup Required)
1. Install the application: `uv sync`
2. Run the application: `uv run python main.py`
3. Access at `http://localhost:8000`

**Benefits of CPU-based embeddings:**
- ✅ Zero setup required
- ✅ Works offline
- ✅ 100% uptime guarantee
- ✅ No external dependencies
- ✅ Privacy-focused (all processing local)

For most users, CPU-based embeddings provide excellent performance and reliability. Continue reading this guide only if you need enhanced performance with local LLMs or have specific model requirements.

## Overview

LM Studio provides local LLM and embedding model serving capabilities that power the SigmaHQ RAG system. This guide covers installation, model setup, and configuration.

## Installation

### 1. Download and Install LM Studio

1. Visit [LM Studio](https://lmstudio.ai/) and download the appropriate version for your operating system
2. Install the application following the platform-specific instructions
3. Launch LM Studio

### 2. Required Models

The SigmaHQ RAG system requires two models:

#### Chat Model
- **Model**: `mistralai/ministral-3-14b-reasoning`
- **Purpose**: Generate responses to user queries
- **Download**: Search for "ministral-3-14b-reasoning" in LM Studio's model hub
- **Load**: Click "Download" and wait for completion

#### Embedding Model
- **Model**: `text-embedding-all-minilm-l6-v2-embedding`
- **Purpose**: Generate vector embeddings for document processing
- **Download**: Search for "text-embedding-all-minilm-l6-v2-embedding" in LM Studio's model hub
- **Load**: Click "Download" and wait for completion

### 3. Server Configuration

1. **Open Server Settings**:
   - Click the "Server" icon in the left sidebar
   - Or navigate to Settings → Server

2. **Configure Server**:
   - **Host**: `localhost`
   - **Port**: `1234`
   - **Enable CORS**: Check this option
   - **Enable SSL**: Uncheck (unless you have specific SSL requirements)

3. **Start Server**:
   - Click "Start Server"
   - Verify the server status shows "Running"

### 4. Model Loading

1. **Load Chat Model**:
   - Go to the "Local Models" tab
   - Find `mistralai/ministral-3-14b-reasoning`
   - Click "Load" to load it into memory

2. **Load Embedding Model**:
   - Go to the "Local Models" tab
   - Find `text-embedding-all-minilm-l6-v2-embedding`
   - Click "Load" to load it into memory

## Configuration

### Environment Variables

Set these environment variables in your `.env` file:

```env
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://localhost:1234/v1
```

### Model Parameters

For optimal performance with the SigmaHQ RAG system:

#### Chat Model Settings
- **Temperature**: 0.7 (for chat service)
- **Max Tokens**: 5000
- **Top P**: 0.9

#### Application Configuration (`data/config.json`)
```json
{
  "llm": {
    "base_url": "http://localhost:1234",
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000
  }
}
```

## Troubleshooting

### Common Issues

#### Server Won't Start
- **Check Port**: Ensure port 1234 is not in use by another application
- **Firewall**: Check if your firewall is blocking LM Studio
- **Permissions**: Ensure LM Studio has necessary permissions

#### Models Won't Load
- **Memory**: Check if you have sufficient RAM (recommended: 16GB+)
- **Disk Space**: Ensure sufficient disk space for model files
- **Corruption**: Try re-downloading the model

#### Connection Errors
- **URL**: Verify `http://localhost:1234/v1` is correct
- **Server Status**: Ensure LM Studio server is running
- **Network**: Check network connectivity

### Performance Optimization

#### Memory Management
- **Close Other Applications**: Free up RAM before loading models
- **Model Quantization**: Consider using quantized versions if available

## Verification

### Test Connection

Use this Python script to verify LM Studio integration:

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# Test chat completion
response = client.chat.completions.create(
    model="mistralai/ministral-3-14b-reasoning",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
print(response.choices[0].message.content)

# Test embeddings
embedding = client.embeddings.create(
    model="text-embedding-all-minilm-l6-v2-embedding",
    input="Hello world"
)
print(f"Embedding dimension: {len(embedding.data[0].embedding)}")
```

### Expected Output
- Chat completion should return a response
- Embedding should return a vector with appropriate dimensions
- No connection errors should occur

## Support

For additional support:
- [LM Studio Documentation](https://docs.lmstudio.ai/)
- [LM Studio Community](https://community.lmstudio.ai/)
- [SigmaHQ RAG Issues](https://github.com/frack113/sigmahqrag/issues)

## Notes

- Always keep LM Studio updated to the latest version
- Monitor system resources during heavy usage
- Consider using dedicated hardware for production deployments
- Regularly backup your model configurations