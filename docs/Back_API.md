# Backend API Documentation

API d'administration pour la gestion des backends (llama.cpp et Qdrant).

Base URL: `http://localhost:8000/admin/backend/`

## Vue d'ensemble

L'API backend unifiée utilise un pattern action-based avec des paramètres query `action` et `service`. Elle permet de télécharger et mettre à jour les binaires des services locaux.

**Services supportés :**
- `llama` (llama.cpp server)
- `qdrant` (Qdrant vector store)

**Actions disponibles :**
- `download` - Télécharger et installer une version (GET/POST)
- `cancel` - Annuler un téléchargement en cours (POST)
- `progress` - Suivre le progrès d'un téléchargement (GET, SSE)
- `status` - Obtenir le statut des versions et backups (GET)

---

## GET /admin/backend/

Endpoint unifié pour les opérations de lecture.

### Paramètres Query

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `action` | string | Oui | Action à effectuer : `progress`, `status` |
| `service` | string | Non | Service concerné : `llama`, `qdrant` |
| `download_id` | string | Non* | ID du téléchargement (requis pour `progress`) |

### Actions

#### 1. progress - Suivi du progrès

Retourne un flux SSE (Server-Sent Events) avec le progrès du téléchargement.

**Paramètres :**
- `action=progress`
- `download_id` (requis)

**Réponse SSE :**
```json
{"percentage": 50.5, "bytes_downloaded": 52428800, "total_bytes": 104857600, "speed_bps": 1048576}
```

**Status final :**
```json
{"status": "completed", "file_path": "/path/to/binary"}
{"status": "cancelled"}
{"status": "failed", "error": "..."}
```

#### 2. status - Statut des versions

Retourne le statut actuel des services et les backups disponibles.

**Paramètres :**
- `action=status`

**Réponse :**
```json
{
  "services": {
    "llama_cpp": {
      "current_version": "main",
      "last_updated": "2026-04-28T12:00:00"
    },
    "qdrant": {
      "current_version": "v1.7.0",
      "last_updated": "2026-04-27T10:00:00"
    }
  },
  "available_backups": [
    {
      "backup_id": "backup-123",
      "service": "llama.cpp",
      "version": "main",
      "created": "2026-04-28T12:00:00",
      "size_bytes": 104857600
    }
  ]
}
```

---

## POST /admin/backend/

Endpoint unifié pour les opérations d'écriture.

### Paramètres Query

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `action` | string | Oui | Action à effectuer : `download`, `cancel` |
| `service` | string | Non* | Service concerné : `llama`, `qdrant` (requis pour `download`) |
| `version` | string | Non | Version à télécharger (défaut: `latest`) |
| `download_id` | string | Non* | ID du téléchargement (requis pour `cancel`) |

### Actions

#### 1. download - Télécharger et installer

Télécharge une version et l'installe automatiquement. Si aucune version n'est spécifiée, télécharge la version `latest`.

**Paramètres :**
- `action=download`
- `service` (requis) : `llama` ou `qdrant`
- `version` (optionnel, défaut: `latest`)

**Réponse :**
```json
{
  "download_id": "uuid-123",
  "status": "started",
  "service": "llama.cpp",
  "version": "main",
  "target_path": "/path/to/bin/llama-cpp"
}
```

**Notes :**
- Le téléchargement s'effectue en arrière-plan
- L'installation est automatique après téléchargement
- Utiliser l'action `progress` avec le `download_id` pour suivre le progrès

#### 2. cancel - Annuler un téléchargement

Annule un téléchargement en cours et nettoie les fichiers partiels.

**Paramètres :**
- `action=cancel`
- `download_id` (requis)

**Réponse :**
```json
{
  "download_id": "uuid-123",
  "status": "cancelled",
  "message": "Download cancelled and partial file cleaned up"
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 400 | Requête invalide (action, service manquant, etc.) |
| 404 | Ressource non trouvée (download_id invalide) |
| 500 | Erreur interne du serveur |

**Format d'erreur :**
```json
{"error": "Invalid action"}
{"error": "Valid service required (llama, qdrant)"}
{"error": "download_id required for action=progress"}
```

---

## Exemples avec curl

### Télécharger la version latest (par défaut)
```bash
curl -X POST "http://localhost:8000/admin/backend/?action=download&service=llama"
```

### Télécharger une version spécifique
```bash
curl -X POST "http://localhost:8000/admin/backend/?action=download&service=llama&version=main"
```

### Suivre le progrès (SSE)
```bash
curl "http://localhost:8000/admin/backend/?action=progress&download_id=uuid-123"
```

### Annuler un téléchargement
```bash
curl -X POST "http://localhost:8000/admin/backend/?action=cancel&download_id=uuid-123"
```

### Obtenir le statut
```bash
curl "http://localhost:8000/admin/backend/?action=status"
```

---

## Script de test

Utiliser le script `scripts/test_api_admin_backend.py` pour tester l'API :

```bash
# Télécharger la version latest
python scripts/test_api_admin_backend.py download --service llama

# Télécharger une version spécifique
python scripts/test_api_admin_backend.py download --service llama --version main

# Annuler un téléchargement
python scripts/test_api_admin_backend.py cancel --download-id uuid-123

# Suivre le progrès
python scripts/test_api_admin_backend.py progress --download-id uuid-123

# Obtenir le statut
python scripts/test_api_admin_backend.py status
```

---

## Notes techniques

- L'API utilise `create_download_manager()` pour gérer les téléchargements
- L'API utilise `create_update_service()` pour le statut (via `get_status()`)
- Les téléchargements supportent les formats `.zip` et `.tar.gz`
- L'installation extrait automatiquement l'archive dans `BIN_DIR`
- Le progrès est disponible via SSE (Server-Sent Events)
