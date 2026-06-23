import json
import re
import sys
from pathlib import Path

import requests
import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


# =========================
# Config
# =========================

QDRANT_URL = "http://localhost:6333"

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

EMBED_MODEL = "mxbai-embed-large"
LLM_MODEL = "gemma4:e4b"

SPEC_COLLECTION_NAME = "ask_spec_collection"

# Nom demandé, conservé tel quel.
RULES_COLLECTION_NAME = "rules_simga_collection"

VECTOR_SIZE = 1024

SPEC_INPUT_FILE = Path("Texte collé(6).txt")

RULES_BATCH_SIZE = 32
MAX_EMBED_CHARS = 2000

client = QdrantClient(url=QDRANT_URL)


# =========================
# Qdrant
# =========================

def ensure_collection(collection_name: str) -> None:
    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        print(f"Collection créée : {collection_name}")
    else:
        print(f"Collection déjà existante : {collection_name}")


# =========================
# Utils
# =========================

def truncate_for_embedding(text: str, max_chars: int = MAX_EMBED_CHARS) -> str:
    text = text.strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[TRUNCATED_FOR_EMBEDDING]"


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {path}. "
            "Place le fichier dans le même dossier que main.py "
            "ou modifie SPEC_INPUT_FILE."
        )

    return path.read_text(encoding="utf-8")


# =========================
# Chunking Spec H2
# =========================

def chunk_by_h2(text: str) -> list[dict]:
    pattern = re.compile(
        r"^##\s+(.+?)\s*$",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))
    chunks = []

    for index, match in enumerate(matches):
        section_title = match.group(1).strip()

        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        section_text = text[start:end].strip()

        chunks.append(
            {
                "chunk_type": "h2_section",
                "title": section_title,
                "text": section_text,
                "embedding_text": truncate_for_embedding(section_text),
                "metadata": {
                    "chunk_type": "h2_section",
                    "section_level": "h2",
                    "section_title": section_title,
                    "chunk_index": index,
                },
            }
        )

    return chunks


# =========================
# Chunking Spec Q/A
# =========================

def extract_current_h2(text_before: str) -> str | None:
    h2_titles = re.findall(
        r"^##\s+(.+?)\s*$",
        text_before,
        flags=re.MULTILINE,
    )

    return h2_titles[-1].strip() if h2_titles else None


def extract_current_h3(text_before: str) -> str | None:
    h3_titles = re.findall(
        r"^###\s+(.+?)\s*$",
        text_before,
        flags=re.MULTILINE,
    )

    return h3_titles[-1].strip() if h3_titles else None


def chunk_by_qa(text: str) -> list[dict]:
    pattern = re.compile(
        r"\*\*Q:\*\*\s*(?P<question>.*?)\n"
        r"\*\*A:\*\*\s*(?P<answer>.*?)(?=\n\*\*Q:\*\*|\n###\s+|\n##\s+|\Z)",
        re.DOTALL,
    )

    chunks = []

    for index, match in enumerate(pattern.finditer(text)):
        question = match.group("question").strip()
        answer = match.group("answer").strip()

        text_before = text[: match.start()]

        h2 = extract_current_h2(text_before)
        h3 = extract_current_h3(text_before)

        chunk_text = f"Question: {question}\nAnswer: {answer}"

        chunks.append(
            {
                "chunk_type": "qa_pair",
                "title": question,
                "text": chunk_text,
                "embedding_text": truncate_for_embedding(chunk_text),
                "metadata": {
                    "chunk_type": "qa_pair",
                    "question": question,
                    "answer": answer,
                    "h2_section": h2,
                    "h3_section": h3,
                    "chunk_index": index,
                },
            }
        )

    return chunks


# =========================
# Ollama
# =========================

def generate_response(prompt: str) -> str:
    response = requests.post(
        OLLAMA_GENERATE_URL,
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=180,
    )

    response.raise_for_status()

    return response.json()["response"]


def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "input": text,
            "truncate": True,
        },
        timeout=180,
    )

    if response.status_code >= 400:
        print("\n[ERROR]: Ollama embedding failed")
        print(f"[ERROR]: Status code: {response.status_code}")
        print(f"[ERROR]: Response body: {response.text}")
        print(f"[ERROR]: Input length chars: {len(text)}")
        print(f"[ERROR]: Input preview: {text[:500]}")
        response.raise_for_status()

    result = response.json()

    return result["embeddings"][0]


