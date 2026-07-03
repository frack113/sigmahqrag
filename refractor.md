# Refractor — Sigma Rule Management

Fichier de travail pour le refactoring de la gestion des règles Sigma dans l'application.

## 1. Problématiques Identifiées

### 1.1 Chemins de Validation Dupliqués

Deux chemins de validation distincts avec des règles et des retours incompatibles :

```
Chemin A (Production) :
  POST /api/v1/chat/upload → ChatService.validate_and_store_yaml()
    → SigmaValidator.validate(bytes)
      → YAML parse, required: id/name/description/detection
      → detection non-empty, condition syntax check
      → deprecated field warnings (level, falsepositives)
    → Retourne: dict[str, Any] brut
    → Stocké en mémoire dans ChatService._uploaded_rule

Chemin B (Tests uniquement — mort) :
  validate_sigma_rule(SigmaRule)
    → title/condition/detection non-empty
    → level enum, status enum
    → Retourne: ValidationResult (Pydantic model)
    → Aucun appelant en production
```

| Aspect | SigmaValidator (A) | validate_sigma_rule (B) | parser.py |
|--------|-------------------|------------------------|-----------|
| **Taille fichier** | 1MB max | — | 1MB max |
| **Parse YAML** | Oui | — (opère sur modèle) | Oui |
| **Champs requis** | `id`, `name`, `description`, `detection` | `title`, `detection`, `condition` | `title`, `detection` |
| **Validation detection** | Dict non-vide | Dict non-vide | Présence |
| **Validation condition** | Références syntaxe | Non-vide | — |
| **Level** | Warning deprecated | Validation enum | — |
| **Status** | Non vérifié | Validation enum | — |
| **Retour** | `dict` brut | `ValidationResult` | `SigmaRule \| None` |
| **Erreur** | Exception (422) | Pydantic model | `None` / log |

### 1.2 Incohérence de Nommage des Champs

- `SigmaValidator` vérifie `name` (norme Sigma v2)
- `SigmaRule` (modèle canonique) utilise `title`
- `parser.py` mappe YAML `title` → `SigmaRule.title`
- Conséquence : si une règle a `name:` dans le YAML, `SigmaValidator` l'accepte mais `SigmaRule.title` sera vide ; inversement si `title:`, le parseur fonctionne mais le validateur rejette.

### 1.3 Deux Types `ValidationError` Incompatibles

- `src/shared/exceptions.py:ValidationError(Exception)` — HTTP 422, catchable
- `src/application/documents/models.py:ValidationError(BaseModel)` — Pydantic model, non-catchable
- Même nom, même sémantique (field + message), API incompatible

### 1.4 Duplication Downloader / Processor

`src/application/documents/sigma_ref_downloader.py` (753 lignes) et `sigma_ref_processor.py` (413 lignes) partagent le même domaine (téléchargement de documents de référence) avec duplication lourde :

| Fonction | downloader.py | processor.py |
|----------|--------------|-------------|
| **SHA256 fichier** | `_sha256_file()` (10 lignes) | `_sha256_file()` (7 lignes, quasi-identique) |
| **SHA256 string** | `_sha256()` (5 lignes) | `_sha256_bytes()` (4 lignes) |
| **HEAD request** | `_head_content_type()` | `_head_request()` (signatures différentes) |
| **Download HTTP** | `_download_file()` (3 retries + backoff) | `_download_one()` (lambda, 0 retry) |
| **Entry builder** | `_make_entry()` | `_build_head_entry()` / `_build_download_entry()` |
| **Normalisation URL** | `normalize_url()` (complète) | `_normalize_url()` (triviale — juste strip+rstrip) |
| **Constantes** | `DEFAULT_REQUEST_DELAY`, `DEFAULT_MAX_WORKERS` (lignes 50-51) | Mêmes constantes (lignes 20-21) |
| `_TYPE_TO_EXT` | Défini deux fois dans la même fonction (lignes 548-555, 630-637) | — |
| `httpx.Client` | Nouvelle instance par requête | Nouvelle instance par requête |
| `import hashlib` | Dans le corps des fonctions | Dans le corps des fonctions |

Risque concret : la normalisation URL différente (downloader supprime fragments, processor non) peut causer des `url_hash` différents entre les deux chemins pour la même URL.

### 1.5 Duplication Discovery Worker

`src/workers/sigma/discovery_worker.py` (502 lignes) :

- `_process_github` / `_process_spec` : structure quasi-identique (~65 lignes chacun), seule la stratégie d'énumération des repos change
- `_scan_all_github` / `_scan_all_spec` : quasi-identiques
- `_write_entries` / `_write_spec_entries` : quasi-identiques (seul le nom de méthode DB change)
- `get_sigma_rule_id` importé à l'intérieur d'une boucle (perte de perf)

