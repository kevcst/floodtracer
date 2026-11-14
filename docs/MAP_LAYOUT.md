# Immersive map

Branch: `feat/map-immersive`. Based directly on main commit `bf0fc92`.

The explorer is now the landing screen and starts the existing guided tour automatically. The original site palette (including automatic light/dark mode), fonts, published datasets, calculations and five tour steps are preserved.

The tour offers Previous, Next, chapter shortcuts, source inspection and Skip. Finishing or skipping reveals free exploration: all six locations, five scientific layers, visibility switches, comparison dates, opacity, downloads and spot histories remain available. The active location and layer stay visible in the header. Context, impact tables, graphs, validation, methods and downloads are available through Study & results instead of preceding the map. Sources & limits opens the contextual source panel without requiring tour completion.

Presentation-specific behavior: the map fills the viewport, the tour floats at the left, and tools open at the right.

On small screens the story becomes a compact lower panel and tools open as a full-screen panel. The map supports pan, zoom and the existing Before / After divider. Chapters are manual and Next waits for loading. No analytical outputs were regenerated or scientifically revalidated by this presentation change.

Run from the repository root:

```bash
python3 -m http.server 8003 --bind 127.0.0.1 --directory app
```

Open http://127.0.0.1:8003. No build or backend is required.
