---
title: 'Central Application Configuration via sigmahqrag.toml'
type: 'feature'
created: '2026-04-28'
status: 'done'
context: []
baseline_commit: '29ba9ac'
specLoopIteration: 1
---

## Intent

**Problem:** L'application a des configurations éparpillées et pas de point central pour les options utilisateur. Le fichier `./data/sigmahqrag.toml` existe mais n'est pas utilisé comme configuration centrale.

**Approach:** Utiliser `./data/sigmahqrag.toml` comme point central pour toutes les options de l'application (backend selection, model paths, service ports, etc.) avec valeurs par défaut sensées.

## Boundaries & Constraints

**Always:** 
- Utiliser `./data/sigmahqrag.toml` comme configuration centrale
- Prévoir des valeurs par défaut raisonnables
- Support des options : backend GPU, chemins modèles, ports services, versions

**Ask First:** 
- Si une structure différente est proposée

**Never:** 
- Casser la compatibilité avec les déploiements existants
- Nécessiter une reconfiguration complète

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Config manquant | `data/sigmahqrag.toml` inexistant | Utilise valeurs par défaut | Log warning, continue avec défauts |
| GPU invalide | `gpu_type = "invalid"` | Utilise défaut ("cpu") | Log warning, use default |
| Port en usage | Port déjà pris | Détecte et suggère alternative | Error message claire |

## Code Map

- `data/sigmahqrag.toml` -- Fichier de configuration centrale (existe déjà)
- `src/config.py` -- Module de configuration (à vérifier/créer)
- `src/admin/version_manager.py` -- Déjà modifié pour lire gpu_type
- `src/services/llama_service.py` -- Utilisera config pour base_url
- `src/services/qdrant_service.py` -- Utilisera config pour host/port

## Tasks & Acceptance

**Execution:**

- [x] `data/sigmahqrag.toml` -- Définir structure complète avec toutes les options -- Ajouter sections : `[backend]`, `[models]`, `[services]`, `[logging]` -- Documenter chaque option avec commentaires
- [x] `src/config.py` -- Refactoriser pour lire `data/sigmahqrag.toml` -- Fonction `load_config()` retournant dict avec valeurs par défaut -- Gérer les erreurs de parsing TOML -- Supprimer références à `config.json`
- [x] `src/admin/version_manager.py` -- Modifier `_read_gpu_reference()` pour utiliser `config.py` -- Standardiser lecture config
- [x] `src/services/llama_service.py` -- Utiliser config pour `base_url` et `model_name`
- [x] `src/services/qdrant_service.py` -- Utiliser config pour `host`, `port`, `collection_name`, `vector_size`

**Acceptance Criteria:**

- Given config manquant, when app demarre, then utilise valeurs par défaut sans crash
- Given `gpu_type = "hip"` in config, when downloading llama.cpp, then télécharge version HIP
- Given `llama.base_url = "http://localhost:8080"`, when service initialise, then utilise cette URL
- Given config invalide (TOML malformé), when app demarre, then log error et utilise défauts
- Given `qdrant.port = 6334`, when service initialise, then utilise port 6334

## Design Notes

Structure proposée pour `data/sigmahqrag.toml` :
```toml
[backend]
gpu_type = "hip"  # hip, cuda, cpu (for llama.cpp downloads)

[models]
llm_dir = "models/llm"
embeddings_dir = "models/embeddings"

[services.llama]
base_url = "http://127.0.0.1:8080"
model_name = "llama-3-8b-q4_k_m.gguf"

[services.qdrant]
host = "127.0.0.1"
port = 6333
collection_name = "sigma_rules"
vector_size = 384

[paths]
bin_dir = "data/bin"
models_dir = "data/models"
logs_dir = "logs"
backup_dir = "backups"

[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

Current `src/config.py` uses `config.json` - will be refactored to use TOML.

## Verification

**Commands:**

- `python -c "from src.config import load_config; print(load_config())"` -- expected: dict avec config par défaut
- `ruff check src/config.py` -- expected: pas d'erreurs
- `mypy src/config.py` -- expected: pas d'erreurs de type
