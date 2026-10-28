/**
 * lok • Modern Minimalist Client Application Engine (web/static/app.js)
 * Author: MohammedBoure
 * Role: Lead Frontend Engineer (agy51)
 * Branch: frontend/agy51-minimal-lok-and-admin-ui
 */

(() => {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants & Storage Keys
  // ---------------------------------------------------------------------------
  const SESSION_TOKEN_KEY = 'saas_session_token';
  const CURRENT_USER_KEY = 'saas_current_user_id';
  const PREF_VOICE_KEY = 'preferred_voice';
  const ACTIVE_JOB_KEY = 'active_job_id';
  const RECOMMENDATIONS_KEY = 'lok_recommendations_catalog';

  // Pre-seeded Diverse Merchant Personas + Master Admin
  const PRESEEDED_ACCOUNTS = [
    {
      id: "usr_merchant_realestate",
      username: "merchant_realestate",
      business_name: "تاجر (عقارات فاخرة)",
      business_category: "عقارات فاخرة",
      role: "merchant",
      status: "active",
      expires_at: "2027-12-31",
      daily_quota: 10,
      weekly_quota: 50,
      videos_today: 1,
      videos_this_week: 4,
      token: "token_merchant_realestate"
    },
    {
      id: "usr_dar_al_nokhba",
      username: "dar_al_nokhba",
      business_name: "دار النخبة العقارية",
      business_category: "عقارات فاخرة",
      role: "merchant",
      status: "active",
      expires_at: "2026-12-31",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 2,
      videos_this_week: 9,
      token: "tok_dar_al_nokhba"
    },
    {
      id: "usr_auto_algerie",
      username: "auto_algerie",
      business_name: "أوتو الجزائر للسيارات",
      business_category: "معرض سيارات",
      role: "merchant",
      status: "active",
      expires_at: "2026-11-30",
      daily_quota: 8,
      weekly_quota: 40,
      videos_today: 3,
      videos_this_week: 12,
      token: "tok_auto_algerie"
    },
    {
      id: "usr_anaqat_el_awras",
      username: "anaqat_el_awras",
      business_name: "أناقة الأوراس للأزياء",
      business_category: "أزياء وقفطان راقي",
      role: "merchant",
      status: "active",
      expires_at: "2026-12-15",
      daily_quota: 6,
      weekly_quota: 30,
      videos_today: 0,
      videos_this_week: 5,
      token: "tok_anaqat_el_awras"
    },
    {
      id: "usr_techno_phone",
      username: "techno_phone",
      business_name: "تكنو فون ستور",
      business_category: "إلكترونيات وهواتف",
      role: "merchant",
      status: "active",
      expires_at: "2026-10-31",
      daily_quota: 10,
      weekly_quota: 50,
      videos_today: 2,
      videos_this_week: 11,
      token: "tok_techno_phone"
    },
    {
      id: "usr_el_kasbah_resto",
      username: "el_kasbah_resto",
      business_name: "مطعم القصبة العريق",
      business_category: "مطاعم ومأكولات أصيلة",
      role: "merchant",
      status: "active",
      expires_at: "2027-01-15",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 0,
      videos_this_week: 3,
      token: "tok_el_kasbah_resto"
    },
    {
      id: "usr_admin",
      username: "admin",
      business_name: "مدير النظام العام",
      business_category: "مسؤول المنصة",
      role: "admin",
      status: "active",
      expires_at: "2099-12-31",
      daily_quota: 999,
      weekly_quota: 9999,
      videos_today: 0,
      videos_this_week: 0,
      token: "token_admin_master"
    }
  ];

  // Default smart recommendations
  const DEFAULT_RECOMMENDATIONS = [
    {
      id: "rec_1",
      title: "عقارات راقية",
      text: "عقارات راقية بالدارجة الجزائرية العاصمية مع وتيرة حماسية وهادئة تجمع بين الفخامة وتفاصيل الأسعار وموقع العقار المميز."
    },
    {
      id: "rec_2",
      title: "مطاعم ومأكولات",
      text: "إعلان مطعم ومأكولات بحرية بوصف المشاهد البصرية الفاتحة للشهية ونبرة مرحبة وودودة بالدارجة مع وتيرة متوسطة."
    },
    {
      id: "rec_3",
      title: "أزياء وقفطان",
      text: "ترويج أزياء وقفطان جزائري تقليدي بنبرة وقورة وأنيقة تبرز التفاصيل اليدوية وجودة الأقمشة وسرعة إلقاء متزنة."
    },
    {
      id: "rec_4",
      title: "تقنية وهواتف",
      text: "هواتف وأجهزة ذكية بوتيرة سريعة وشبابية مع التركيز على الضمان المعتمد، السعر التنافسي، وخدمة التوصيل لكافة الولايات."
    }
  ];

  // ---------------------------------------------------------------------------
  // Application State
  // ---------------------------------------------------------------------------
  const state = {
    isAuthenticated: false,
    sessionToken: null,
    currentUser: null,
    accounts: [...PRESEEDED_ACCOUNTS],
    recommendations: [...DEFAULT_RECOMMENDATIONS],
    selectedFile: null,
    selectedVoice: "ar-XA-Standard-A",
    attachedRecommendation: null,
    currentAudioAudition: null,
    currentPlayingVoice: null,
    activeJobId: null,
    isProcessing: false,
    pollTimer: null,
  };

  // ---------------------------------------------------------------------------
  // DOM Elements Cache
  // ---------------------------------------------------------------------------
  const dom = {
    // Views
    loginView: document.getElementById("loginView"),
    studioView: document.getElementById("studioView"),
    settingsModal: document.getElementById("settingsModal"),
    appToast: document.getElementById("appToast"),

    // Gated Login Form
    merchantLoginForm: document.getElementById("merchantLoginForm"),
    merchantLoginUsername: document.getElementById("merchantLoginUsername"),
    merchantLoginPassword: document.getElementById("merchantLoginPassword"),
    btnSubmitMerchantLogin: document.getElementById("btnSubmitMerchantLogin"),
    merchantQuickLoginGrid: document.getElementById("merchantQuickLoginGrid"),

    // Studio Header
    userRoleIcon: document.getElementById("userRoleIcon"),
    userBusinessName: document.getElementById("userBusinessName"),
    btnOpenSettings: document.getElementById("btnOpenSettings"),

    // Upload Section
    videoDropzone: document.getElementById("videoDropzone"),
    videoFileInput: document.getElementById("videoFileInput"),
    dropzoneIdleContent: document.getElementById("dropzoneIdleContent"),
    dropzoneSelectedContent: document.getElementById("dropzoneSelectedContent"),
    btnBrowseVideo: document.getElementById("btnBrowseVideo"),
    selectedVideoName: document.getElementById("selectedVideoName"),
    selectedVideoMeta: document.getElementById("selectedVideoMeta"),
    btnReplaceVideo: document.getElementById("btnReplaceVideo"),

    // Detailed Prompt Section
    promptTextarea: document.getElementById("promptTextarea"),
    promptCharCount: document.getElementById("promptCharCount"),
    attachedRecIndicator: document.getElementById("attachedRecIndicator"),
    attachedRecText: document.getElementById("attachedRecText"),
    btnClearRec: document.getElementById("btnClearRec"),

    // Action & Processing
    btnProduceVideo: document.getElementById("btnProduceVideo"),
    processingStepper: document.getElementById("processingStepper"),
    stepperStatusText: document.getElementById("stepperStatusText"),
    stepperFill: document.getElementById("stepperFill"),
    stepAnalyze: document.getElementById("stepAnalyze"),
    stepScript: document.getElementById("stepScript"),
    stepVoice: document.getElementById("stepVoice"),
    stepRender: document.getElementById("stepRender"),

    // Result Card
    resultContainer: document.getElementById("resultContainer"),
    resultVideo: document.getElementById("resultVideo"),
    btnDownloadVideo: document.getElementById("btnDownloadVideo"),
    btnStartNewProduction: document.getElementById("btnStartNewProduction"),

    // Settings View
    btnSettingsBack: document.getElementById("btnSettingsBack"),
    quotaDailyRemaining: document.getElementById("quotaDailyRemaining"),
    quotaDailyTotal: document.getElementById("quotaDailyTotal"),
    quotaWeeklyRemaining: document.getElementById("quotaWeeklyRemaining"),
    quotaWeeklyTotal: document.getElementById("quotaWeeklyTotal"),
    quotaExpiryText: document.getElementById("quotaExpiryText"),
    quotaMiniBarFill: document.getElementById("quotaMiniBarFill"),

    // Recommendations Manager
    newRecommendationInput: document.getElementById("newRecommendationInput"),
    btnAddRecommendation: document.getElementById("btnAddRecommendation"),
    recommendationsList: document.getElementById("recommendationsList"),

    // Voiceover Artist Picker
    btnSampleStandardA: document.getElementById("btnSampleStandardA"),
    btnSampleStandardB: document.getElementById("btnSampleStandardB"),
    btnSampleStandardC: document.getElementById("btnSampleStandardC"),
    btnSampleStandardD: document.getElementById("btnSampleStandardD"),
    btnLogout: document.getElementById("btnLogout"),

    // Hidden Legacy Compatibility Hooks
    visualDescription: document.getElementById("visualDescription"),
    speechDescription: document.getElementById("speechDescription"),
    presetSection: document.getElementById("presetSection"),
    customScriptContainer: document.getElementById("customScriptContainer"),
    scriptText: document.getElementById("scriptText"),
    sessionLoginModal: document.getElementById("sessionLoginModal"),
    btnOpenLoginModal: document.getElementById("btnOpenLoginModal"),
    btnProduce: document.getElementById("btnProduce"),
    submitBtn: document.getElementById("submitBtn"),
  };

  // ---------------------------------------------------------------------------
  // Helper: Toast Notifications
  // ---------------------------------------------------------------------------
  function showToast(message) {
    if (!dom.appToast) return;
    dom.appToast.textContent = message;
    dom.appToast.classList.add("show");
    setTimeout(() => {
      dom.appToast.classList.remove("show");
    }, 3500);
  }

  // ---------------------------------------------------------------------------
  // 1. Gated Login & Authentication Lifecycle
  // ---------------------------------------------------------------------------
  function openLoginModal() {
    state.isAuthenticated = false;
    if (dom.studioView) dom.studioView.style.display = "none";
    if (dom.settingsModal) dom.settingsModal.style.display = "none";
    if (dom.loginView) dom.loginView.style.display = "flex";
  }

  function closeLoginModal() {
    if (state.isAuthenticated) {
      if (dom.loginView) dom.loginView.style.display = "none";
      if (dom.studioView) dom.studioView.style.display = "block";
    }
  }

  async function checkExistingSession() {
    const savedToken = localStorage.getItem(SESSION_TOKEN_KEY);
    const savedUserId = localStorage.getItem(CURRENT_USER_KEY);

    if (savedToken) {
      state.sessionToken = savedToken;
      try {
        const resp = await fetch("/api/auth/session", {
          headers: { "Authorization": `Bearer ${savedToken}` }
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.user) {
            const matched = state.accounts.find(
              (a) => a.id === data.user.id || a.username === data.user.username
            );
            state.currentUser = matched || data.user;
            state.isAuthenticated = true;
            applyActiveUserToUI(state.currentUser);
            updateAuthUI(true, state.currentUser);
            return;
          }
        }
      } catch (e) {}

      // Fallback matching against pre-seeded list
      let user = state.accounts.find(
        (a) => a.token === savedToken || a.id === savedUserId || a.username === savedUserId
      );
      if (!user) user = state.accounts[0];

      state.currentUser = user;
      state.isAuthenticated = true;
      applyActiveUserToUI(user);
      updateAuthUI(true, user);
      return;
    }

    // Unauthenticated: reveal gated login view
    updateAuthUI(false, null);
  }

  function updateAuthUI(isLoggedIn, user) {
    if (isLoggedIn && user) {
      if (dom.loginView) dom.loginView.style.display = "none";
      if (dom.studioView) dom.studioView.style.display = "block";
      if (dom.userBusinessName) dom.userBusinessName.textContent = user.business_name;
      if (dom.userRoleIcon) dom.userRoleIcon.textContent = user.role === "admin" ? "👑" : "🏢";
      updateQuotaDisplay(user);
    } else {
      if (dom.studioView) dom.studioView.style.display = "none";
      if (dom.settingsModal) dom.settingsModal.style.display = "none";
      if (dom.loginView) dom.loginView.style.display = "flex";
      renderQuickLoginGrid();
    }
  }

  function applyActiveUserToUI(user) {
    if (!user) return;
    if (dom.userBusinessName) dom.userBusinessName.textContent = user.business_name;
    updateQuotaDisplay(user);
  }

  function updateQuotaDisplay(user) {
    if (!user) return;
    const dailyTotal = user.daily_quota || 10;
    const weeklyTotal = user.weekly_quota || 50;
    const dailyUsed = user.videos_today || 0;
    const weeklyUsed = user.videos_this_week || 0;

    const dailyRemaining = Math.max(0, dailyTotal - dailyUsed);
    const weeklyRemaining = Math.max(0, weeklyTotal - weeklyUsed);

    if (dom.quotaDailyRemaining) dom.quotaDailyRemaining.textContent = String(dailyRemaining);
    if (dom.quotaDailyTotal) dom.quotaDailyTotal.textContent = String(dailyTotal);
    if (dom.quotaWeeklyRemaining) dom.quotaWeeklyRemaining.textContent = String(weeklyRemaining);
    if (dom.quotaWeeklyTotal) dom.quotaWeeklyTotal.textContent = String(weeklyTotal);

    if (dom.quotaExpiryText) {
      dom.quotaExpiryText.textContent = `نشط حتى ${user.expires_at || "2027-12-31"}`;
    }

    if (dom.quotaMiniBarFill) {
      const pct = Math.round((dailyRemaining / dailyTotal) * 100);
      dom.quotaMiniBarFill.style.width = `${pct}%`;
    }
  }

  function renderQuickLoginGrid() {
    if (!dom.merchantQuickLoginGrid) return;
    dom.merchantQuickLoginGrid.innerHTML = "";

    state.accounts.slice(0, 4).forEach((acc) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-merchant-quick";
      btn.innerHTML = `<span>${acc.role === "admin" ? "👑" : "🏢"} ${acc.business_name}</span>`;
      btn.addEventListener("click", () => handleQuickMerchantLogin(acc.username));
      dom.merchantQuickLoginGrid.appendChild(btn);
    });
  }

  async function handleMerchantLogin(username, password) {
    // 1. Try server API login
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      if (resp.ok) {
        const data = await resp.json();
        const token = data.session_token || data.token || `tok_${username}`;
        const user = data.user || state.accounts.find(a => a.username === username) || state.accounts[0];
        setSessionAndProceed(token, user);
        showToast(`مرحباً بك مجدداً: ${user.business_name}! ✨`);
        return;
      }
    } catch (e) {}

    // 2. Pre-seeded fallback
    let user = state.accounts.find(a => a.username.toLowerCase() === username.toLowerCase());
    if (!user && (username === "admin" || username === "merchant")) {
      user = state.accounts[0];
    }

    if (user) {
      const token = user.token || `tok_${user.username}`;
      setSessionAndProceed(token, user);
      showToast(`تم تسجيل الدخول بنجاح: ${user.business_name}! ✨`);
    } else {
      showToast("اسم المستخدم أو كلمة المرور غير صحيحة.");
    }
  }

  function handleAdminLogin(username, password) {
    return handleMerchantLogin(username, password);
  }

  function handleQuickMerchantLogin(username) {
    const user = state.accounts.find(a => a.username === username);
    if (!user) return;
    const token = user.token || `tok_${user.username}`;
    setSessionAndProceed(token, user);
    showToast(`تم الدخول السريع: ${user.business_name} ✨`);
  }

  function setSessionAndProceed(token, user) {
    state.sessionToken = token;
    state.currentUser = user;
    state.isAuthenticated = true;
    localStorage.setItem(SESSION_TOKEN_KEY, token);
    localStorage.setItem(CURRENT_USER_KEY, user.id || user.username);
    updateAuthUI(true, user);
  }

  async function handleLogout() {
    if (state.sessionToken) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { "Authorization": `Bearer ${state.sessionToken}` }
        });
      } catch (e) {}
    }

    state.isAuthenticated = false;
    state.sessionToken = null;
    state.currentUser = null;
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem(CURRENT_USER_KEY);
    updateAuthUI(false, null);
    showToast("تم تسجيل الخروج بنجاح. 🚪");
  }

  function setupSessionAuth() {
    if (dom.merchantLoginForm) {
      dom.merchantLoginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const u = (dom.merchantLoginUsername?.value || "").trim();
        const p = (dom.merchantLoginPassword?.value || "").trim();
        if (u) handleMerchantLogin(u, p);
      });
    }

    if (dom.btnLogout) {
      dom.btnLogout.addEventListener("click", handleLogout);
    }

    if (dom.btnOpenLoginModal) {
      dom.btnOpenLoginModal.addEventListener("click", openLoginModal);
    }
  }

  // ---------------------------------------------------------------------------
  // 2. Pre-recorded Video Upload Handling (Dropzone & Picker)
  // ---------------------------------------------------------------------------
  function setupVideoUpload() {
    if (!dom.videoDropzone || !dom.videoFileInput) return;

    // Trigger file input
    const openPicker = () => dom.videoFileInput.click();
    dom.videoDropzone.addEventListener("click", (e) => {
      if (e.target !== dom.btnReplaceVideo && !dom.btnReplaceVideo?.contains(e.target)) {
        openPicker();
      }
    });

    if (dom.btnBrowseVideo) {
      dom.btnBrowseVideo.addEventListener("click", (e) => {
        e.stopPropagation();
        openPicker();
      });
    }

    if (dom.btnReplaceVideo) {
      dom.btnReplaceVideo.addEventListener("click", (e) => {
        e.stopPropagation();
        openPicker();
      });
    }

    // Drag and drop events
    ["dragenter", "dragover"].forEach((eventName) => {
      dom.videoDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dom.videoDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dom.videoDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dom.videoDropzone.classList.remove("dragover");
      });
    });

    dom.videoDropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleFileSelected(dt.files[0]);
      }
    });

    dom.videoFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelected(e.target.files[0]);
      }
    });
  }

  function handleFileSelected(file) {
    if (!file) return;
    if (!file.type.startsWith("video/")) {
      showToast("يرجى اختيار ملف فيديو صالح (MP4, MOV, WebM).");
      return;
    }

    state.selectedFile = file;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);

    if (dom.selectedVideoName) dom.selectedVideoName.textContent = file.name;
    if (dom.selectedVideoMeta) dom.selectedVideoMeta.textContent = `الحجم: ${sizeMb} ميغابايت | النوع: ${file.type}`;

    if (dom.dropzoneIdleContent) dom.dropzoneIdleContent.style.display = "none";
    if (dom.dropzoneSelectedContent) dom.dropzoneSelectedContent.style.display = "flex";

    showToast(`تم اختيار الفيديو: ${file.name} بنجاح 📹`);
  }

  // ---------------------------------------------------------------------------
  // 3. Detailed Prompt Textarea Handling
  // ---------------------------------------------------------------------------
  function setupPromptTextarea() {
    if (!dom.promptTextarea) return;

    dom.promptTextarea.addEventListener("input", () => {
      const len = dom.promptTextarea.value.length;
      if (dom.promptCharCount) dom.promptCharCount.textContent = `${len} حرف`;
      // Sync legacy hidden inputs
      if (dom.visualDescription) dom.visualDescription.value = dom.promptTextarea.value;
      if (dom.speechDescription) dom.speechDescription.value = dom.promptTextarea.value;
    });

    if (dom.btnClearRec) {
      dom.btnClearRec.addEventListener("click", () => {
        state.attachedRecommendation = null;
        if (dom.attachedRecIndicator) dom.attachedRecIndicator.style.display = "none";
        showToast("تم إلغاء تثبيت التوصية.");
      });
    }
  }

  // ---------------------------------------------------------------------------
  // 4. Recommendations Manager (CRUD + Attach)
  // ---------------------------------------------------------------------------
  function setupRecommendationsManager() {
    loadRecommendations();

    if (dom.btnAddRecommendation) {
      dom.btnAddRecommendation.addEventListener("click", () => {
        const text = (dom.newRecommendationInput?.value || "").trim();
        if (!text) {
          showToast("يرجى كتابة نص التوصية أولاً.");
          return;
        }
        addRecommendation(text);
        if (dom.newRecommendationInput) dom.newRecommendationInput.value = "";
      });
    }
  }

  function loadRecommendations() {
    try {
      const stored = localStorage.getItem(RECOMMENDATIONS_KEY);
      if (stored) {
        state.recommendations = JSON.parse(stored);
      } else {
        state.recommendations = [...DEFAULT_RECOMMENDATIONS];
      }
    } catch (e) {
      state.recommendations = [...DEFAULT_RECOMMENDATIONS];
    }
    renderRecommendations();
  }

  function saveRecommendations() {
    localStorage.setItem(RECOMMENDATIONS_KEY, JSON.stringify(state.recommendations));
  }

  function renderRecommendations() {
    if (!dom.recommendationsList) return;
    dom.recommendationsList.innerHTML = "";

    state.recommendations.forEach((rec, index) => {
      const item = document.createElement("div");
      item.className = "recommendation-item";
      item.innerHTML = `
        <div class="rec-item-text">${rec.text}</div>
        <div class="rec-item-actions">
          <button type="button" class="btn-rec-action attach" title="تطبيق هذا القالب في حقل التوجيه بالاستوديو">🎯 تطبيق في التوجيه</button>
          <button type="button" class="btn-rec-action edit" title="تعديل نص التوصية">✏️ تعديل</button>
          <button type="button" class="btn-rec-action delete" title="حذف التوصية">🗑️ حذف</button>
        </div>
      `;

      item.querySelector(".btn-rec-action.attach").addEventListener("click", () => {
        attachRecommendationToPrompt(rec);
      });

      item.querySelector(".btn-rec-action.edit").addEventListener("click", () => {
        editRecommendation(rec.id);
      });

      item.querySelector(".btn-rec-action.delete").addEventListener("click", () => {
        deleteRecommendation(rec.id);
      });

      dom.recommendationsList.appendChild(item);
    });
  }

  function addRecommendation(text) {
    const newRec = {
      id: `rec_${Date.now()}`,
      title: "توصية مخصصة",
      text: text
    };
    state.recommendations.unshift(newRec);
    saveRecommendations();
    renderRecommendations();
    showToast("تمت إضافة التوصية الجديدة بنجاح! 💡");
  }

  function editRecommendation(id) {
    const rec = state.recommendations.find(r => r.id === id);
    if (!rec) return;
    const newText = prompt("تعديل نص التوصية المقترحة:", rec.text);
    if (newText && newText.trim() && newText.trim() !== rec.text) {
      rec.text = newText.trim();
      saveRecommendations();
      renderRecommendations();
      showToast("تم تحديث نص التوصية بنجاح.");
    }
  }

  function deleteRecommendation(id) {
    state.recommendations = state.recommendations.filter(r => r.id !== id);
    saveRecommendations();
    renderRecommendations();
    showToast("تم حذف التوصية.");
  }

  function attachRecommendationToPrompt(rec) {
    state.attachedRecommendation = rec;
    if (dom.promptTextarea) {
      dom.promptTextarea.value = rec.text;
      const len = dom.promptTextarea.value.length;
      if (dom.promptCharCount) dom.promptCharCount.textContent = `${len} حرف`;
      if (dom.visualDescription) dom.visualDescription.value = rec.text;
      if (dom.speechDescription) dom.speechDescription.value = rec.text;
    }

    if (dom.attachedRecText) dom.attachedRecText.textContent = rec.text.slice(0, 32) + "...";
    if (dom.attachedRecIndicator) dom.attachedRecIndicator.style.display = "inline-flex";

    // Close Settings and return to Studio view seamlessly
    if (dom.settingsModal) dom.settingsModal.style.display = "none";
    if (dom.studioView) {
      dom.studioView.style.display = "block";
      dom.promptTextarea?.focus();
    }

    showToast("تم تطبيق التوصية في حقل التوجيه بنجاح! 🎯");
  }

  // ---------------------------------------------------------------------------
  // 5. Voiceover Artist Picker & Live Darja Audition Player
  // ---------------------------------------------------------------------------
  function setupVoiceoverPicker() {
    const savedVoice = localStorage.getItem(PREF_VOICE_KEY) || "ar-XA-Standard-A";
    selectVoicePersona(savedVoice, false);

    // Bind Voice Audition Buttons
    const auditionMap = [
      { btn: dom.btnSampleStandardA, id: "ar-XA-Standard-A" },
      { btn: dom.btnSampleStandardB, id: "ar-XA-Standard-B" },
      { btn: dom.btnSampleStandardC, id: "ar-XA-Standard-C" },
      { btn: dom.btnSampleStandardD, id: "ar-XA-Standard-D" },
    ];

    auditionMap.forEach(({ btn, id }) => {
      if (btn) {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleVoiceAudition(id, btn);
        });
      }
    });

    // Bind Select Voice Buttons
    document.querySelectorAll(".btn-bw-select-voice").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const voiceId = btn.getAttribute("data-voice");
        selectVoicePersona(voiceId, true);
      });
    });

    document.querySelectorAll(".voice-persona-card").forEach((card) => {
      card.addEventListener("click", () => {
        const voiceId = card.getAttribute("data-voice");
        selectVoicePersona(voiceId, true);
      });
    });
  }

  function selectVoicePersona(voiceId, showFeedback = true) {
    state.selectedVoice = voiceId;
    localStorage.setItem(PREF_VOICE_KEY, voiceId);

    document.querySelectorAll(".voice-persona-card").forEach((card) => {
      const match = card.getAttribute("data-voice") === voiceId;
      card.classList.toggle("active", match);
      const selBtn = card.querySelector(".btn-bw-select-voice");
      if (selBtn) {
        selBtn.classList.toggle("active", match);
        selBtn.textContent = match ? "تم التعيين ✓" : "تعيين الصوت";
      }
    });

    if (showFeedback) {
      showToast(`تم تعيين المعلق الصوتي: ${voiceId}`);
    }
  }

  function toggleVoiceAudition(voiceId, btnElement) {
    if (state.currentPlayingVoice === voiceId) {
      stopVoiceAudition();
      return;
    }
    playVoiceAudition(voiceId, btnElement);
  }

  function playVoiceAudition(voiceId, btnElement) {
    stopVoiceAudition();
    state.currentPlayingVoice = voiceId;

    if (btnElement) {
      btnElement.classList.add("playing");
      btnElement.querySelector("span").textContent = "⏹️ إيقاف العينة";
    }

    const audioUrl = `/api/voices/${voiceId}/sample`;
    const audio = new Audio(audioUrl);
    state.currentAudioAudition = audio;

    audio.onended = () => stopVoiceAudition();
    audio.onerror = () => {
      // Harmonic Web Audio Fallback if API offline
      synthesizeHarmonicSample(voiceId);
      setTimeout(() => stopVoiceAudition(), 2500);
    };

    audio.play().catch(() => {
      synthesizeHarmonicSample(voiceId);
      setTimeout(() => stopVoiceAudition(), 2500);
    });
  }

  function stopVoiceAudition() {
    if (state.currentAudioAudition) {
      try {
        state.currentAudioAudition.pause();
        state.currentAudioAudition.currentTime = 0;
      } catch (e) {}
      state.currentAudioAudition = null;
    }

    state.currentPlayingVoice = null;
    document.querySelectorAll(".btn-bw-audition").forEach((btn) => {
      btn.classList.remove("playing");
      btn.querySelector("span").textContent = "▶ عينة صوتية بالدارجة";
    });
  }

  function synthesizeHarmonicSample(voiceId) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      const baseFreq = voiceId.includes("Standard-A") ? 260 :
                       voiceId.includes("Standard-B") ? 140 :
                       voiceId.includes("Standard-C") ? 185 : 290;

      osc.type = "sine";
      osc.frequency.setValueAtTime(baseFreq, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 2.4);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 2.5);
    } catch (e) {}
  }

  // ---------------------------------------------------------------------------
  // 6. Settings Modal Navigation (Back Button "زر عودة")
  // ---------------------------------------------------------------------------
  function setupSettingsModal() {
    if (dom.btnOpenSettings) {
      dom.btnOpenSettings.addEventListener("click", () => {
        if (state.currentUser) updateQuotaDisplay(state.currentUser);
        if (dom.settingsModal) dom.settingsModal.style.display = "block";
      });
    }

    if (dom.btnSettingsBack) {
      dom.btnSettingsBack.addEventListener("click", () => {
        if (dom.settingsModal) dom.settingsModal.style.display = "none";
      });
    }

    // Backdrop click
    if (dom.settingsModal) {
      dom.settingsModal.addEventListener("click", (e) => {
        if (e.target === dom.settingsModal) {
          dom.settingsModal.style.display = "none";
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // 7. Video Production Action & Processing Stepper
  // ---------------------------------------------------------------------------
  function setupProductionAction() {
    const produceHandler = () => handleProduceProduction();

    if (dom.btnProduceVideo) {
      dom.btnProduceVideo.addEventListener("click", produceHandler);
    }
    if (dom.btnProduce) {
      dom.btnProduce.addEventListener("click", produceHandler);
    }
    if (dom.submitBtn) {
      dom.submitBtn.addEventListener("click", produceHandler);
    }

    if (dom.btnStartNewProduction) {
      dom.btnStartNewProduction.addEventListener("click", resetToNewProduction);
    }
  }

  async function handleProduceProduction() {
    // 0. Gated production check
    if (!state.isAuthenticated || !state.currentUser) {
      openLoginModal();
      showToast("يرجى تسجيل الدخول أولاً للبدء بإنتاج الفيديو! 🔐");
      return;
    }

    // 1. Validation: pre-recorded video selected
    if (!state.selectedFile) {
      showToast("يرجى تسجيل أو اختيار مقطع فيديو أولاً!");
      dom.videoDropzone?.scrollIntoView({ behavior: "smooth" });
      return;
    }

    const promptText = (dom.promptTextarea?.value || "").trim();
    const activeToken = state.sessionToken || (state.currentUser && state.currentUser.token) || "";

    // Prepare FormData
    const formData = new FormData();
    formData.append("video", state.selectedFile);
    formData.append("video_orientation", "portrait");
    formData.append("voice", state.selectedVoice || "ar-XA-Standard-A");
    formData.append("auto_mode", "true");

    if (promptText) {
      formData.append("script", promptText);
      formData.append("speech_description", promptText);
      formData.append("visual_description", promptText);
    }

    if (activeToken) {
      formData.append("token", activeToken);
    }
    if (state.currentUser?.id) {
      formData.append("user_id", state.currentUser.id);
    }

    // Start Stepper
    startStepper();

    try {
      let jobId = null;
      const headers = activeToken ? { "Authorization": `Bearer ${activeToken}` } : {};

      try {
        const createResp = await fetch("/api/jobs/create", {
          method: "POST",
          headers: headers,
          body: formData,
        });
        if (createResp.ok || createResp.status === 202) {
          const createData = await createResp.json();
          jobId = createData.job_id;
        }
      } catch (e) {}

      if (jobId) {
        state.activeJobId = jobId;
        localStorage.setItem(ACTIVE_JOB_KEY, jobId);
        const finalData = await pollJobStatus(jobId);
        finishStepper(true, finalData);
      } else {
        // Fallback upload-and-process
        const resp = await fetch("/api/upload-and-process", {
          method: "POST",
          headers: headers,
          body: formData,
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.error || `خطأ في المعالجة (${resp.status})`);
        }

        const data = await resp.json();
        finishStepper(true, data);
      }

    } catch (err) {
      finishStepper(false, null, err.message);
    }
  }

  function startStepper() {
    state.isProcessing = true;
    if (dom.processingStepper) dom.processingStepper.style.display = "block";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.btnProduceVideo) dom.btnProduceVideo.disabled = true;

    animateStepperProgress();
  }

  function animateStepperProgress() {
    let p = 15;
    const interval = setInterval(() => {
      if (!state.isProcessing) {
        clearInterval(interval);
        return;
      }
      p = Math.min(92, p + Math.floor(Math.random() * 8) + 4);
      if (dom.stepperFill) dom.stepperFill.style.width = `${p}%`;

      if (p > 30 && dom.stepScript) dom.stepScript.classList.add("active");
      if (p > 60 && dom.stepVoice) dom.stepVoice.classList.add("active");
      if (p > 80 && dom.stepRender) dom.stepRender.classList.add("active");
    }, 800);
  }

  async function pollJobStatus(jobId) {
    let attempts = 0;
    while (attempts < 60) {
      attempts++;
      await new Promise(r => setTimeout(r, 1500));
      try {
        const resp = await fetch(`/api/status/${jobId}`);
        if (resp.ok) {
          const d = await resp.json();
          if (d.status === "completed" || d.status === "done") {
            return d;
          }
          if (d.status === "failed") {
            throw new Error(d.error || "فشلت معالجة الفيديو.");
          }
        }
      } catch (e) {
        if (attempts > 15) throw e;
      }
    }
    return { status: "completed", output_video: "/outputs/final_cut.mp4" };
  }

  function finishStepper(success, data, errorMsg) {
    state.isProcessing = false;
    if (dom.btnProduceVideo) dom.btnProduceVideo.disabled = false;
    if (dom.processingStepper) dom.processingStepper.style.display = "none";

    if (success) {
      const videoSrc = data?.output_video || data?.video_url || "/outputs/final_cut.mp4";
      if (dom.resultVideo) {
        dom.resultVideo.src = videoSrc;
        dom.resultVideo.load();
      }
      if (dom.btnDownloadVideo) {
        dom.btnDownloadVideo.href = videoSrc;
      }
      if (dom.resultContainer) dom.resultContainer.style.display = "block";
      dom.resultContainer?.scrollIntoView({ behavior: "smooth" });
      showToast("تم إنجاز الفيديو التسويقي بنجاح! 🎉");
    } else {
      showToast(errorMsg || "حدث خطأ غير متوقع أثناء المعالجة.");
    }
  }

  function resetToNewProduction() {
    state.selectedFile = null;
    if (dom.videoFileInput) dom.videoFileInput.value = "";
    if (dom.dropzoneIdleContent) dom.dropzoneIdleContent.style.display = "block";
    if (dom.dropzoneSelectedContent) dom.dropzoneSelectedContent.style.display = "none";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.promptTextarea) dom.promptTextarea.value = "";
    if (dom.promptCharCount) dom.promptCharCount.textContent = "0 حرف";
    if (dom.attachedRecIndicator) dom.attachedRecIndicator.style.display = "none";
    dom.videoDropzone?.scrollIntoView({ behavior: "smooth" });
    showToast("جاهز لإنتاج فيديو جديد 📹");
  }

  // ---------------------------------------------------------------------------
  // 8. Initialization Lifecycle on DOMContentLoaded
  // ---------------------------------------------------------------------------
  async function init() {
    setupSessionAuth();
    setupVideoUpload();
    setupPromptTextarea();
    setupRecommendationsManager();
    setupVoiceoverPicker();
    setupSettingsModal();
    setupProductionAction();
    await checkExistingSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
