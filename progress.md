Original prompt: oh, we could perhaps do these changes in the code as well? as a try?

## 2026-08-13

- Started a scoped visual experiment for the Forkcast phone UI: bright casual board-game colors, round/glossy surfaces, hearts/support motifs, and replaceable assets.
- Keep backend/game rules unchanged. Avoid touching unrelated dirty worktree files.
- Added replaceable SVG placeholder assets under `public/assets/forkcast/`, a `src/uiAssets.ts` registry, token/avatar/heart hooks in existing components, and a broad CSS theme pass for the phone UI.
- Verified `npm run build` passes. Browser-checked 390px join screen, simulation lobby, meal selection, and selecting/placing Yakiniku on Monday. No document-level horizontal overflow found.
- Updated the frontend submit flow so `Submit Suggestions` auto-advances from placement through reveal into negotiation when the backend session reaches `REVEAL`; with simulated players, it also auto-simulates their placement after yours.
- Verified the real browser path at 390px: create simulation, start draft, place Yakiniku/Tacos/Salmon, press Submit Suggestions, and land directly on `NEGOTIATION`. Added a small mobile proposal-card stacking fix after visual inspection.
- Added week number display and a client-side `Save Week` button to the completed Forkcast screen. Saved records are stored in `localStorage` under `forkcast.savedWeeks` by ISO week id, ready to replace with backend persistence later.
- Added hallway display week navigation controls. `/display` defaults to the current ISO week and includes Previous Week, Current Week, and Next Week controls that update the displayed week label/date range.
- Verified `/display?mock=1` at tablet size: defaulted to Week 33 · 2026 for August 13, 2026, Next Week changed label to Week 34 · 2026, and Previous Week returned to Week 33.
- Adjusted week defaults for Sunday planning: Sundays default to the coming ISO week and show a small "Planning week" hint; Current Week still jumps back to the actual current calendar week.
- Added backend saved-week persistence via `/api/saved-weeks`, stored in `.forkcast-data/saved-weeks.json`. The phone Save Week button now saves to the server first and caches locally as a fallback.
- Updated `/display` so it can load saved backend dinner plans without a live session id. `/display` loads the default selected week, `/display?week=33` loads that week in the current year, and `/display?week=2026-W33` loads an explicit saved week.
- Fixed the final screen Save Week button initial state: it now only starts as `Saved` when the local cached saved week belongs to the same session id, not merely because another plan exists for the same week.