### 1.6 Code Mort

| Fichier | Code | Statut |
|---------|------|--------|
| `chunker.py` | `_generate_eval_questions()` (lignes 503-515) | Jamais appelé. Le rich chunking utilise des listes inline. |
| `chunker.py` | `chunk_sigma_rules_rich()` (lignes 527-534) | Marqué "backwards-compatible", rien ne l'appelle. `SigmaChunker.process()` est le seul chemin actif. |
| `chunker.py` | `post_process()` — le `if enable_eval_questions` | N'a aucun effet observable. `return documents` est exécuté dans tous les cas. |
| `orchestrator.py` | `class RAGPipeline` (22 lignes) | Thin wrapper autour de `SearchEngine`, probablement mort. |
| `documents/validator.py` | `validate_sigma_rule()` | Importé et testé uniquement dans les tests. Aucun appelant en production. |
| `processor.py` | `GITHUB_BLOB_PATTERN: Any = None` (ligne 22) | Placeholder jamais rempli. |
| `downloader.py` | Paramètre `path` de `_load_registry` / `_save_registry` | Jamais utilisé, seul `db` est utilisé. |
| `downloader.py` | Paramètre `request_delay` de `download_references()` | Déclaré, jamais référencé dans le corps. |
| `processor.py` | Paramètre `request_delay` de `process_sigma_refs()` | Même chose. |

### 1.7 Complexité du Chunker

`SigmaChunker._chunk_rule()` fait ~346 lignes (lignes 89-434) et concentre trop de responsabilités :
- Extraction des champs depuis le dict brut
- Construction de templates textes pour 12+ types de chunks
- Itération sur les blocs de détection avec boucles imbriquées (field/operator groups + atomic indicators)
- Enrichissement LLM inline (lignes 414-432)
- Génération de questions d'évaluation inline

### 1.8 Collision de Noms `RAGPipeline`

Deux classes portent le même nom dans des packages différents :
- `src/application/chat/rag.py:RAGPipeline` — orchestrateur de génération LLM (actif)
- `src/core/pipeline/orchestrator.py:RAGPipeline` — thin wrapper SearchEngine (probablement mort)

### 1.9 État Sessionnel ChatService

`ChatService` maintient un état mutable en mémoire (session) :
- `_history`, `_uploaded_rule`, `_last_citations`, `_current_prompt_id`
- Fonctionne pour un usage mono-utilisateur local
- Empêche toute mise à l'échelle horizontale
- L'état devrait être externalisé (cache distribué, DB, etc.)

### 1.10 Absence de Module HTTP Partagé

- `httpx.Client` créé frais à chaque requête dans 4 fichiers : downloader, processor, translate (?), chat
- Aucun pool de connexions HTTP
- Logique de retry/backoff dupliquée (downloader l'a, processor ne l'a pas)
- HEAD requests dupliquées avec signatures différentes

### 1.11 Double Parsing YAML

`sigma_utils.py` parse le même fichier YAML deux fois si un appelant veut à la fois les références et le rule_id. Appelé depuis `discovery_worker.py` en boucle par fichier — l'impact est multiplié.

### 1.12 Deux Chemins d'Indexation ≠

- **Chemin A (Upload interactif)** : validation uniquement → stocké en mémoire → PAS indexé dans Qdrant
- **Chemin B (Discovery fond)** : parse → chunk → index dans Qdrant (sigma_rules)
- Écart : les règles uploadées interactivement ne sont PAS présentes dans la recherche vectorielle

### 1.13 Aucun Tuning Qdrant Spécifique aux Collections

Les 3 collections Qdrant (`sigma_rules`, `sigma_docs`, `sigma_spec`) sont créées avec la même configuration minimale :

```python
VectorParams(size=384, distance=Distance.COSINE)
SparseVectorParams(index=SparseIndexParams())  # "text-sparse"
```

| Paramètre manquant | Impact |
|-------------------|--------|
| `hnsw_config` | Utilise les defaults serveur (m=16, ef_construct=100) — probablement ok mais non évalué |
| `quantization_config` | Aucune quantification — les vecteurs dense sont stockés en float32 intégral |
| `optimizers_config` | Aucun tuning — indexing_threshold_kb par défaut (20 MB) |
| Per-collection tuning | Les 3 collections ont la même config, alors que leurs usages diffèrent (recherche fréquente vs froide) |

### 1.14 Custom BM25 Sparse Encoder Non Standard