# =========================
# Ingestion Spec -> Qdrant
# =========================

def ingest_chunks_to_qdrant(
    chunks: list[dict],
    id_offset: int,
    collection_name: str,
) -> None:
    points = []

    for index, chunk in enumerate(chunks):
        embedding_source = chunk.get("embedding_text") or chunk["text"]

        adjusted_prompt = f"Represent this passage for retrieval: {embedding_source}"

        embedding = embed_text(adjusted_prompt)

        point = PointStruct(
            id=id_offset + index,
            vector=embedding,
            payload={
                "text": chunk["text"],
                "embedding_text": embedding_source,
                "title": chunk["title"],
                **chunk["metadata"],
            },
        )

        points.append(point)

    if not points:
        print(f"Aucun point à insérer dans {collection_name}")
        return

    client.upsert(
        collection_name=collection_name,
        wait=True,
        points=points,
    )

    print(f"{len(points)} chunks insérés dans {collection_name}")


def ingest_spec_file() -> None:
    ensure_collection(SPEC_COLLECTION_NAME)

    text = read_text(SPEC_INPUT_FILE)

    h2_chunks = chunk_by_h2(text)
    qa_chunks = chunk_by_qa(text)

    print(f"H2 chunks trouvés : {len(h2_chunks)}")
    print(f"QA chunks trouvés : {len(qa_chunks)}")

    ingest_chunks_to_qdrant(
        chunks=h2_chunks,
        id_offset=0,
        collection_name=SPEC_COLLECTION_NAME,
    )

    ingest_chunks_to_qdrant(
        chunks=qa_chunks,
        id_offset=10000,
        collection_name=SPEC_COLLECTION_NAME,
    )

    print("\nIngestion spec terminée.")


# =========================
# Chargement règles Sigma
# =========================

def is_sigma_rule(doc: dict) -> bool:
    return (
        isinstance(doc, dict)
        and "title" in doc
        and "id" in doc
        and "logsource" in doc
        and "detection" in doc
    )


def load_sigma_rules(path_str: str) -> list[dict]:
    path = Path(path_str).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"[DEBUG]: Folder not found: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"[DEBUG]: Not a directory: {path}")

    sigma_rules = []
    yaml_files = list(path.rglob("*.yml"))

    print(f"[DEBUG]: YAML files found: {len(yaml_files)}")

    for file_path in yaml_files:
        try:
            with file_path.open(encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))

        except yaml.YAMLError as exc:
            print(f"[WARN]: YAML error in {file_path}: {exc}")
            continue

        except UnicodeDecodeError as exc:
            print(f"[WARN]: Encoding error in {file_path}: {exc}")
            continue

        for doc_index, doc in enumerate(docs):
            if not is_sigma_rule(doc):
                continue

            rule = dict(doc)

            rule["_source_file"] = file_path.name
            rule["_source_path"] = str(file_path)
            rule["_doc_index"] = doc_index

            try:
                rule["_relative_path"] = str(file_path.relative_to(path))
            except ValueError:
                rule["_relative_path"] = str(file_path)

            sigma_rules.append(rule)

    print(f"[DEBUG]: Valid Sigma rules loaded: {len(sigma_rules)}")

    return sigma_rules


# =========================
# Chunking règles Sigma
# =========================

