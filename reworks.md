# reworks.md — Plan de Correction `src/presentation`

## Status
- **Phase 1** ✅ Bugfixes critiques (XSS, delete URL, couleurs hardcodées) — `9f9fded`
- **Phase 2** ✅ Duplication cleanup (admin.js supprimé) — `d846b3e`
- **Phase 3.1-3.2** ✅ Suppression legacy (base.html.j2, legacy.css) — `0cfe4c4`
- **Phase 3.3** ✅ Extraction JS inline → fichiers externes — `9e0fff2`
- **Phase 3.4** ✅ Inline styles → classes CSS — `8406894`
- **Phase 4.1** ✅ Fix `spec_discovery` polling — `8406894`
- **Phase 4.2** ✅ Déjà fait (`_release-selector.html.j2`)
- **Phase 5.1** ✅ Ajout `<meta name="color-scheme">` — `8406894`
- **Phase 5.2** ⏸️ Reporté
- **Code Review #2** ✅ Bugs critiques C1-C3, H1-H2, dead code cleanup — `6596de8`

## Restant (ROI moyen/faible)
- **Duplication** : `github.js` vs `sigma-spec.js` (~95% identiques)
- **Duplication** : `escHtml`/`escAttr` dans 6 fichiers
- **Duplication** : LLM/Embedding model pairs dans `config.js`
- **JS inline** : `prompts.html.j2` (~200 lignes à extraire)
- **Couleurs hardcodées** : `logs.css`, `progress-bar.js`
- **XSS** : `local.html.j2:255` — `file.original_url` sans escAttr
- **H3** : `config.js` — 90 lignes de style inline dans `loadReleasesTable()`
- **Phase 5.2** : Extraire `--chat-*` de theme.css (faible ROI)
