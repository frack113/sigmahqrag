# Plan de Refactoring — Pages Frontend

## Phase 1 — Critiques (Urgent) ✅ COMPLETÉ

### 1.1 Bloquer les clics concurrents pendant le streaming
**Fichier :** `src/presentation/static/js/internal/config.js`
- ✅ Ajouté `_isSaving` flag global
- ✅ Ajouté `if (_isSaving) return;` dans `saveBackendConfig()`
- ✅ Ajouté `if (_isSaving) return;` dans `saveLoggingConfig()`
- ✅ Ajouté `if (_isSaving) return;` dans `saveBackendServiceConfig()`
- ✅ Ajouté `.finally(() => { _isSaving = false; })` dans les 3 fonctions

### 1.2 Fallback pour le toggle theme
**Fichier :** `src/presentation/templates/shared/_header.html.j2`
- ✅ Vérifié : le checkbox existe déjà avec handler JS
- ✅ Le toggle fonctionne sans JavaScript via CSS `:checked`

---

## Phase 2 — Robustesse ✅ COMPLETÉ

### 2.1 Timeout sur les requêtes API ✅
**Fichier :** `src/presentation/static/js/internal/config.js`
- ✅ Ajouté fonction `fetchWithTimeout()` avec AbortController (10s timeout)

### 2.2 Validation des clés API ⏭️
**Statut :** Non trouvé — aucune fonction `saveApiKey()` existante

### 2.3 Utiliser le système de confirmation existant ✅
**Fichiers :** `prompts.js`, `repo-browser.js`
- ✅ Remplacé `confirm()` par `showConfirm()` dans `deletePrompt()`
- ✅ Remplacé `confirm()` par `showConfirm()` dans `syncRepo()`
- ✅ Remplacé `confirm()` par `showConfirm()` dans `deleteRepo()`
- ✅ `vectordb.js` utilise déjà `showConfirm()`

### 2.4 Debounce sur la recherche de fichiers ⏭️
**Statut :** Déjà implémenté dans `logs.js` (ligne 39-41)

### 2.5 Reconnexion SSE automatique ✅
**Fichier :** `src/presentation/static/js/internal/logs.js`
- ✅ Déjà implémenté avec retry 3s (ligne 144-159)

### 2.6 Feedback visuel pendant le chargement modèle ✅
**Fichier :** `src/presentation/static/js/internal/config.js`
- ✅ `_setLlmBusy()` et `_setEmbBusy()` gèrent déjà le feedback visuel

### 2.7 Auto-refresh status Qdrant ✅
**Fichier :** `src/presentation/static/js/internal/vectordb.js`
- ✅ Ajouté `setInterval(loadVectorDB, 30000)` pour refresh toutes les 30s

---

## Phase 3 — Qualité du code ✅ COMPLETÉ

### 3.1 Encapsulation de l'état config ⏭️
**Statut :** `window.__CONFIG__` non trouvé — CONFIG est un const local

### 3.2 Skeleton loader pour les sections ⏭️
**Statut :** `fetchSections()` non trouvé — Les sections sont statiques dans les templates

### 3.3 Validation schema config LLM ⏭️
**Statut :** `saveLLMConfig()` non trouvé — La config LLM utilise `saveBackendServiceConfig()`

### 3.4 Vérification police Inter ⏭️
**Statut :** Police `system-ui, -apple-system, sans-serif` utilisée — Inter non référencé

---

## Résumé Phase 3

Tous les items de Phase 3 sont **non applicables** — le code existe déjà sous une forme différente ou les fonctions cibles n'existent pas.

---

## Ordre d'exécution

1. **Phase 1** ✅ (15 min) — Corrections critiques
2. **Phase 2** ✅ (30 min) — Robustesse et UX
3. **Phase 3** ✅ (5 min) — Vérification qualité (items non applicables)