`src/core/search/sparse_encoder.py` implémente un BM25 custom avec :
- Token IDs basés sur MD5 modulo 2^24
- Poids : `1.0 + log(term_frequency)` (pas de IDF, pas de normalisation par doc length)
- Stop words anglais codés en dur (107 mots)
- **Pas de stemming, pas de configuration par langue**

Points d'attention :
- L'absence d'IDF signifie que les tokens fréquents ne sont pas pénalisés
- Le hash MD5 peut causer des collisions (2^24 ≈ 16M IDs, acceptable mais non déterministe)
- Aucune configuration pour le français alors que le modèle d'embedding est `multilingual-e5-small`
- Pas de `avg_len` configuré pour BM25 — Qdrant ne peut pas normaliser par longueur de document

### 1.15 Pas d'Évaluation de la Qualité de Recherche

- Aucun golden set / ground truth dataset pour mesurer recall@k
- Aucune évaluation comparative : exact search vs approximate, flat vs rich chunks
- Le paramètre `alpha=0.3` du hybrid search n'a jamais été tuné sur des données réelles
- Fusion RRF avec `k=60` — valeur par défaut, jamais ajustée

### 1.16 Pipeline d'Indexation Synchrone avec Batch Size Faible

- `IngestionPipeline.run()` utilise `num_workers=0` (séquentiel)
- `embed_batch_size=8` — très conservateur pour un modèle 384-dim
- Pas de désactivation HNSW pendant le bulk load (reconstruit à chaque insertion)
- Stratégie delete-and-reindex : pas d'upsert incrémental, reconstruction complète

### 1.17 Deux Chemins Concurrents pour le Téléchargement des Références

Le téléchargement des documents de référence des règles Sigma est implémenté par **deux fichiers distincts** qui font la même chose différemment :

| Aspect | `sigma_ref_downloader.py` (753 lignes) | `sigma_ref_processor.py` (413 lignes) |
|--------|----------------------------------------|---------------------------------------|
| **Point d'entrée** | `download_references(rules_dir, ...)` — scanne les fichiers YAML directement | `process_sigma_refs(db, ...)` — lit les entrées du `doc_registry` |
| **Appelé par** | API endpoint `POST /api/v1/documents/index-sigma-ref` | Worker `SigmaRefProcessor` (background) |
| **Normalisation URL** | Complète : GitHub blob→raw, strips fragments, refs/heads | Triviale : `url.strip().rstrip("/")` |
| **Nommage fichiers** | `{url_hash}{ext}` (ex: `abc123.md`) | `_sanitize_filename(url)` (ex: `documentation_page`) |
| **Registry** | Dict mémoire + flush final vers DB | Appels DB unitaires par opération |
| **Retry download** | Oui (3 retries, backoff exponentiel) | Non (0 retry, pas de backoff) |
| **SSRF protection** | Oui (`_is_private_url()`) | **Non** |
| **HEAD request** | `_head_content_type()` — retourne Content-Type seulement | `_head_request()` — retourne Content-Type + size + final_url |
| **hashlib import** | Dans le corps des fonctions | Dans le corps des fonctions |
| **Lock** | `_registry_lock` global (threading.Lock) | Aucun |

**Conséquence directe** : le même URL peut avoir un `url_hash` différent entre les deux chemins à cause de la normalisation divergente, causant des doublons dans le registry et des téléchargements redondants.

### 1.18 Problèmes de Stockage Local des Références

Les fichiers téléchargés sont stockés dans `data/documents/sigmaref/` :