def sigma_rule_to_yaml_text(rule: dict) -> str:
    clean_rule = {
        key: value
        for key, value in rule.items()
        if not key.startswith("_")
    }

    return yaml.safe_dump(
        clean_rule,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def get_logsource_field(rule: dict, field_name: str) -> str | None:
    logsource = rule.get("logsource")

    if not isinstance(logsource, dict):
        return None

    value = logsource.get(field_name)

    if value is None:
        return None

    return str(value)


def chunk_sigma_rules(rules: list[dict]) -> list[dict]:
    """

    """

    chunks = []

    for index, rule in enumerate(rules):
        rule_yaml = sigma_rule_to_yaml_text(rule)

        title = rule.get("title", "Untitled Sigma Rule")
        rule_id = rule.get("id")

        description = rule.get("description")
        level = rule.get("level")
        status = rule.get("status")
        tags = rule.get("tags", [])

        logsource_product = get_logsource_field(rule, "product")
        logsource_category = get_logsource_field(rule, "category")
        logsource_service = get_logsource_field(rule, "service")

        detection = rule.get("detection")
        falsepositives = rule.get("falsepositives")

        full_chunk_text = f"""
Sigma Rule Title: {title}
Sigma Rule ID: {rule_id}
Description: {description}
Status: {status}
Level: {level}
Tags: {tags}
Logsource product: {logsource_product}
Logsource category: {logsource_category}
Logsource service: {logsource_service}
Source path: {rule.get("_relative_path")}

YAML:
{rule_yaml}
""".strip()

        embedding_text = f"""
Sigma Rule Title: {title}
Sigma Rule ID: {rule_id}
Description: {description}
Status: {status}
Level: {level}
Tags: {tags}
Logsource product: {logsource_product}
Logsource category: {logsource_category}
Logsource service: {logsource_service}
False positives: {falsepositives}
Detection:
{detection}
""".strip()

        embedding_text = truncate_for_embedding(embedding_text)

        chunks.append(
            {
                "chunk_type": "sigma_rule",
                "title": title,
                "text": full_chunk_text,
                "embedding_text": embedding_text,
                "metadata": {
                    "chunk_type": "sigma_rule",
                    "rule_id": rule_id,
                    "title": title,
                    "description": description,
                    "status": status,
                    "level": level,
                    "tags": tags,
                    "logsource_product": logsource_product,
                    "logsource_category": logsource_category,
                    "logsource_service": logsource_service,
                    "source_file": rule.get("_source_file"),
                    "source_path": rule.get("_source_path"),
                    "relative_path": rule.get("_relative_path"),
                    "chunk_index": index,
                },
            }
        )

    return chunks


# =========================
# Ingestion règles Sigma -> Qdrant
# =========================

def ingest_rule_chunks_to_qdrant(
    chunks: list[dict],
    collection_name: str,
) -> None:
    ensure_collection(collection_name)

    batch = []
    total_inserted = 0
    total_skipped = 0

    for index, chunk in enumerate(chunks):
        embedding_source = chunk.get("embedding_text") or chunk["text"]

        adjusted_prompt = f"Represent this Sigma rule for retrieval: {embedding_source}"

        try:
            embedding = embed_text(adjusted_prompt)

        except Exception as exc:
            total_skipped += 1

            print("\n[WARN]: Failed to embed rule")
            print(f"[WARN]: Index: {index}")
            print(f"[WARN]: Title: {chunk.get('title')}")
            print(f"[WARN]: Rule ID: {chunk.get('metadata', {}).get('rule_id')}")
            print(f"[WARN]: Path: {chunk.get('metadata', {}).get('relative_path')}")
            print(f"[WARN]: Error: {exc}")

            continue

        rule_id = chunk["metadata"].get("rule_id")

        if rule_id:
            point_id = rule_id
        else:
            point_id = index

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": chunk["text"],
                "embedding_text": embedding_source,
                "title": chunk["title"],
                **chunk["metadata"],
            },
        )

        batch.append(point)

        if len(batch) >= RULES_BATCH_SIZE:
            client.upsert(
                collection_name=collection_name,
                wait=True,
                points=batch,
            )

            total_inserted += len(batch)
            print(f"[DEBUG]: {total_inserted} règles insérées...")

            batch = []

    if batch:
        client.upsert(
            collection_name=collection_name,
            wait=True,
            points=batch,
        )

        total_inserted += len(batch)

    print(f"[DEBUG]: Total règles insérées dans {collection_name}: {total_inserted}")
    print(f"[DEBUG]: Total règles ignorées: {total_skipped}")


def load_rules_step(path_str: str) -> None:
    rules = load_sigma_rules(path_str)

    print("\n--- Exemples de règles chargées ---")

    for rule in rules[:5]:
        print("")
        print(f"Title: {rule.get('title')}")
        print(f"ID: {rule.get('id')}")
        print(f"Path: {rule.get('_relative_path')}")
        print(f"Logsource: {rule.get('logsource')}")
        print(f"Tags: {rule.get('tags')}")

    chunks = chunk_sigma_rules(rules)

    print("\n--- Résumé ---")
    print(f"Règles chargées: {len(rules)}")
    print(f"Chunks générés: {len(chunks)}")


