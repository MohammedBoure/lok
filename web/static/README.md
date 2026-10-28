# lok • Minimalist Studio & Bootstrap Admin Portal Architecture (`web/static/`)

## 1. Executive Summary & Design Mission
The `web/static/` directory provides the client-side user interface for **'lok'** (`منصة إنتاج الفيديو الذكي للتجار والشركات`), following a radical minimalist redesign and a modern high-contrast Black & White monochrome aesthetic.

The platform is structured into two core environments:
1. **Public/Merchant Client UI (`/` -> `index.html`)**:
   - Modern Black & White (`lok`) styling with zero clutter.
   - **Gated Authentication**: Unauthenticated visitors are greeted with a clean login screen before any studio features or controls become visible.
   - **Minimalist Studio ("الواجهة نظيفة وفارغة")**: Keeps strictly essential controls:
     1. Pre-recorded video upload area (dropzone and file picker for ready videos; camera recording streams removed).
     2. Detailed prompt textarea (instructing speech speed, visual scenes, emotional tone, and Algerian Darja/Arabic dialect).
     3. Simple Settings button (`"⚙️ الإعدادات"`) opening a focused settings view with a Back button (`"← العودة للاستوديو"`).
     4. 1-Click Produce Video button (`"✨ إنتاج الفيديو التسويقي"`).
   - **Focused Settings View**:
     - Current balance and remaining quota indicator (daily remaining, weekly remaining, subscription validity).
     - Recommendations Manager (create, edit, delete prompt snippets, and attach directly to the studio prompt).
     - Voiceover Artist Picker with Algerian Darja audition audio player (`ar-XA-Standard-A/B/C/D`).
     - Session Logout button.
2. **Dedicated Bootstrap Admin Portal (`/admin` -> `admin.html`)**:
   - Built with **Bootstrap 5** for mobile and desktop responsiveness.
   - Dedicated administrator login view for credentials `pluto` and `plutosw4`.
   - Complete Accounts Management Table listing: username, business name, category, active/suspended status, start validity date (`valid_from`), expiration date (`expires_at`), daily quota, and weekly quota.
   - Modals for adding new accounts, editing details/quotas, changing passwords, and reviewing historical activity event logs.

---

## 2. File Manifest & Responsibilities