- **Aucune structure de sous-répertoires** — tous les fichiers sont à plat dans un seul dossier (plusieurs milliers de fichiers potentiellement)
- **Nommage incohérent** — le downloader utilise des hash (déterministe, prévisible), le processor utilise le nom du fichier original (variable, risque de collision)
- **Pas de nettoyage** — les fichiers orphelins (URLs qui ne sont plus référencés par aucune règle) ne sont jamais supprimés
- **Pas de déduplication cross-rule** — si une URL est référencée par 10 règles, elle est téléchargée 1 fois mais son `rule_id`/`title` dans le registry est écrasé à chaque mise à jour (perte de l'information de provenance)

### 1.19 Cycle de Vie `embed_status` Incohérent

Le statut d'embedding traverse `discovery` → `head_verified` → `embedded`, mais :

- `process_sigma_refs()` crée des entrées avec `embed_status = "head_verified"` pour les URLs de type non supporté → **entrées mortes** qui ne seront jamais promues
- `download_references()` utilise toujours `embed_status = "discovery"` après téléchargement
- Aucun mécanisme de nettoyage pour les entrées bloquées en `head_verified`

### 1.20 Pas de Table de Jonction Règle↔Référence

La table `doc_registry` stocke `rule_id` et `title` par URL, mais :
- Si 2 règles partagent la même référence, seule la dernière écriture survit
- Impossible de répondre à "quelles règles référencent ce document ?"
- Impossible de savoir si un document est orphelin (plus référencé par aucune règle)

## 2. Propositions d'Optimisation

### P0 — Priorité Critique

#### P0.1 Extraire les fonctions SHA256 partagées

Créer `src/shared/utils/crypto_utils.py` :
- `compute_sha256_str(data: str) -> str`
- `compute_sha256_file(path: Path) -> str`

Supprimer les 3 implémentations dupliquées dans :
- `discovery_base.py:15`
- `sigma_ref_downloader.py:725`
- `sigma_ref_processor.py:392`

#### P0.2 Unifier la normalisation URL

Une seule `normalize_url()` dans `src/shared/utils/url_utils.py` avec la logique complète du downloader (GitHub blob→raw, fragments, refs/heads). Utiliser partout pour garantir la cohérence des `url_hash`.

### P1 — Priorité Haute

#### P1.1 Consolider les validateurs

- `SigmaValidator.validate()` retourne un `SigmaRule` (via `SigmaRule.from_dict()`) au lieu d'un `dict` brut
- Fusionner les contrôles de `validate_sigma_rule()` (level enum, status enum) dans `SigmaValidator`
- Normaliser les champs : `title` partout, avec alias `name` en lecture si besoin
- Supprimer `src/application/documents/validator.py` après fusion
- Standardiser sur `src/shared/exceptions.ValidationError` (exception)

#### P1.2 Extraire le download HTTP partagé

Créer `src/shared/utils/http_utils.py` :
- `head_url(url, timeout=10) -> tuple[str|None, int|None, str|None]`
- `download_file(url, output_path, max_retries=3) -> tuple[bool, int|None]`
- Pool de connexions `httpx.AsyncClient` partagé
- Logique de retry avec backoff harmonisée

#### P1.3 Factoriser les builders d'entrées registry

Fonction unique `build_registry_entry()` dans `src/shared/utils/registry_utils.py` avec paramètre `embed_status` par défaut. Remplacer `_make_entry`, `_build_head_entry`, `_build_download_entry`.

#### P1.4 Factoriser les méthodes du DiscoveryWorker

- `_scan_all_github` + `_scan_all_spec` → `_scan_all_files(prepare_entry_fn)`
- `_write_entries` + `_write_spec_entries` → `_write_entries(batch_upsert_fn, spec_mode=False)`
- `_process_github` + `_process_spec` → paramétrer la stratégie d'énumération des repos

#### P1.5 Supprimer le code mort

- `_generate_eval_questions()` dans chunker.py
- `chunk_sigma_rules_rich()` dans chunker.py
- `orchestrator.py:RAGPipeline` — supprimer la classe, les appelants utilisent `SearchEngine` directement
- `GITHUB_BLOB_PATTERN: Any = None` dans processor.py
- Paramètres morts (`path`, `request_delay`) dans downloader/processor
- `validate_sigma_rule()` dans documents/validator.py (après fusion P1.1)

### P2 — Priorité Moyenne

#### P2.1 Décomposer `_chunk_rule()` 

Extraire :
- `_extract_fields(rule: dict) -> dict` (lignes 98-116)
- `_build_executive_summary(rule, fields) -> dict` (chunk type 1)
- `_build_metadata_lifecycle(rule, fields) -> dict` (chunk type 2)
- ... et ainsi de suite pour les 12+ types
- `_enrich_by_llm(chunks) -> chunks` (étape séparée, lignes 414-432)

#### P2.2 Résoudre la collision RAGPipeline

Renommer ou supprimer `src/core/pipeline/orchestrator.py:RAGPipeline`.

#### P2.3 Externaliser l'état ChatService

- Propager `session_id` depuis l'API
- Stocker `_history`, `_uploaded_rule` dans un store (cache LRU, DuckDB, etc.)
- Permettre la scalabilité horizontale

#### P2.4 Normaliser les imports

- `import hashlib` en haut des fichiers, pas dans le corps des fonctions
- `from src.shared.utils.sigma_utils import get_sigma_rule_id` en haut de `discovery_worker.py`, pas dans la boucle

#### P2.5 Constante NULL_UUID

Définir `NULL_UUID = "00000000-0000-0000-0000-000000000000"` dans `src/shared/constants.py` et l'utiliser partout.

#### P2.6 Dédoublonner `_TYPE_TO_EXT`

Définir une fois comme constante module dans `identify_file_type.py` ou `sigma_ref_downloader.py`.

### P3 — Priorité Basse

#### P3.1 Split downloader.py (753 lignes)

Diviser `sigma_ref_downloader.py` en modules < 400 lignes :
- `sigma_ref_downloader.py` — orchestration
- `sigma_ref_http.py` — HTTP helpers
- `sigma_ref_registry.py` — registry management

#### P3.2 Connection pooling HTTP

Réutiliser `httpx.Client` (ou `AsyncClient`) avec un pool de connexions dans toutes les phases de téléchargement batch.

#### P3.3 Unifier les deux chemins d'indexation

Permettre aux règles uploadées interactivement d'être optionnellement indexées dans Qdrant (ex. paramètre `index_after_upload`).

### R1 — Priorité Haute (Téléchargement Références)

#### R1.1 Unifier `download_references()` et `process_sigma_refs()`

Une seule fonction `download_sigma_references(source, db, ...)` avec deux modes d'entrée :
- `mode="scan"` : scanne les fichiers YAML directement (ancien downloader)
- `mode="registry"` : lit les entrées du doc_registry (ancien processor)

La normalisation URL, le nommage des fichiers, le retry, et la détection SSRF doivent être **identiques** dans les deux modes.

#### R1.2 Standardiser le Nommage des Fichiers

- Format unique : `{url_hash}{ext}` (comme le downloader actuel)
- Supprimer `_sanitize_filename()` du processor
- Garantir qu'un même URL produit toujours le même chemin disque

#### R1.3 Ajouter une Table de Jonction `rule_references`

```sql
CREATE TABLE rule_references (
    rule_id    TEXT NOT NULL,
    url_hash   TEXT NOT NULL,
    PRIMARY KEY (rule_id, url_hash)
);
```

- Permet de retrouver toutes les références d'une règle
- Permet de détecter les documents orphelins (URLs non référencées)
- Nettoyage possible : supprimer les fichiers dont l'URL_hash n'est plus dans `rule_references`

#### R1.4 Nettoyer les Entrées Mortes du Registry

- Supprimer les entrées `head_verified` de plus de X jours
- Supprimer les entrées dont `url_hash` n'est plus dans `rule_references`
- Tâche planifiée (cron) ou déclenchée manuellement

#### R1.5 Ajouter SSRF Protection dans le Processor

Copier `_is_private_url()` du downloader et l'utiliser dans `process_sigma_refs()` avant toute HEAD request. Sans ça, le processor est vulnérable aux SSRF.

### R2 — Priorité Moyenne (Organisation Stockage)

#### R2.1 Structure de Sous-Répertoires

```
data/documents/sigmaref/
  ├── markdown/       # .md files
  ├── html/           # .html files
  ├── pdf/            # .pdf files
  ├── plain_text/     # .txt files
  └── office/         # .docx files
```

- Préserve le nom `{url_hash}{ext}` dans chaque sous-répertoire
- Évite d'avoir 10 000 fichiers dans le même dossier

#### R2.2 Garbage Collection des Fichiers Orphelins

- Scanner `data/documents/sigmaref/` pour les fichiers dont le nom ne correspond à aucun `url_hash` dans `doc_registry`
- Supprimer les fichiers orphelins (avec confirmation)
- Option : déplacer vers `.trash/` avant suppression définitive

### R3 — Priorité Basse (Traçabilité)

#### R3.1 Enrichir le Registry avec la Liste des Règles Sources

Ajouter un champ `referenced_by: list[str]` dans `doc_registry` (ou utiliser la table `rule_references`) pour savoir quelles règles référencent un document donné. Utile pour :
- Debug : "pourquoi ce document a été téléchargé ?"
- Mise à jour : "re-télécharger les docs des règles modifiées"
- Suppression : "ce document n'est plus référencé, on peut le supprimer"

## 3. Plan d'Exécution Suggéré

```
Phase 1 — P0 (nettoyage critique)
  ├── P0.1 Extraire crypto_utils.py (SHA256)
  ├── P0.2 Unifier normalize_url()
  ├── P1.5 Supprimer le code mort évident
  └── P2.4 Normaliser les imports hashlib/sigma_utils

Phase 2 — P1 (consolidation validateurs + HTTP)
  ├── P1.1 Consolider SigmaValidator → retourne SigmaRule
  ├── P1.2 Extraire http_utils.py (HEAD + download + retry)
  ├── P1.3 Factoriser registry entry builders
  └── Supprimer doc la mort (validate_sigma_rule, etc.)

Phase 3 — P1 (factorisation workers)
  ├── P1.4 Factoriser _scan_all_* / _write_* / _process_*
  └── P2.5 Constante NULL_UUID

Phase 4 — P2 (qualité de code)
  ├── P2.1 Décomposer _chunk_rule()
  ├── P2.2 Résoudre collision RAGPipeline
  ├── P2.3 Externaliser état ChatService
  └── P2.6 Dédoublonner _TYPE_TO_EXT

Phase 5 — P3 (architecture)
  ├── P3.1 Split downloader.py
  ├── P3.2 Connection pooling HTTP
  └── P3.3 Unifier chemins d'indexation
```

## 4. Propositions Qdrant (Basées sur les Skills)

### Q0 — Priorité Critique (Qualité de Recherche)

#### Q0.1 Créer un Golden Set pour Évaluer Recall@k

- Échantillonner 100-200 requêtes réelles avec jugements de pertinence
- Mesurer recall@k avant/après chaque changement de config
- Voir Qdrant Search Quality Diagnosis skill

#### Q0.2 Tester Exact Search Comme Baseline

- Avant tout tuning HNSH, comparer exact search vs approximate search
- Si l'écart est > 5%, tuner `ef` et `m` du HNSW
- Permet d'isoler les problèmes de modèle d'embedding vs index

### Q1 — Priorité Haute (Performance Indexation)

#### Q1.1 Ajouter `quantization_config` aux Collections

```python
quantization_config=ScalarQuantization(
    scalar=ScalarQuantizationConfig(
        type=ScalarType.INT8,
        always_ram=True,
        quantile=0.5,
    )
)
```

- Réduction mémoire 4x pour les vecteurs dense en RAM
- Perte de qualité < 1% recall avec rescore
- Activation immédiate pour les 3 collections

#### Q1.2 Augmenter `embed_batch_size` et Paralléliser

- `embed_batch_size` : 8 → **64** (384-dim, CPU, safe)
- `num_workers` : 0 → **2-4** pour ingestion parallèle
- Désactiver HNSW pendant le bulk load : `indexing_threshold_kb = 0` → temporairement très haut, restaurer après

### Q2 — Priorité Moyenne (Tuning Recherche)

#### Q2.1 Tuner l'Alpha du Hybrid Search par Collection

- Remplacer le `alpha=0.3` global par des valeurs par collection :
  - `sigma_rules` : α=0.5 (sémantique + lexical équilibré — les règles ont un vocabulaire technique précis)
  - `sigma_docs` : α=0.7 (plus lexical — docs de référence, termes exacts)
  - `sigma_spec` : α=0.3 (plus sémantique — spécifications, concepts)
- Évaluer avec le golden set (Q0.1)

#### Q2.2 Tuner la Fusion RRF

- `k=60` actuel → tester `k=30`, `k=60`, `k=100` avec le golden set
- Poids par collection dans le RRF (weighted RRF) si une collection domine
- Envisager DBSF si les distributions de score entre dense et sparse sont trop différentes

#### Q2.3 Ajouter `hnsw_config` par Collection

```python
hnsw_config=HnswConfigDiff(
    m=16,           # default ok pour 384-dim
    ef_construct=200,  # 100 → 200 pour meilleure qualité à l'indexation
    full_scan_threshold_kb=10000,  # 10 MB, identique au serveur
    on_disk=False,  # sigma_rules en RAM
)
```

- `sigma_docs` et `sigma_spec` (collections froides) : `on_disk=True` + `async_scorer`

### Q3 — Priorité Basse (Architecture Vectorstore)

#### Q3.1 Stocker les Sparse Vectors sur Disk

```python
sparse_vectors_config={
    "text-sparse": SparseVectorParams(
        index=SparseIndexParams(on_disk=True)
    )
}
```

- Les vecteurs sparse BM25 sont rarement tous consultés
- Bon candidat pour le stockage disque (économise RAM)

#### Q3.2 Revoir le Sparse Encoder Custom

- Benchmarker `bm25_sparse_encoder` vs le BM25 natif de Qdrant (configuré par language)
- Avantages BM25 natif Qdrant :
  - Calcul côté serveur (pas de transfert des vecteurs sparse)
  - Tokenization + stemming standardisés
  - Support multi-langue (français, etc.)
  - IDF calculé automatiquement
- Si le custom encoder est conservé, ajouter au moins le calcul d'IDF et la normalisation par doc length

#### Q3.3 Oversampling + Rescore avec Quantification

```python
quantization_config=ScalarQuantization(
    scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True),
    rescore=True,
    oversampling=2.0,
)
```

- Permet de chercher dans un pool 2x plus large (vitesse ×2 grâce à la quantification)
- Rescore les top_k sur les vecteurs originaux pour préserver la qualité

#### Q3.4 Pipeline d'Indexation Incrémental

- Remplacer la stratégie delete-and-reindex par des upserts par `rule_id`
- Nécessite : identifier les règles nouvelles/modifiées vs inchangées
- Avantage : pas de downtime de la collection, indexation plus rapide
- Combinable avec `indexing_threshold_kb` haut initial + baisse progressive

## 5. Call Graph — Phase 0 Audit

### SigmaValidator.validate()

**Production callers (1 fichier, 1 site d'appel direct) :**
| Fichier | Ligne | Usage | Type attente |
|---------|-------|-------|-------------|
| `src/application/chat/service.py` | 357 | `ChatService.validate_and_store_yaml()` → stocke dans `_uploaded_rule` | `dict[str, Any]` |
| `src/application/chat/rag.py` | 99,133,269,305 | `explain_rule()`, `explain_rule_stream()`, `analyze_coverage()`, `analyze_coverage_stream()` | `dict[str, Any]` (param `rule_data`) |
| `src/application/chat/rag.py` | 380 | `_format_rule_yaml()` | `yaml.dump(rule)` attend un dict |
| `src/application/chat/rag.py` | 387 | `_fallback_explanation()` | `.get('name', 'Unknown')`, `.get('id')`, `.get('description')` |

**Consommateurs indirects de `_uploaded_rule` (dict) via `ChatService` :**
| Méthode | Accès | Ligne |
|---------|-------|-------|
| `_handle_explain()` | `.get("name", "")` | 234 |
| `_handle_explain_stream()` | `.get("name", "")` | 248 |
| `_handle_coverage()` | passé tel quel | 265 |
| `_handle_coverage_stream()` | passé tel quel | 342 |

**Tests :**
| Fichier | Usage |
|---------|-------|
| `tests/unit/application/services/test_sigma_validator.py` | 19 tests unitaires, `validate()` sur bytes |
| `tests/unit/application/services/test_sigma_validator_advanced.py` | 6 tests avancés |
| `tests/unit/application/services/test_chat_service_cache.py` | `SigmaValidator` mocké (`patch`) |
| `tests/integration/test_chat_flow.py` | `_uploaded_rule` set manuellement comme dict (l.92) |

### download_references()

**Production callers (1 fichier, 1 site) :**
| Fichier | Ligne | Contexte |
|---------|-------|----------|
| `src/api/v1/documents/documents.py` | 35 | `POST /api/v1/documents/index-sigma-ref` |

**Tests :**
| Fichier | Usage |
|---------|-------|
| `tests/unit/application/documents/test_sigma_ref_downloader.py` | 15+ appels, tests unitaires complets |

### process_sigma_refs()

**Production callers (1 fichier, 1 site) :**
| Fichier | Ligne | Contexte |
|---------|-------|----------|
| `src/workers/sigma/sigmaref_worker.py` | 41 | `SigmaRefProcessor.process()` worker background |

**Tests :**
| Fichier | Usage |
|---------|-------|
| `tests/unit/workers/test_discovery_workers.py` | Mocké (l.28, 50) |

### validate_sigma_rule() — CONFIRMÉ CODE MORT

**Production callers : AUCUN**

**Tests uniquement :**
| Fichier | Usage |
|---------|-------|
| `tests/unit/application/documents/test_documents.py` | 5 appels (l.69, 84, 98, 113, 131) |

### Risques Identifiés pour P1.1 (dict → SigmaRule)

1. `ChatService._uploaded_rule` typé `dict[str, Any] | None` → doit passer à `SigmaRule | None`
2. Tous les `.get("name", "")` → deviennent `.title` (ou alias `.name` si préservé)
3. `_format_rule_yaml()` utilise `yaml.dump(rule_dict)` → nécessite `rule.model_dump()`
4. `_fallback_explanation()` utilise `.get()` sur dict → nécessite accès attribut
5. Mock dans `test_chat_service_cache.py` patch `SigmaValidator` → pas de changement nécessaire
6. Test intégration `test_chat_flow.py` set `_uploaded_rule` comme dict brut → à migrer vers `SigmaRule`

### Tests de Régression à Écrire (avant P1.1) DONE by commit 6474065

- [x] Capturer le contrat `dict` actuel de `SigmaValidator.validate()` (bracket access, .get(), yaml.dump(), ValidationError)
- [x] Capturer les patterns de `ChatService._uploaded_rule` (`.get("name", "")`, `.get("id", "N/A")`)
- [x] Capturer le contrat `_format_rule_yaml()` et `_fallback_explanation()`

---

## 6. Plan d'Exécution Final

```
Phase 1 — P0 + R (nettoyage critique) DONE by commmit 8d24148dbfe4be3e6fe529800f5516613a0217c6
  ├── P0.1 Extraire crypto_utils.py (SHA256)
  ├── P0.2 Unifier normalize_url()
  ├── R1.5 Ajouter SSRF protection dans le processor
  ├── P1.5 Supprimer le code mort évident
  └── P2.4 Normaliser les imports hashlib/sigma_utils

Phase 2 — P1.2 + P1.3 (infra indépendante, 0 risque) DONE by commit 6474065
  ├── P1.2 Extraire src/shared/http.py (HEAD + download + retry + pool httpx)
  ├── P1.3 Factoriser build_registry_entry() — pure factory sans IO
  └── Tests : mock httpx, retry/backoff, SSRF, golden path + edge cases

Phase 3 — P1.1 (validator consolidation, protégé par audit Phase 0) DONE by commit 259bccd
  ├── Audit préalable : cartographier tous les callers, tests de régression
  ├── SigmaValidator.validate() → retourne SigmaRule (pydantic)
  ├── Merge checks de validate_sigma_rule() + shared.exceptions.ValidationError
  ├── Normalisation title/name (name alias via @property)
  ├── Supprimer validate_sigma_rule(), ValidationError/ValidationResult
  └── Tests : 52 unit tests verts, ruff/mypy clean

Phase 4 — R1.1 + R1.2 (download unification, dépend de P1.2) DONE by commit 2f2efe7
  ├── download_sigma_references(source, db, mode="scan"|"registry")
  ├── Standardiser nommage {url_hash}{ext} dans les 2 modes
  ├── Contract test : même URL → même nom de fichier
  └── processor.py passe de 318l à 56l (délégation pure)

Phase 5 — R1 (traçabilité références) DONE by commit 33e1f70 + follow-up
  ├── R1.3 Ajouter table rule_references (junction rule↔reference)
  ├── R1.4 Nettoyer entrées mortes head_verified
  │   ├── delete_head_verified_orphans() — head_verified sans content_sha256
  │   └── delete_unreferenced_entries() — sigmaref entries sans url_hash dans rule_references
  ├── R1.4 integré dans DocGCWorker.process()
  └── R3.1 Enrichir registry avec liste des règles sources

Phase 6 — Q0-Q1 (qualité recherche + perf indexation Qdrant)
  ├── Q0.1 Créer golden set pour évaluation recall@k
  ├── Q0.2 Tester exact search comme baseline
  ├── Q1.1 Ajouter quantization_config aux 3 collections
  └── Q1.2 Augmenter embed_batch_size (8→64) + paralléliser (workers 0→4)

Phase 7 — P1 (factorisation workers) DONE
  ├── P1.4 Factoriser _scan_all_github + _scan_all_spec → _scan_all(prepare_fn)
  │   ├── _write_entries + _write_spec_entries → _write_entries(batch_upsert_fn)
  │   └── _collect_repo_files() extrait du rglob commun github+spec
  ├── P2.5 Constante NULL_UUID dans src/shared/constants.py (6 fichiers modifiés)
  └── Q2.3 Ajouter hnsw_config par collection via collection_hnsw_config()
      ├── sigma_rules → in-RAM, ef_construct=200
      ├── sigma_docs → on-disk
      └── sigma_spec → on-disk

Phase 8 — P2 + R2 (qualité de code + organisation stockage)
  ├── P2.1 Décomposer _chunk_rule()
  ├── P2.2 Résoudre collision RAGPipeline
  ├── P2.3 Externaliser état ChatService
  ├── P2.6 Dédoublonner _TYPE_TO_EXT
  ├── R2.1 Structure sous-répertoires par type (markdown/, html/, pdf/)
  └── R2.2 Garbage collection fichiers orphelins

Phase 9 — Q2-Q3 (tuning recherche + architecture vectorstore) DONE
  ├── Q2.1 Tuner alpha hybrid search par collection
  ├── Q2.2 Tuner fusion RRF (k, weighted)
  ├── Q3.1 Stocker sparse vectors sur disk
  ├── Q3.2 Revoir sparse encoder (benchmark BM25 natif)
  └── Q3.4 Pipeline d'indexation incrémental

Phase 10 — P3 + Q3 (architecture finale)
  ├── P3.1 Split downloader.py (si toujours pertinent après R1.1)
  ├── P3.2 Connection pooling HTTP
  ├── P3.3 Unifier chemins d'indexation (upload→Qdrant)
  └── Q3.3 Oversampling + rescore avec quantification
```


#  opencode -s ses_0deda6082ffeIa2vHoUdYiWbpY