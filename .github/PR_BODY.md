## Summary

Complete CSS refactor and theme system for SigmaHQ RAG.

## Changes

### Architecture
- Modular CSS split into ase/, layout/, components/ packages, replacing monolithic main.css and _shared-layout.css
- Shared Jinja layout (layout.html) with blocks for sidebar, content, scripts — all pages inherit consistently
- Chat migrated from standalone chat.html to chat/index.html extending shared layout
- Removed 490-line _shared-layout.css and unused PLAN_draft.md

### Theme system
- Light/dark theme toggle (Sun/Moon slider) in top-right header
- 78 CSS custom properties in 	heme.css covering backgrounds, text, borders, shadows, colors
- All 21+ CSS/HTML/JS files migrated from hardcoded colors to ar(--*)
- Flash-prevention inline script in <head> reads localStorage before first render
- Smooth transitions on all major components with prefers-reduced-motion support

### UX fixes (Sally audit)
- --text-muted lightened from #999 to #777 for WCAG compliance
- Focus ring changed from #00FF00 to #3498db / #5dade2
- Native <button> font-size synced to 14px (matching .btn)
- order-radius standardized to 4px
- Fixed chat sidebar nesting causing white block in light mode
- Remaining hardcoded colors in status/nav migrated to variables

### Stats
44 files changed, 1493 insertions(+), 1180 deletions(-)
