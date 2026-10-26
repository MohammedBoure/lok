/**
 * Algerian Real Estate Mobile Studio - Client Application Logic (web/static/app.js)
 * Author: MohammedBoure
 * Role: Mobile Front-End & Real Estate UI/UX Lead (agy51)
 * Branch: frontend/agy51-mobile-web-system
 */

(() => {
  'use strict';

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
    processingSecondsElapsed: 0,
    processingTimerInterval: null,
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

    // Presets & Script
    presetsSelectorGrid: document.getElementById("presetsSelectorGrid"),
    scriptText: document.getElementById("scriptText"),
    wordCount: document.getElementById("wordCount"),
    charCount: document.getElementById("charCount"),
    speechEstDuration: document.getElementById("speechEstDuration"),
    btnResetScript: document.getElementById("btnResetScript"),
    btnClearScript: document.getElementById("btnClearScript"),

    // Audio & Ducking
    voiceSelect: document.getElementById("voiceSelect"),
    duckSlider: document.getElementById("duckSlider"),
    duckValBadge: document.getElementById("duckValBadge"),

    // Production Stepper & CTA
    btnProduce: document.getElementById("btnProduce"),
    stepperBox: document.getElementById("stepperBox"),
    stepperTimer: document.getElementById("stepperTimer"),
    progressBarFill: document.getElementById("progressBarFill"),
    stepsList: document.getElementById("stepsList"),

    // Result & Delivery
    resultSection: document.getElementById("resultSection"),
    finalVideoPlayer: document.getElementById("finalVideoPlayer"),
    telemetryBadgesGrid: document.getElementById("telemetryBadgesGrid"),
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
      // Backend might be offline or starting
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
      // Close viewfinder if open
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
      // Release existing tracks
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

    // Populate initial text if textarea is empty
    const active = presets.find((p) => p.id === state.currentPresetId) || presets[0];
    if (active && !dom.scriptText.value.trim()) {
      dom.scriptText.value = active.description;
      updateScriptAnalytics();
    }
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
  // Animated Multi-Stage Processing Stepper
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

  function startProcessingStepper() {
    state.isProcessing = true;
    state.processingSecondsElapsed = 0;
    dom.btnProduce.disabled = true;
    dom.stepperBox.style.display = "block";
    dom.resultSection.style.display = "none";
    dom.stepperTimer.textContent = "00:00";

    setStepperState(1, 15);

    // Elapsed timer
    state.processingTimerInterval = setInterval(() => {
      state.processingSecondsElapsed++;
      dom.stepperTimer.textContent = formatSeconds(state.processingSecondsElapsed);
    }, 1000);

    // Smooth progressive stepper advancement during the processing request
    // Step 2 at ~1.5s (Extracting keyframes)
    state.stepAnimationTimeout = setTimeout(() => {
      if (state.isProcessing) setStepperState(2, 38);

      // Step 3 at ~3.5s (Neural Voiceover)
      state.stepAnimationTimeout = setTimeout(() => {
        if (state.isProcessing) setStepperState(3, 62);

        // Step 4 at ~5.5s (Sidechain Ducking & Assembly)
        state.stepAnimationTimeout = setTimeout(() => {
          if (state.isProcessing) setStepperState(4, 85);
        }, 2000);
      }, 2000);
    }, 1500);
  }

  function finishProcessingStepper(success = true) {
    state.isProcessing = false;
    clearInterval(state.processingTimerInterval);
    clearTimeout(state.stepAnimationTimeout);
    dom.btnProduce.disabled = false;

    if (success) {
      setStepperState(5, 100);
    } else {
      dom.stepperBox.style.display = "none";
    }
  }

  // ---------------------------------------------------------------------------
  // Video Production Action & API Dispatch
  // ---------------------------------------------------------------------------
  if (dom.btnProduce) {
    dom.btnProduce.addEventListener("click", async () => {
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

      // 2. Prepare FormData matching web/server.py upload-and-process contract
      const formData = new FormData();
      formData.append("video", state.selectedFile);

      const scriptVal = (dom.scriptText?.value || "").trim();
      if (scriptVal) {
        formData.append("script", scriptVal);
      }

      if (state.currentPresetId) {
        formData.append("preset", state.currentPresetId);
      }

      if (dom.voiceSelect?.value) {
        formData.append("voice", dom.voiceSelect.value);
      }

      if (dom.duckSlider?.value) {
        formData.append("duck_level", dom.duckSlider.value);
      }

      // 3. Initiate Stepper & Request
      startProcessingStepper();
      dom.stepperBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

      try {
        const response = await fetch("/api/upload-and-process", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `خطأ في المعالجة (رمز الاستجابة: ${response.status})`);
        }

        const data = await response.json();
        finishProcessingStepper(true);

        // Allow user to see Step 5 "Complete" for 500ms before revealing output
        setTimeout(() => {
          displayFinalResult(data);
        }, 500);

      } catch (err) {
        finishProcessingStepper(false);
        console.error("Video processing failed:", err);
        showToast(`فشل الإنتاج: ${err.message}`);
      }
    });
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

    // Telemetry Badges
    const duration = data.duration ? `${data.duration.toFixed(1)} ثانية` : "--";
    const res = data.resolution || "--";
    const orientationLabel = data.orientation === "portrait" ? "عمودي 9:16" : "أفقي 16:9";
    const synth = data.synthesizer || "Gemini Neural";
    const renderTime = data.metadata?.render_seconds ? `${data.metadata.render_seconds}s` : "--";
    const fileSize = data.file_size_bytes ? formatBytes(data.file_size_bytes) : "--";
    const jobId = data.job_id || "--";

    dom.telemetryBadgesGrid.innerHTML = `
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

  // New production reset button
  if (dom.btnStartNewProduction) {
    dom.btnStartNewProduction.addEventListener("click", () => {
      state.selectedFile = null;
      dom.previewPlayer.src = "";
      dom.videoPreviewCard.style.display = "none";
      dom.resultSection.style.display = "none";
      dom.stepperBox.style.display = "none";
      window.scrollTo({ top: 0, behavior: "smooth" });
      showToast("جاهز لتصوير أو اختيار فيديو جديد");
    });
  }

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------
  async function init() {
    checkServerHealth();
    await loadPresetsFromAPI();
    updateScriptAnalytics();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
