# Static Web Assets (`web/static/`)

## 1. Directory Overview & Role
This directory contains static client-side web assets for the **Algerian Real Estate Mobile Studio** web application. It is served directly by the Starlette ASGI server at `/static` and mounted at root `/` to provide smartphone operators with an instant, zero-friction interface for video capture, script customizing, and promo cut generation.

---

## 2. File Manifest

| File | Type | Purpose |
| :--- | :--- | :--- |
| [`index.html`](file:///home/pluto/projects/lok/web/static/index.html) | HTML5 / Single Page App | Mobile-first responsive web studio supporting live camera capture, preset selection, custom script editing, ducking sliders, and video preview. |
| [`README.md`](file:///home/pluto/projects/lok/web/static/README.md) | Markdown | Documentation for client-side assets and interface design. |

---

## 3. UI Features & Mobile Usability
- **Direct Smartphone Camera Ingestion**: Uses HTML5 `<input type="file" accept="video/*" capture="environment">` enabling direct hardware video camera recording or gallery upload.
- **RTL Arabic Typography**: Full Arabic support using Google Cairo font with responsive French subtitle tags for real estate listings.
- **Dynamic Preset Selector**: Instant selection cards for Algiers Luxury F4, Oran Seaview Villa, Constantine Commercial, and Rental Apartment.
- **Sidechain Ducking Control**: Real-time interactive slider allowing users to adjust ambient synth pad volume levels (5% to 50%).
- **Interactive Result Showcase**:
  - HTML5 video playback with native controls.
  - Horizontally scrollable keyframe gallery showing timestamps.
  - Direct download buttons for the final marketing video cut (`cut_<job_id>.mp4`) and narration track (`narration_<job_id>.wav`).
  - Telemetry badges displaying rendering time, resolution, orientation, and speech synthesizer used.