def ingest_rules_step(path_str: str) -> None:
    rules = load_sigma_rules(path_str)

    chunks = chunk_sigma_rules(rules)

    print("\n--- Ingestion règles Sigma ---")
    print(f"Règles chargées: {len(rules)}")
    print(f"Chunks générés: {len(chunks)}")
    print(f"Collection cible: {RULES_COLLECTION_NAME}")

    ingest_rule_chunks_to_qdrant(
        chunks=chunks,
        collection_name=RULES_COLLECTION_NAME,
    )

    print("\nIngestion règles Sigma terminée.")


# =========================
# Routeur
# =========================

def extract_json_from_llm_output(raw: str) -> dict:
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)

    if not match:
        return {
            "route": "unknown",
            "reason": "Impossible de parser la réponse du routeur.",
        }

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {
            "route": "unknown",
            "reason": "JSON invalide retourné par le routeur.",
        }


def classify_question_with_llm(question: str) -> dict:
    prompt = f"""
Tu es un routeur pour un système RAG Sigma.

Tu dois classer la question utilisateur dans UNE SEULE catégorie :

spec_only:
La question demande comment comprendre Sigma, sa syntaxe, ses champs,
logsource, detection, condition, modifiers, category, product, service, etc.

rules_only:
La question demande de chercher, lister, filtrer ou retrouver des règles Sigma
dans une base de règles.

both:
La question demande d'expliquer, analyser, interpréter ou comparer des règles Sigma.
Elle nécessite à la fois la spec Sigma et les règles Sigma.

unknown:
La question est ambiguë ou ne concerne pas Sigma.

Réponds uniquement avec un JSON valide au format :
{{"route": "spec_only|rules_only|both|unknown", "reason": "raison courte"}}

Question utilisateur:
{question}
"""

    raw = generate_response(prompt)

    data = extract_json_from_llm_output(raw)

    route = data.get("route", "unknown")
    reason = data.get("reason", "")

    if route not in {"spec_only", "rules_only", "both", "unknown"}:
        route = "unknown"
        reason = "Route invalide retournée par le LLM."

    return {
        "route": route,
        "reason": reason,
    }


# =========================
# Retrieval
# =========================

def search_relevant_passages(
    prompt: str,
    collection_name: str,
    limit: int = 5,
) -> list:
    adjusted_prompt = f"Represent this sentence for searching relevant passages: {prompt}"

    embedding = embed_text(adjusted_prompt)

    results = client.query_points(
        collection_name=collection_name,
        query=embedding,
        with_payload=True,
        limit=limit,
    )

    return results.points


def format_spec_results(points: list) -> str:
    formatted = []

    for index, point in enumerate(points, start=1):
        formatted.append(
            f"""
[SPEC RESULT {index}]
Collection: {SPEC_COLLECTION_NAME}
Type: {point.payload.get('chunk_type')}
Title: {point.payload.get('title')}
Section H2: {point.payload.get('h2_section') or point.payload.get('section_title')}
Section H3: {point.payload.get('h3_section')}

Text:
{point.payload.get('text')}
[/SPEC RESULT {index}]
""".strip()
        )

    return "\n\n".join(formatted)


def format_rules_results(points: list) -> str:
    formatted = []

    for index, point in enumerate(points, start=1):
        formatted.append(
            f"""
[RULE RESULT {index}]
Collection: {RULES_COLLECTION_NAME}
Rule title: {point.payload.get('title')}
Rule ID: {point.payload.get('rule_id')}
Level: {point.payload.get('level')}
Status: {point.payload.get('status')}
Tags: {point.payload.get('tags')}
Logsource product: {point.payload.get('logsource_product')}
Logsource category: {point.payload.get('logsource_category')}
Logsource service: {point.payload.get('logsource_service')}
Source path: {point.payload.get('relative_path')}

YAML:
{point.payload.get('text')}
[/RULE RESULT {index}]
""".strip()
        )

    return "\n\n".join(formatted)


# =========================
# Réponses RAG
# =========================

