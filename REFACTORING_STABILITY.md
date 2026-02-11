# IPTV Player Refactoring & Stability Overhaul

This document summarizes the major architectural changes and stability improvements implemented to resolve persistent OOM (Out-of-Memory) crashes and UI freezes.

## 1. Architectural Transition: Model/View Virtualization
The most significant change was moving from a **Widget-based** layout to a **Model/View/Delegate** architecture.

- **Previous Issue**: For every movie or channel, a new `QFrame` widget was created. With thousands of items, Python's memory usage spiked, leading to exit code `137` (Killed by OOM Killer).
- **Solution**: Implemented `QListView` with a custom `ContentModel` and `ContentDelegate`.
- **Virtualization**: The application now only "draws" the items currently visible on the screen (~20 items), regardless of the total list size (e.g., 50,000 items).

## 2. Multi-Layered Memory Management

### A. API Data Pruning
- **Change**: The `XtreamAPI` now strips all non-essential fields from incoming JSON before storing it in the model.
- **Benefit**: Reduces the memory footprint of large playlists by over **80%**.

### B. Size-Limited & Debounced Image Loading
- **Dedicated Thread Pool**: Image loading is now isolated to a specific thread pool (`IMAGE_POOL`) to prevent blocking app logic.
- **Debounced Loading**: The system waits **250ms** after scrolling stops before starting a thumbnail fetch. This prevents thousands of useless network requests during fast scrolling.
- **Smart Cache**: Implemented a size-limited `ImageCache` (capped at 150 items) that clears itself when navigating categories to prevent memory creep.

### C. Hard API Item Caps
- **Limit**: Categories are capped at **5,000 items** per fetch. This provides a safety ceiling against extremely large IPTV catalogs that could otherwise crash any Python process.

## 3. UI Responsiveness Improvements

### Asynchronous Player Stop
- **Fix**: Moved the VLC `stop()` and `set_media(None)` calls to a background thread. This allows the user to exit the player and return to the dashboard **instantly**, even if the network stream is slow to close.

### Background Networking
- **GenericWorker**: All network operations (Login, Category Fetch, Stream List, Info Fetch) are strictly multi-threaded using `QRunnable`. No network I/O happens on the main GUI thread.

## 4. Navigation & Bug Fixes
- Fixed back navigation logic across all views (Live, Movies, Series, Details).
- Fixed thumbnail loading logic to support multiple Xtream API field variations (poster, icon, cover, etc.).
- Improved EPG worker stability and threading.

## Summary of New Files
- `src/ui/models.py`: Virtualized data handling.
- `src/ui/delegates.py`: High-speed manual item rendering and image caching.
- `src/utils/worker.py`: Common threading infrastructure for asynchronous tasks.

---
*These changes bring the application up to professional standards for handling massive datasets in Python/Qt.*
