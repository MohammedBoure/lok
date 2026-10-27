/**
 * Algerian Real Estate Mobile Studio - Client Application Logic (web/static/app.js)
 * Author: MohammedBoure
 * Role: Mobile Front-End & Real Estate UI/UX Lead (agy51)
 * Branch: frontend/agy51-one-click-ux-and-session-persistence
 */

(() => {
  'use strict';

  // ---------------------------------------------------------------------------
  // Session Persistence Constants
  // ---------------------------------------------------------------------------
  const ACTIVE_JOB_KEY = 'active_job_id';

  // ---------------------------------------------------------------------------
  // Catalog of Algerian Real Estate Presets (Offline Defaults & Fallback)
  // ---------------------------------------------------------------------------
  const DEFAULT_ALGERIAN_PRESETS = [
    {
      id: "algiers_f4_luxury",
      title_ar: "شقة فاخرة F4 - الجزائر العاصمة",
      title_fr: "Appartement F4 Haut Standing - Alger",
      description: "شقة فاخرة من أربع غرف بتشطيبات عالية الجودة في قلب العاصمة، إطلالة ساحرة وموقع هادئ قريب من كل المرافق الحيوية.",
    },
    {
      id: "oran_seaview_villa",
      title_ar: "فيلا عصرية بواجهة بحرية - وهران",
      title_fr: "Villa Moderne Vue sur Mer - Oran",
      description: "فيلا عصرية بواجهة بحرية خلابة في وهران، حديقة خاصة ومسبح وتصميم معماري رفيع يلبي أعلى معايير الرفاهية.",
    },
    {
      id: "constantine_commercial",
      title_ar: "محل تجاري استراتيجي - قسنطينة",
      title_fr: "Local Commercial Stratégique - Constantine",
      description: "محل تجاري في موقع استراتيجي نشط بمدينة قسنطينة، واجهة واسعة وحركة تجارية ممتازة مناسب لكافة المشاريع.",
    },
    {
      id: "rental_apartment",
      title_ar: "شقة مجهزة ومؤثثة للكراء",
      title_fr: "Appartement Équipé en Location",
      description: "شقة مؤثثة بالكامل ومجهزة بأحدث التجهيزات للكراء في موقع متميز، راحة وأمان لعائلتك.",
    },
  ];

  // ---------------------------------------------------------------------------
  // Application State
  // ---------------------------------------------------------------------------
  const state = {
    selectedFile: null,
    selectedSource: "",
    currentPresetId: "algiers_f4_luxury",
    presets: [...DEFAULT_ALGERIAN_PRESETS],

    // In-Browser Live Viewfinder & MediaRecorder State
    activeStream: null,
    mediaRecorder: null,
    recordedChunks: [],
    isRecording: false,
    currentFacingMode: "environment", // "environment" (rear) or "user" (selfie)
    recSecondsElapsed: 0,
    recTimerInterval: null,

    // Production & Pipeline State
    isProcessing: false,
    activeJobId: null,
    processingSecondsElapsed: 0,
    processingTimerInterval: null,
    statusPollInterval: null,
    stepAnimationTimeout: null,
    currentJobResult: null,
  };

  // ---------------------------------------------------------------------------
  // DOM Elements Cache
  // ---------------------------------------------------------------------------
  const dom = {
    systemStatusChip: document.getElementById("systemStatusChip"),

    // File Inputs & Capture Triggers
    cameraInput: document.getElementById("cameraInput"),
    galleryInput: document.getElementById("galleryInput"),
    btnNativeCamera: document.getElementById("btnNativeCamera"),
    btnToggleViewfinder: document.getElementById("btnToggleViewfinder"),
    btnGalleryUpload: document.getElementById("btnGalleryUpload"),
    dropZone: document.getElementById("dropZone"),

    // Viewfinder
    viewfinderPanel: document.getElementById("viewfinderPanel"),
    viewfinderVideo: document.getElementById("viewfinderVideo"),
    viewfinderNotice: document.getElementById("viewfinderNotice"),
    viewfinderNoticeText: document.getElementById("viewfinderNoticeText"),
    recBadge: document.getElementById("recBadge"),
    recStatusText: document.getElementById("recStatusText"),
    recTimer: document.getElementById("recTimer"),
    btnRecordToggle: document.getElementById("btnRecordToggle"),
    btnFlipCamera: document.getElementById("btnFlipCamera"),
    btnCloseViewfinder: document.getElementById("btnCloseViewfinder"),
    btnViewfinderCancel: document.getElementById("btnViewfinderCancel"),

    // Video Preview
    videoPreviewCard: document.getElementById("videoPreviewCard"),
    previewPlayer: document.getElementById("previewPlayer"),
    previewDuration: document.getElementById("previewDuration"),
    previewSize: document.getElementById("previewSize"),
    previewDimensions: document.getElementById("previewDimensions"),
    previewOrientation: document.getElementById("previewOrientation"),
    btnChangeVideo: document.getElementById("btnChangeVideo"),

    // 1-Click & Advanced Accordion
    advancedAccordion: document.getElementById("advancedAccordion"),
    presetsSelectorGrid: document.getElementById("presetsSelectorGrid"),
    scriptText: document.getElementById("scriptText"),
    wordCount: document.getElementById("wordCount"),
    charCount: document.getElementById("charCount"),
    speechEstDuration: document.getElementById("speechEstDuration"),
    btnResetScript: document.getElementById("btnResetScript"),
    btnClearScript: document.getElementById("btnClearScript"),

    // Audio & Ducking
    voiceSelect: document.getElementById("voiceSelect"),
    musicSelect: document.getElementById("musicSelect"),
    duckSlider: document.getElementById("duckSlider"),
    duckValBadge: document.getElementById("duckValBadge"),

    // Production Stepper & CTA
    btnProduce: document.getElementById("btnProduce"),
    submitBtn: document.getElementById("submitBtn"),
    stepperBox: document.getElementById("stepperBox"),
    stepperTimer: document.getElementById("stepperTimer"),
    progressBarFill: document.getElementById("progressBarFill"),
    stepsList: document.getElementById("stepsList"),
    btnCancelSession: document.getElementById("btnCancelSession"),

    // Linguistic Video & Speech Intent Prompts + Prompt History
    visualDescription: document.getElementById("visualDescription"),
    speechDescription: document.getElementById("speechDescription"),
    promptHistorySelect: document.getElementById("promptHistorySelect"),
    promptHistoryChips: document.getElementById("promptHistoryChips"),
    btnSavePrompt: document.getElementById("btnSavePrompt"),
    btnRefreshPromptHistory: document.getElementById("btnRefreshPromptHistory"),
    btnClearPrompts: document.getElementById("btnClearPrompts"),
    promptSaveStatus: document.getElementById("promptSaveStatus"),

    // AI Agent Live Telemetry Elements
    aiAgentLiveCard: document.getElementById("aiAgentLiveCard"),
    aiStepBadge: document.getElementById("aiStepBadge"),
    aiAgentMessage: document.getElementById("aiAgentMessage"),
    aiAgentLogs: document.getElementById("aiAgentLogs"),

    // Result & Delivery
    resultSection: document.getElementById("resultSection"),
    finalVideoPlayer: document.getElementById("finalVideoPlayer"),
    telemetryBadgesGrid: document.getElementById("telemetryBadgesGrid"),
    emotionalToneSpotlight: document.getElementById("emotionalToneSpotlight"),
    emotionalToneVal: document.getElementById("emotionalToneVal"),
    btnResetNewVideo: document.getElementById("btnResetNewVideo"),
    btnDownloadVideo: document.getElementById("btnDownloadVideo"),
    btnShareVideo: document.getElementById("btnShareVideo"),
    btnDownloadAudio: document.getElementById("btnDownloadAudio"),
    btnShareWhatsApp: document.getElementById("btnShareWhatsApp"),
    btnShareTelegram: document.getElementById("btnShareTelegram"),
    btnCopyVideoLink: document.getElementById("btnCopyVideoLink"),
    keyframesCarousel: document.getElementById("keyframesCarousel"),
    keyframesCountBadge: document.getElementById("keyframesCountBadge"),
    btnStartNewProduction: document.getElementById("btnStartNewProduction"),

    // Modal & Toast
    keyframeModal: document.getElementById("keyframeModal"),
    modalFrameImg: document.getElementById("modalFrameImg"),
    modalFrameTitle: document.getElementById("modalFrameTitle"),
    modalFrameTimestamp: document.getElementById("modalFrameTimestamp"),
    btnModalDownload: document.getElementById("btnModalDownload"),
    btnModalClose: document.getElementById("btnModalClose"),
    appToast: document.getElementById("appToast"),

    // Production Principles Elements & Logs Telemetry
    btnOpenPrinciples: document.getElementById("btnOpenPrinciples"),
    btnClosePrinciples: document.getElementById("btnClosePrinciples"),
    principlesModal: document.getElementById("principlesModal"),
    principlesForm: document.getElementById("principlesForm"),
    btnSavePrinciples: document.getElementById("btnSavePrinciples"),
    btnResetPrinciples: document.getElementById("btnResetPrinciples"),
    principlesSaveStatus: document.getElementById("principlesSaveStatus"),
    btnCopyLogs: document.getElementById("btnCopyLogs"),
    chkAutoScroll: document.getElementById("chkAutoScroll"),

    // Principle Form Controls & Master Directives
    principleCustomInstructions: document.getElementById("principleCustomInstructions"),
    principleDialect: document.getElementById("principleDialect"),
    principlePerspective: document.getElementById("principlePerspective"),
    chipDarja: document.getElementById("chipDarja"),
    chipWalkthrough: document.getElementById("chipWalkthrough"),
    chipConnected: document.getElementById("chipConnected"),
    chipFormal: document.getElementById("chipFormal"),
    chipClear: document.getElementById("chipClear"),
    principleVoiceGuidelines: document.getElementById("principleVoiceGuidelines"),
    principleVoicePacing: document.getElementById("principleVoicePacing"),
    principleVoicePronunciation: document.getElementById("principleVoicePronunciation"),
    principleVoiceToneBias: document.getElementById("principleVoiceToneBias"),
    principleNarrativeGuidelines: document.getElementById("principleNarrativeGuidelines"),
    principleNarrativeAlignment: document.getElementById("principleNarrativeAlignment"),
    principleNarrativeAudience: document.getElementById("principleNarrativeAudience"),
    principleVisualDucking: document.getElementById("principleVisualDucking"),
    principleVisualTheme: document.getElementById("principleVisualTheme"),
    principleEnableAutoAnnotations: document.getElementById("principleEnableAutoAnnotations"),
    principleAnnotationStyle: document.getElementById("principleAnnotationStyle"),
    principleAnnotationPosition: document.getElementById("principleAnnotationPosition"),
  };

  // ---------------------------------------------------------------------------
  // Utility: Toast Notifications
  // ---------------------------------------------------------------------------
  let toastTimer = null;
  function showToast(message, duration = 3200) {
    if (!dom.appToast) return;
    clearTimeout(toastTimer);
    dom.appToast.textContent = message;
    dom.appToast.classList.add("show");
    toastTimer = setTimeout(() => {
      dom.appToast.classList.remove("show");
    }, duration);
  }

  // ---------------------------------------------------------------------------
  // Utility: Formatting Helpers
  // ---------------------------------------------------------------------------
  function formatSeconds(sec) {
    const s = Math.max(0, Math.floor(sec || 0));
    const mins = Math.floor(s / 60);
    const rem = s % 60;
    return `${String(mins).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  }

  // ---------------------------------------------------------------------------
  // Health & Service Discovery
  // ---------------------------------------------------------------------------
  async function checkServerHealth() {
    try {
      const res = await fetch("/api/health", { cache: "no-store" });
      if (res.ok) {
        if (dom.systemStatusChip) {
          dom.systemStatusChip.innerHTML = `
            <span class="status-indicator online"></span>
            <span class="status-label">خادم الإنتاج متصل وجاهز</span>
          `;
        }
        return true;
      }
    } catch {
      // Backend offline or booting
    }
    if (dom.systemStatusChip) {
      dom.systemStatusChip.innerHTML = `
        <span class="status-indicator offline"></span>
        <span class="status-label">وضع الاستعداد المحلي</span>
      `;
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Video Ingestion: File Handler & Metadata Inspector
  // ---------------------------------------------------------------------------
  function handleSelectedVideo(file, sourceDesc = "ملف مختار") {
    if (!file) return;

    // Check basic type or extension
    const isVideo = file.type.startsWith("video/") || /\.(mp4|mov|webm|m4v|mkv)$/i.test(file.name);
    if (!isVideo) {
      showToast("يرجى اختيار ملف فيديو صالح (MP4, MOV, WebM)");
      return;
    }

    state.selectedFile = file;
    state.selectedSource = sourceDesc;

    // Build blob object URL for local preview
    const videoUrl = URL.createObjectURL(file);
    dom.previewPlayer.src = videoUrl;
    dom.previewPlayer.load();

    // Reset meta text
    dom.previewSize.textContent = formatBytes(file.size);
    dom.previewDuration.textContent = "جاري التحميل...";
    dom.previewDimensions.textContent = "--";
    dom.previewOrientation.textContent = "--";

    dom.previewPlayer.onloadedmetadata = () => {
      const durationSec = dom.previewPlayer.duration;
      dom.previewDuration.textContent = `${durationSec.toFixed(1)} ثانية`;

      const w = dom.previewPlayer.videoWidth;
      const h = dom.previewPlayer.videoHeight;
      dom.previewDimensions.textContent = `${w}x${h}`;

      if (h > w) {
        dom.previewOrientation.textContent = "عمودي (9:16)";
      } else if (w > h) {
        dom.previewOrientation.textContent = "أفقي (16:9)";
      } else {
        dom.previewOrientation.textContent = "مربع (1:1)";
      }
    };

    // Show preview card
    dom.videoPreviewCard.style.display = "block";
    dom.videoPreviewCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

    showToast(`تم تجهيز الفيديو بنجاح (${sourceDesc})`);
  }

  // ---------------------------------------------------------------------------
  // Mobile Camera Capture Modalities
  // ---------------------------------------------------------------------------

  // Modality 1: Native HTML5 Camera Capture (Environment Facing)
  if (dom.btnNativeCamera && dom.cameraInput) {
    dom.btnNativeCamera.addEventListener("click", () => {
      stopViewfinderStream();
      dom.cameraInput.click();
    });

    dom.cameraInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        handleSelectedVideo(file, "كاميرا الهاتف الأساسية");
      }
    });
  }

  // Modality 2: Gallery Picker
  if (dom.btnGalleryUpload && dom.galleryInput) {
    dom.btnGalleryUpload.addEventListener("click", () => {
      dom.galleryInput.click();
    });

    dom.galleryInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        handleSelectedVideo(file, "معرض الهاتف");
      }
    });
  }

  // Modality 3: Desktop Drag & Drop
  if (dom.dropZone && dom.galleryInput) {
    dom.dropZone.addEventListener("click", () => {
      dom.galleryInput.click();
    });

    dom.dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dom.dropZone.classList.add("dragover");
    });

    dom.dropZone.addEventListener("dragleave", () => {
      dom.dropZone.classList.remove("dragover");
    });

    dom.dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dom.dropZone.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleSelectedVideo(e.dataTransfer.files[0], "سحب وإفلات");
      }
    });
  }

  // Change video button
  if (dom.btnChangeVideo) {
    dom.btnChangeVideo.addEventListener("click", () => {
      dom.cameraInput.value = "";
      dom.galleryInput.value = "";
      dom.cameraInput.click();
    });
  }

  // ---------------------------------------------------------------------------
  // Modality 4: In-Browser Live Viewfinder Recorder (MediaRecorder API)
  // ---------------------------------------------------------------------------
  async function startViewfinderStream(facingMode = "environment") {
    state.currentFacingMode = facingMode;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      displayViewfinderNotice(
        "المعاينة الحية غير مدعومة في هذا المتصفح أو تتطلب اتصال HTTPS آمن. يُرجى النقر على زر 'تسجيل بالكاميرا' أعلاه حيث يعمل دون قيود!"
      );
      return;
    }

    try {
      stopViewfinderStream();

      const constraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: true,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      state.activeStream = stream;
      dom.viewfinderVideo.srcObject = stream;
      dom.viewfinderNotice.style.display = "none";
      dom.viewfinderPanel.style.display = "block";
      dom.recStatusText.textContent = "جاهز للتسجيل";
      dom.recTimer.textContent = "00:00";
      dom.recBadge.classList.remove("recording");
    } catch (err) {
      console.warn("Could not start live media stream:", err);
      displayViewfinderNotice(
        "تعذر الوصول لكاميرا المتصفح الحية (قد يتطلب أذونات الكاميرا أو اتصال HTTPS). يمكنك الضغط على 'تسجيل بالكاميرا' أعلاه للالتقاط بكاميرا الهاتف الأساسية مباشرة!"
      );
    }
  }

  function displayViewfinderNotice(text) {
    dom.viewfinderNoticeText.textContent = text;
    dom.viewfinderNotice.style.display = "flex";
    dom.viewfinderPanel.style.display = "block";
  }

  function stopViewfinderStream() {
    if (state.activeStream) {
      state.activeStream.getTracks().forEach((track) => track.stop());
      state.activeStream = null;
    }
    if (dom.viewfinderVideo) {
      dom.viewfinderVideo.srcObject = null;
    }
  }

  function toggleLiveViewfinder() {
    if (dom.viewfinderPanel.style.display === "none") {
      startViewfinderStream(state.currentFacingMode);
      dom.viewfinderPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      closeViewfinder();
    }
  }

  function closeViewfinder() {
    if (state.isRecording) {
      stopRecordingMedia();
    }
    stopViewfinderStream();
    dom.viewfinderPanel.style.display = "none";
  }

  function getSupportedMimeType() {
    const types = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm',
      'video/mp4',
    ];
    for (const t of types) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) {
        return t;
      }
    }
    return '';
  }

  function startRecordingMedia() {
    if (!state.activeStream) {
      showToast("الكاميرا غير مفعلة");
      return;
    }

    state.recordedChunks = [];
    const mimeType = getSupportedMimeType();
    const options = mimeType ? { mimeType } : {};

    try {
      state.mediaRecorder = new MediaRecorder(state.activeStream, options);
    } catch (e) {
      console.error("Failed to construct MediaRecorder:", e);
      showToast("تعذر بدء مسجل المتصفح، يرجى استخدام زر الكاميرا الأساسية");
      return;
    }

    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.recordedChunks.push(event.data);
      }
    };

    state.mediaRecorder.onstop = () => {
      clearInterval(state.recTimerInterval);
      state.isRecording = false;

      const blobType = state.recordedChunks[0]?.type || 'video/webm';
      const ext = blobType.includes('mp4') ? 'mp4' : 'webm';
      const recordedBlob = new Blob(state.recordedChunks, { type: blobType });
      const recordedFile = new File(
        [recordedBlob],
        `recording_${new Date().toISOString().replace(/[:.]/g, '-')}.${ext}`,
        { type: blobType }
      );

      closeViewfinder();
      handleSelectedVideo(recordedFile, "تسجيل المتصفح الحي");
    };

    state.mediaRecorder.start(250);
    state.isRecording = true;
    state.recSecondsElapsed = 0;

    dom.btnRecordToggle.classList.add("recording");
    dom.recBadge.classList.add("recording");
    dom.recStatusText.textContent = "جاري التسجيل";

    state.recTimerInterval = setInterval(() => {
      state.recSecondsElapsed++;
      dom.recTimer.textContent = formatSeconds(state.recSecondsElapsed);
    }, 1000);
  }

  function stopRecordingMedia() {
    if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
      state.mediaRecorder.stop();
    }
    dom.btnRecordToggle.classList.remove("recording");
    dom.recBadge.classList.remove("recording");
    dom.recStatusText.textContent = "تم إيقاف التسجيل";
  }

  // Viewfinder Event Listeners
  if (dom.btnToggleViewfinder) {
    dom.btnToggleViewfinder.addEventListener("click", toggleLiveViewfinder);
  }
  if (dom.btnCloseViewfinder) {
    dom.btnCloseViewfinder.addEventListener("click", closeViewfinder);
  }
  if (dom.btnViewfinderCancel) {
    dom.btnViewfinderCancel.addEventListener("click", closeViewfinder);
  }
  if (dom.btnRecordToggle) {
    dom.btnRecordToggle.addEventListener("click", () => {
      if (!state.isRecording) {
        startRecordingMedia();
      } else {
        stopRecordingMedia();
      }
    });
  }
  if (dom.btnFlipCamera) {
    dom.btnFlipCamera.addEventListener("click", () => {
      if (state.isRecording) {
        showToast("يرجى إيقاف التسجيل أولاً لتبديل الكاميرا");
        return;
      }
      const newFacing = state.currentFacingMode === "environment" ? "user" : "environment";
      startViewfinderStream(newFacing);
      showToast(newFacing === "user" ? "تم التحويل للكاميرا الأمامية" : "تم التحويل للكاميرا الخلفية");
    });
  }

  // ---------------------------------------------------------------------------
  // Algerian Real Estate Presets & Script Management
  // ---------------------------------------------------------------------------
  function renderPresets(presets) {
    if (!dom.presetsSelectorGrid) return;
    dom.presetsSelectorGrid.innerHTML = "";

    presets.forEach((preset) => {
      const card = document.createElement("div");
      card.className = "preset-chip-card" + (preset.id === state.currentPresetId ? " active" : "");
      card.setAttribute("role", "radio");
      card.setAttribute("aria-checked", String(preset.id === state.currentPresetId));
      card.dataset.id = preset.id;

      card.innerHTML = `
        <div class="preset-title-ar">${preset.title_ar}</div>
        <div class="preset-title-fr">${preset.title_fr}</div>
        <div class="preset-desc-snip">${preset.description}</div>
      `;

      card.addEventListener("click", () => {
        document.querySelectorAll(".preset-chip-card").forEach((c) => {
          c.classList.remove("active");
          c.setAttribute("aria-checked", "false");
        });
        card.classList.add("active");
        card.setAttribute("aria-checked", "true");

        state.currentPresetId = preset.id;
        dom.scriptText.value = preset.description;
        updateScriptAnalytics();
        showToast(`تم تطبيق قالب: ${preset.title_ar}`);
      });

      dom.presetsSelectorGrid.appendChild(card);
    });
  }

  async function loadPresetsFromAPI() {
    try {
      const res = await fetch("/api/presets");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          state.presets = data;
          renderPresets(data);
          return;
        }
      }
    } catch (err) {
      console.warn("Could not load presets from /api/presets, fallback to built-in presets:", err);
    }
    renderPresets(state.presets);
  }

  function updateScriptAnalytics() {
    const text = (dom.scriptText?.value || "").trim();
    const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
    const chars = text.length;

    // Average Arabic speech speed: ~2.5 words per second
    const estSec = words > 0 ? Math.max(2, Math.round(words / 2.4)) : 0;

    if (dom.wordCount) dom.wordCount.textContent = String(words);
    if (dom.charCount) dom.charCount.textContent = String(chars);
    if (dom.speechEstDuration) dom.speechEstDuration.textContent = `~${estSec} ثانية`;
  }

  if (dom.scriptText) {
    dom.scriptText.addEventListener("input", updateScriptAnalytics);
  }

  if (dom.btnResetScript) {
    dom.btnResetScript.addEventListener("click", () => {
      const p = state.presets.find((x) => x.id === state.currentPresetId) || state.presets[0];
      if (p) {
        dom.scriptText.value = p.description;
        updateScriptAnalytics();
        showToast("تمت استعادة النص الأصلي للقالب");
      }
    });
  }

  if (dom.btnClearScript) {
    dom.btnClearScript.addEventListener("click", () => {
      dom.scriptText.value = "";
      updateScriptAnalytics();
      dom.scriptText.focus();
    });
  }

  // ---------------------------------------------------------------------------
  // Audio Controls & Dynamic Ducking Slider
  // ---------------------------------------------------------------------------
  if (dom.duckSlider && dom.duckValBadge) {
    dom.duckSlider.addEventListener("input", (e) => {
      const pct = Math.round(parseFloat(e.target.value) * 100);
      dom.duckValBadge.textContent = `${pct}%`;
    });
  }

  // ---------------------------------------------------------------------------
  // Animated Multi-Stage Processing Stepper & Live AI Agent Telemetry
  // ---------------------------------------------------------------------------
  function setStepperState(activeStep, progressPercent) {
    if (dom.progressBarFill) {
      dom.progressBarFill.style.width = `${progressPercent}%`;
    }

    for (let i = 1; i <= 5; i++) {
      const stepEl = document.getElementById(`step${i}`);
      if (!stepEl) continue;

      if (i < activeStep) {
        stepEl.className = "step-item completed";
      } else if (i === activeStep) {
        stepEl.className = "step-item active";
      } else {
        stepEl.className = "step-item";
      }
    }
  }

  function formatLogTimestamp() {
    const d = new Date();
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
  }

  function parseLogEntry(rawText) {
    const timeStr = formatLogTimestamp();
    let tagStr = "[وكيل]";
    let tagClass = "tag-init";
    let body = rawText;

    // Detect bracketed category tag e.g. [فحص الوسائط]
    const bracketMatch = rawText.match(/^\[([^\]]+)\]\s*(.*)$/);
    if (bracketMatch) {
      tagStr = `[${bracketMatch[1]}]`;
      body = bracketMatch[2];
      const t = bracketMatch[1];
      if (t.includes("فحص") || t.includes("وسائط")) tagClass = "tag-media";
      else if (t.includes("رؤية") || t.includes("معمار")) tagClass = "tag-vision";
      else if (t.includes("شعور") || t.includes("تحليل")) tagClass = "tag-mood";
      else if (t.includes("صوت") || t.includes("tts")) tagClass = "tag-tts";
      else if (t.includes("مكساج") || t.includes("موسيقى")) tagClass = "tag-mix";
      else if (t.includes("ملصق") || t.includes("كتاب")) tagClass = "tag-overlay";
      else if (t.includes("إخراج") || t.includes("نهائي")) tagClass = "tag-render";
    } else if (rawText.includes("●")) {
      body = rawText.replace(/^●\s*/, "");
    }
    return { timeStr, tagStr, tagClass, body };
  }

  function updateAIAgentStatus(step, percent, message, logs) {
    setStepperState(step, percent);

    if (dom.aiStepBadge) {
      dom.aiStepBadge.textContent = `المرحلة ${Math.min(5, step)} من 5`;
    }

    if (dom.aiAgentMessage && message) {
      dom.aiAgentMessage.textContent = message;
    }

    if (dom.aiAgentLogs && Array.isArray(logs) && logs.length > 0) {
      dom.aiAgentLogs.innerHTML = "";
      logs.forEach((logText, idx) => {
        const parsed = parseLogEntry(logText);
        const entryDiv = document.createElement("div");
        entryDiv.className = idx === logs.length - 1 ? "log-entry highlight" : "log-entry";

        const timeSpan = document.createElement("span");
        timeSpan.className = "log-time";
        timeSpan.textContent = parsed.timeStr;

        const tagSpan = document.createElement("span");
        tagSpan.className = `log-tag ${parsed.tagClass}`;
        tagSpan.textContent = parsed.tagStr;

        const textSpan = document.createElement("span");
        textSpan.className = "log-text";
        textSpan.textContent = parsed.body;

        entryDiv.appendChild(timeSpan);
        entryDiv.appendChild(tagSpan);
        entryDiv.appendChild(textSpan);
        dom.aiAgentLogs.appendChild(entryDiv);
      });

      if (!dom.chkAutoScroll || dom.chkAutoScroll.checked) {
        dom.aiAgentLogs.scrollTop = dom.aiAgentLogs.scrollHeight;
      }
    }
  }

  function startProcessingStepper(existingJobId = null) {
    state.isProcessing = true;
    state.activeJobId = existingJobId;
    state.processingSecondsElapsed = 0;
    if (dom.btnProduce) dom.btnProduce.disabled = true;
    if (dom.stepperBox) dom.stepperBox.style.display = "block";
    if (dom.resultSection) dom.resultSection.style.display = "none";
    if (dom.stepperTimer) dom.stepperTimer.textContent = "00:00";

    updateAIAgentStatus(
      1,
      12,
      "وكيل الذكاء الاصطناعي يقوم بفحص أبعاد الفيديو وتجهيز المسارات الصوتية...",
      ["تم استلام ملف الفيديو من الهاتف وحفظه بنجاح على الخادم."]
    );

    // Elapsed timer
    if (state.processingTimerInterval) clearInterval(state.processingTimerInterval);
    state.processingTimerInterval = setInterval(() => {
      state.processingSecondsElapsed++;
      if (dom.stepperTimer) {
        dom.stepperTimer.textContent = formatSeconds(state.processingSecondsElapsed);
      }
    }, 1000);
  }

  function finishProcessingStepper(success = true) {
    state.isProcessing = false;
    if (state.processingTimerInterval) clearInterval(state.processingTimerInterval);
    if (state.statusPollInterval) clearInterval(state.statusPollInterval);
    state.statusPollInterval = null;
    if (dom.btnProduce) dom.btnProduce.disabled = false;

    if (success) {
      setStepperState(5, 100);
      if (dom.aiStepBadge) dom.aiStepBadge.textContent = "المرحلة النهائية: مكتمل";
      if (dom.aiAgentMessage) dom.aiAgentMessage.textContent = "اكتمل إنتاج الفيديو التسويقي بنجاح! جاهز للمعاينة والمشاركة.";
    } else {
      if (dom.stepperBox) dom.stepperBox.style.display = "none";
    }
  }

  // ---------------------------------------------------------------------------
  // Polling Engine (600ms Live Telemetry)
  // ---------------------------------------------------------------------------
  function pollJobStatus(jobId) {
    if (state.statusPollInterval) clearInterval(state.statusPollInterval);

    return new Promise((resolve, reject) => {
      state.statusPollInterval = setInterval(async () => {
        try {
          const sResp = await fetch(`/api/status/${jobId}`);
          if (sResp.status === 404) {
            clearInterval(state.statusPollInterval);
            state.statusPollInterval = null;
            reject(new Error("Job not found (404)"));
            return;
          }
          if (!sResp.ok) return;
          const sData = await sResp.json();

          if (sData.status === "completed" || sData.video_url) {
            clearInterval(state.statusPollInterval);
            state.statusPollInterval = null;
            resolve(sData.result || sData);
          } else if (sData.status === "failed") {
            clearInterval(state.statusPollInterval);
            state.statusPollInterval = null;
            reject(new Error(sData.error || sData.message || "فشلت معالجة الفيديو"));
          } else if (sData.status === "processing" || sData.status === "queued") {
            updateAIAgentStatus(
              sData.step || 2,
              sData.progress_percent || 30,
              sData.message,
              sData.agent_logs
            );
          }
        } catch (pollErr) {
          console.warn("Poll check error:", pollErr);
        }
      }, 600);
    });
  }

  // ---------------------------------------------------------------------------
  // Session Persistence & Seamless Reconnection
  // ---------------------------------------------------------------------------
  async function restoreSavedSession() {
    const savedJobId = localStorage.getItem(ACTIVE_JOB_KEY);
    if (!savedJobId) return;

    console.info(`[Session Persistence] Found active job ID: ${savedJobId}. Checking live status...`);

    // Immediately display the telemetry / progress section
    if (dom.stepperBox) dom.stepperBox.style.display = "block";
    if (dom.resultSection) dom.resultSection.style.display = "none";
    updateAIAgentStatus(
      1,
      20,
      `جاري استعادة حالة الجلسة السابقة (المعرف: #${savedJobId.substring(0, 8)})...`,
      [`تم استئناف الاتصال بالجلسة السابقة #${savedJobId}. جاري فحص الحالة اللحظية من الخادم...`]
    );

    try {
      const resp = await fetch(`/api/status/${savedJobId}`);
      if (resp.status === 404) {
        console.warn(`[Session Persistence] Job ${savedJobId} returned 404 Not Found.`);
        localStorage.removeItem(ACTIVE_JOB_KEY);
        finishProcessingStepper(false);
        showToast("انتهت صلاحية الجلسة السابقة أو لم تعد موجودة.");
        return;
      }

      if (!resp.ok) {
        console.warn(`[Session Persistence] HTTP ${resp.status} checking job status`);
        return;
      }

      const sData = await resp.json();

      if (sData.status === "completed" || sData.video_url) {
        console.info(`[Session Persistence] Job ${savedJobId} is completed. Switching to final cut player.`);
        finishProcessingStepper(true);
        displayFinalResult(sData.result || sData);
        showToast("تمت استعادة الفيديو المكتمل بنجاح!");
      } else if (sData.status === "processing" || sData.status === "queued") {
        console.info(`[Session Persistence] Job ${savedJobId} is still processing. Resuming 600ms polling.`);
        startProcessingStepper(savedJobId);
        updateAIAgentStatus(
          sData.step || 2,
          sData.progress_percent || 25,
          sData.message || "جاري استكمال المعالجة...",
          sData.agent_logs || []
        );

        try {
          const finalData = await pollJobStatus(savedJobId);
          finishProcessingStepper(true);
          setTimeout(() => {
            displayFinalResult(finalData);
          }, 400);
        } catch (pollErr) {
          finishProcessingStepper(false);
          localStorage.removeItem(ACTIVE_JOB_KEY);
          alert("فشلت معالجة الفيديو في الجلسة المستعادة: " + pollErr.message);
        }
      } else if (sData.status === "failed") {
        console.warn(`[Session Persistence] Job ${savedJobId} is failed.`);
        localStorage.removeItem(ACTIVE_JOB_KEY);
        finishProcessingStepper(false);
        alert("فشلت معالجة الفيديو في الجلسة السابقة: " + (sData.error || sData.message || "خطأ غير معروف"));
      }
    } catch (err) {
      console.error("[Session Persistence] Failed to reconnect to job:", err);
    }
  }

  // ---------------------------------------------------------------------------
  // Reset & New Video Action
  // ---------------------------------------------------------------------------
  function resetSessionAndNewVideo() {
    localStorage.removeItem(ACTIVE_JOB_KEY);
    if (state.statusPollInterval) {
      clearInterval(state.statusPollInterval);
      state.statusPollInterval = null;
    }
    if (state.processingTimerInterval) {
      clearInterval(state.processingTimerInterval);
      state.processingTimerInterval = null;
    }

    state.isProcessing = false;
    state.activeJobId = null;
    state.selectedFile = null;
    state.currentJobResult = null;

    if (dom.previewPlayer) dom.previewPlayer.src = "";
    if (dom.finalVideoPlayer) dom.finalVideoPlayer.src = "";
    if (dom.videoPreviewCard) dom.videoPreviewCard.style.display = "none";
    if (dom.resultSection) dom.resultSection.style.display = "none";
    if (dom.stepperBox) dom.stepperBox.style.display = "none";
    if (dom.cameraInput) dom.cameraInput.value = "";
    if (dom.galleryInput) dom.galleryInput.value = "";
    if (dom.scriptText) dom.scriptText.value = "";
    if (dom.btnProduce) dom.btnProduce.disabled = false;

    window.scrollTo({ top: 0, behavior: "smooth" });
    showToast("تم بدء جلسة جديدة جاهزة لتصوير أو اختيار فيديو جديد");
  }

  // ---------------------------------------------------------------------------
  // Video Production Action & 1-Click Zero-Effort Dispatch
  // ---------------------------------------------------------------------------
  async function handleProduceProduction() {
    // 1. Validation: Verify video file selected
    if (!state.selectedFile) {
      showToast("يرجى تسجيل أو اختيار مقطع فيديو أولاً!");
      if (dom.btnNativeCamera) {
        dom.btnNativeCamera.scrollIntoView({ behavior: "smooth" });
        dom.btnNativeCamera.style.transform = "scale(1.05)";
        setTimeout(() => (dom.btnNativeCamera.style.transform = ""), 400);
      }
      return;
    }

    // 2. Prepare FormData matching 1-Click zero-effort mode or advanced overrides
    const formData = new FormData();
    formData.append("video", state.selectedFile);

    // Linguistic visual and speech intent prompt descriptions
    const visualDesc = (dom.visualDescription?.value || "").trim();
    const speechDesc = (dom.speechDescription?.value || "").trim();
    if (visualDesc) {
      formData.append("visual_description", visualDesc);
    }
    if (speechDesc) {
      formData.append("speech_description", speechDesc);
    }

    const isAccordionOpen = dom.advancedAccordion && dom.advancedAccordion.open;
    const scriptVal = (dom.scriptText?.value || "").trim();

    if (!isAccordionOpen || !scriptVal) {
      // Zero-effort 1-click mode: AI agent infers script, emotional tone & music automatically
      formData.append("auto_mode", "true");
      if (scriptVal) {
        formData.append("script", scriptVal);
      }
    } else {
      // Advanced Customization Mode (user explicitly expanded and configured)
      if (scriptVal) {
        formData.append("script", scriptVal);
      }
      if (state.currentPresetId) {
        formData.append("preset", state.currentPresetId);
      }
      if (dom.voiceSelect?.value && dom.voiceSelect.value !== "auto") {
        formData.append("voice", dom.voiceSelect.value);
      }
      if (dom.musicSelect?.value) {
        formData.append("music", dom.musicSelect.value);
      }
      if (dom.duckSlider?.value) {
        formData.append("duck_level", dom.duckSlider.value);
      }
    }

    // 3. Initiate Stepper & Request
    startProcessingStepper();
    dom.stepperBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
      let jobId = null;
      try {
        const createResp = await fetch("/api/jobs/create", {
          method: "POST",
          body: formData,
        });
        if (createResp.ok || createResp.status === 202) {
          const createData = await createResp.json();
          jobId = createData.job_id;
        }
      } catch (e) {
        console.warn("Async job creation not available, falling back to direct upload:", e);
      }

      if (jobId) {
        state.activeJobId = jobId;
        // Store active job in localStorage for session persistence & seamless reconnection
        localStorage.setItem(ACTIVE_JOB_KEY, jobId);

        const finalData = await pollJobStatus(jobId);
        finishProcessingStepper(true);
        setTimeout(() => {
          displayFinalResult(finalData);
        }, 400);

      } else {
        // Fallback direct upload-and-process
        const response = await fetch("/api/upload-and-process", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `خطأ في المعالجة (رمز الاستجابة: ${response.status})`);
        }

        const data = await response.json();
        if (data.job_id) {
          localStorage.setItem(ACTIVE_JOB_KEY, data.job_id);
        }
        finishProcessingStepper(true);
        setTimeout(() => {
          displayFinalResult(data);
        }, 500);
      }

    } catch (err) {
      finishProcessingStepper(false);
      localStorage.removeItem(ACTIVE_JOB_KEY);
      console.error("Video processing failed:", err);
      showToast(`فشل الإنتاج: ${err.message}`);
    }
  }

  if (dom.btnProduce) {
    dom.btnProduce.addEventListener("click", handleProduceProduction);
  }
  if (dom.submitBtn) {
    dom.submitBtn.addEventListener("click", handleProduceProduction);
  }

  // ---------------------------------------------------------------------------
  // Post-Production Delivery & Playback Studio
  // ---------------------------------------------------------------------------
  function displayFinalResult(data) {
    state.currentJobResult = data;

    // Load final video into player
    dom.finalVideoPlayer.src = data.video_url;
    dom.finalVideoPlayer.load();

    // Configure downloads
    dom.btnDownloadVideo.href = data.video_url;
    dom.btnDownloadAudio.href = data.narration_audio_url || "#";

    // Emotional Tone & Vision Telemetry Display
    const emotionalTone = data.emotional_tone ||
      data.metadata?.emotional_tone ||
      (data.result && (data.result.emotional_tone || data.result.metadata?.emotional_tone)) ||
      null;

    if (emotionalTone) {
      if (dom.emotionalToneVal) dom.emotionalToneVal.textContent = emotionalTone;
      if (dom.emotionalToneSpotlight) dom.emotionalToneSpotlight.style.display = "flex";
    } else {
      if (dom.emotionalToneSpotlight) dom.emotionalToneSpotlight.style.display = "none";
    }

    // Telemetry Badges
    const duration = data.duration ? `${data.duration.toFixed(1)} ثانية` : "--";
    const res = data.resolution || "--";
    const orientationLabel = data.orientation === "portrait" ? "عمودي 9:16" : "أفقي 16:9";
    const synth = data.synthesizer || "Gemini Neural";
    const renderTime = data.metadata?.render_seconds ? `${data.metadata.render_seconds}s` : "--";
    const fileSize = data.file_size_bytes ? formatBytes(data.file_size_bytes) : "--";
    const jobId = data.job_id || "--";

    let toneChipHtml = "";
    if (emotionalTone) {
      toneChipHtml = `
        <div class="telemetry-chip highlight-tone">
          <span class="chip-label">🎭 الحالة الشعورية:</span>
          <span class="chip-val">${emotionalTone}</span>
        </div>
      `;
    }

    dom.telemetryBadgesGrid.innerHTML = `
      ${toneChipHtml}
      <div class="telemetry-chip accent">
        <span class="chip-label">⏱️ المدة:</span>
        <span class="chip-val">${duration}</span>
      </div>
      <div class="telemetry-chip">
        <span class="chip-label">📐 الأبعاد:</span>
        <span class="chip-val">${res} (${orientationLabel})</span>
      </div>
      <div class="telemetry-chip">
        <span class="chip-label">💾 الحجم:</span>
        <span class="chip-val">${fileSize}</span>
      </div>
      <div class="telemetry-chip">
        <span class="chip-label">🎙️ محرك الصوت:</span>
        <span class="chip-val">${synth}</span>
      </div>
      <div class="telemetry-chip">
        <span class="chip-label">⚡ سرعة المونتاج:</span>
        <span class="chip-val">${renderTime}</span>
      </div>
      <div class="telemetry-chip">
        <span class="chip-label">🔖 معرف العملية:</span>
        <span class="chip-val">#${jobId.substring(0, 8)}</span>
      </div>
    `;

    // Keyframes Carousel
    renderKeyframes(data.keyframes || []);

    // Reveal Result Card
    dom.resultSection.style.display = "block";
    dom.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast("✨ اكتمل إنتاج الفيديو التسويقي بنجاح!");
  }

  function renderKeyframes(keyframes) {
    if (!dom.keyframesCarousel) return;
    dom.keyframesCarousel.innerHTML = "";

    const count = keyframes.length;
    if (dom.keyframesCountBadge) {
      dom.keyframesCountBadge.textContent = `${count} لقطة`;
    }

    if (count === 0) {
      dom.keyframesCarousel.innerHTML = `<div style="color: var(--text-muted); font-size: 0.8rem; padding: 10px;">لا توجد لقطات مفتاحية متاحة</div>`;
      return;
    }

    keyframes.forEach((kf, idx) => {
      const card = document.createElement("div");
      card.className = "keyframe-card";
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", `لقطة مفتاحية عند ${kf.timestamp.toFixed(1)} ثانية`);

      card.innerHTML = `
        <img src="${kf.url}" alt="Keyframe ${kf.frame_index || idx}" loading="lazy">
        <span class="keyframe-badge">${kf.timestamp.toFixed(1)}s</span>
      `;

      card.addEventListener("click", () => {
        openKeyframeModal(kf.url, kf.timestamp, idx + 1);
      });

      dom.keyframesCarousel.appendChild(card);
    });
  }

  // ---------------------------------------------------------------------------
  // Keyframe Modal Viewer
  // ---------------------------------------------------------------------------
  function openKeyframeModal(imgUrl, timestamp, index) {
    dom.modalFrameImg.src = imgUrl;
    dom.modalFrameTitle.textContent = `لقطة مفتاحية #${index}`;
    dom.modalFrameTimestamp.textContent = `التوقيت: ${timestamp.toFixed(2)} ثانية`;
    dom.btnModalDownload.href = imgUrl;
    dom.keyframeModal.style.display = "flex";
  }

  function closeKeyframeModal() {
    dom.keyframeModal.style.display = "none";
    dom.modalFrameImg.src = "";
  }

  if (dom.btnModalClose) {
    dom.btnModalClose.addEventListener("click", closeKeyframeModal);
  }
  if (dom.keyframeModal) {
    dom.keyframeModal.addEventListener("click", (e) => {
      if (e.target === dom.keyframeModal) {
        closeKeyframeModal();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Social Sharing & Web Share API
  // ---------------------------------------------------------------------------
  function getAbsoluteVideoUrl() {
    if (!state.currentJobResult?.video_url) return window.location.href;
    return new URL(state.currentJobResult.video_url, window.location.origin).href;
  }

  if (dom.btnShareVideo) {
    dom.btnShareVideo.addEventListener("click", async () => {
      const videoUrl = getAbsoluteVideoUrl();
      const shareTitle = "فيديو تسويقي عقاري | استوديو عقارات الجزائر";
      const shareText = state.currentJobResult?.script || "شاهد هذا العرض العقاري المميز!";

      if (navigator.share) {
        try {
          await navigator.share({
            title: shareTitle,
            text: shareText,
            url: videoUrl,
          });
          showToast("تمت المشاركة بنجاح");
          return;
        } catch (err) {
          if (err.name !== "AbortError") {
            console.warn("Web Share API failed, fallback to copy:", err);
          } else {
            return;
          }
        }
      }

      // Clipboard fallback
      copyToClipboard(videoUrl, "تم نسخ رابط الفيديو إلى الحافظة!");
    });
  }

  function copyToClipboard(text, successMessage) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMessage);
      }).catch(() => {
        fallbackCopy(text, successMessage);
      });
    } else {
      fallbackCopy(text, successMessage);
    }
  }

  function fallbackCopy(text, successMessage) {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    try {
      document.execCommand("copy");
      showToast(successMessage);
    } catch {
      showToast("يرجى نسخ الرابط يدوياً: " + text);
    }
    document.body.removeChild(el);
  }

  if (dom.btnShareWhatsApp) {
    dom.btnShareWhatsApp.addEventListener("click", () => {
      const videoUrl = getAbsoluteVideoUrl();
      const text = encodeURIComponent(`شاهد هذا العرض العقاري المميز:\n${videoUrl}`);
      window.open(`https://api.whatsapp.com/send?text=${text}`, "_blank");
    });
  }

  if (dom.btnShareTelegram) {
    dom.btnShareTelegram.addEventListener("click", () => {
      const videoUrl = getAbsoluteVideoUrl();
      const text = encodeURIComponent(state.currentJobResult?.script || "عرض عقاري مميز");
      window.open(`https://t.me/share/url?url=${encodeURIComponent(videoUrl)}&text=${text}`, "_blank");
    });
  }

  if (dom.btnCopyVideoLink) {
    dom.btnCopyVideoLink.addEventListener("click", () => {
      copyToClipboard(getAbsoluteVideoUrl(), "تم نسخ الرابط المباشر للفيديو!");
    });
  }

  // ---------------------------------------------------------------------------
  // Production Principles Manager & Live Logs Telemetry
  // ---------------------------------------------------------------------------
  async function loadPrinciplesFromAPI() {
    try {
      const resp = await fetch("/api/principles");
      if (!resp.ok) return;
      const data = await resp.json();
      populatePrinciplesForm(data);
    } catch (e) {
      console.warn("Could not load production principles:", e);
    }
  }

  function populatePrinciplesForm(data) {
    if (!data) return;
    const md = data.master_directive || {};
    const vp = data.voice_principles || {};
    const np = data.narrative_principles || {};
    const vis = data.visual_principles || {};
    const ap = data.annotation_principles || {};

    if (dom.principleCustomInstructions) dom.principleCustomInstructions.value = md.custom_instructions || "";
    if (dom.principleDialect) dom.principleDialect.value = md.dialect || "algerian_darja";
    if (dom.principlePerspective) dom.principlePerspective.value = md.perspective || "videographer_walkthrough";

    if (dom.principleVoiceGuidelines) dom.principleVoiceGuidelines.value = vp.guidelines || "";
    if (dom.principleVoicePacing) dom.principleVoicePacing.value = vp.pacing || "";
    if (dom.principleVoicePronunciation) dom.principleVoicePronunciation.value = vp.pronunciation || "";
    if (dom.principleVoiceToneBias) dom.principleVoiceToneBias.value = vp.active_tone_bias || "فاخر وهادئ";

    if (dom.principleNarrativeGuidelines) dom.principleNarrativeGuidelines.value = np.guidelines || "";
    if (dom.principleNarrativeAlignment) dom.principleNarrativeAlignment.value = np.length_alignment || "";
    if (dom.principleNarrativeAudience) dom.principleNarrativeAudience.value = np.target_audience || "";

    if (dom.principleVisualDucking) dom.principleVisualDucking.value = String(vis.smart_ducking_volume || "0.15");
    if (dom.principleVisualTheme) dom.principleVisualTheme.value = vis.selected_music_theme || "luxury_piano";

    if (dom.principleEnableAutoAnnotations) dom.principleEnableAutoAnnotations.checked = ap.enable_auto_annotations !== false;
    if (dom.principleAnnotationStyle) dom.principleAnnotationStyle.value = ap.font_style || "luxury_gold";
    if (dom.principleAnnotationPosition) dom.principleAnnotationPosition.value = ap.position || "lower_third";
  }

  function getPrinciplesFromForm() {
    return {
      version: "1.1.0",
      master_directive: {
        title: "المبدأ العام والتوجيه المخصص للذكاء الاصطناعي (Master Custom Directive)",
        custom_instructions: dom.principleCustomInstructions?.value?.trim() || "",
        dialect: dom.principleDialect?.value || "algerian_darja",
        perspective: dom.principlePerspective?.value || "videographer_walkthrough",
        scene_connectivity: "connected_visual"
      },
      voice_principles: {
        title: "مبادئ ومعايير التعليق الصوتي العصبي",
        guidelines: dom.principleVoiceGuidelines?.value?.trim() || "",
        pacing: dom.principleVoicePacing?.value?.trim() || "",
        pronunciation: dom.principleVoicePronunciation?.value?.trim() || "",
        active_tone_bias: dom.principleVoiceToneBias?.value || "فاخر وهادئ"
      },
      narrative_principles: {
        title: "مبادئ الوصف المعماري والترويج العقاري",
        guidelines: dom.principleNarrativeGuidelines?.value?.trim() || "",
        length_alignment: dom.principleNarrativeAlignment?.value?.trim() || "",
        target_audience: dom.principleNarrativeAudience?.value?.trim() || ""
      },
      visual_principles: {
        title: "مبادئ الإخراج الصوتي والموسيقي",
        smart_ducking_volume: parseFloat(dom.principleVisualDucking?.value || "0.15"),
        selected_music_theme: dom.principleVisualTheme?.value || "luxury_piano",
        auto_music_matching: true
      },
      annotation_principles: {
        title: "مبادئ الكتابات والملصقات التوضيحية على الفيديو",
        enable_auto_annotations: Boolean(dom.principleEnableAutoAnnotations?.checked),
        font_style: dom.principleAnnotationStyle?.value || "luxury_gold",
        position: dom.principleAnnotationPosition?.value || "lower_third",
        banner_opacity: 0.85
      }
    };
  }

  // Quick Preset Chips for Master Directive
  function appendOrSetDirective(phrase, newDialect = null, newPerspective = null) {
    if (!dom.principleCustomInstructions) return;
    const current = dom.principleCustomInstructions.value.trim();
    if (!current) {
      dom.principleCustomInstructions.value = phrase;
    } else if (!current.includes(phrase)) {
      dom.principleCustomInstructions.value = `${current}، ${phrase}`;
    }
    if (newDialect && dom.principleDialect) dom.principleDialect.value = newDialect;
    if (newPerspective && dom.principlePerspective) dom.principlePerspective.value = newPerspective;
    dom.principleCustomInstructions.focus();
  }

  if (dom.chipDarja) {
    dom.chipDarja.addEventListener("click", () => {
      appendOrSetDirective("إستخدم اللهجة الجزائرية الدارجة العفوية في الوصف والتعليق", "algerian_darja");
    });
  }
  if (dom.chipWalkthrough) {
    dom.chipWalkthrough.addEventListener("click", () => {
      appendOrSetDirective("الصوت يجب أن يكون وصفياً مع المشهد ومتصلاً تماماً كأن الشخص الذي يصور هو من يتكلم بنفسه أثناء الجولة", null, "videographer_walkthrough");
    });
  }
  if (dom.chipConnected) {
    dom.chipConnected.addEventListener("click", () => {
      appendOrSetDirective("التعليق الصوتي وصفي ومتصل بكل مشهد يظهر في الفيديو لحظة بلحظة");
    });
  }
  if (dom.chipFormal) {
    dom.chipFormal.addEventListener("click", () => {
      appendOrSetDirective("تحدث بنبرة عربية فصيحة راقية تبرز الفخامة والأناقة في وصف العقار", "standard_arabic", "third_person_narrator");
    });
  }
  if (dom.chipClear) {
    dom.chipClear.addEventListener("click", () => {
      if (dom.principleCustomInstructions) dom.principleCustomInstructions.value = "";
    });
  }

  function openPrinciplesModal() {
    if (!dom.principlesModal) return;
    loadPrinciplesFromAPI();
    dom.principlesModal.style.display = "flex";
    if (dom.principlesSaveStatus) dom.principlesSaveStatus.style.display = "none";
  }

  function closePrinciplesModal() {
    if (!dom.principlesModal) return;
    dom.principlesModal.style.display = "none";
  }

  if (dom.btnOpenPrinciples) {
    dom.btnOpenPrinciples.addEventListener("click", openPrinciplesModal);
  }
  if (dom.btnClosePrinciples) {
    dom.btnClosePrinciples.addEventListener("click", closePrinciplesModal);
  }
  if (dom.principlesModal) {
    dom.principlesModal.addEventListener("click", (e) => {
      if (e.target === dom.principlesModal) closePrinciplesModal();
    });
  }

  if (dom.principlesForm) {
    dom.principlesForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = getPrinciplesFromForm();
      try {
        if (dom.btnSavePrinciples) dom.btnSavePrinciples.disabled = true;
        const res = await fetch("/api/principles", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          if (dom.principlesSaveStatus) {
            dom.principlesSaveStatus.className = "principles-status-feedback success";
            dom.principlesSaveStatus.textContent = "✓ تم حفظ وتطبيق المبادئ بنجاح في الواجهة الخلفية! ستعتمد في جميع عمليات الإنتاج القادمة.";
            dom.principlesSaveStatus.style.display = "block";
          }
          showToast("تم تطبيق مبادئ الإنتاج بنجاح في الخادم!");
        } else {
          throw new Error(`Server returned ${res.status}`);
        }
      } catch (err) {
        if (dom.principlesSaveStatus) {
          dom.principlesSaveStatus.className = "principles-status-feedback error";
          dom.principlesSaveStatus.textContent = `تعذر حفظ المبادئ: ${err.message}`;
          dom.principlesSaveStatus.style.display = "block";
        }
      } finally {
        if (dom.btnSavePrinciples) dom.btnSavePrinciples.disabled = false;
      }
    });
  }

  if (dom.btnResetPrinciples) {
    dom.btnResetPrinciples.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/principles/reset", { method: "POST" });
        if (res.ok) {
          const resetData = await res.json();
          populatePrinciplesForm(resetData);
          if (dom.principlesSaveStatus) {
            dom.principlesSaveStatus.className = "principles-status-feedback success";
            dom.principlesSaveStatus.textContent = "✓ تم استعادة المبادئ الافتراضية بنجاح.";
            dom.principlesSaveStatus.style.display = "block";
          }
          showToast("تمت استعادة المبادئ الافتراضية بنجاح!");
        }
      } catch (err) {
        showToast("فشل استعادة المبادئ الافتراضية");
      }
    });
  }

  if (dom.btnCopyLogs) {
    dom.btnCopyLogs.addEventListener("click", () => {
      if (!dom.aiAgentLogs) return;
      const entries = dom.aiAgentLogs.querySelectorAll(".log-entry");
      if (entries.length === 0) {
        showToast("سجل الأحداث فارغ حالياً");
        return;
      }
      const lines = [];
      entries.forEach((el) => lines.push(el.innerText.replace(/\s+/g, " ").trim()));
      copyToClipboard(lines.join("\n"), "تم نسخ سجل أحداث الإنتاج كاملاً!");
    });
  }

  // ---------------------------------------------------------------------------
  // Linguistic Prompts & SQLite Saved History Manager
  // ---------------------------------------------------------------------------
  const SAVED_PROMPTS_KEY = "saved_linguistic_prompts_cache";

  const DEFAULT_SAVED_PROMPTS = [
    {
      id: "prompt-1",
      title: "جولة فيلا راقية بإطلالة بحرية",
      visual_description: "جولة تبدأ من الصالون الملكي وتنتقل إلى الشرفة المطلة على البحر مع إبراز المطبخ العصري والحديقة المحيطة",
      speech_description: "رحب بالمشاهدين واشرح مميزات الموقع الهادئ والتشطيبات الفاخرة وسعرها المغري"
    },
    {
      id: "prompt-2",
      title: "شقة عصرية F4 بالجزائر العاصمة",
      visual_description: "استعراض بهو المدخل الفسيح والغرف المشمسة، مع إبراز المطبخ المجهز بأحدث الخزائن والأجهزة والحمام الإيطالي الفاخر",
      speech_description: "أبرز القرب من المواصلات العامة والمدارس والمرافق الحيوية في قلب العاصمة مع الدفتر العقاري الجاهز"
    },
    {
      id: "prompt-3",
      title: "محل تجاري حيوي على واجهة رئيسية",
      visual_description: "تصوير واجهة المحل الزجاجية العريضة على الشارع التجاري الرئيسي، والارتفاع الشاهق للسقف والمساحة المفتوحة",
      speech_description: "ركز على الحركية التجارية العالية، الكثافة السكانية في الحي، والعائد الاستثماري المضمون للمشروع"
    }
  ];

  let currentPromptsList = [];

  async function fetchPromptHistory() {
    try {
      const resp = await fetch("/api/prompts/history");
      if (resp.ok) {
        const data = await resp.json();
        const prompts = Array.isArray(data)
          ? data
          : data.prompts || data.history || data.items || [];

        if (prompts && prompts.length > 0) {
          currentPromptsList = prompts;
          try {
            localStorage.setItem(SAVED_PROMPTS_KEY, JSON.stringify(prompts));
          } catch (_) {}
          renderPromptHistory(currentPromptsList);
          return;
        }
      }
    } catch (e) {
      console.warn("Backend /api/prompts/history not reachable, using cached/mock prompts:", e);
    }

    // Decoupled Fallback: Load from localStorage or DEFAULT_SAVED_PROMPTS
    try {
      const cached = localStorage.getItem(SAVED_PROMPTS_KEY);
      if (cached) {
        currentPromptsList = JSON.parse(cached);
      } else {
        currentPromptsList = [...DEFAULT_SAVED_PROMPTS];
        localStorage.setItem(SAVED_PROMPTS_KEY, JSON.stringify(currentPromptsList));
      }
    } catch (_) {
      currentPromptsList = [...DEFAULT_SAVED_PROMPTS];
    }
    renderPromptHistory(currentPromptsList);
  }

  function renderPromptHistory(prompts) {
    if (!prompts) return;

    // 1. Populate Dropdown Select
    if (dom.promptHistorySelect) {
      dom.promptHistorySelect.innerHTML = '<option value="">-- اختر وصفاً محفوظاً للاستعادة الفورية --</option>';
      prompts.forEach((p, idx) => {
        const opt = document.createElement("option");
        opt.value = p.id || String(idx);
        const title = p.title || p.visual_description?.slice(0, 35) || `وصف محفوظ #${idx + 1}`;
        opt.textContent = `📜 ${title}`;
        dom.promptHistorySelect.appendChild(opt);
      });
    }

    // 2. Populate 1-Tap Quick Restoration Chips
    if (dom.promptHistoryChips) {
      dom.promptHistoryChips.innerHTML = "";
      prompts.forEach((p, idx) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "prompt-chip";
        const title = p.title || p.visual_description?.slice(0, 25) || `وصف ${idx + 1}`;
        chip.textContent = `✨ ${title}`;
        chip.title = "انقر للاستعادة الفورية في حقلي الوصف";
        chip.addEventListener("click", () => {
          restorePrompt(p);
        });
        dom.promptHistoryChips.appendChild(chip);
      });
    }
  }

  function restorePrompt(promptItem) {
    if (!promptItem) return;
    if (dom.visualDescription) {
      dom.visualDescription.value = promptItem.visual_description || "";
      dom.visualDescription.classList.remove("flash-highlight");
      void dom.visualDescription.offsetWidth; // re-trigger animation
      dom.visualDescription.classList.add("flash-highlight");
    }
    if (dom.speechDescription) {
      dom.speechDescription.value = promptItem.speech_description || "";
      dom.speechDescription.classList.remove("flash-highlight");
      void dom.speechDescription.offsetWidth;
      dom.speechDescription.classList.add("flash-highlight");
    }
    const label = promptItem.title || promptItem.visual_description?.slice(0, 25) || "الوصف";
    showToast(`تم استعادة ${label} بنجاح!`);
  }

  async function saveCurrentPrompt() {
    const visual = (dom.visualDescription?.value || "").trim();
    const speech = (dom.speechDescription?.value || "").trim();

    if (!visual && !speech) {
      if (dom.promptSaveStatus) {
        dom.promptSaveStatus.className = "prompt-status-msg error";
        dom.promptSaveStatus.textContent = "يرجى كتابة وصف مرئي أو صوتي قبل الحفظ!";
        dom.promptSaveStatus.style.display = "block";
      }
      showToast("يرجى كتابة وصف مرئي أو صوتي قبل الحفظ!");
      return;
    }

    const title = visual.slice(0, 30) || speech.slice(0, 30) || "وصف مخصص";
    const newPrompt = {
      id: `prompt-${Date.now()}`,
      title: title,
      visual_description: visual,
      speech_description: speech,
      created_at: new Date().toISOString()
    };

    if (dom.btnSavePrompt) dom.btnSavePrompt.disabled = true;

    try {
      const resp = await fetch("/api/prompts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newPrompt)
      });

      if (resp.ok) {
        const saved = await resp.json().catch(() => ({}));
        const savedItem = saved.prompt || saved.item || newPrompt;
        currentPromptsList.unshift(savedItem);
        try {
          localStorage.setItem(SAVED_PROMPTS_KEY, JSON.stringify(currentPromptsList));
        } catch (_) {}
        renderPromptHistory(currentPromptsList);
        if (dom.promptSaveStatus) {
          dom.promptSaveStatus.className = "prompt-status-msg success";
          dom.promptSaveStatus.textContent = "✓ تم حفظ الوصف الحالي بنجاح في قاعدة البيانات!";
          dom.promptSaveStatus.style.display = "block";
        }
        showToast("✓ تم حفظ الوصف الحالي بنجاح!");
      } else {
        throw new Error(`Server returned status ${resp.status}`);
      }
    } catch (e) {
      console.warn("Backend /api/prompts not ready, saving to decoupled localStorage:", e);
      // Decoupled Mock Fallback
      currentPromptsList.unshift(newPrompt);
      try {
        localStorage.setItem(SAVED_PROMPTS_KEY, JSON.stringify(currentPromptsList));
      } catch (_) {}
      renderPromptHistory(currentPromptsList);
      if (dom.promptSaveStatus) {
        dom.promptSaveStatus.className = "prompt-status-msg success";
        dom.promptSaveStatus.textContent = "✓ تم حفظ الوصف بنجاح في السجل المحلي!";
        dom.promptSaveStatus.style.display = "block";
      }
      showToast("✓ تم حفظ الوصف الحالي بنجاح!");
    } finally {
      if (dom.btnSavePrompt) dom.btnSavePrompt.disabled = false;
      setTimeout(() => {
        if (dom.promptSaveStatus) dom.promptSaveStatus.style.display = "none";
      }, 4000);
    }
  }

  // Handle prompt select change
  if (dom.promptHistorySelect) {
    dom.promptHistorySelect.addEventListener("change", (e) => {
      const selectedId = e.target.value;
      if (!selectedId) return;
      const found = currentPromptsList.find(
        (p, idx) => p.id === selectedId || String(idx) === selectedId
      );
      if (found) {
        restorePrompt(found);
      }
    });
  }

  // Handle refresh prompt history
  if (dom.btnRefreshPromptHistory) {
    dom.btnRefreshPromptHistory.addEventListener("click", () => {
      fetchPromptHistory();
      showToast("تم تحديث سجل الأوصاف");
    });
  }

  // Handle save current prompt
  if (dom.btnSavePrompt) {
    dom.btnSavePrompt.addEventListener("click", saveCurrentPrompt);
  }

  // Handle clear prompts
  if (dom.btnClearPrompts) {
    dom.btnClearPrompts.addEventListener("click", () => {
      if (dom.visualDescription) dom.visualDescription.value = "";
      if (dom.speechDescription) dom.speechDescription.value = "";
      showToast("تم تفريغ حقلي الوصف");
    });
  }

  // Handle accordion toggle to fetch prompt history
  if (dom.advancedAccordion) {
    dom.advancedAccordion.addEventListener("toggle", () => {
      if (dom.advancedAccordion.open) {
        fetchPromptHistory();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Reset & New Video Handlers
  // ---------------------------------------------------------------------------
  if (dom.btnStartNewProduction) {
    dom.btnStartNewProduction.addEventListener("click", resetSessionAndNewVideo);
  }
  if (dom.btnResetNewVideo) {
    dom.btnResetNewVideo.addEventListener("click", resetSessionAndNewVideo);
  }
  if (dom.btnCancelSession) {
    dom.btnCancelSession.addEventListener("click", resetSessionAndNewVideo);
  }

  // ---------------------------------------------------------------------------
  // Initialization & Session Reconnection on Load
  // ---------------------------------------------------------------------------
  async function init() {
    checkServerHealth();
    await loadPresetsFromAPI();
    await loadPrinciplesFromAPI();
    await fetchPromptHistory();
    updateScriptAnalytics();
    await restoreSavedSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
