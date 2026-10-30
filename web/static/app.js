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
      id: "usr_pluto",
      username: "pluto",
      business_name: "المشرف العام (Pluto Admin)",
      business_category: "مسؤول المنصة",
      role: "admin",
      status: "active",
      expires_at: "2099-12-31",
      daily_quota: 999,
      weekly_quota: 9999,
      videos_today: 0,
      videos_this_week: 0,
      token: "token_admin_pluto"
    },
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
    loginErrorMessage: document.getElementById("loginErrorMessage"),
    loginErrorAlert: document.getElementById("loginErrorAlert") || document.getElementById("loginErrorMessage"),
    loginCredentialHints: document.getElementById("loginCredentialHints"),

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
    promptTextarea: document.getElementById("promptTextarea") || document.getElementById("promptInput"),
    promptInput: document.getElementById("promptTextarea") || document.getElementById("promptInput"),
    promptInputHint: document.getElementById("promptInputHint"),
    promptCharCount: document.getElementById("promptCharCount"),
    attachedRecIndicator: document.getElementById("attachedRecIndicator"),
    attachedRecText: document.getElementById("attachedRecText"),
    btnClearRec: document.getElementById("btnClearRec"),

    // Action & Processing
    btnProduceVideo: document.getElementById("btnProduceVideo"),
    processingStepper: document.getElementById("processingStepper"),
    stepperStatusText: document.getElementById("stepperStatusText"),
    stepperFill: document.getElementById("stepperFill"),
    stepFrames: document.getElementById("stepFrames"),
    stepAnalyze: document.getElementById("stepAnalyze"),
    stepScript: document.getElementById("stepScript"),
    stepVoice: document.getElementById("stepVoice"),
    stepRender: document.getElementById("stepRender"),
    stepAnnotations: document.getElementById("stepAnnotations"),

    // Result Card
    resultCard: document.getElementById("resultCard"),
    resultContainer: document.getElementById("resultContainer"),
    resultVideo: document.getElementById("resultVideo"),
    btnDownloadVideo: document.getElementById("btnDownloadVideo"),
    btnShareVideo: document.getElementById("btnShareVideo"),
    btnStartNewProduction: document.getElementById("btnStartNewProduction"),

    // Generated Narration Script & Overlay Elements
    generatedScriptCard: document.getElementById("generatedScriptCard"),
    generatedScriptText: document.getElementById("generatedScriptText"),
    btnCopyScript: document.getElementById("btnCopyScript"),
    resultOverlayPill: document.getElementById("resultOverlayPill"),
    resultOverlayText: document.getElementById("resultOverlayText"),
    bottomTextBadge: document.getElementById("bottomTextBadge"),
    overlayFontBadge: document.getElementById("overlayFontBadge"),
    propertySpecsBadge: document.getElementById("propertySpecsBadge"),
    resultMusicPill: document.getElementById("resultMusicPill"),
    resultMusicText: document.getElementById("resultMusicText"),
    resultMusicIcon: document.getElementById("resultMusicIcon"),
    resultMusicBadge: document.getElementById("resultMusicBadge"),
    resultMontagePill: document.getElementById("resultMontagePill"),
    resultMontageText: document.getElementById("resultMontageText"),

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
  function getStoredSessionToken() {
    // 1. Check localStorage keys
    const fromLocal = localStorage.getItem("session_token") ||
                      localStorage.getItem(SESSION_TOKEN_KEY) ||
                      localStorage.getItem("auth_token");
    if (fromLocal && fromLocal.trim()) return fromLocal.trim();

    // 2. Check document.cookie
    try {
      const match = document.cookie.match(/(?:^|;\s*)(?:session_token|auth_token)=([^;]+)/);
      if (match && match[1]) {
        return decodeURIComponent(match[1]).trim();
      }
    } catch (e) {}

    return null;
  }

  function persistSessionTokens(token, user) {
    if (!token) return;
    // Store in localStorage
    localStorage.setItem("session_token", token);
    localStorage.setItem("auth_token", token);
    localStorage.setItem(SESSION_TOKEN_KEY, token);
    if (user) {
      localStorage.setItem(CURRENT_USER_KEY, String(user.id || user.username));
    }

    // Store in document.cookie: path=/; max-age=604800 (7 days); SameSite=Lax
    try {
      document.cookie = `session_token=${encodeURIComponent(token)}; path=/; max-age=604800; SameSite=Lax`;
      document.cookie = `auth_token=${encodeURIComponent(token)}; path=/; max-age=604800; SameSite=Lax`;
    } catch (e) {}
  }

  function clearSessionTokens() {
    localStorage.removeItem("session_token");
    localStorage.removeItem("auth_token");
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem(CURRENT_USER_KEY);

    try {
      document.cookie = "session_token=; path=/; max-age=0; SameSite=Lax";
      document.cookie = "auth_token=; path=/; max-age=0; SameSite=Lax";
    } catch (e) {}
  }

  function showLoginError(msg) {
    if (dom.loginErrorMessage) {
      dom.loginErrorMessage.textContent = msg;
      dom.loginErrorMessage.style.display = "block";
    }
    if (dom.loginErrorAlert && dom.loginErrorAlert !== dom.loginErrorMessage) {
      dom.loginErrorAlert.textContent = msg;
    }
    showToast(msg);
  }

  function clearLoginError() {
    if (dom.loginErrorMessage) {
      dom.loginErrorMessage.textContent = "";
      dom.loginErrorMessage.style.display = "none";
    }
    if (dom.loginErrorAlert && dom.loginErrorAlert !== dom.loginErrorMessage) {
      dom.loginErrorAlert.textContent = "";
    }
  }

  function openLoginModal() {
    state.isAuthenticated = false;
    clearLoginError();
    if (dom.studioView) dom.studioView.style.display = "none";
    if (dom.settingsModal) dom.settingsModal.style.display = "none";
    if (dom.loginView) dom.loginView.style.display = "flex";
  }

  function closeLoginModal() {
    if (state.isAuthenticated) {
      clearLoginError();
      if (dom.loginView) dom.loginView.style.display = "none";
      if (dom.studioView) dom.studioView.style.display = "block";
    }
  }

  async function checkExistingSession() {
    const savedToken = getStoredSessionToken();
    const savedUserId = localStorage.getItem(CURRENT_USER_KEY);

    if (savedToken) {
      state.sessionToken = savedToken;
      try {
        const resp = await fetch("/api/auth/session", {
          headers: { "Authorization": `Bearer ${savedToken}` },
          credentials: "include"
        });

        if (resp.ok) {
          const data = await resp.json();
          if (data.user) {
            const matched = state.accounts.find(
              (a) => a.id === data.user.id || a.username.toLowerCase() === data.user.username.toLowerCase()
            );
            state.currentUser = matched || data.user;
            state.isAuthenticated = true;
            persistSessionTokens(savedToken, state.currentUser);
            applyActiveUserToUI(state.currentUser);
            updateAuthUI(true, state.currentUser);
            return;
          }
        } else if (resp.status === 401 || resp.status === 403) {
          // Session is invalid or revoked -> clear and present login view
          clearSessionTokens();
          state.isAuthenticated = false;
          state.sessionToken = null;
          state.currentUser = null;
          updateAuthUI(false, null);
          return;
        }
      } catch (e) {
        // Network or offline fallback
      }

      // Fallback matching against pre-seeded list for offline demo
      let user = state.accounts.find(
        (a) => a.token === savedToken || a.id === savedUserId || a.username === savedUserId
      );
      if (user) {
        state.currentUser = user;
        state.isAuthenticated = true;
        persistSessionTokens(savedToken, user);
        applyActiveUserToUI(user);
        updateAuthUI(true, user);
        return;
      }
    }

    // Unauthenticated: reveal gated login view
    clearSessionTokens();
    state.isAuthenticated = false;
    state.sessionToken = null;
    state.currentUser = null;
    updateAuthUI(false, null);
  }

  function updateAuthUI(isLoggedIn, user) {
    if (isLoggedIn && user) {
      clearLoginError();
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

    const quickList = [
      { username: "pluto", label: "👑 المشرف pluto", pass: "plutosw4" },
      { username: "merchant_realestate", label: "🏢 عقارات فاخرة", pass: "merchant123" },
      { username: "dar_al_nokhba", label: "🏢 دار النخبة", pass: "merchant123" },
      { username: "auto_algerie", label: "🚗 أوتو الجزائر", pass: "merchant123" }
    ];

    quickList.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-merchant-quick";
      btn.innerHTML = `<span>${item.label}</span>`;
      btn.title = `دخول سريع بالحساب (${item.username})`;
      btn.addEventListener("click", () => {
        if (dom.merchantLoginUsername) dom.merchantLoginUsername.value = item.username;
        if (dom.merchantLoginPassword) dom.merchantLoginPassword.value = item.pass;
        clearLoginError();
        handleMerchantLogin(item.username, item.pass);
      });
      dom.merchantQuickLoginGrid.appendChild(btn);
    });
  }

  async function handleMerchantLogin(rawUsername, rawPassword) {
    clearLoginError();
    const username = (rawUsername || "").trim();
    const password = (rawPassword || "").trim();

    if (!username) {
      showLoginError("يرجى إدخال اسم المستخدم.");
      return;
    }

    if (dom.btnSubmitMerchantLogin) {
      dom.btnSubmitMerchantLogin.disabled = true;
    }

    // 1. Try server API login
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password })
      });

      if (resp.ok) {
        const data = await resp.json();
        const token = data.session_token || data.token || (data.session && data.session.token) || `tok_${username}`;
        const user = data.user || state.accounts.find(a => a.username.toLowerCase() === username.toLowerCase()) || state.accounts[0];
        setSessionAndProceed(token, user);
        showToast(`مرحباً بك مجدداً: ${user.business_name}! ✨`);
        if (dom.btnSubmitMerchantLogin) dom.btnSubmitMerchantLogin.disabled = false;
        return;
      } else if (resp.status === 401) {
        showLoginError("اسم المستخدم أو كلمة المرور غير صحيحة");
        if (dom.btnSubmitMerchantLogin) dom.btnSubmitMerchantLogin.disabled = false;
        return;
      } else if (resp.status === 403) {
        showLoginError("الحساب معطل أو منتهي الصلاحية");
        if (dom.btnSubmitMerchantLogin) dom.btnSubmitMerchantLogin.disabled = false;
        return;
      }
    } catch (e) {
      // Network failure, fallback to offline accounts
    }

    // 2. Pre-seeded fallback (offline mode)
    let user = state.accounts.find(a => a.username.toLowerCase() === username.toLowerCase());
    if (user) {
      const isPlutoValid = (username.toLowerCase() === "pluto" && (password === "plutosw4" || !password));
      const isAdminValid = (username.toLowerCase() === "admin" && (password === "admin123" || !password));
      const isMerchantValid = (password === "merchant123" || !password);

      if (isPlutoValid || isAdminValid || isMerchantValid) {
        const token = user.token || `tok_${user.username}`;
        setSessionAndProceed(token, user);
        showToast(`تم تسجيل الدخول بنجاح: ${user.business_name}! ✨`);
      } else {
        showLoginError("اسم المستخدم أو كلمة المرور غير صحيحة");
      }
    } else {
      showLoginError("اسم المستخدم أو كلمة المرور غير صحيحة");
    }

    if (dom.btnSubmitMerchantLogin) {
      dom.btnSubmitMerchantLogin.disabled = false;
    }
  }

  function handleAdminLogin(username, password) {
    return handleMerchantLogin(username, password);
  }

  function handleQuickMerchantLogin(username) {
    const user = state.accounts.find(a => a.username.toLowerCase() === username.toLowerCase());
    if (!user) return;
    const token = user.token || `tok_${user.username}`;
    setSessionAndProceed(token, user);
    showToast(`تم الدخول السريع: ${user.business_name} ✨`);
  }

  function setSessionAndProceed(token, user) {
    state.sessionToken = token;
    state.currentUser = user;
    state.isAuthenticated = true;
    persistSessionTokens(token, user);
    updateAuthUI(true, user);
  }

  async function handleLogout() {
    if (state.sessionToken) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { "Authorization": `Bearer ${state.sessionToken}` },
          credentials: "include"
        });
      } catch (e) {}
    }

    clearSessionTokens();
    state.isAuthenticated = false;
    state.sessionToken = null;
    state.currentUser = null;
    updateAuthUI(false, null);
    showToast("تم تسجيل الخروج بنجاح. 🚪");
  }

  function setupSessionAuth() {
    if (dom.merchantLoginForm) {
      dom.merchantLoginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const u = (dom.merchantLoginUsername?.value || "").trim();
        const p = (dom.merchantLoginPassword?.value || "").trim();
        handleMerchantLogin(u, p);
      });
    }

    // Support Enter key submission on username and password fields
    const handleEnterKey = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const u = (dom.merchantLoginUsername?.value || "").trim();
        const p = (dom.merchantLoginPassword?.value || "").trim();
        handleMerchantLogin(u, p);
      }
    };

    if (dom.merchantLoginUsername) {
      dom.merchantLoginUsername.addEventListener("keydown", handleEnterKey);
      dom.merchantLoginUsername.addEventListener("input", clearLoginError);
    }
    if (dom.merchantLoginPassword) {
      dom.merchantLoginPassword.addEventListener("keydown", handleEnterKey);
      dom.merchantLoginPassword.addEventListener("input", clearLoginError);
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

    if (dom.btnCopyScript) {
      dom.btnCopyScript.addEventListener("click", handleCopyScript);
    }
  }

  async function handleCopyScript() {
    const text = (dom.generatedScriptText?.textContent || "").trim();
    if (!text) {
      showToast("لا يوجد نص سيناريو لنسخه حالياً.");
      return;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      showToast("تم نسخ نص السيناريو بنجاح! 📋");
      const labelEl = dom.btnCopyScript.querySelector(".copy-label");
      if (labelEl) {
        const orig = labelEl.textContent;
        labelEl.textContent = "تم النسخ ✓";
        setTimeout(() => { labelEl.textContent = orig; }, 2000);
      }
    } catch (e) {
      showToast("تعذر نسخ النص تلقائياً.");
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
    const activeToken = state.sessionToken || (state.currentUser && state.currentUser.token) || getStoredSessionToken() || "";

    // Prepare FormData
    const formData = new FormData();
    formData.append("video", state.selectedFile);
    formData.append("video_orientation", "portrait");
    formData.append("voice", state.selectedVoice || "ar-XA-Standard-A");
    formData.append("auto_mode", "true");

    if (promptText) {
      formData.append("script", promptText);
      formData.append("prompt", promptText);
      formData.append("speech_description", promptText);
      formData.append("visual_description", promptText);

      // Support persistent bottom text / phone number overlay if instructed
      const phoneMatch = promptText.match(/(?:0|\+?213)[567][0-9]{8}/);
      if (phoneMatch) {
        formData.append("fixed_text", phoneMatch[0]);
        formData.append("bottom_text", phoneMatch[0]);
        formData.append("phone_number", phoneMatch[0]);
      }

      // Music and font control flags
      if (promptText.includes("بدون موسيقى") || promptText.includes("كتم الموسيقى") || promptText.includes("بدون صوت موسيقى")) {
        formData.append("mute_music", "true");
      }
      if (promptText.includes("بخط كبير") || promptText.includes("خط كبير") || promptText.includes("كبير وواضح") || promptText.includes("كبير و بارز")) {
        formData.append("large_font", "true");
      }
    }

    if (activeToken) {
      formData.append("token", activeToken);
      formData.append("session_token", activeToken);
      formData.append("auth_token", activeToken);
    }
    if (state.currentUser?.id) {
      formData.append("user_id", String(state.currentUser.id));
    }

    // Prepare request headers with Authorization: Bearer <token>
    const headers = {};
    if (activeToken) {
      headers["Authorization"] = `Bearer ${activeToken}`;
      headers["X-Session-Token"] = activeToken;
    }

    // Start Stepper with live production status
    startStepper();
    updateStepperStatus("1. جاري استخراج الإطارات وفحص خصائص الفيديو...", 15, "stepFrames");

    try {
      let jobId = null;

      try {
        updateStepperStatus("2. جاري تحليل المشاهد وصياغة السيناريو الذكي...", 35, "stepAnalyze");
        const createResp = await fetch("/api/jobs/create", {
          method: "POST",
          headers: headers,
          credentials: "include",
          body: formData,
        });

        if (createResp.status === 401) {
          throw new Error("جلسة العمل منتهية أو غير مصرح بها. يرجى تسجيل الدخول مجدداً.");
        }
        if (createResp.status === 403) {
          throw new Error("الحساب معطل أو تم استنفاد الحصة المسموحة.");
        }

        if (createResp.ok || createResp.status === 202) {
          const createData = await createResp.json();
          jobId = createData.job_id;
        }
      } catch (e) {
        if (e.message && (e.message.includes("جلسة") || e.message.includes("الحساب"))) {
          throw e;
        }
      }

      if (jobId) {
        state.activeJobId = jobId;
        localStorage.setItem(ACTIVE_JOB_KEY, jobId);
        const finalData = await pollJobStatus(jobId);
        updateStepperStatus("اكتمل إنتاج الفيديو التسويقي بنجاح!", 100, "stepAnnotations");
        finishStepper(true, finalData);
      } else {
        // Fallback upload-and-process
        updateStepperStatus("جاري معالجة الفيديو والمونتاج المباشر...", 50, "stepVoice");
        const resp = await fetch("/api/upload-and-process", {
          method: "POST",
          headers: headers,
          credentials: "include",
          body: formData,
        });

        if (resp.status === 401) {
          throw new Error("جلسة العمل منتهية أو غير مصرح بها. يرجى تسجيل الدخول مجدداً.");
        }
        if (resp.status === 403) {
          throw new Error("الحساب معطل أو تم استنفاد الحصة المسموحة.");
        }

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.message || err.error || `خطأ في المعالجة (${resp.status})`);
        }

        const data = await resp.json();
        updateStepperStatus("اكتمل إنتاج الفيديو التسويقي بنجاح!", 100, "stepAnnotations");
        finishStepper(true, data);
      }

    } catch (err) {
      finishStepper(false, null, err.message);
    }
  }

  function buildDynamicVideoUrl(rawUrl) {
    if (!rawUrl) return "";
    const buster = `v=${Date.now()}`;
    return rawUrl.includes("?") ? `${rawUrl}&${buster}` : `${rawUrl}?${buster}`;
  }

  function resolveStepFromTelemetry(stepNum, percent, message) {
    const msg = (message || "").toLowerCase();
    if (msg.includes("ملصق") || msg.includes("نصوص") || msg.includes("كتاب") || stepNum >= 5 || percent >= 95) {
      return "stepAnnotations";
    }
    if (msg.includes("رندرة") || msg.includes("مونتاج") || msg.includes("موسيقى") || stepNum === 4 || (percent >= 80 && percent < 95)) {
      return "stepRender";
    }
    if (msg.includes("صوت") || msg.includes("تعليق") || msg.includes("tts") || (percent >= 65 && percent < 80)) {
      return "stepVoice";
    }
    if (msg.includes("سيناريو") || msg.includes("وصف") || (percent >= 45 && percent < 65)) {
      return "stepScript";
    }
    if (msg.includes("vision") || msg.includes("تحليل") || msg.includes("مشاهد") || stepNum === 2 || (percent >= 25 && percent < 45)) {
      return "stepAnalyze";
    }
    return "stepFrames";
  }

  function updateStepperStatus(statusText, progressPercent, activeStepId) {
    if (dom.stepperStatusText && statusText) {
      dom.stepperStatusText.textContent = statusText;
    }
    const percent = Math.max(5, Math.min(100, Math.round(progressPercent || 0)));
    if (dom.stepperFill) {
      dom.stepperFill.style.width = `${percent}%`;
    }

    const steps = ["stepFrames", "stepAnalyze", "stepScript", "stepVoice", "stepRender", "stepAnnotations"];
    const activeIdx = steps.indexOf(activeStepId);
    steps.forEach((stepId, idx) => {
      const el = document.getElementById(stepId);
      if (el) {
        el.classList.toggle("active", activeIdx >= 0 ? idx <= activeIdx : false);
      }
    });
  }

  function startStepper() {
    state.isProcessing = true;
    if (dom.processingStepper) dom.processingStepper.style.display = "block";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.resultVideo) {
      dom.resultVideo.removeAttribute("src");
      dom.resultVideo.load();
    }
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
      p = Math.min(92, p + Math.floor(Math.random() * 4) + 2);
      if (dom.stepperFill) dom.stepperFill.style.width = `${p}%`;
      const stepId = resolveStepFromTelemetry(0, p, "");
      const steps = ["stepFrames", "stepAnalyze", "stepScript", "stepVoice", "stepRender", "stepAnnotations"];
      const activeIdx = steps.indexOf(stepId);
      steps.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle("active", idx <= activeIdx);
      });
    }, 1200);
  }

  async function pollJobStatus(jobId) {
    let attempts = 0;
    const maxAttempts = 120;
    while (attempts < maxAttempts) {
      attempts++;
      await new Promise(r => setTimeout(r, 1500));
      try {
        const token = state.sessionToken || (state.currentUser && state.currentUser.token) || getStoredSessionToken() || "";
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const resp = await fetch(`/api/status/${jobId}`, {
          headers: headers,
          credentials: "include"
        });
        if (resp.ok) {
          const d = await resp.json();
          const percent = d.progress_percent !== undefined ? d.progress_percent : (d.progress !== undefined ? d.progress : 15);
          const msg = d.message || d.step_description || "جاري معالجة الفيديو وإنتاج المحتوى الذكي...";
          const stepId = resolveStepFromTelemetry(d.step, percent, msg);

          // Real-time stage reflection (Extracting frames, Vision AI analysis, Speech generation, Video rendering, Annotations)
          updateStepperStatus(msg, percent, stepId);

          const isComplete = (d.status === "completed" || d.status === "done" || percent >= 100);
          if (isComplete) {
            // DO NOT load or reveal the video card or set video.src until status === 'completed' or progress === 100
            return d;
          }
          if (d.status === "failed" || d.status === "error") {
            throw new Error(d.error || d.message || "فشلت معالجة الفيديو.");
          }
        }
      } catch (e) {
        if (attempts > 30) throw e;
      }
    }
    throw new Error("استغرقت معالجة الفيديو وقتاً طويلاً. يرجى التحقق من لوحة التحكم أو إعادة المحاولة.");
  }

  function finishStepper(success, data, errorMsg) {
    state.isProcessing = false;
    if (dom.btnProduceVideo) dom.btnProduceVideo.disabled = false;
    if (dom.processingStepper) dom.processingStepper.style.display = "none";

    if (success) {
      // NEVER hardcode '/outputs/final_cut.mp4' as the sole video source!
      // Dynamically inspect data.video_url || data.output_video_url || ...
      const rawVideoUrl = (data && (
        data.video_url ||
        data.output_video_url ||
        data.output_video ||
        (data.result && (data.result.video_url || data.result.output_video_url || data.result.output_video))
      )) || "/outputs/final_cut.mp4";

      // Append timestamp cache-busting query parameter (?v=Date.now()) to video src
      const dynamicVideoSrc = buildDynamicVideoUrl(rawVideoUrl);

      if (dom.resultVideo) {
        dom.resultVideo.src = dynamicVideoSrc;
        dom.resultVideo.load();
      }
      if (dom.btnDownloadVideo) {
        dom.btnDownloadVideo.href = dynamicVideoSrc;
        const jobSlug = (data && data.job_id) ? `lok_${data.job_id}.mp4` : "lok_production.mp4";
        dom.btnDownloadVideo.setAttribute("download", jobSlug);
      }
      if (dom.btnShareVideo) {
        dom.btnShareVideo.href = dynamicVideoSrc;
      }

      // 1. Display Generated Narration Script
      const generatedScript = (data && (
        data.script ||
        data.inferred_script ||
        (data.result && (data.result.script || data.result.inferred_script))
      )) || "";

      if (dom.generatedScriptCard && dom.generatedScriptText) {
        if (generatedScript && String(generatedScript).trim()) {
          dom.generatedScriptText.textContent = String(generatedScript).trim();
          dom.generatedScriptCard.style.display = "block";
        } else {
          dom.generatedScriptCard.style.display = "none";
        }
      }

      // 2. Display Persistent Bottom Text, Large Font, and Property Specs
      const overlayText = (data && (
        data.bottom_text ||
        data.phone_number ||
        data.fixed_text ||
        (data.result && (data.result.bottom_text || data.result.phone_number || data.result.fixed_text))
      )) || "";

      const largeFontApplied = Boolean(data && (
        data.large_font_applied ||
        (data.result && data.result.large_font_applied)
      ));

      const propFeatures = (data && (
        data.property_features ||
        (data.result && data.result.property_features)
      )) || {};

      let hasOverlayInfo = false;
      if (dom.resultOverlayPill) {
        if (overlayText && String(overlayText).trim()) {
          const cleanOverlay = String(overlayText).trim();
          if (dom.resultOverlayText) dom.resultOverlayText.textContent = cleanOverlay;
          if (dom.bottomTextBadge) dom.bottomTextBadge.textContent = cleanOverlay;
          hasOverlayInfo = true;
        } else {
          if (dom.resultOverlayText) dom.resultOverlayText.textContent = "";
          if (dom.bottomTextBadge) dom.bottomTextBadge.textContent = "";
        }

        // Large Font badge
        if (dom.overlayFontBadge) {
          if (largeFontApplied) {
            dom.overlayFontBadge.textContent = "🔍 بخط كبير وواضح";
            dom.overlayFontBadge.style.display = "inline-flex";
            hasOverlayInfo = true;
          } else {
            dom.overlayFontBadge.style.display = "none";
          }
        }

        // Property Specs badge
        if (dom.propertySpecsBadge) {
          const specsParts = [];
          if (propFeatures.unit) specsParts.push(propFeatures.unit);
          if (propFeatures.property_type && propFeatures.property_type !== "عقار") specsParts.push(propFeatures.property_type);
          if (propFeatures.sea_view) specsParts.push("مطل على البحر");
          if (specsParts.length > 0) {
            dom.propertySpecsBadge.textContent = `🏡 ${specsParts.join(" • ")}`;
            dom.propertySpecsBadge.style.display = "inline-flex";
            hasOverlayInfo = true;
          } else {
            dom.propertySpecsBadge.style.display = "none";
          }
        }

        dom.resultOverlayPill.style.display = hasOverlayInfo ? "inline-flex" : "none";
      }

      // 3. Display Music & Audio Balance Feedback Pill
      const isMusicMuted = Boolean(data && (
        data.music_muted === true ||
        (data.result && data.result.music_muted === true) ||
        (data.music_track && data.music_track.muted === true) ||
        (data.result && data.result.music_track && data.result.music_track.muted === true)
      ));

      const musicTrackObj = (data && (data.music_track || (data.result && data.result.music_track))) || {};
      const musicVolume = (data && (data.music_volume !== undefined ? data.music_volume : (data.result && data.result.music_volume))) ?? musicTrackObj.volume;

      if (dom.resultMusicPill && dom.resultMusicText) {
        if (isMusicMuted || musicVolume === 0) {
          dom.resultMusicPill.classList.add("muted");
          if (dom.resultMusicIcon) dom.resultMusicIcon.textContent = "🔇";
          dom.resultMusicText.textContent = "صوت نقي 100% (تم كتم وإلغاء موسيقى الخلفية بالكامل)";
          if (dom.resultMusicBadge) {
            dom.resultMusicBadge.textContent = "كتم كامل";
            dom.resultMusicBadge.style.display = "inline-block";
          }
          dom.resultMusicPill.style.display = "inline-flex";
        } else {
          dom.resultMusicPill.classList.remove("muted");
          if (dom.resultMusicIcon) dom.resultMusicIcon.textContent = "🎵";

          let trackTitle = musicTrackObj.title || "بيانو فاخر";
          let volPercent = 16;
          if (typeof musicVolume === "number") {
            volPercent = Math.round(musicVolume * 100);
          }
          dom.resultMusicText.textContent = `${trackTitle} (مستوى الصوت: ${volPercent}%)`;
          if (dom.resultMusicBadge) {
            dom.resultMusicBadge.textContent = `${volPercent}%`;
            dom.resultMusicBadge.style.display = "inline-block";
          }
          dom.resultMusicPill.style.display = "inline-flex";
        }
      }

      // 4. Display Video Montage Feedback Pill
      const isMontageApplied = Boolean(data && (data.montage_applied || (data.result && data.result.montage_applied)));
      const montageInfo = (data && (data.montage_details || (data.result && data.result.montage_details))) || {};
      if (dom.resultMontagePill && dom.resultMontageText) {
        if (isMontageApplied) {
          const postDur = montageInfo.duration ? `${montageInfo.duration.toFixed(1)} ثانية` : "";
          const origDur = montageInfo.original_duration ? ` (من أصل ${montageInfo.original_duration.toFixed(1)} ثانية)` : "";
          dom.resultMontageText.textContent = `تم اقتطاع المشاهد وتجهيز الفيديو بمدة ${postDur}${origDur}`;
          dom.resultMontagePill.style.display = "inline-flex";
        } else {
          dom.resultMontagePill.style.display = "none";
        }
      }

      if (dom.resultContainer) {
        dom.resultContainer.style.display = "block";
        dom.resultContainer.scrollIntoView({ behavior: "smooth" });
      }
      showToast("تم إنجاز الفيديو التسويقي بنجاح! 🎉");
    } else {
      if (dom.resultContainer) dom.resultContainer.style.display = "none";
      if (dom.generatedScriptCard) dom.generatedScriptCard.style.display = "none";
      if (dom.resultOverlayPill) dom.resultOverlayPill.style.display = "none";
      if (dom.resultMusicPill) dom.resultMusicPill.style.display = "none";
      if (dom.resultMontagePill) dom.resultMontagePill.style.display = "none";
      showToast(errorMsg || "حدث خطأ غير متوقع أثناء المعالجة.");
    }
  }

  function resetToNewProduction() {
    state.selectedFile = null;
    if (dom.videoFileInput) dom.videoFileInput.value = "";
    if (dom.dropzoneIdleContent) dom.dropzoneIdleContent.style.display = "block";
    if (dom.dropzoneSelectedContent) dom.dropzoneSelectedContent.style.display = "none";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.resultVideo) {
      dom.resultVideo.removeAttribute("src");
      dom.resultVideo.load();
    }
    if (dom.generatedScriptCard) dom.generatedScriptCard.style.display = "none";
    if (dom.generatedScriptText) dom.generatedScriptText.textContent = "";
    if (dom.resultOverlayPill) dom.resultOverlayPill.style.display = "none";
    if (dom.resultOverlayText) dom.resultOverlayText.textContent = "";
    if (dom.bottomTextBadge) dom.bottomTextBadge.textContent = "";
    if (dom.overlayFontBadge) dom.overlayFontBadge.style.display = "none";
    if (dom.propertySpecsBadge) dom.propertySpecsBadge.style.display = "none";
    if (dom.resultMusicPill) dom.resultMusicPill.style.display = "none";
    if (dom.resultMusicText) dom.resultMusicText.textContent = "";
    if (dom.resultMusicBadge) dom.resultMusicBadge.style.display = "none";
    if (dom.resultMontagePill) dom.resultMontagePill.style.display = "none";
    if (dom.resultMontageText) dom.resultMontageText.textContent = "";
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
