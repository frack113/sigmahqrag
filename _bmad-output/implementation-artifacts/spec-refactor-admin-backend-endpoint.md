---
title: 'Refactor Admin Backend API to Action-Based Pattern'
type: 'refactor'
created: '2026-04-28'
status: 'done'
context: []
baseline_commit: 'b1ec0c9'
specLoopIteration: 1
---

<!-- Target: 900-1300 tokens. Above 1600 = high risk of context rot. -->

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** Les endpoints admin pour download et update (`/download`, `/download/cancel`, `/download/{id}/progress`, `/update/apply`, `/update/rollback`, `/update/status`) utilisent des routes séparées au lieu du pattern action-based unifié.

**Approach:** Unifier les endpoints de gestion backend sous `/admin/backend/` avec paramètres `action` et `service`, suivant le pattern de `admin_llm.py` et `admin_service.py`.

## Boundaries & Constraints

**Always:** 
- Utiliser le pattern action-based avec paramètres query (`action`, `service`)
- Gérer les services : llama.cpp (`llama`) et qdrant
- Maintenir la compatibilité avec `require_role(UserRole.ADMIN)` pour tous les endpoints
- Utiliser `create_download_manager()` et `create_update_service()` pour les opérations

**Ask First:** 
- Si une autre approche que GET/POST avec action est proposée
- Si le refactoring doit inclure d'autres endpoints

**Never:** 
- Modifier le comportement des opérations (download, update)
- Changer les chemins des binaires ou la configuration
- Casser la compatibilité SSE pour le progrès des téléchargements

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Download | POST `/admin/backend/?action=download&service=llama&version=...` | `{"download_id": ..., "status": ...}` | 400 si version manquante, 500 si échec |
| Cancel download | POST `/admin/backend/?action=cancel&download_id=...` | `{"download_id": ..., "status": "cancelled"}` | 400 si download_id invalide |
| Download progress | GET `/admin/backend/?action=progress&download_id=...` | SSE stream | 400 si download_id invalide |
| Update apply | POST `/admin/backend/?action=apply&service=llama&version=...` | `{"success": true, ...}` | 400 si service/version manquant |
| Update rollback | POST `/admin/backend/?action=rollback&service=llama` | `{"success": true, ...}` | 400 si service invalide |
| Update status | GET `/admin/backend/?action=status` | `{"versions": ..., "backups": ...}` | 500 en cas d'erreur |
| Invalid action | GET `/admin/backend/?action=invalid` | 400 `{"error": "Invalid action"}` | Retourner code 400 |

</frozen-after-approval>

## Code Map

- `src/api/routes/admin_backend.py` -- Nouveau fichier pour les endpoints backend (download, update) refactorisés (pattern action-based)
- `src/api/routes/admin.py` -- Fichier existant contenant les endpoints à nettoyer (download, update)
- `src/api/routes/admin_llm.py` -- Pattern de référence (action-based avec query params)
- `src/api/routes/admin_service.py` -- Pattern de référence (action-based services)
- `src/admin/download_manager.py` -- Logique métier pour download
- `src/admin/update_manager.py` -- Logique métier pour update
- `src/api/dependencies.py` -- Dépendances FastAPI (require_role)
- `scripts/test_api_admin_backend.py` -- Script de test pour valider les endpoints backend

## Tasks & Acceptance

**Execution:**

- [x] `src/api/routes/admin_backend.py` -- Créer nouveau fichier avec endpoints unifiés (GET + POST sur `/admin/backend/`) suivant le pattern action-based -- Implémenter download, cancel, progress, update apply/rollback/status
- [x] `src/api/routes/admin.py` -- Supprimer les endpoints backend (download, download/cancel, download/{id}/progress, update/apply, update/rollback, update/status) -- Garder uniquement les endpoints health
- [x] `scripts/test_api_admin_backend.py` -- Créer script de test (style argparse comme test_api_admin_llm.py) pour valider les endpoints GET/POST `/admin/backend/` -- Tester actions download, cancel, progress, apply, rollback, status

