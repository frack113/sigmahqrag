from pathlib import Path

from sigma import (
    load_sigma_rules,
    chunk_sigma_rules_rich,
    build_ragas_dataset,
    save_ragas_dataset_json,
)

from sigma.embed_dataset import embed_json_dataset_file


project_root = Path(__file__).resolve().parents[4]
sigma_dir = project_root / "src/back/rag/transforms/sigma"

rules = load_sigma_rules(str("/home/yaya/GitRepos/sigma"))

chunks = []
for rule in rules:
    chunks.extend(chunk_sigma_rules_rich(rule))

dataset = build_ragas_dataset(chunks)

ragas_path = sigma_dir / "ragas_dataset.json"
embedded_path = sigma_dir / "dataset_embedded.json"

save_ragas_dataset_json(dataset, ragas_path)

print("rules:", len(rules))
print("chunks:", len(chunks))
print("dataset rows:", len(dataset))
print("saved dataset:", ragas_path)

embed_json_dataset_file(
    input_path=ragas_path,
    output_path=embedded_path,
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    batch_size=32,
    limit=None,
)

print("saved embedded dataset:", embedded_path)