| File | Language / Framework | Primary Responsibility |
| :--- | :--- | :--- |
| [`index.html`](file:///home/pluto/projects/lok/web/static/index.html) | Semantic HTML5 (RTL) | Minimalist 'lok' client UI layout: gated login screen, pre-recorded video dropzone, detailed prompt textarea, produce button, settings modal with Back button, balance meters, recommendations manager, and voiceover Darja audition player. |
| [`style.css`](file:///home/pluto/projects/lok/web/static/style.css) | Modern CSS3 | Black & White monochrome design system: deep black backgrounds (`#09090b`), pure white buttons (`.btn-bw-primary`), dropzone states, custom textareas, settings overlays, and responsive mobile breakpoints. |
| [`app.js`](file:///home/pluto/projects/lok/web/static/app.js) | Vanilla ES2022 JavaScript | Client state engine: session gating, pre-recorded file ingestion, prompt binding, recommendations CRUD and prompt attachment, Darja voice audition playback, quota updates, and video production dispatch. |
| [`admin.html`](file:///home/pluto/projects/lok/web/static/admin.html) | HTML5 / Bootstrap 5 | Dedicated Admin Portal served at `/admin`: authentication for `pluto` / `plutosw4`, accounts management table, quota configuration, validity dates, password resets, and activity event log viewer. |
| [`README.md`](file:///home/pluto/projects/lok/web/static/README.md) | Markdown (English) | Complete technical documentation, state workflows, user journey diagrams, and REST API integration specifications. |

---

## 3. UI Architecture & Navigation Workflow

```mermaid
flowchart TD
    subgraph ClientSession["Client UI Navigation Flow (lok)"]
        Start(["User Visits /"]) --> CheckToken{"Has Active Session?"}
        CheckToken -->|No| GatedLogin["Gated Login Screen (#loginView)"]
        CheckToken -->|Yes| Studio["Minimalist Studio UI (#studioView)"]

        GatedLogin -->|Submit Credentials / 1-Tap Demo| AuthVerify["Verify Token / Login API"]
        AuthVerify -->|Valid| Studio

        Studio --> Upload["1. Upload Pre-recorded Video (#videoDropzone)"]
        Studio --> Prompt["2. Detailed Prompt (#promptTextarea)"]
        Studio --> SettingsBtn["3. Simple Settings Button (#btnOpenSettings)"]
        Studio --> ProduceBtn["4. Produce Video (#btnProduceVideo)"]

        SettingsBtn --> SettingsModal["Settings View (#settingsModal)"]
        SettingsModal --> BackBtn["Back Button: ← العودة للاستوديو (#btnSettingsBack)"]
        BackBtn --> Studio

        SettingsModal --> Quotas["Current Balance & Quota Display"]
        SettingsModal --> RecManager["Recommendations Manager (CRUD + Attach)"]
        SettingsModal --> VoicePicker["Voiceover Artist Picker & Darja Audition"]
        SettingsModal --> LogoutBtn["Logout Button (#btnLogout)"]

        RecManager -->|Attach Snippet| Prompt
        LogoutBtn --> GatedLogin
    end

    subgraph AdminPortal["Admin Portal Navigation Flow (/admin)"]
        AdminVisit(["Admin Visits /admin"]) --> CheckAdmin{"Admin Logged In?"}
        CheckAdmin -->|No| AdminLogin["Admin Login View (pluto / plutosw4)"]
        CheckAdmin -->|Yes| AdminDash["Admin Dashboard View"]

        AdminLogin -->|Authenticate| AdminDash
        AdminDash --> AccountsTable["Accounts Table (valid_from, expires_at, quotas)"]
        AdminDash --> AddModal["Add Account Modal"]
        AdminDash --> EditModal["Edit Account Modal"]
        AdminDash --> PassModal["Change Password Modal"]
        AdminDash --> LogsModal["Activity Event Logs Modal"]
        AdminDash --> AdminLogout["Logout"] --> AdminLogin
    end
```

---

## 4. 'lok' Studio UI Details

### A. Pre-Recorded Video Upload Area
- Clean drag-and-drop zone (`#videoDropzone`) with hidden `<input type="file" id="videoFileInput" accept="video/*">`.
- Dedicated exclusively to pre-recorded / phone camera video files (MP4, MOV, WebM).
- In-browser live camera recording controls and viewfinder elements have been eliminated to ensure pure zero-friction simplicity.
- Automatically computes and displays video file name, size (MB), and format.

### B. Detailed Prompt Input
- Generous, high-contrast textarea (`#promptTextarea`) guiding merchants to define:
  1. **Speech Speed (`سرعة الإلقاء`)**: Dynamic pacing vs. calm measured delivery.
  2. **Visual Scenes (`المشاهد المرئية`)**: Architectural highlights, interior lighting, exterior facades, product closeups.
  3. **Tone (`نبرة الصوت`)**: Prestigious commercial, warm and inviting, or high-energy youth.
  4. **Dialect (`اللهجة`)**: Algerian Darja (Algiers, Oran, Constantine) or Modern Standard Arabic.
- Integrated indicator chip (`#attachedRecIndicator`) showing active attached recommendation template.

### C. Settings View with Back Button
Accessible via `#btnOpenSettings` and dismissible via `#btnSettingsBack` (`"← العودة للاستوديو"`):
1. **Balance & Quota Indicator**:
   - Daily videos remaining / total (`#quotaDailyRemaining` / `#quotaDailyTotal`).
   - Weekly videos remaining / total (`#quotaWeeklyRemaining` / `#quotaWeeklyTotal`).
   - Active subscription validity date (`#quotaExpiryText`).
   - High-contrast visual progress meter (`#quotaMiniBarFill`).
2. **Recommendations Manager ("التوصيات")**:
   - Manage reusable prompt snippets.
   - **Create**: Add new recommendation with instant persistence.
   - **Edit**: Inline modal prompt to edit recommendation text.
   - **Delete**: Remove obsolete recommendation.
   - **Attach (`🎯 تطبيق في التوجيه`)**: Instantly populates the recommendation text into `#promptTextarea`, shows confirmation feedback, and returns smoothly to the studio view.
3. **Voiceover Artist Picker**:
   - Selection of 4 neural voice models:
     - `ar-XA-Standard-A`: Aisha (warm female tone in Algerian Darja).
     - `ar-XA-Standard-B`: Amine (authoritative male tone in Algerian Darja).
     - `ar-XA-Standard-C`: Karim (dynamic youth male tone in Algerian Darja).
     - `ar-XA-Standard-D`: Meriem (elegant female tone in Algerian Darja).
   - Audio Audition Player (`"▶ عينة صوتية بالدارجة"`): Plays real audio sample streamed from `/api/voices/{voice_id}/sample` with Web Audio harmonic synth fallback if offline.
4. **Session Logout**:
   - Invalidates local credentials and smoothly resets interface to the gated login view.

---

## 5. Bootstrap Admin Portal (`/admin` -> `admin.html`)

### A. Dedicated Authentication
- Standard credentials: **`pluto`** / **`plutosw4`**.
- Accessible directly at `/admin` or `/static/admin.html`.

### B. Accounts Management Table
Responsive Bootstrap 5 dark table (`#accountsTable`):
- **User ID**: System numeric identifier.
- **Username**: Unique tenant handle (`dar_al_nokhba`, `auto_algerie`, etc.).
- **Business Name**: Commercial brand or company name.
- **Category**: Sector taxonomy badge.
- **Status**: Live status badge (`Active` / `Suspended`).
- **Validity Start Date (`valid_from`)**: Account initiation / subscription commencement.
- **Expiration Date (`expires_at`)**: Subscription termination date.
- **Daily Quota**: Current usage vs. daily limit.
- **Weekly Quota**: Current usage vs. weekly limit.
- **Action Buttons**:
  - `✏️ تعديل`: Modifies business name, category, quotas, validity dates, and status.
  - `🔑 كلمة المرور`: Resets account password.
  - `📜 السجل`: Opens the chronological activity event logs modal.
  - `تبديل الحالة`: Instantly toggles between Active and Suspended states.

### C. Activity Event Log Viewer Modal
Displays timestamped historical actions for any tenant:
- Account creation and initial quota allocation.
- Subscription renewals and quota revisions.
- Password change events.
- Video generation dispatches and completed cuts.
- Administrative status overrides.

---

## 6. REST API Integration Matrix

| Endpoint | Method | Caller | Payload / Headers | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `/admin` | `GET` | Browser | None | Serves the Bootstrap 5 Admin Portal (`admin.html`). |
| `/api/auth/login` | `POST` | Client UI | JSON: `username`, `password` | Authenticates merchant and creates session token. |
| `/api/auth/logout` | `POST` | Client / Admin | `Authorization: Bearer <token>` | Invalidation of active session. |
| `/api/auth/session` | `GET` | Client UI | `Authorization: Bearer <token>` | Reconnects existing session on page load. |
| `/api/admin/login` | `POST` | Admin Portal | JSON: `username`, `password` (`pluto` / `plutosw4`) | Authenticates administrator. |
| `/api/admin/accounts` | `GET` | Admin Portal | `Authorization: Bearer <token>` | Retrieves full list of merchant accounts. |
| `/api/admin/accounts` | `POST` | Admin Portal | JSON: account fields & quotas | Registers new merchant account. |
| `/api/admin/accounts/{id}` | `PATCH` | Admin Portal | JSON: quota, status, dates | Updates merchant account metadata and quotas. |
| `/api/admin/accounts/{id}/logs`| `GET` | Admin Portal | `Authorization: Bearer <token>` | Retrieves chronological activity events for tenant. |
| `/api/voices/{id}/sample` | `GET` | Client UI | `voice_id` parameter | Streams Algerian Darja audio sample for audition. |
| `/api/jobs/create` | `POST` | Client UI | `multipart/form-data`: `video`, `script`, `voice` | Dispatches video production job. |
| `/api/status/{job_id}` | `GET` | Client UI | `job_id` parameter | Live status polling for production job. |

---

## 7. Strict Character Mapping Compliance
As mandated by platform directives, all text, comments, documentation, and HTML/CSS/JS code maintain strict typography standards with **zero occurrences of the forbidden character U+0669**.
