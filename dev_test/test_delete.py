import httpx, subprocess, time, sys, os

# Set the secret for testing
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"

from src.auth.security import create_access_token
from src.auth.models import UserRole

# Create a token for an admin user
token = create_access_token({"sub": "admin", "role": UserRole.ADMIN})
headers = {"Authorization": f"Bearer {token}"}

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8007"],
    cwd=r"D:\rootme\sigmahqrag", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, env=os.environ.copy()
)
time.sleep(6)

try:
    print("=== Test DELETE /llm/Qwen/Qwen3-8B-GGUF ===")
    r = httpx.delete("http://127.0.0.1:8007/llm/Qwen/Qwen3-8B-GGUF", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
    
except Exception as e:
    print(f"Error during test: {e}")
    stderr = proc.stderr.read()
    if stderr:
        print(f"Server Stderr:\n{stderr}")
    
finally:
    proc.terminate()
    proc.wait()