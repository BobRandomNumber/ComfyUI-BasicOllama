# Change Log

## [0.2.0] - 2026-01-11

### Added
- **Asynchronous Model Loading:** The Ollama model list is now fetched dynamically via the frontend. This ensures **zero impact** on ComfyUI startup and browser loading times.
- **Visual Connection Alerts:** The node now turns **dark red** if it cannot reach the Ollama backend (either at startup or during generation), providing immediate visual feedback.
- **Dynamic API Endpoint:** Added a custom backend route (`/basic_ollama/models`) to handle non-blocking model fetching.
- **Runtime Connection Monitoring:** The node now detects if the connection to Ollama is lost *during* generation and alerts the user visually.
- **Improved Logging:** Console logs now explicitly state which model a system prompt is being applied to (e.g., "Applying User provided system prompt to llama3").

### Changed
- **Performance Optimization:** Removed blocking `requests` calls during the Python node registration phase.
- **UI Responsiveness:** The `ollama_model` widget now initializes with a "Loading..." placeholder and updates once the backend responds.
- **Code Cleanup:** Removed unused dependencies (`ctypes`) and replaced custom console coloring with standard logging for better compatibility.
- **README Updates:** Documentation now reflects the new async architecture and visual status indicators.

### Fixed
- Fixed an issue where a slow or missing Ollama connection could cause ComfyUI to hang or delay browser initialization.

## [0.1.0]

- Initial release.
