# SigmaHQ RAG - Performance Optimization Guide

## Overview
This guide provides comprehensive strategies for optimizing the performance of the SigmaHQ RAG application.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Application Configuration](#application-configuration)
3. [LM Studio Optimization](#lm-studio-optimization)
4. [Database Performance](#database-performance)
5. [RAG Pipeline Optimization](#rag-pipeline-optimization)
6. [Memory Management](#memory-management)
7. [Network Optimization](#network-optimization)
8. [Monitoring and Profiling](#monitoring-and-profiling)
9. [Production Deployment](#production-deployment)

## System Requirements

### Minimum Requirements
- **CPU**: 4 cores (8+ recommended)
- **RAM**: 8GB (16GB+ recommended)
- **Storage**: 50GB SSD (100GB+ recommended)
- **Network**: 100Mbps bandwidth

### Recommended Requirements
- **CPU**: 8+ cores with AVX2 support
- **RAM**: 32GB+ (64GB for large document collections)
- **Storage**: 500GB+ NVMe SSD
- **Network**: 1Gbps bandwidth

### GPU Requirements (Optional)
- **NVIDIA GPU**: RTX 3080 or better
- **VRAM**: 12GB+ recommended
- **CUDA**: Version 11.8 or higher

## Application Configuration

### Performance Settings
```json
{
  "performance": {
    "memory_limit_mb": 4096,
    "max_concurrent_requests": 20,
    "cache_ttl": 7200,
    "enable_caching": true,
    "batch_size": 32,
    "worker_threads": 8
  },
  "llm": {
    "timeout": 120,
    "retries": 3,
    "retry_delay": 1.0,
    "streaming": true
  },
  "rag": {
    "chunk_size": 1500,
    "chunk_overlap": 200,
    "similarity_threshold": 0.75,
    "max_results": 15,
    "batch_processing": true
  }
}
```

### Environment Variables
```bash
# Memory Management
PYTHONMALLOC=malloc
MALLOC_ARENA_MAX=2

# Performance Tuning
UV_THREADPOOL_SIZE=16
PYTHONOPTIMIZE=1

# Caching
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0

# Database
SQLITE_CACHE_SIZE=10000
SQLITE_JOURNAL_MODE=WAL
```

## LM Studio Optimization

### Model Selection
- **Chat Models**: Use quantized models for faster inference
- **Embedding Models**: Choose models optimized for speed vs. accuracy
- **Model Size**: Balance model size with available memory

### LM Studio Configuration
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 1234,
    "cors_enabled": true,
    "ssl_enabled": false
  },
  "models": {
    "chat": {
      "model": "mistralai/ministral-3-14b-reasoning",
      "quantization": "q4_0",
      "gpu_layers": 20
    },
    "embedding": {
      "model": "text-embedding-all-minilm-l6-v2-embedding",
      "quantization": "q4_0",
      "batch_size": 32
    }
  }
}
```

### Performance Tips
1. **GPU Acceleration**: Enable GPU layers for faster inference
2. **Model Quantization**: Use quantized models to reduce memory usage
3. **Batch Processing**: Process multiple requests simultaneously
4. **Connection Pooling**: Reuse connections to reduce overhead

## Database Performance

### SQLite Optimization
```sql
-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;

-- Increase cache size
PRAGMA cache_size=10000;

-- Optimize for large datasets
PRAGMA temp_store=memory;
PRAGMA mmap_size=268435456;
```

### Database Configuration
```json
{
  "database": {
    "url": "sqlite:///data/sigmahq.db",
    "timeout": 60,
    "pool_size": 20,
    "max_overflow": 40,
    "echo": false,
    "connect_args": {
      "check_same_thread": false,
      "timeout": 30
    }
  }
}
```

### Indexing Strategy
```sql
-- Create indexes for frequently queried fields
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

## RAG Pipeline Optimization

### Document Processing
```python
# Optimize chunking strategy
chunk_size = 1500  # Balance between context and performance
chunk_overlap = 200  # Ensure context continuity
max_concurrent_processing = 4  # Limit concurrent processing

# Use efficient text splitters
from langchain.text_splitter import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    separators=["\n\n", "\n", ".", " ", ""]
)
```

### Vector Search Optimization
```python
# Optimize similarity search
similarity_threshold = 0.75  # Balance precision and recall
max_results = 15  # Limit results for faster response
search_type = "similarity"  # Use appropriate search type

# Use efficient vector stores
from chromadb import Client
client = Client(
    settings=Settings(
        chroma_db_impl="sqlite",
        persist_directory="data/chroma"
    )
)
```

### Caching Strategy
```python
# Implement multi-level caching
from functools import lru_cache
import redis

# LRU cache for expensive operations
@lru_cache(maxsize=1000)
def expensive_operation(input):
    return result

# Redis cache for distributed caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)
redis_client.setex("key", 3600, "value")  # Cache for 1 hour
```

## Memory Management

### Memory Monitoring
```python
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    print(f"CPU: {psutil.cpu_percent()}%")
    
    # Force garbage collection
    gc.collect()
```

### Memory Optimization
```python
# Use generators for large datasets
def process_large_dataset():
    for item in large_dataset:
        yield process_item(item)

# Clear unused variables
del large_variable
gc.collect()

# Use memory mapping for large files
import mmap
with open('large_file.txt', 'r') as f:
    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
        # Process file without loading into memory
        pass
```

### Memory Limits
```json
{
  "memory_limits": {
    "max_memory_usage": "80%",
    "gc_threshold": 100000000,  # 100MB
    "memory_warning_threshold": "70%",
    "memory_critical_threshold": "90%"
  }
}
```

## Network Optimization

### Connection Management
```python
import aiohttp
from aiohttp import ClientSession, TCPConnector

# Configure connection pool
connector = TCPConnector(
    limit=100,  # Max connections
    limit_per_host=10,  # Max connections per host
    ttl_dns_cache=300,  # DNS cache TTL
    use_dns_cache=True
)

async with ClientSession(connector=connector) as session:
    # Make requests with connection pooling
    pass
```

### Request Optimization
```python
# Use async requests for better performance
import asyncio
import aiohttp

async def fetch_data(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return responses

# Implement request retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def reliable_request(session, url):
    async with session.get(url) as response:
        return await response.json()
```

## Monitoring and Profiling

### Performance Metrics
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        print(f"{func.__name__}: {end_time - start_time:.2f}s")
        return result
    return wrapper

@monitor_performance
def process_query(query):
    # Process query
    pass
```

### Profiling Tools
```python
import cProfile
import pstats

# Profile function execution
def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Execute function
    process_query("test query")
    
    profiler.disable()
    
    # Save and analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

### Monitoring Dashboard
```python
# Create performance dashboard
import matplotlib.pyplot as plt
import pandas as pd

def create_performance_dashboard(metrics):
    df = pd.DataFrame(metrics)
    
    # Response time chart
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 2, 1)
    plt.plot(df['timestamp'], df['response_time'])
    plt.title('Response Time')
    
    # Memory usage chart
    plt.subplot(2, 2, 2)
    plt.plot(df['timestamp'], df['memory_usage'])
    plt.title('Memory Usage')
    
    # Request count chart
    plt.subplot(2, 2, 3)
    plt.plot(df['timestamp'], df['request_count'])
    plt.title('Request Count')
    
    plt.tight_layout()
    plt.savefig('performance_dashboard.png')
```

## Production Deployment

### Load Balancing
```yaml
# Docker Compose with load balancing
version: '3.8'
services:
  app:
    image: sigmahqrag:production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    ports:
      - "8000:8000"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Auto-scaling
```yaml
# Kubernetes auto-scaling configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sigmahqrag-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sigmahqrag
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Monitoring Stack
```yaml
# Prometheus and Grafana setup
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Performance Testing
```python
# Load testing with Locust
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def chat_query(self):
        self.client.post("/api/chat/send", json={
            "message": "What is machine learning?",
            "session_id": "test-session"
        })
    
    @task
    def upload_document(self):
        with open("test.pdf", "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            self.client.post("/api/documents/upload", files=files)
```

## Best Practices

### Code Optimization
1. **Use async/await**: Implement asynchronous operations where possible
2. **Batch operations**: Process multiple items together
3. **Lazy loading**: Load data only when needed
4. **Caching**: Implement multi-level caching strategy
5. **Connection pooling**: Reuse database and HTTP connections

### Deployment Optimization
1. **Container optimization**: Use multi-stage builds and minimal base images
2. **Resource allocation**: Properly size containers and VMs
3. **Monitoring**: Implement comprehensive monitoring and alerting
4. **Auto-scaling**: Configure auto-scaling based on metrics
5. **CDN**: Use CDN for static assets and document storage

### Maintenance
1. **Regular updates**: Keep dependencies and models updated
2. **Performance reviews**: Regularly review and optimize performance
3. **Capacity planning**: Monitor usage patterns and plan capacity
4. **Backup strategies**: Implement efficient backup and recovery
5. **Security updates**: Apply security patches promptly

This performance optimization guide provides comprehensive strategies for maximizing the performance of your SigmaHQ RAG application in production environments.