def answer_with_spec_rag(prompt: str) -> str:
    if not client.collection_exists(collection_name=SPEC_COLLECTION_NAME):
        return (
            f"La collection {SPEC_COLLECTION_NAME} n'existe pas encore. "
            "Lance d'abord : uv run main.py ingest_spec"
        )

    spec_results = search_relevant_passages(
        prompt=prompt,
        collection_name=SPEC_COLLECTION_NAME,
        limit=5,
    )

    spec_context = format_spec_results(spec_results)

    updated_prompt = f"""
Tu es un assistant spécialisé dans la spécification Sigma.

Tu as reçu des passages récupérés depuis la collection de spécification Sigma :
- Collection : {SPEC_COLLECTION_NAME}
- Contenu : documentation, syntaxe, champs, modifiers, logsource, detection, condition, etc.

Réponds à la question utilisateur uniquement à partir des passages récupérés.

Règles strictes :
- N'invente pas d'information absente des passages.
- Si les passages ne contiennent pas la réponse, dis clairement que tu ne sais pas.
- Réponds en français.

Objectif :
- Donne une réponse claire et pédagogique.
- Explique le rôle du concept demandé.
- Donne un exemple YAML seulement si les passages récupérés en contiennent ou permettent clairement d'en construire un.
- Mentionne les champs importants.

<retrieved-spec-data>
{spec_context}
</retrieved-spec-data>

<user-question>
{prompt}
</user-question>
"""

    return generate_response(updated_prompt)


def answer_with_rules_rag(prompt: str) -> str:
    if not client.collection_exists(collection_name=RULES_COLLECTION_NAME):
        return (
            f"La collection {RULES_COLLECTION_NAME} n'existe pas encore. "
            "Lance d'abord : uv run main.py ingest_rules ~/GitRepos/sigma"
        )

    rules_results = search_relevant_passages(
        prompt=prompt,
        collection_name=RULES_COLLECTION_NAME,
        limit=5,
    )

    print("\n--- DEBUG retrieved rules ---")
    for point in rules_results:
        print(f"Title: {point.payload.get('title')}")
        print(f"ID: {point.payload.get('rule_id')}")
        print(f"Path: {point.payload.get('relative_path')}")
        print("---")

    rules_context = format_rules_results(rules_results)

    updated_prompt = f"""
Tu es un assistant spécialisé dans les règles Sigma.

Tu dois répondre UNIQUEMENT à partir des règles récupérées dans la collection Qdrant.

Collection utilisée :
- Nom : {RULES_COLLECTION_NAME}
- Type : collection de règles Sigma YAML réelles

Règles strictes :
- N'invente jamais de règle Sigma.
- N'invente jamais d'ID.
- N'invente jamais de YAML.
- Ne crée pas d'exemples génériques.
- Utilise uniquement les titres, IDs, chemins, tags, logsource et YAML présents dans <retrieved-rules-data>.
- Si aucune règle récupérée ne répond clairement à la question, dis-le.
- Ne modifie pas le YAML des règles récupérées.
- Ne présente pas une règle comme réelle si elle n'apparaît pas dans les données récupérées.

Format de réponse attendu :
Pour chaque règle pertinente :
1. Titre
2. ID
3. Chemin source
4. Pourquoi elle est pertinente
5. Extrait YAML court, uniquement copié depuis les données récupérées

Question utilisateur :
{prompt}

<retrieved-rules-data>
{rules_context}
</retrieved-rules-data>
"""

    return generate_response(updated_prompt)


