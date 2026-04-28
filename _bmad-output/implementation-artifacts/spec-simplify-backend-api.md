---
title: 'Simplify Backend API - Remove Apply/Rollback, Download Updates by Default'
type: 'refactor'
created: '2026-04-28'
status: 'done'
context: []
baseline_commit: 'f266a38d67f1a489c9cdb0b92375feda8b3fc03a'
specLoopIteration: 1
---

## Intent

**Problem:** L'API backend actuelle a trop d'actions (`download`, `cancel`, `apply`, `rollback`) alors que le download manager fait déjà l'installation automatiquement via `_extract_and_install`.

**Approach:** Simplifier l'API en supprimant `apply` et `rollback`. L'action `download` fait déjà l'update par défaut. Rendre le paramètre `version` optionnel (défaut: "latest").

## Boundaries & Constraints

**Always:** 
- Retourner une API simple avec les actions: `download`, `cancel`, `progress`, `status`
- `download` sans version télécharge la version "latest"
- Maintenir la compatibilité SSE pour le progrès

**Ask First:** 
- Si une autre approche est proposée

**Never:** 
- Casser la fonctionnalité de téléchargement et d'installation
- Supprimer les services supportés (llama.cpp, qdrant)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Download latest | POST `/admin/backend/?action=download&service=llama` | `{"download_id": ..., "status": ...}` | 400 si service manquant |
| Download specific | POST `/admin/backend/?action=download&service=llama&version=main` | `{"download_id": ..., "status": ...}` | 400 si service manquant |
| Cancel download | POST `/admin/backend/?action=cancel&download_id=...` | `{"download_id": ..., "status": "cancelled"}` | 400 si download_id invalide |
| Download progress | GET `/admin/backend/?action=progress&download_id=...` | SSE stream | 400 si download_id invalide |
| Update status | GET `/admin/backend/?action=status` | `{"services": ..., "available_backups": ...}` | 500 en cas d'erreur |
| Invalid action | GET `/admin/backend/?action=invalid` | 400 `{"error": "Invalid action"}` | Retourner code 400 |

## Code Map

- `src/api/routes/admin_backend.py` -- Modifier pour supprimer apply/rollback, rendre version optionnelle
- `src/admin/download_manager.py` -- Déjà fait: _extract_and_install appelé après download
- `src/admin/update_manager.py` -- Garder get_status(), supprimer apply_update() et rollback()
- `scripts/test_api_admin_backend.py` -- Mettre à jour pour refléter les changements

## Tasks & Acceptance

**Execution:**

- [x] `src/api/routes/admin_backend.py` -- Supprimer `apply` et `rollback` de `VALID_POST_ACTIONS` -- Supprimer les cas dans le match -- Rendre `version` optionnel (défaut "latest") dans `backend_post`
- [x] `src/admin/update_manager.py` -- Supprimer les méthodes `apply_update()` et `rollback()` -- Garder `get_status()` et `_check_service_health()`
- [x] `src/admin/download_manager.py` -- Vérifier et améliorer le téléchargement pour llama.cpp et qdrant -- Corriger `_extract_and_install()` si nécessaire -- S'assurer que l'extraction fonctionne pour les deux services
- [x] `src/admin/version_manager.py` -- Vérifier la récupération des releases GitHub pour llama.cpp et qdrant -- S'assurer que `find_matching_asset()` retourne le bon asset pour chaque service
- [x] `scripts/test_api_admin_backend.py` -- Supprimer les commandes apply et rollback -- Supprimer les fonctions cmd_apply() et cmd_rollback() -- Rendre `--version` optionnel avec défaut "latest" pour download -- Mettre à jour le parser d'arguments
- [x] `docs/Back_API.md` -- Créer documentation complète de l'API backend -- Définir tous les endpoints (GET/POST) -- Documenter les paramètres et réponses attendues

**Acceptance Criteria:**

- Given action download sans version, when POST `/admin/backend/?action=download&service=llama`, then télécharge la version latest et installe (ou skipe si déjà installée)
- Given action download avec version, when POST `/admin/backend/?action=download&service=llama&version=X`, then télécharge la version X et installe (ou skipe si déjà installée)
- Given version déjà installée, when POST `/admin/backend/?action=download&service=llama&version=X`, then retourne status "skipped" avec message "Version already installed"
- Given action apply supprimée, when POST `/admin/backend/?action=apply&service=llama`, then retourne erreur 400 "Invalid action"
- Given action rollback supprimée, when POST `/admin/backend/?action=rollback&service=llama`, then retourne erreur 400 "Invalid action"
- Given action status, when GET `/admin/backend/?action=status`, then retourne le statut (utilise update_manager.get_status())

## Design Notes

L'action `download` dans `download_manager.py` fait déjà l'installation via `_extract_and_install()` (ligne 202-204). Donc `apply` est redondant.

Le `version` par défaut "latest" sera géré par `version_manager.get_release(service, version)` qui accepte déjà "latest".

## Verification

**Commands:**

- `curl -X POST "http://localhost:8000/admin/backend/?action=download&service=llama"` -- expected: JSON avec download_id (télécharge latest)
- `curl -X POST "http://localhost:8000/admin/backend/?action=download&service=llama&version=main"` -- expected: JSON avec download_id (télécharge version main)
- `curl -X POST "http://localhost:8000/admin/backend/?action=apply&service=llama"` -- expected: erreur 400
- `ruff check src/api/routes/admin_backend.py` -- expected: pas d'erreurs
- `mypy src/api/routes/admin_backend.py` -- expected: pas d'erreurs de type

## Suggested Review Order

**API Simplification (Entry Point)**

- Suppression d'apply/rollback dans admin_backend.py, version optionnelle par défaut "latest"
  [`admin_backend.py:29`](../../src/api/routes/admin_backend.py#L29)

- Suppression des cas apply/rollback dans le match POST
  [`admin_backend.py:131`](../../src/api/routes/admin_backend.py#L131)

**Update Manager Cleanup**

- Suppression des méthodes apply_update() et rollback(), conservation de get_status()
  [`update_manager.py:1`](../../src/admin/update_manager.py#L1)

**Download Manager Improvements**

- Amélioration de _extract_and_install() pour une meilleure gestion des erreurs et extraction
  [`download_manager.py:226`](../../src/admin/download_manager.py#L226)

**Version Manager Improvements**

- Simplification de find_matching_asset() pour llama.cpp et qdrant
  [`version_manager.py:148`](../../src/admin/version_manager.py#L148)

**Test Script Update**

- Suppression des commandes apply/rollback, version optionnelle avec défaut "latest"
  [`test_api_admin_backend.py:12`](../../scripts/test_api_admin_backend.py#L12)

**Documentation**

- Création de la documentation complète de l'API backend
  [`Back_API.md:1`](../../docs/Back_API.md#L1)