**Acceptance Criteria:**

- Given action download, when POST `/admin/backend/?action=download&service=llama&version=X`, then le téléchargement démarre et retourne `{"download_id": ...}`
- Given action progress, when GET `/admin/backend/?action=progress&download_id=X`, then le SSE stream est retourné
- Given action apply, when POST `/admin/backend/?action=apply&service=llama&version=X`, then l'update s'applique et retourne `{"success": true}`
- Given action status, when GET `/admin/backend/?action=status`, then retourne le statut des versions et backups
- Given action invalide, when GET `/admin/backend/?action=invalid`, then retourne erreur 400

## Design Notes

Pattern cible (inspiré de `admin_llm.py` et `admin_service.py`) :

```python
@router.get("/backend/")
async def backend_get(
    action: str = Query(..., description="Action: progress, status"),
    service: str | None = Query(None, description="Service: llama, qdrant"),
    download_id: str | None = Query(None, description="Download ID for progress"),
) -> JSONResponse | StreamingResponse:
    match action:
        case "progress":
            # SSE stream
        case "status":
            # Status JSON
        case _:
            # 400 Invalid action

@router.post("/backend/")
async def backend_post(
    action: str = Query(..., description="Action: download, cancel, apply, rollback"),
    service: str | None = Query(None, description="Service: llama, qdrant"),
    version: str | None = Query(None, description="Version for download/apply"),
    download_id: str | None = Query(None, description="Download ID for cancel"),
) -> JSONResponse:
    match action:
        case "download":
            # Start download
        case "cancel":
            # Cancel download
        case "apply":
            # Apply update
        case "rollback":
            # Rollback update
        case _:
            # 400 Invalid action
```

## Verification

**Commands:**

- `curl -X POST "http://localhost:8000/admin/backend/?action=download&service=llama&version=main"` -- expected: JSON avec download_id
- `curl "http://localhost:8000/admin/backend/?action=progress&download_id=XXX"` -- expected: SSE stream
- `curl -X POST "http://localhost:8000/admin/backend/?action=apply&service=llama&version=main"` -- expected: JSON avec success=true
- `ruff check src/api/routes/admin_backend.py` -- expected: pas d'erreurs
- `mypy src/api/routes/admin_backend.py` -- expected: pas d'erreurs de type

## Suggested Review Order

**Unified Action-Based Backend Endpoint (Core Change)**

- Nouveau fichier avec endpoints GET/POST unifiés pour download et update
  [`admin_backend.py:60`](../../src/api/routes/admin_backend.py#L60)

- Normalisation des paramètres et validation des actions/services
  [`admin_backend.py:32`](../../src/api/routes/admin_backend.py#L32)

- Gestion SSE pour le progrès des téléchargements (avec json.dumps)
  [`admin_backend.py:39`](../../src/api/routes/admin_backend.py#L39)

- Opérations download, cancel, apply, rollback avec gestion d'erreurs
  [`admin_backend.py:117`](../../src/api/routes/admin_backend.py#L117)

**Nettoyage Admin (Suppression Anciens Endpoints)**

- Suppression des 6 endpoints backend (download, cancel, progress, apply, rollback, status)
  [`admin.py:107`](../../src/api/routes/admin.py#L107)

**Test Script (Validation)**

- Script de test argparse pour valider tous les endpoints backend
  [`test_api_admin_backend.py:1`](../../scripts/test_api_admin_backend.py#L1)

**Corrections Appliquées**

- Sérialisation JSON corrigée pour ServiceVersionInfo et BackupInfo
  [`update_manager.py:219`](../../src/admin/update_manager.py#L219)

**Integration (Router Registration)**

- Import du nouveau router admin_backend dans __init__.py
  [`__init__.py:3`](../../src/api/routes/__init__.py#L3)