def answer_with_both_rag(prompt: str) -> str:
    if not client.collection_exists(collection_name=SPEC_COLLECTION_NAME):
        return (
            f"La collection {SPEC_COLLECTION_NAME} n'existe pas encore. "
            "Lance d'abord : uv run main.py ingest_spec"
        )

    if not client.collection_exists(collection_name=RULES_COLLECTION_NAME):
        return (
            f"La collection {RULES_COLLECTION_NAME} n'existe pas encore. "
            "Lance d'abord : uv run main.py ingest_rules ~/GitRepos/sigma"
        )

    spec_results = search_relevant_passages(
        prompt=prompt,
        collection_name=SPEC_COLLECTION_NAME,
        limit=5,
    )

    rules_results = search_relevant_passages(
        prompt=prompt,
        collection_name=RULES_COLLECTION_NAME,
        limit=5,
    )

    print("\n--- DEBUG retrieved spec ---")
    for point in spec_results:
        print(f"Title: {point.payload.get('title')}")
        print(f"Type: {point.payload.get('chunk_type')}")
        print("---")

    print("\n--- DEBUG retrieved rules ---")
    for point in rules_results:
        print(f"Title: {point.payload.get('title')}")
        print(f"ID: {point.payload.get('rule_id')}")
        print(f"Path: {point.payload.get('relative_path')}")
        print("---")

    spec_context = format_spec_results(spec_results)
    rules_context = format_rules_results(rules_results)

    updated_prompt = f"""
Tu es un assistant spécialisé dans Sigma.

Tu as reçu deux types de contexte provenant de deux collections différentes :

1. Collection de spécification Sigma :
- Nom : {SPEC_COLLECTION_NAME}
- Rôle : expliquer la syntaxe Sigma, les champs, logsource, detection, condition, modifiers, tags, taxonomy, etc.

2. Collection de règles Sigma :
- Nom : {RULES_COLLECTION_NAME}
- Rôle : fournir des règles Sigma YAML réelles, avec leurs titres, IDs, logsource, detection, tags, level, description, etc.

Règles strictes :
- N'invente jamais de règle Sigma.
- N'invente jamais d'ID.
- N'invente jamais de YAML.
- Ne crée pas d'exemples génériques.
- Pour les informations de syntaxe/spec, utilise uniquement <retrieved-spec-data>.
- Pour les règles réelles, utilise uniquement <retrieved-rules-data>.
- Si une information n'est pas dans les données récupérées, dis-le clairement.
- Ne modifie pas le YAML des règles récupérées.

La question utilisateur nécessite les deux sources :
- Utilise la spécification pour expliquer ou valider la syntaxe.
- Utilise les règles pour analyser, comparer ou illustrer avec des règles réelles.

Réponds en français.

Quand tu mentionnes une information :
- indique "Source spec" si elle vient de {SPEC_COLLECTION_NAME}
- indique "Source rules" si elle vient de {RULES_COLLECTION_NAME}

<retrieved-spec-data collection="{SPEC_COLLECTION_NAME}">
{spec_context}
</retrieved-spec-data>

<retrieved-rules-data collection="{RULES_COLLECTION_NAME}">
{rules_context}
</retrieved-rules-data>

<user-question>
{prompt}
</user-question>
"""

    return generate_response(updated_prompt)


# =========================
# Ask avec routeur
# =========================

def ask() -> None:
    prompt = input("Enter a prompt: ")

    route_info = classify_question_with_llm(prompt)

    route = route_info["route"]
    reason = route_info["reason"]

    print("\n--- Routeur ---")
    print(f"Route: {route}")
    print(f"Reason: {reason}")

    if route == "spec_only":
        print("\n--- Mode RAG spec ---\n")

        response = answer_with_spec_rag(prompt)
        print(response)

    elif route == "rules_only":
        print("\n--- Mode RAG rules ---\n")

        response = answer_with_rules_rag(prompt)
        print(response)

    elif route == "both":
        print("\n--- Mode RAG spec + rules ---\n")

        response = answer_with_both_rag(prompt)
        print(response)

    elif route == "unknown":
        print("\n--- Mode LLM classique sans RAG ---\n")

        response = generate_response(prompt)
        print(response)

    else:
        print("\nRoute inconnue, fallback LLM classique.\n")

        response = generate_response(prompt)
        print(response)


# =========================
# CLI
# =========================

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  uv run main.py ingest_spec")
        print("  uv run main.py load_rules ~/GitRepos/sigma")
        print("  uv run main.py ingest_rules ~/GitRepos/sigma")
        print("  uv run main.py ask")
        return

    command = sys.argv[1]

    if command == "ingest_spec":
        ingest_spec_file()

    elif command == "load_rules":
        if len(sys.argv) < 3:
            print("Usage:")
            print("  uv run main.py load_rules ~/GitRepos/sigma")
            return

        sigma_repo_path = sys.argv[2]
        load_rules_step(sigma_repo_path)

    elif command == "ingest_rules":
        if len(sys.argv) < 3:
            print("Usage:")
            print("  uv run main.py ingest_rules ~/GitRepos/sigma")
            return

        sigma_repo_path = sys.argv[2]
        ingest_rules_step(sigma_repo_path)

    elif command == "ask":
        ask()

    else:
        print(f"Commande inconnue : {command}")
        print("Commandes disponibles :")
        print("  ingest_spec")
        print("  load_rules")
        print("  ingest_rules")
        print("  ask")


if __name__ == "__main__":
    main()