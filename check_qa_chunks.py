"""Check how many Q&A chunks are created for ask_spec.md and if they're in Qdrant."""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Count Q&A pairs in the file
qa_path = Path("AskRag/ask_spec.md")
content = qa_path.read_text(encoding="utf-8")
qa_pattern = re.compile(r"\*\*Q:\*\*\s*(.+?)\n\*\*A:\*\*\s*(.+?)(?=\n\*\*|\Z)", re.DOTALL)
matches = qa_pattern.findall(content)
print(f"Q&A pairs in ask_spec.md: {len(matches)}")

# Check specific questions exist as patterns
for idx, (q, a) in enumerate(matches, 1):
    q_clean = q.strip()
    if idx in [43, 74, 126, 150]:
        print(f"\n[{idx}] Q: {q_clean[:80]}")
        print(f"    A preview: {a.strip()[:80]}")

# Now check what chunks are actually indexed in Qdrant for sigma_spec
print("\n--- Checking Qdrant sigma_spec collection ---")
try:
    from src.infrastructure.vectorstore import QdrantVectorService
    svc = QdrantVectorService(collection_name="sigma_spec")
    count = svc.count()
    print(f"Total points in sigma_spec: {count}")
    
    # Try a direct search for "maps key value pairs evaluated"
    results = svc.search("How are maps key/value pairs evaluated", limit=5)
    print(f"\nTop results for 'maps (key/value pairs)':")
    for r in results[:3]:
        text_preview = r.get("text", "")[:120]
        score = r.get("score", 0)
        meta = r.get("metadata", {})
        chunk_type = meta.get("chunk_type", "?")
        print(f"  Score={score:.4f} type={chunk_type}: {text_preview}")
except Exception as e:
    print(f"Error: {e}")
