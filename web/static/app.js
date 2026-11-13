/**
 * lok • Modern Minimalist Client Application Engine (web/static/app.js)
 * Author: MouhammedBoure <mohamadbormoz2@gmail.com>
 * Role: Lead Frontend Engineer (agy51)
 * Branch: frontend/agy51-polling-resilience-and-progress-telemetry
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
    },
    {
      id: "rec_5",
      title: "صوت نقي (بدون موسيقى)",
      text: "صوت نقي 100% بدون موسيقى كتم كامل لموسيقى الخلفية مع إبراز التفاصيل ورقم الهاتف 0558815453."
    },
    {
      id: "rec_6",
      title: "ترجمة متزامنة لكلام المعلق",
      text: "ترجمة متزامنة لكلام المعلق كلمة بكلمة مع المشاهد ونبرة حماسية بدون موسيقى."
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
    editableCuts: [],
    optIn: {
      captions: false,
      music: false,
      timeline: false
    },
    selectedMusicTrack: "luxury_piano",
    musicTracksCatalog: [],
    musicPreviewAudio: null,
    isCapcutPanelOpen: false,
    isTimelinePanelOpen: false,
    selectedCaptionTemplate: "",
    captionPosition: "",
    captionSize: "medium",
    screenOverlay: {
      enabled: false,
      text: "",
      x_pct: 0.50,
      y_pct: 0.92,
      font: "tahoma_bold",
      effect: "solid_dark",
      size: "medium",
      text_color: "default"
    },
    screenOverlayDirty: false,
    overlayCatalog: {
      fonts: [],
      effects: []
    },
    overlayPreviewObjectUrl: null
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
    studioErrorBox: document.getElementById("studioErrorBox"),
    studioErrorMessage: document.getElementById("studioErrorMessage"),
    btnRetryProduction: document.getElementById("btnRetryProduction"),

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
    resultCaptionsPill: document.getElementById("resultCaptionsPill"),
    resultCaptionsText: document.getElementById("resultCaptionsText"),
    resultCaptionsIcon: document.getElementById("resultCaptionsIcon"),
    resultCaptionsBadge: document.getElementById("resultCaptionsBadge"),
    resultMontagePill: document.getElementById("resultMontagePill"),
    resultMontageText: document.getElementById("resultMontageText"),
    shotsTimelineSection: document.getElementById("shotsTimelineSection"),
    timelineBadge: document.getElementById("timelineBadge"),
    shotsTimelineList: document.getElementById("shotsTimelineList"),
    cutsEditActions: document.getElementById("cutsEditActions"),
    btnApplyCutsEdit: document.getElementById("btnApplyCutsEdit"),

    // Opt-In Features Toggles
    optInQuickBar: document.getElementById("optInQuickBar"),
    btnToggleCaptionsOptIn: document.getElementById("btnToggleCaptionsOptIn"),
    statusCaptionsOptIn: document.getElementById("statusCaptionsOptIn"),
    btnToggleMusicOptIn: document.getElementById("btnToggleMusicOptIn"),
    statusMusicOptIn: document.getElementById("statusMusicOptIn"),
    btnToggleTimelineOptIn: document.getElementById("btnToggleTimelineOptIn"),
    statusTimelineOptIn: document.getElementById("statusTimelineOptIn"),
    musicTrackPickerWrap: document.getElementById("musicTrackPickerWrap"),
    musicTrackSelect: document.getElementById("musicTrackSelect"),
    btnPreviewMusic: document.getElementById("btnPreviewMusic"),
    musicTrackLicenseBadge: document.getElementById("musicTrackLicenseBadge"),
    capcutStudioSection: document.getElementById("capcutStudioSection"),
    btnToggleCapcutPresets: document.getElementById("btnToggleCapcutPresets"),
    capcutPresetsBody: document.getElementById("capcutPresetsBody"),
    capcutPresetsChevron: document.getElementById("capcutPresetsChevron"),
    btnToggleTimelinePanel: document.getElementById("btnToggleTimelinePanel"),
    shotsTimelineBody: document.getElementById("shotsTimelineBody"),
    timelinePanelChevron: document.getElementById("timelinePanelChevron"),
    timelineCountPill: document.getElementById("timelineCountPill"),
    sectionOptInPreferences: document.getElementById("sectionOptInPreferences"),
    settingToggleCaptions: document.getElementById("settingToggleCaptions"),
    settingToggleMusic: document.getElementById("settingToggleMusic"),
    settingToggleTimeline: document.getElementById("settingToggleTimeline"),

    // Persistent Screen Note / Phone Designer
    btnToggleScreenNoteOptIn: document.getElementById("btnToggleScreenNoteOptIn"),
    statusScreenNoteOptIn: document.getElementById("statusScreenNoteOptIn"),
    screenOverlaySummaryBar: document.getElementById("screenOverlaySummaryBar"),
    overlaySummaryTextPreview: document.getElementById("overlaySummaryTextPreview"),
    overlaySummaryMetaPreview: document.getElementById("overlaySummaryMetaPreview"),
    btnEditScreenOverlay: document.getElementById("btnEditScreenOverlay"),
    btnClearScreenOverlay: document.getElementById("btnClearScreenOverlay"),
    screenOverlayModal: document.getElementById("screenOverlayModal"),
    btnCloseScreenOverlayModal: document.getElementById("btnCloseScreenOverlayModal"),
    btnCancelScreenOverlayModal: document.getElementById("btnCancelScreenOverlayModal"),
    btnSaveScreenOverlay: document.getElementById("btnSaveScreenOverlay"),
    btnDisableScreenOverlay: document.getElementById("btnDisableScreenOverlay"),
    overlayScreenStage: document.getElementById("overlayScreenStage"),
    overlayPreviewVideo: document.getElementById("overlayPreviewVideo"),
    overlayStagePlaceholder: document.getElementById("overlayStagePlaceholder"),
    draggableOverlayNode: document.getElementById("draggableOverlayNode"),
    draggableOverlayNodeText: document.getElementById("draggableOverlayNodeText"),
    overlayCoordsBadge: document.getElementById("overlayCoordsBadge"),
    overlayTextInput: document.getElementById("overlayTextInput"),
    overlayFontList: document.getElementById("overlayFontList"),
    overlaySelectedFontLabel: document.getElementById("overlaySelectedFontLabel"),
    overlayEffectList: document.getElementById("overlayEffectList"),
    btnReplayOverlayEffect: document.getElementById("btnReplayOverlayEffect"),
    overlaySizePills: document.getElementById("overlaySizePills"),
    overlayColorSwatches: document.getElementById("overlayColorSwatches"),

    // Interactive User Guide Modal (Top-Right Opt-In + First-Open Highlight)
    btnOpenUserGuide: document.getElementById("btnOpenUserGuide"),
    btnLoginUserGuide: document.getElementById("btnLoginUserGuide"),
    userGuideModal: document.getElementById("userGuideModal"),
    btnCloseUserGuideModal: document.getElementById("btnCloseUserGuideModal"),
    btnAcknowledgeUserGuide: document.getElementById("btnAcknowledgeUserGuide"),
    userGuideHighlightTip: document.getElementById("userGuideHighlightTip"),
    btnDismissGuideTip: document.getElementById("btnDismissGuideTip"),

    // CapCut-Style Animated Caption Studio
    captionTemplatesGrid: document.getElementById("captionTemplatesGrid"),
    capcutActiveBadge: document.getElementById("capcutActiveBadge"),
    captionPositionSelect: document.getElementById("captionPositionSelect"),
    captionSizeSelect: document.getElementById("captionSizeSelect"),
    customCaptionTextarea: document.getElementById("customCaptionTextarea"),
    btnPreviewSmartSplit: document.getElementById("btnPreviewSmartSplit"),
    capcutSplitPreview: document.getElementById("capcutSplitPreview"),
    splitPreviewEngine: document.getElementById("splitPreviewEngine"),
    splitChunksList: document.getElementById("splitChunksList"),

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
  // 5.5. Opt-In Feature Toggles & Preferences (Zero-Clutter Minimalist Architecture)
  // ---------------------------------------------------------------------------
  const OPTIN_SETTINGS_KEY = "lok_optin_settings";

  function loadOptInSettings() {
    try {
      const saved = localStorage.getItem(OPTIN_SETTINGS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        state.optIn.captions = Boolean(parsed.captions);
        state.optIn.music = Boolean(parsed.music);
        state.optIn.timeline = Boolean(parsed.timeline);
      }
    } catch (_) {
      // Keep defaults: false
    }
    syncOptInUI();
  }

  function saveOptInSettings() {
    try {
      localStorage.setItem(OPTIN_SETTINGS_KEY, JSON.stringify(state.optIn));
    } catch (_) {}
  }

  function setOptInFeature(feature, enabled, notify = true) {
    if (feature in state.optIn) {
      state.optIn[feature] = Boolean(enabled);
      saveOptInSettings();
      syncOptInUI();
      if (notify) {
        const names = {
          captions: "ترجمة الكلام المتزامنة",
          music: "الموسيقى التصويرية",
          timeline: "مخطط المشاهد واللقطات"
        };
        const st = state.optIn[feature] ? "تم التفعيل بنجاح ✓" : "تم التعطيل (الافتراضي)";
        showToast(`${names[feature] || feature}: ${st}`);
      }
    }
  }

  function syncOptInUI() {
    // 1. Captions
    if (dom.btnToggleCaptionsOptIn) {
      dom.btnToggleCaptionsOptIn.classList.toggle("active", state.optIn.captions);
      dom.btnToggleCaptionsOptIn.setAttribute("aria-pressed", state.optIn.captions ? "true" : "false");
    }
    if (dom.statusCaptionsOptIn) {
      dom.statusCaptionsOptIn.textContent = state.optIn.captions ? "مفعل ✓" : "معطل";
    }
    if (dom.settingToggleCaptions) {
      dom.settingToggleCaptions.checked = state.optIn.captions;
    }

    // 2. Music
    if (dom.btnToggleMusicOptIn) {
      dom.btnToggleMusicOptIn.classList.toggle("active", state.optIn.music);
      dom.btnToggleMusicOptIn.setAttribute("aria-pressed", state.optIn.music ? "true" : "false");
    }
    if (dom.statusMusicOptIn) {
      dom.statusMusicOptIn.textContent = state.optIn.music ? "مفعل ✓" : "معطل";
    }
    if (dom.settingToggleMusic) {
      dom.settingToggleMusic.checked = state.optIn.music;
    }

    // 3. Timeline
    if (dom.btnToggleTimelineOptIn) {
      dom.btnToggleTimelineOptIn.classList.toggle("active", state.optIn.timeline);
      dom.btnToggleTimelineOptIn.setAttribute("aria-pressed", state.optIn.timeline ? "true" : "false");
    }
    if (dom.statusTimelineOptIn) {
      dom.statusTimelineOptIn.textContent = state.optIn.timeline ? "مفعل ✓" : "معطل";
    }
    if (dom.settingToggleTimeline) {
      dom.settingToggleTimeline.checked = state.optIn.timeline;
    }
    if (dom.musicTrackPickerWrap) {
      dom.musicTrackPickerWrap.style.display = state.optIn.music ? "flex" : "none";
      if (!state.optIn.music) {
        stopMusicPreview();
      }
    }

    // 4. Persistent Screen Note / Phone
    const hasOverlay = Boolean(state.screenOverlay && state.screenOverlay.enabled && String(state.screenOverlay.text || "").trim());
    if (dom.btnToggleScreenNoteOptIn) {
      dom.btnToggleScreenNoteOptIn.classList.toggle("active", hasOverlay);
      dom.btnToggleScreenNoteOptIn.setAttribute("aria-pressed", hasOverlay ? "true" : "false");
    }
    if (dom.statusScreenNoteOptIn) {
      dom.statusScreenNoteOptIn.textContent = hasOverlay ? "مفعل ✓" : "إضافة";
    }
    if (dom.screenOverlaySummaryBar) {
      dom.screenOverlaySummaryBar.style.display = hasOverlay ? "flex" : "none";
      if (hasOverlay) {
        const so = state.screenOverlay;
        if (dom.overlaySummaryTextPreview) {
          dom.overlaySummaryTextPreview.textContent = so.text;
        }
        if (dom.overlaySummaryMetaPreview) {
          const fontObj = (state.overlayCatalog.fonts || []).find((f) => f.id === so.font);
          const fxObj = (state.overlayCatalog.effects || []).find((e) => e.id === so.effect);
          const fontLabel = fontObj ? fontObj.name_ar : so.font;
          const fxLabel = fxObj ? fxObj.name_ar : so.effect;
          dom.overlaySummaryMetaPreview.textContent = `${fontLabel} • ${fxLabel} • (${Math.round(so.x_pct * 100)}%, ${Math.round(so.y_pct * 100)}%)`;
        }
      }
    }
  }

  const MUSIC_TRACK_STORAGE_KEY = "lok_selected_music_track";

  function stopMusicPreview() {
    if (state.musicPreviewAudio) {
      try {
        state.musicPreviewAudio.pause();
        state.musicPreviewAudio.currentTime = 0;
      } catch (e) {}
      state.musicPreviewAudio = null;
    }
    if (dom.btnPreviewMusic) {
      dom.btnPreviewMusic.classList.remove("is-playing");
      dom.btnPreviewMusic.innerHTML = "<span>▶ استمع</span>";
    }
  }

  function updateMusicLicenseBadge() {
    if (!dom.musicTrackLicenseBadge) return;
    const active = (state.musicTracksCatalog || []).find((t) => t.id === state.selectedMusicTrack);
    if (active) {
      dom.musicTrackLicenseBadge.textContent = `${active.style || "Music"} — ${active.license || "Free"}`;
    }
  }

  async function loadMusicTracks() {
    if (!dom.musicTrackSelect) return;
    try {
      const savedTrack = localStorage.getItem(MUSIC_TRACK_STORAGE_KEY);
      if (savedTrack) {
        state.selectedMusicTrack = savedTrack;
      }
    } catch (e) {}

    try {
      const res = await fetch("/api/music-tracks");
      if (!res.ok) return;
      const tracks = await res.json();
      if (!Array.isArray(tracks) || tracks.length === 0) return;
      state.musicTracksCatalog = tracks;

      const currentVal = state.selectedMusicTrack;
      dom.musicTrackSelect.innerHTML = "";
      let foundSelected = false;
      tracks.forEach((tr) => {
        const opt = document.createElement("option");
        opt.value = tr.id;
        opt.textContent = tr.title_ar || tr.title || tr.id;
        if (tr.id === currentVal) {
          opt.selected = true;
          foundSelected = true;
        }
        dom.musicTrackSelect.appendChild(opt);
      });

      if (!foundSelected && tracks[0]) {
        state.selectedMusicTrack = tracks[0].id;
        dom.musicTrackSelect.value = tracks[0].id;
      }
      updateMusicLicenseBadge();
    } catch (err) {
      console.warn("Failed to load music tracks:", err);
    }
  }

  function setupMusicTrackPicker() {
    if (dom.musicTrackSelect) {
      dom.musicTrackSelect.addEventListener("change", (e) => {
        state.selectedMusicTrack = e.target.value || "luxury_piano";
        try {
          localStorage.setItem(MUSIC_TRACK_STORAGE_KEY, state.selectedMusicTrack);
        } catch (err) {}
        stopMusicPreview();
        updateMusicLicenseBadge();
      });
    }
    if (dom.btnPreviewMusic) {
      dom.btnPreviewMusic.addEventListener("click", () => {
        if (state.musicPreviewAudio && !state.musicPreviewAudio.paused) {
          stopMusicPreview();
          return;
        }
        stopMusicPreview();
        const trackId = state.selectedMusicTrack || (dom.musicTrackSelect && dom.musicTrackSelect.value) || "luxury_piano";
        const active = (state.musicTracksCatalog || []).find((t) => t.id === trackId);
        const audioUrl = (active && active.audio_url) || `/api/music-tracks/${encodeURIComponent(trackId)}/audio`;
        const audio = new Audio(audioUrl);
        state.musicPreviewAudio = audio;
        dom.btnPreviewMusic.classList.add("is-playing");
        dom.btnPreviewMusic.innerHTML = "<span>⏹ إيقاف</span>";
        audio.addEventListener("ended", stopMusicPreview);
        audio.addEventListener("error", () => {
          stopMusicPreview();
          showToast("تعذر تشغيل معاينة المقطوعة الموسيقية.");
        });
        audio.play().catch(() => {
          stopMusicPreview();
          showToast("تعذر تشغيل المعاينة الصوتية حالياً.");
        });
      });
    }
  }

  function setCapcutPanelOpen(open) {
    const isOpen = Boolean(open);
    state.isCapcutPanelOpen = isOpen;
    if (dom.capcutPresetsBody) {
      dom.capcutPresetsBody.style.display = isOpen ? "block" : "none";
    }
    if (dom.capcutStudioSection) {
      dom.capcutStudioSection.classList.toggle("is-collapsed", !isOpen);
    }
    if (dom.btnToggleCapcutPresets) {
      dom.btnToggleCapcutPresets.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
    if (dom.capcutPresetsChevron) {
      dom.capcutPresetsChevron.textContent = isOpen ? "▴ إخفاء القوالب" : "▾ عرض القوالب";
    }
  }

  function setTimelinePanelOpen(open) {
    const isOpen = Boolean(open);
    state.isTimelinePanelOpen = isOpen;
    if (dom.shotsTimelineBody) {
      dom.shotsTimelineBody.style.display = isOpen ? "block" : "none";
    }
    if (dom.shotsTimelineSection) {
      dom.shotsTimelineSection.classList.toggle("is-collapsed", !isOpen);
    }
    if (dom.btnToggleTimelinePanel) {
      dom.btnToggleTimelinePanel.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
    if (dom.timelinePanelChevron) {
      dom.timelinePanelChevron.textContent = isOpen ? "▴ إخفاء التفاصيل" : "▾ عرض التفاصيل";
    }
  }

  function setupCollapsiblePanels() {
    setCapcutPanelOpen(false);
    setTimelinePanelOpen(false);
    if (dom.btnToggleCapcutPresets) {
      dom.btnToggleCapcutPresets.addEventListener("click", () => {
        setCapcutPanelOpen(!state.isCapcutPanelOpen);
      });
    }
    if (dom.btnToggleTimelinePanel) {
      dom.btnToggleTimelinePanel.addEventListener("click", () => {
        setTimelinePanelOpen(!state.isTimelinePanelOpen);
      });
    }
  }

  // ---------------------------------------------------------------------------
  // 5B. Interactive Persistent Screen Note / Phone Designer Modal
  // ---------------------------------------------------------------------------
  const OVERLAY_COLOR_HEX = {
    default: "",
    white: "#ffffff",
    gold: "#ffd166",
    cyan: "#4cc9f0",
    emerald: "#38d399",
    rose: "#ff6b8b"
  };

  let overlayDraft = null;

  function ensureOverlayFontFaces(fonts) {
    let styleEl = document.getElementById("dynamicOverlayFontsStyle");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "dynamicOverlayFontsStyle";
      document.head.appendChild(styleEl);
    }
    const rules = [];
    (fonts || []).forEach((f) => {
      if (f && f.id && f.font_url) {
        const family = `lokOverlayFont_${f.id}`;
        rules.push(`@font-face { font-family: "${family}"; src: url("${f.font_url}") format("truetype"); font-display: swap; }`);
      }
    });
    styleEl.textContent = rules.join("\n");
  }

  async function loadOverlayCatalog() {
    try {
      const res = await fetch("/api/overlay-options");
      if (!res.ok) return;
      const data = await res.json();
      if (data && Array.isArray(data.fonts)) {
        state.overlayCatalog.fonts = data.fonts;
        ensureOverlayFontFaces(data.fonts);
      }
      if (data && Array.isArray(data.effects)) {
        state.overlayCatalog.effects = data.effects;
      }
      if (overlayDraft && dom.screenOverlayModal && dom.screenOverlayModal.style.display !== "none") {
        renderOverlayFontCards();
        renderOverlayEffectCards();
        updateOverlayStagePreview();
      }
      syncOptInUI();
    } catch (e) {
      // Fallback silently if offline
    }
  }

  function updateOverlayStagePreview(replayAnimation = false) {
    if (!overlayDraft || !dom.draggableOverlayNode || !dom.draggableOverlayNodeText) return;

    const previewTxt = (overlayDraft.text || "").trim() || "0550 12 34 56";
    dom.draggableOverlayNodeText.textContent = previewTxt;
    dom.draggableOverlayNode.classList.toggle("is-placeholder-sample", !(overlayDraft.text || "").trim());

    const xp = Math.max(0.05, Math.min(0.95, Number(overlayDraft.x_pct ?? 0.5)));
    const yp = Math.max(0.05, Math.min(0.95, Number(overlayDraft.y_pct ?? 0.92)));
    dom.draggableOverlayNode.style.left = `${(xp * 100).toFixed(1)}%`;
    dom.draggableOverlayNode.style.top = `${(yp * 100).toFixed(1)}%`;

    if (dom.overlayCoordsBadge) {
      const snappedCenter = Math.abs(xp - 0.5) < 0.015 ? " • منتصف" : "";
      dom.overlayCoordsBadge.textContent = `X: ${Math.round(xp * 100)}% | Y: ${Math.round(yp * 100)}%${snappedCenter}`;
    }

    const chosenFont = (state.overlayCatalog.fonts || []).find((f) => f.id === overlayDraft.font);
    if (chosenFont && chosenFont.font_url) {
      dom.draggableOverlayNode.style.fontFamily = `"lokOverlayFont_${chosenFont.id}", "Cairo", sans-serif`;
      if (dom.overlaySelectedFontLabel) {
        dom.overlaySelectedFontLabel.textContent = chosenFont.name_ar || chosenFont.name_en || chosenFont.id;
      }
    } else {
      dom.draggableOverlayNode.style.fontFamily = `"Cairo", sans-serif`;
      if (dom.overlaySelectedFontLabel) {
        dom.overlaySelectedFontLabel.textContent = overlayDraft.font || "Tahoma Bold";
      }
    }

    const fxClasses = [
      "overlay-fx-solid_dark",
      "overlay-fx-luxury_gold",
      "overlay-fx-clean_outline",
      "overlay-fx-neon_glow",
      "overlay-fx-fade_in",
      "overlay-fx-pulse_glow",
      "overlay-fx-slide_up",
      "overlay-fx-urgent_red"
    ];
    dom.draggableOverlayNode.classList.remove(...fxClasses, "overlay-size-small", "overlay-size-medium", "overlay-size-large");
    dom.draggableOverlayNode.classList.add(`overlay-fx-${overlayDraft.effect || "solid_dark"}`);
    dom.draggableOverlayNode.classList.add(`overlay-size-${overlayDraft.size || "medium"}`);

    const customHex = OVERLAY_COLOR_HEX[overlayDraft.text_color || "default"] || "";
    dom.draggableOverlayNode.style.color = customHex;

    if (replayAnimation) {
      dom.draggableOverlayNode.classList.remove("fx-replay-anim");
      void dom.draggableOverlayNode.offsetWidth;
      dom.draggableOverlayNode.classList.add("fx-replay-anim");
    }

    if (dom.overlaySizePills) {
      dom.overlaySizePills.querySelectorAll("[data-size]").forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-size") === (overlayDraft.size || "medium"));
      });
    }
    if (dom.overlayColorSwatches) {
      dom.overlayColorSwatches.querySelectorAll("[data-color]").forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-color") === (overlayDraft.text_color || "default"));
      });
    }
  }

  function renderOverlayFontCards() {
    if (!dom.overlayFontList) return;
    const fonts = state.overlayCatalog.fonts && state.overlayCatalog.fonts.length
      ? state.overlayCatalog.fonts
      : [
          { id: "tahoma_bold", name_ar: "تاهوما عريض", name_en: "Tahoma Bold", sample_ar: "0550 12 34 56 • عرض حصري" },
          { id: "arial_bold", name_ar: "أريال واضح", name_en: "Arial Bold", sample_ar: "0550 12 34 56 • شقة فاخرة" },
          { id: "segoe_bold", name_ar: "سيغو حديث", name_en: "Segoe UI Bold", sample_ar: "0550 12 34 56 • تواصل معنا" }
        ];
    dom.overlayFontList.innerHTML = "";
    fonts.forEach((f) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "overlay-choice-card overlay-font-card" + (overlayDraft && overlayDraft.font === f.id ? " active" : "");
      card.setAttribute("data-font-id", f.id);
      if (f.font_url) {
        card.style.fontFamily = `"lokOverlayFont_${f.id}", "Cairo", sans-serif`;
      }
      card.innerHTML = `
        <span class="overlay-choice-title">${f.name_ar || f.name_en}</span>
        <span class="overlay-choice-sample">${f.sample_ar || "0550 12 34 56"}</span>
      `;
      card.addEventListener("click", () => {
        if (!overlayDraft) return;
        overlayDraft.font = f.id;
        renderOverlayFontCards();
        updateOverlayStagePreview(false);
      });
      dom.overlayFontList.appendChild(card);
    });
  }

  function renderOverlayEffectCards() {
    if (!dom.overlayEffectList) return;
    const effects = state.overlayCatalog.effects && state.overlayCatalog.effects.length
      ? state.overlayCatalog.effects
      : [
          { id: "solid_dark", name_ar: "شريط داكن أنيق", description_ar: "صندوق أسود شبه شفاف", animated: false },
          { id: "luxury_gold", name_ar: "ذهبي فاخر", description_ar: "نص ذهبي للعقارات الراقية", animated: false },
          { id: "clean_outline", name_ar: "حدود بدون خلفية", description_ar: "نص واضح بحدود سوداء", animated: false },
          { id: "neon_glow", name_ar: "توهج نيون", description_ar: "توهج سماوي جذاب", animated: false },
          { id: "fade_in", name_ar: "ظهور تدريجي", description_ar: "دخول ناعم في البداية", animated: true },
          { id: "pulse_glow", name_ar: "نبض حيوي", description_ar: "تأثير نبض مستمر ملفت", animated: true },
          { id: "slide_up", name_ar: "انزلاق للأعلى", description_ar: "حركة دخول من الأسفل", animated: true },
          { id: "urgent_red", name_ar: "شريط عرض عاجل", description_ar: "خلفية حمراء لافتة", animated: false }
        ];
    dom.overlayEffectList.innerHTML = "";
    effects.forEach((fx) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "overlay-choice-card overlay-effect-card" + (overlayDraft && overlayDraft.effect === fx.id ? " active" : "");
      card.setAttribute("data-effect-id", fx.id);
      const badge = fx.animated ? `<span class="overlay-fx-badge">متحرك ✨</span>` : `<span class="overlay-fx-badge static">ثابت</span>`;
      card.innerHTML = `
        <div class="overlay-fx-head">
          <span class="overlay-choice-title">${fx.name_ar || fx.name_en}</span>
          ${badge}
        </div>
        <span class="overlay-choice-desc">${fx.description_ar || ""}</span>
      `;
      card.addEventListener("click", () => {
        if (!overlayDraft) return;
        overlayDraft.effect = fx.id;
        renderOverlayEffectCards();
        updateOverlayStagePreview(true);
      });
      dom.overlayEffectList.appendChild(card);
    });
  }

  function openScreenOverlayModal() {
    if (!dom.screenOverlayModal) return;

    const current = state.screenOverlay || {};
    let seedText = String(current.text || "").trim();
    if (!seedText && dom.promptTextarea) {
      const match = (dom.promptTextarea.value || "").match(/(?:0|\+?213)[567][0-9]{8}/);
      if (match) seedText = match[0];
    }

    overlayDraft = {
      text: seedText,
      x_pct: typeof current.x_pct === "number" ? current.x_pct : 0.50,
      y_pct: typeof current.y_pct === "number" ? current.y_pct : 0.92,
      font: current.font || "tahoma_bold",
      effect: current.effect || "solid_dark",
      size: current.size || "medium",
      text_color: current.text_color || "default"
    };

    if (dom.overlayTextInput) {
      dom.overlayTextInput.value = overlayDraft.text;
    }

    // Bind selected video preview if user already picked a file
    if (dom.overlayPreviewVideo && dom.overlayStagePlaceholder) {
      if (state.overlayPreviewObjectUrl) {
        try { URL.revokeObjectURL(state.overlayPreviewObjectUrl); } catch (e) {}
        state.overlayPreviewObjectUrl = null;
      }
      if (state.selectedFile) {
        state.overlayPreviewObjectUrl = URL.createObjectURL(state.selectedFile);
        dom.overlayPreviewVideo.src = state.overlayPreviewObjectUrl;
        dom.overlayPreviewVideo.style.display = "block";
        dom.overlayStagePlaceholder.style.display = "none";
        dom.overlayPreviewVideo.play().catch(() => {});
      } else {
        dom.overlayPreviewVideo.removeAttribute("src");
        dom.overlayPreviewVideo.style.display = "none";
        dom.overlayStagePlaceholder.style.display = "flex";
      }
    }

    renderOverlayFontCards();
    renderOverlayEffectCards();
    updateOverlayStagePreview(true);

    dom.screenOverlayModal.style.display = "block";
    document.body.style.overflow = "hidden";
    if (dom.overlayTextInput) {
      setTimeout(() => dom.overlayTextInput.focus(), 60);
    }
  }

  function closeScreenOverlayModal() {
    if (!dom.screenOverlayModal) return;
    dom.screenOverlayModal.style.display = "none";
    document.body.style.overflow = "";
    if (dom.overlayPreviewVideo) {
      try { dom.overlayPreviewVideo.pause(); } catch (e) {}
    }
    if (state.overlayPreviewObjectUrl) {
      try { URL.revokeObjectURL(state.overlayPreviewObjectUrl); } catch (e) {}
      state.overlayPreviewObjectUrl = null;
    }
  }

  function disableScreenOverlay() {
    state.screenOverlay.enabled = false;
    state.screenOverlay.text = "";
    state.screenOverlayDirty = true;
    syncOptInUI();
    closeScreenOverlayModal();
    showToast("تمت إزالة النص الثابت من الشاشة.");
  }

  function setupScreenOverlayDesigner() {
    if (dom.btnToggleScreenNoteOptIn) {
      dom.btnToggleScreenNoteOptIn.addEventListener("click", openScreenOverlayModal);
    }
    if (dom.btnEditScreenOverlay) {
      dom.btnEditScreenOverlay.addEventListener("click", openScreenOverlayModal);
    }
    if (dom.btnClearScreenOverlay) {
      dom.btnClearScreenOverlay.addEventListener("click", disableScreenOverlay);
    }
    if (dom.btnDisableScreenOverlay) {
      dom.btnDisableScreenOverlay.addEventListener("click", disableScreenOverlay);
    }
    if (dom.btnCloseScreenOverlayModal) {
      dom.btnCloseScreenOverlayModal.addEventListener("click", closeScreenOverlayModal);
    }
    if (dom.btnCancelScreenOverlayModal) {
      dom.btnCancelScreenOverlayModal.addEventListener("click", closeScreenOverlayModal);
    }
    if (dom.screenOverlayModal) {
      dom.screenOverlayModal.addEventListener("click", (e) => {
        if (e.target === dom.screenOverlayModal) {
          closeScreenOverlayModal();
        }
      });
    }

    if (dom.overlayTextInput) {
      dom.overlayTextInput.addEventListener("input", () => {
        if (!overlayDraft) return;
        overlayDraft.text = dom.overlayTextInput.value;
        updateOverlayStagePreview(false);
      });
    }

    if (dom.btnReplayOverlayEffect) {
      dom.btnReplayOverlayEffect.addEventListener("click", () => {
        updateOverlayStagePreview(true);
      });
    }

    if (dom.overlaySizePills) {
      dom.overlaySizePills.querySelectorAll("[data-size]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (!overlayDraft) return;
          overlayDraft.size = btn.getAttribute("data-size") || "medium";
          updateOverlayStagePreview(false);
        });
      });
    }

    if (dom.overlayColorSwatches) {
      dom.overlayColorSwatches.querySelectorAll("[data-color]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (!overlayDraft) return;
          overlayDraft.text_color = btn.getAttribute("data-color") || "default";
          updateOverlayStagePreview(false);
        });
      });
    }

    if (dom.screenOverlayModal) {
      dom.screenOverlayModal.querySelectorAll("[data-snap-x][data-snap-y]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (!overlayDraft) return;
          overlayDraft.x_pct = parseFloat(btn.getAttribute("data-snap-x")) || 0.5;
          overlayDraft.y_pct = parseFloat(btn.getAttribute("data-snap-y")) || 0.92;
          updateOverlayStagePreview(false);
        });
      });
    }

    if (dom.btnSaveScreenOverlay) {
      dom.btnSaveScreenOverlay.addEventListener("click", () => {
        if (!overlayDraft) return;
        const cleanText = String(overlayDraft.text || "").trim();
        if (!cleanText) {
          showToast("يرجى كتابة نص الملاحظة أو رقم الهاتف أولاً.");
          if (dom.overlayTextInput) dom.overlayTextInput.focus();
          return;
        }
        state.screenOverlay = {
          enabled: true,
          text: cleanText,
          x_pct: Number((overlayDraft.x_pct ?? 0.5).toFixed(4)),
          y_pct: Number((overlayDraft.y_pct ?? 0.92).toFixed(4)),
          font: overlayDraft.font || "tahoma_bold",
          effect: overlayDraft.effect || "solid_dark",
          size: overlayDraft.size || "medium",
          text_color: overlayDraft.text_color || "default"
        };
        state.screenOverlayDirty = true;
        syncOptInUI();
        closeScreenOverlayModal();
        showToast("تم تثبيت النص وموضعه وخطه على الشاشة بنجاح! 📌");
      });
    }

    // Free drag positioning inside the interactive preview stage (mouse + touch via Pointer Events)
    if (dom.draggableOverlayNode && dom.overlayScreenStage) {
      let dragging = false;
      let activePointerId = null;

      const updateCoordsFromClient = (clientX, clientY) => {
        if (!overlayDraft || !dom.overlayScreenStage) return;
        const rect = dom.overlayScreenStage.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        let xp = (clientX - rect.left) / rect.width;
        let yp = (clientY - rect.top) / rect.height;
        xp = Math.max(0.05, Math.min(0.95, xp));
        yp = Math.max(0.05, Math.min(0.95, yp));
        // Gentle magnetic snap near exact horizontal center
        if (Math.abs(xp - 0.5) < 0.018) {
          xp = 0.5;
        }
        overlayDraft.x_pct = Number(xp.toFixed(4));
        overlayDraft.y_pct = Number(yp.toFixed(4));
        updateOverlayStagePreview(false);
      };

      dom.draggableOverlayNode.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        dragging = true;
        activePointerId = e.pointerId;
        dom.draggableOverlayNode.classList.add("is-dragging");
        try { dom.draggableOverlayNode.setPointerCapture(e.pointerId); } catch (err) {}
        updateCoordsFromClient(e.clientX, e.clientY);
      });

      dom.draggableOverlayNode.addEventListener("pointermove", (e) => {
        if (!dragging || (activePointerId !== null && e.pointerId !== activePointerId)) return;
        e.preventDefault();
        updateCoordsFromClient(e.clientX, e.clientY);
      });

      const endDrag = (e) => {
        if (!dragging) return;
        dragging = false;
        activePointerId = null;
        dom.draggableOverlayNode.classList.remove("is-dragging");
        try { dom.draggableOverlayNode.releasePointerCapture(e.pointerId); } catch (err) {}
      };
      dom.draggableOverlayNode.addEventListener("pointerup", endDrag);
      dom.draggableOverlayNode.addEventListener("pointercancel", endDrag);
    }
  }

  // ---------------------------------------------------------------------------
  // 5C. Interactive User Guide (Top-Right Button + First-Visit Highlight Only)
  // ---------------------------------------------------------------------------
  const USER_GUIDE_SEEN_KEY = "lok_user_guide_seen";

  function clearUserGuideHighlight() {
    try {
      localStorage.setItem(USER_GUIDE_SEEN_KEY, "1");
    } catch (e) {}
    if (dom.btnOpenUserGuide) dom.btnOpenUserGuide.classList.remove("is-first-visit-highlight");
    if (dom.btnLoginUserGuide) dom.btnLoginUserGuide.classList.remove("is-first-visit-highlight");
    if (dom.userGuideHighlightTip) dom.userGuideHighlightTip.style.display = "none";
  }

  function openUserGuideModal() {
    clearUserGuideHighlight();
    if (!dom.userGuideModal) return;
    dom.userGuideModal.style.display = "block";
    document.body.style.overflow = "hidden";
  }

  function closeUserGuideModal() {
    if (!dom.userGuideModal) return;
    dom.userGuideModal.style.display = "none";
    document.body.style.overflow = "";
  }

  function setupUserGuide() {
    let seen = false;
    try {
      seen = localStorage.getItem(USER_GUIDE_SEEN_KEY) === "1";
    } catch (e) {
      seen = false;
    }

    // Never auto-open the modal on first visit — only highlight the top-right button
    if (!seen) {
      if (dom.btnOpenUserGuide) dom.btnOpenUserGuide.classList.add("is-first-visit-highlight");
      if (dom.btnLoginUserGuide) dom.btnLoginUserGuide.classList.add("is-first-visit-highlight");
      if (dom.userGuideHighlightTip) dom.userGuideHighlightTip.style.display = "flex";
    }

    if (dom.btnOpenUserGuide) {
      dom.btnOpenUserGuide.addEventListener("click", openUserGuideModal);
    }
    if (dom.btnLoginUserGuide) {
      dom.btnLoginUserGuide.addEventListener("click", openUserGuideModal);
    }
    if (dom.btnDismissGuideTip) {
      dom.btnDismissGuideTip.addEventListener("click", (e) => {
        e.stopPropagation();
        clearUserGuideHighlight();
      });
    }
    if (dom.btnCloseUserGuideModal) {
      dom.btnCloseUserGuideModal.addEventListener("click", closeUserGuideModal);
    }
    if (dom.btnAcknowledgeUserGuide) {
      dom.btnAcknowledgeUserGuide.addEventListener("click", closeUserGuideModal);
    }
    if (dom.userGuideModal) {
      dom.userGuideModal.addEventListener("click", (e) => {
        if (e.target === dom.userGuideModal) {
          closeUserGuideModal();
        }
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && dom.userGuideModal && dom.userGuideModal.style.display !== "none") {
        closeUserGuideModal();
      }
    });
  }

  function setupOptInToggles() {
    loadOptInSettings();

    // Quick Bar Toggles
    if (dom.btnToggleCaptionsOptIn) {
      dom.btnToggleCaptionsOptIn.addEventListener("click", () => {
        setOptInFeature("captions", !state.optIn.captions);
      });
    }
    if (dom.btnToggleMusicOptIn) {
      dom.btnToggleMusicOptIn.addEventListener("click", () => {
        setOptInFeature("music", !state.optIn.music);
      });
    }
    if (dom.btnToggleTimelineOptIn) {
      dom.btnToggleTimelineOptIn.addEventListener("click", () => {
        setOptInFeature("timeline", !state.optIn.timeline);
      });
    }

    // Settings Modal Switches
    if (dom.settingToggleCaptions) {
      dom.settingToggleCaptions.addEventListener("change", (e) => {
        setOptInFeature("captions", e.target.checked);
      });
    }
    if (dom.settingToggleMusic) {
      dom.settingToggleMusic.addEventListener("change", (e) => {
        setOptInFeature("music", e.target.checked);
      });
    }
    if (dom.settingToggleTimeline) {
      dom.settingToggleTimeline.addEventListener("change", (e) => {
        setOptInFeature("timeline", e.target.checked);
      });
    }
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

    if (dom.btnRetryProduction) {
      dom.btnRetryProduction.addEventListener("click", () => {
        if (dom.studioErrorBox) dom.studioErrorBox.style.display = "none";
        handleProduceProduction();
      });
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
        formData.append("music_muted", "true");
      }
      if (promptText.includes("بخط كبير") || promptText.includes("خط كبير") || promptText.includes("كبير وواضح") || promptText.includes("كبير و بارز")) {
        formData.append("large_font", "true");
      }
    }

    // Explicit Opt-In Features Handling
    const isCaptionsOpted = Boolean(
      state.optIn.captions ||
      (promptText && (promptText.includes("ترجمة") || promptText.includes("subtitles") || promptText.includes("captions")))
    );
    const isMusicOpted = Boolean(
      state.optIn.music ||
      (promptText && (promptText.includes("موسيقى") && !promptText.includes("بدون موسيقى") && !promptText.includes("كتم الموسيقى")))
    );
    const isTimelineOpted = Boolean(
      state.optIn.timeline ||
      (promptText && (promptText.includes("مخطط") || promptText.includes("لقطات") || promptText.includes("مشاهد") || promptText.includes("timeline")))
    );

    formData.append("optin_captions", isCaptionsOpted ? "true" : "false");
    formData.append("optin_music", isMusicOpted ? "true" : "false");
    formData.append("optin_timeline", isTimelineOpted ? "true" : "false");

    if (isCaptionsOpted) {
      formData.append("enable_captions", "true");
      formData.append("enable_subtitles", "true");
    }

    // CapCut-Style Animated Caption Template & Custom Text
    const customCaptionText = (dom.customCaptionTextarea?.value || "").trim();
    const chosenTemplate = state.selectedCaptionTemplate || (customCaptionText ? "karaoke_highlight" : "");
    if (chosenTemplate) {
      formData.append("caption_template", chosenTemplate);
      if (customCaptionText) {
        formData.append("custom_caption_text", customCaptionText);
      } else if (!isCaptionsOpted) {
        // When user picks an animated template without custom text, style the narration captions
        formData.append("enable_captions", "true");
        formData.append("enable_subtitles", "true");
      }
      const posVal = (dom.captionPositionSelect?.value || state.captionPosition || "").trim();
      const sizeVal = (dom.captionSizeSelect?.value || state.captionSize || "medium").trim();
      if (posVal) formData.append("caption_position", posVal);
      if (sizeVal) formData.append("caption_size", sizeVal);
    }

    if (!isMusicOpted || (promptText && (promptText.includes("بدون موسيقى") || promptText.includes("كتم الموسيقى")))) {
      formData.append("mute_music", "true");
      formData.append("music_muted", "true");
    } else {
      formData.append("enable_music", "true");
      if (state.selectedMusicTrack) {
        formData.append("music_track", state.selectedMusicTrack);
      }
    }

    if (isTimelineOpted) {
      formData.append("enable_timeline", "true");
    }

    // Custom Persistent Draggable Screen Note / Phone Overlay
    if (state.screenOverlay && state.screenOverlay.enabled && String(state.screenOverlay.text || "").trim()) {
      formData.append("overlay_text", String(state.screenOverlay.text).trim());
      formData.append("overlay_x_pct", String(state.screenOverlay.x_pct ?? 0.5));
      formData.append("overlay_y_pct", String(state.screenOverlay.y_pct ?? 0.92));
      formData.append("overlay_font", state.screenOverlay.font || "tahoma_bold");
      formData.append("overlay_effect", state.screenOverlay.effect || "solid_dark");
      formData.append("overlay_size", state.screenOverlay.size || "medium");
      formData.append("overlay_color", state.screenOverlay.text_color || "default");
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

  function buildDynamicVideoUrl(rawUrl, jobId) {
    if (!rawUrl) return "";
    const buster = `v=${Date.now()}`;
    const jobParam = jobId ? `job_id=${encodeURIComponent(jobId)}` : "";
    let sep = rawUrl.includes("?") ? "&" : "?";
    if (jobParam && !rawUrl.includes("job_id=")) {
      return `${rawUrl}${sep}${jobParam}&${buster}`;
    }
    return `${rawUrl}${sep}${buster}`;
  }

  let currentDisplayPercent = 10;
  let targetDisplayPercent = 10;
  let stepperAnimationInterval = null;

  function resolveStepFromTelemetry(stepNum, percent, message) {
    const msg = (message || "").toLowerCase();
    if (msg.includes("ملصق") || msg.includes("نصوص") || msg.includes("كتاب") || stepNum >= 5 || percent >= 95) {
      return "stepAnnotations";
    }
    if (msg.includes("رندرة") || msg.includes("مونتاج") || msg.includes("موسيقى") || stepNum === 4 || (percent >= 75 && percent < 95)) {
      return "stepRender";
    }
    if (msg.includes("صوت") || msg.includes("تعليق") || msg.includes("tts") || stepNum === 3 || (percent >= 50 && percent < 75)) {
      return "stepVoice";
    }
    if (msg.includes("vision") || msg.includes("تحليل") || msg.includes("مشاهد") || msg.includes("سيناريو") || stepNum === 2 || (percent >= 25 && percent < 50)) {
      return "stepAnalyze";
    }
    return "stepFrames";
  }

  function updateStepperStatus(statusText, progressPercent, activeStepId) {
    if (dom.stepperStatusText && statusText) {
      dom.stepperStatusText.textContent = statusText;
    }
    const percent = Math.max(5, Math.min(100, Math.round(progressPercent || 0)));
    targetDisplayPercent = percent;
    if (percent >= 100) {
      currentDisplayPercent = 100;
    }
    if (dom.stepperFill) {
      dom.stepperFill.style.width = `${Math.max(currentDisplayPercent, percent)}%`;
    }

    const steps = ["stepFrames", "stepAnalyze", "stepVoice", "stepRender", "stepAnnotations"];
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
    currentDisplayPercent = 10;
    targetDisplayPercent = 10;
    if (dom.processingStepper) dom.processingStepper.style.display = "block";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.studioErrorBox) dom.studioErrorBox.style.display = "none";
    if (dom.resultVideo) {
      dom.resultVideo.removeAttribute("src");
      dom.resultVideo.load();
    }
    if (dom.btnProduceVideo) dom.btnProduceVideo.disabled = true;

    updateStepperStatus("1. جاري استخراج الإطارات وفحص خصائص الفيديو...", 10, "stepFrames");
    animateStepperProgress();
  }

  function animateStepperProgress() {
    if (stepperAnimationInterval) clearInterval(stepperAnimationInterval);
    stepperAnimationInterval = setInterval(() => {
      if (!state.isProcessing) {
        clearInterval(stepperAnimationInterval);
        stepperAnimationInterval = null;
        return;
      }
      // Smoothly advance display progress towards targetDisplayPercent, never exceeding target
      if (currentDisplayPercent < targetDisplayPercent) {
        currentDisplayPercent = Math.min(targetDisplayPercent, currentDisplayPercent + 1);
        if (dom.stepperFill) dom.stepperFill.style.width = `${currentDisplayPercent}%`;
      }
    }, 150);
  }

  async function pollJobStatus(jobId) {
    let attempts = 0;
    const maxAttempts = 1800; // Extended timeout ceiling (~60 minutes total)
    let consecutiveNetworkErrors = 0;
    const maxNetworkErrors = 10;

    while (attempts < maxAttempts) {
      attempts++;

      // Adaptive polling delay: fast initial checks, then steady interval
      let pollDelayMs = 1500;
      if (attempts <= 5) {
        pollDelayMs = 1000;
      } else if (attempts > 30) {
        pollDelayMs = 2000;
      }

      await new Promise(r => setTimeout(r, pollDelayMs));

      try {
        const token = state.sessionToken || (state.currentUser && state.currentUser.token) || getStoredSessionToken() || "";
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const resp = await fetch(`/api/status/${jobId}?t=${Date.now()}`, {
          headers: headers,
          credentials: "include",
          cache: "no-store"
        });

        // 404 grace period for just-spawned jobs
        if (resp.status === 404 && attempts <= 3) {
          continue;
        }

        if (resp.ok) {
          consecutiveNetworkErrors = 0;
          const d = await resp.json();

          // 1. Immediate completion check: transition immediately without waiting or timeout
          const isComplete = (d.status === "completed" || d.status === "done" || (d.progress_percent !== undefined && d.progress_percent >= 100));
          if (isComplete) {
            updateStepperStatus("اكتمل إنتاج الفيديو التسويقي بنجاح!", 100, "stepAnnotations");
            return d;
          }

          // 2. Immediate failure check: propagate actual backend error message
          if (d.status === "failed" || d.status === "error") {
            const backendError = d.error || d.message || d.detail || (d.result && (d.result.error || d.result.message)) || "فشلت معالجة الفيديو بالذكاء الاصطناعي.";
            throw new Error(backendError);
          }

          // 3. Extract real backend progress percentage
          let serverPercent = null;
          if (d.progress_percent !== undefined && d.progress_percent !== null) {
            serverPercent = Number(d.progress_percent);
          } else if (d.progress !== undefined && d.progress !== null) {
            serverPercent = Number(d.progress);
          }

          // Fallback to step mapping if numeric percentage is missing
          const stepNum = Number(d.step || d.current_step || 0);
          if (serverPercent === null || isNaN(serverPercent) || serverPercent <= 0) {
            if (stepNum === 1) serverPercent = 15;
            else if (stepNum === 2) serverPercent = 35;
            else if (stepNum === 3) serverPercent = 60;
            else if (stepNum === 4) serverPercent = 82;
            else if (stepNum >= 5) serverPercent = 95;
            else serverPercent = Math.min(20, Math.max(10, attempts * 2));
          }

          // Strict Cap: In-flight processing must never prematurely show 100%
          serverPercent = Math.min(96, Math.max(8, serverPercent));

          const msg = d.message || d.step_description || d.status_text || "جاري معالجة الفيديو وإنتاج المحتوى الذكي...";
          const stepId = resolveStepFromTelemetry(stepNum, serverPercent, msg);

          // Update Stepper with real progress
          updateStepperStatus(msg, serverPercent, stepId);
        } else {
          // HTTP error response (e.g. 500, 502)
          consecutiveNetworkErrors++;
          if (consecutiveNetworkErrors >= maxNetworkErrors) {
            throw new Error(`تعذر استلام حالة الفيديو من الخادم (رمز الاستجابة: ${resp.status}).`);
          }
        }
      } catch (e) {
        // If it's a backend failure error, rethrow immediately
        if (e.message && !e.message.includes("Failed to fetch") && !e.message.includes("NetworkError")) {
          throw e;
        }
        consecutiveNetworkErrors++;
        if (consecutiveNetworkErrors >= maxNetworkErrors) {
          throw new Error("انقطع الاتصال بالخادم أثناء متابعة المعالجة. يرجى التحقق من الشبكة وإعادة المحاولة.");
        }
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
      const jobId = (data && (data.job_id || (data.result && data.result.job_id))) || state.activeJobId || "";
      let rawVideoUrl = "";
      if (data) {
        rawVideoUrl = data.video_url ||
          data.output_video_url ||
          data.output_video ||
          (data.result && (data.result.video_url || data.result.output_video_url || data.result.output_video)) ||
          "";
      }

      // Sandboxed Job Directory Isolation:
      // If no explicit video URL but job_id is known, bind to isolated job sandbox directory
      if (!rawVideoUrl && jobId) {
        rawVideoUrl = `/outputs/jobs/${jobId}/final_cut.mp4`;
      }
      if (!rawVideoUrl) {
        rawVideoUrl = "/outputs/final_cut.mp4";
      }

      // Append timestamp cache-busting query parameter (?v=Date.now() and job_id) to video src
      const dynamicVideoSrc = buildDynamicVideoUrl(rawVideoUrl, jobId);

      if (dom.resultVideo) {
        dom.resultVideo.dataset.jobId = jobId;
        dom.resultVideo.dataset.sandboxed = jobId ? "true" : "false";
        dom.resultVideo.onerror = function() {
          if (!this.dataset.retryAttempted) {
            this.dataset.retryAttempted = "true";
            setTimeout(() => {
              this.src = `/outputs/mobile_cuts/cut_${jobId}.mp4?job_id=${jobId}&v=${Date.now()}`;
              this.load();
            }, 1000);
          } else if (!this.dataset.fallbackAttempted) {
            this.dataset.fallbackAttempted = "true";
            this.src = `/outputs/final_cut.mp4?v=${Date.now()}`;
            this.load();
          }
        };
        delete dom.resultVideo.dataset.retryAttempted;
        delete dom.resultVideo.dataset.fallbackAttempted;
        dom.resultVideo.src = dynamicVideoSrc;
        dom.resultVideo.load();
      }
      if (dom.btnDownloadVideo) {
        dom.btnDownloadVideo.href = dynamicVideoSrc;
        const jobSlug = jobId ? `lok_${jobId}.mp4` : "lok_production.mp4";
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

      // 5. Display Synchronized Captions Feedback Pill (Opt-In Controlled)
      const captionsApplied = Boolean(data && (
        (data.subtitles_count !== undefined && data.subtitles_count > 0) ||
        (data.captions_count !== undefined && data.captions_count > 0) ||
        data.captions_applied === true ||
        data.subtitles_applied === true ||
        (Array.isArray(data.captions) && data.captions.length > 0) ||
        (Array.isArray(data.subtitle_segments) && data.subtitle_segments.length > 0) ||
        (Array.isArray(data.subtitles) && data.subtitles.length > 0) ||
        (data.result && (
          (data.result.subtitles_count !== undefined && data.result.subtitles_count > 0) ||
          (data.result.captions_count !== undefined && data.result.captions_count > 0) ||
          data.result.captions_applied === true ||
          data.result.subtitles_applied === true ||
          (Array.isArray(data.result.captions) && data.result.captions.length > 0) ||
          (Array.isArray(data.result.subtitle_segments) && data.result.subtitle_segments.length > 0) ||
          (Array.isArray(data.result.subtitles) && data.result.subtitles.length > 0)
        ))
      ));

      const captionsCount = (data && (
        data.subtitles_count ||
        data.captions_count ||
        (data.captions && data.captions.length) ||
        (data.subtitle_segments && data.subtitle_segments.length) ||
        (data.subtitles && data.subtitles.length) ||
        (data.result && (
          data.result.subtitles_count ||
          data.result.captions_count ||
          (data.result.captions && data.result.captions.length) ||
          (data.result.subtitle_segments && data.result.subtitle_segments.length) ||
          (data.result.subtitles && data.result.subtitles.length)
        ))
      )) || 0;

      const animCaptions = (data && (data.animated_captions || (data.result && data.result.animated_captions))) || null;

      if (dom.resultCaptionsPill && dom.resultCaptionsText) {
        if (animCaptions && animCaptions.chunks_count > 0) {
          const tplLabel = animCaptions.template_name_ar || animCaptions.template || "قالب متحرك";
          dom.resultCaptionsText.textContent = `كابشن متحرك (${tplLabel}) — مقسم بذكاء`;
          if (dom.resultCaptionsBadge) {
            dom.resultCaptionsBadge.textContent = `${animCaptions.chunks_count} مقاطع متحركة`;
            dom.resultCaptionsBadge.style.display = "inline-block";
          }
          dom.resultCaptionsPill.style.display = "inline-flex";
        } else if (captionsApplied || captionsCount > 0) {
          dom.resultCaptionsText.textContent = "ترجمة الكلام متزامنة بدقة عالية مع المشاهد (كلمة بكلمة)";
          if (dom.resultCaptionsBadge) {
            dom.resultCaptionsBadge.textContent = captionsCount > 0 ? `${captionsCount} جمل متزامنة` : "متزامن 100%";
            dom.resultCaptionsBadge.style.display = "inline-block";
          }
          dom.resultCaptionsPill.style.display = "inline-flex";
        } else {
          dom.resultCaptionsPill.style.display = "none";
          if (dom.resultCaptionsText) dom.resultCaptionsText.textContent = "";
          if (dom.resultCaptionsBadge) dom.resultCaptionsBadge.style.display = "none";
        }
      }

      // 6. Display Shot-by-Shot Synchronized Timeline in Script Inspection Card (collapsed until user clicks)
      state.isTimelinePanelOpen = false;
      renderShotTimeline(data);

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
      if (dom.resultCaptionsPill) dom.resultCaptionsPill.style.display = "none";
      if (dom.resultMontagePill) dom.resultMontagePill.style.display = "none";
      if (dom.shotsTimelineSection) dom.shotsTimelineSection.style.display = "none";

      // Show action-oriented failure alert with Retry button
      if (dom.studioErrorBox) {
        if (dom.studioErrorMessage) {
          dom.studioErrorMessage.textContent = errorMsg || "تعذر إكمال إنتاج الفيديو. يرجى إعادة المحاولة.";
        }
        dom.studioErrorBox.style.display = "block";
        dom.studioErrorBox.scrollIntoView({ behavior: "smooth" });
      }

      showToast(errorMsg || "حدث خطأ غير متوقع أثناء المعالجة.");
    }
  }

  function formatTimestampRange(start, end) {
    const s = Math.max(0, Number(start) || 0);
    const sMin = Math.floor(s / 60);
    const sSec = Math.floor(s % 60);
    const sStr = `${sMin}:${sSec < 10 ? "0" : ""}${sSec}`;
    if (end === undefined || end === null || isNaN(end)) {
      return sStr;
    }
    const e = Math.max(s, Number(end) || s);
    const eMin = Math.floor(e / 60);
    const eSec = Math.floor(e % 60);
    const eStr = `${eMin}:${eSec < 10 ? "0" : ""}${eSec}`;
    return `${sStr} - ${eStr}`;
  }

  function renderShotTimeline(data) {
    if (!dom.shotsTimelineSection || !dom.shotsTimelineList) return;

    dom.shotsTimelineList.innerHTML = "";
    state.editableCuts = [];
    if (dom.cutsEditActions) dom.cutsEditActions.style.display = "none";

    const rawEditableCuts = (data && (
      data.editable_cuts ||
      (data.result && data.result.editable_cuts)
    )) || [];

    const rawTimeline = (data && (
      data.shot_timeline ||
      data.timeline ||
      data.scenes ||
      data.shots ||
      (data.result && (data.result.shot_timeline || data.result.timeline || data.result.scenes || data.result.shots))
    )) || [];

    const rawCaptions = (data && (
      data.captions ||
      data.subtitle_segments ||
      data.synchronized_captions ||
      (data.result && (data.result.captions || data.result.subtitle_segments || data.result.synchronized_captions))
    )) || [];

    const rawKeyframes = (data && (
      data.keyframes ||
      (data.result && data.result.keyframes)
    )) || [];

    const hasEditableCuts = Array.isArray(rawEditableCuts) && rawEditableCuts.length > 0;
    const isTimelineOptedIn = Boolean(data && (
      hasEditableCuts ||
      data.timeline_applied === true ||
      data.timeline_enabled === true ||
      data.shots_timeline_applied === true ||
      (Array.isArray(rawTimeline) && rawTimeline.length > 0) ||
      (data.result && (
        data.result.timeline_applied === true ||
        data.result.timeline_enabled === true ||
        data.result.shots_timeline_applied === true ||
        (Array.isArray(data.result.shot_timeline) && data.result.shot_timeline.length > 0) ||
        (Array.isArray(data.result.timeline) && data.result.timeline.length > 0) ||
        (Array.isArray(data.result.scenes) && data.result.scenes.length > 0) ||
        (Array.isArray(data.result.shots) && data.result.shots.length > 0)
      )) ||
      ((data.captions_applied || (data.subtitles_count && data.subtitles_count > 0)) && Array.isArray(rawCaptions) && rawCaptions.length > 0)
    ));

    if (!isTimelineOptedIn) {
      dom.shotsTimelineSection.style.display = "none";
      return;
    }

    const cleanSceneTitle = (rawTitle, idx) => {
      const stripped = String(rawTitle || "")
        .replace(/\s*\[[^\]]*\d+\.\d+s\s*-\s*\d+\.\d+s[^\]]*\]\s*$/i, "")
        .trim()
        .replace(/^[-:\s]+|[-:\s]+$/g, "");
      return stripped || `المشهد ${idx + 1}`;
    };

    let itemsToRender = [];

    if (hasEditableCuts) {
      itemsToRender = rawEditableCuts.map((item, idx) => ({
        scene_index: item.scene_index || (idx + 1),
        start_sec: Number(item.start_sec ?? 0),
        end_sec: Number(item.end_sec ?? ((idx + 1) * 3)),
        timeRange: formatTimestampRange(item.start_sec ?? (idx * 3), item.end_sec ?? ((idx + 1) * 3)),
        title: cleanSceneTitle(item.title || item.room_or_subject, idx),
        description: item.text || "",
        thumb: item.thumb || (rawKeyframes[idx] && rawKeyframes[idx].url) || "",
      }));
    } else if (Array.isArray(rawTimeline) && rawTimeline.length > 0) {
      itemsToRender = rawTimeline.map((item, idx) => ({
        scene_index: item.scene_index || (idx + 1),
        start_sec: Number(item.start_sec ?? item.timestamp ?? (idx * 3)),
        end_sec: Number(item.end_sec ?? ((idx + 1) * 3)),
        timeRange: formatTimestampRange(item.start_sec ?? item.timestamp ?? (idx * 3), item.end_sec ?? ((idx + 1) * 3)),
        title: cleanSceneTitle(item.title || item.room_or_subject || item.room || item.label, idx),
        description: item.narration_line || item.description || item.text || item.details || "",
        thumb: item.thumbnail || item.url || (rawKeyframes[idx] && rawKeyframes[idx].url) || "",
      }));
    } else if (Array.isArray(rawCaptions) && rawCaptions.length > 0) {
      itemsToRender = rawCaptions.map((cap, idx) => ({
        scene_index: idx + 1,
        start_sec: Number(cap.start_sec ?? 0),
        end_sec: Number(cap.end_sec ?? 3),
        timeRange: formatTimestampRange(cap.start_sec, cap.end_sec),
        title: cleanSceneTitle(cap.title || cap.room_or_subject, idx),
        description: cap.text || cap.caption || "",
        thumb: (rawKeyframes[idx] && rawKeyframes[idx].url) || "",
      }));
    } else if (Array.isArray(rawKeyframes) && rawKeyframes.length > 0) {
      itemsToRender = rawKeyframes.slice(0, 8).map((kf, idx) => ({
        scene_index: idx + 1,
        start_sec: Number(kf.timestamp ?? 0),
        end_sec: Number((rawKeyframes[idx + 1]?.timestamp) || ((kf.timestamp || 0) + 3.0)),
        timeRange: formatTimestampRange(kf.timestamp, (rawKeyframes[idx + 1]?.timestamp) || (kf.timestamp + 3.0)),
        title: kf.title || (kf.is_scene_transition ? `انتقال مشهد ${idx + 1}` : `المشهد ${idx + 1}`),
        description: kf.is_scene_transition ? "انتقال بصري بين زوايا التصوير" : "تركيز على تفاصيل وزوايا المكان",
        thumb: kf.url || "",
      }));
    } else {
      const scriptText = (data && (data.script || data.inferred_script || (data.result && (data.result.script || data.result.inferred_script)))) || "";
      const sentences = scriptText.split(/[.،!?\n]+/).map(s => s.trim()).filter(Boolean);
      if (sentences.length > 0) {
        const dur = (data && (data.duration || (data.result && data.result.duration))) || 15;
        const phaseDur = dur / Math.min(sentences.length, 3);
        const labels = ["المقدمة والإطلالة البصرية", "الجولة البصرية والتفاصيل المعمارية", "الخاتمة والدعوة للتواصل"];
        itemsToRender = sentences.slice(0, 3).map((sent, idx) => ({
          scene_index: idx + 1,
          start_sec: idx * phaseDur,
          end_sec: (idx + 1) * phaseDur,
          timeRange: formatTimestampRange(idx * phaseDur, (idx + 1) * phaseDur),
          title: labels[idx] || `المشهد ${idx + 1}`,
          description: sent,
          thumb: "",
        }));
      }
    }

    if (itemsToRender.length > 0) {
      state.editableCuts = itemsToRender.map((item, idx) => ({
        scene_index: item.scene_index || (idx + 1),
        start_sec: item.start_sec,
        end_sec: item.end_sec,
        title: item.title,
        text: item.description || "",
        thumb: item.thumb || "",
      }));

      itemsToRender.forEach((item, idx) => {
        const el = document.createElement("div");
        el.className = "shot-timeline-item";

        const timeCol = document.createElement("div");
        timeCol.className = "shot-time-col";
        const tsSpan = document.createElement("span");
        tsSpan.className = "shot-timestamp";
        tsSpan.textContent = item.timeRange;
        const sceneTag = document.createElement("span");
        sceneTag.className = "shot-scene-name-tag";
        sceneTag.textContent = item.title;
        timeCol.appendChild(tsSpan);
        timeCol.appendChild(sceneTag);
        el.appendChild(timeCol);

        if (item.thumb) {
          const thumbCol = document.createElement("div");
          thumbCol.className = "shot-thumb-col";
          const img = document.createElement("img");
          img.src = item.thumb;
          img.alt = item.title;
          img.className = "shot-thumb-img";
          img.loading = "lazy";
          img.onerror = function() { this.style.display = "none"; };
          thumbCol.appendChild(img);
          el.appendChild(thumbCol);
        }

        const detailsCol = document.createElement("div");
        detailsCol.className = "shot-details-col";

        const metaRow = document.createElement("div");
        metaRow.className = "shot-meta-row";
        const titleEl = document.createElement("div");
        titleEl.className = "shot-title";
        titleEl.textContent = item.title;

        const wcBadge = document.createElement("span");
        wcBadge.className = "shot-word-count";
        const initWords = (item.description || "").trim().split(/\s+/).filter(Boolean).length;
        wcBadge.textContent = `${initWords} كلمة`;
        metaRow.appendChild(titleEl);
        metaRow.appendChild(wcBadge);
        detailsCol.appendChild(metaRow);

        const editor = document.createElement("textarea");
        editor.className = "cut-text-editor";
        editor.rows = 2;
        editor.dir = "rtl";
        editor.dataset.cutIndex = String(idx);
        editor.value = item.description || "";
        editor.placeholder = "اكتب نص التعليق الصوتي لهذه اللقطة...";
        editor.addEventListener("input", () => {
          const val = editor.value;
          if (state.editableCuts[idx]) {
            state.editableCuts[idx].text = val;
          }
          const wc = val.trim().split(/\s+/).filter(Boolean).length;
          wcBadge.textContent = `${wc} كلمة`;
          if (dom.generatedScriptText) {
            dom.generatedScriptText.textContent = state.editableCuts
              .map(c => String(c.text || "").trim())
              .filter(Boolean)
              .join(" ");
          }
        });
        detailsCol.appendChild(editor);
        el.appendChild(detailsCol);
        dom.shotsTimelineList.appendChild(el);
      });

      if (dom.timelineCountPill) {
        const renderedCount = dom.shotsTimelineList ? dom.shotsTimelineList.children.length : state.editableCuts.length;
        dom.timelineCountPill.textContent = `${renderedCount} لقطات`;
      }
      dom.shotsTimelineSection.style.display = "block";
      if (dom.cutsEditActions && state.activeJobId) {
        dom.cutsEditActions.style.display = "flex";
      }
      setTimelinePanelOpen(state.isTimelinePanelOpen);
    } else {
      dom.shotsTimelineSection.style.display = "none";
      setTimelinePanelOpen(false);
    }
  }

  function setupCutsTextEditor() {
    if (!dom.btnApplyCutsEdit) return;
    dom.btnApplyCutsEdit.addEventListener("click", async () => {
      if (!state.activeJobId) {
        showToast("لم يتم العثور على معرف الفيديو لتعديله.");
        return;
      }
      const editors = dom.shotsTimelineList ? dom.shotsTimelineList.querySelectorAll(".cut-text-editor") : [];
      editors.forEach((ed) => {
        const idx = Number(ed.dataset.cutIndex);
        if (!Number.isNaN(idx) && state.editableCuts[idx]) {
          state.editableCuts[idx].text = ed.value;
        }
      });

      const hasAnyText = state.editableCuts.some(c => String(c.text || "").trim().length > 0);
      if (!hasAnyText) {
        showToast("يرجى إدخال نص لقطة واحدة على الأقل قبل التحديث.");
        return;
      }

      const token = getStoredSessionToken();
      const origHtml = dom.btnApplyCutsEdit.innerHTML;
      dom.btnApplyCutsEdit.disabled = true;
      dom.btnApplyCutsEdit.innerHTML = "<span>⏳ جاري إعادة توليد الصوت وتحديث الفيديو...</span>";

      try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(state.activeJobId)}/update-cuts-text`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { "Authorization": `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            cuts: state.editableCuts,
            enable_music: Boolean(state.optIn && state.optIn.music),
            ...(state.optIn && state.optIn.music && state.selectedMusicTrack
              ? { music_track: state.selectedMusicTrack }
              : {}),
            ...(state.screenOverlay && (state.screenOverlay.enabled || state.screenOverlayDirty)
              ? {
                  screen_overlay: state.screenOverlay.enabled && String(state.screenOverlay.text || "").trim()
                    ? {
                        text: String(state.screenOverlay.text).trim(),
                        x_pct: state.screenOverlay.x_pct ?? 0.5,
                        y_pct: state.screenOverlay.y_pct ?? 0.92,
                        font: state.screenOverlay.font || "tahoma_bold",
                        effect: state.screenOverlay.effect || "solid_dark",
                        size: state.screenOverlay.size || "medium",
                        text_color: state.screenOverlay.text_color || "default"
                      }
                    : null
                }
              : {}),
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.message || data.error || "تعذر تحديث الصوت على الفيديو.");
        }

        const refreshedSrc = data.video_url_versioned || `${data.video_url || `/outputs/mobile_cuts/cut_${state.activeJobId}.mp4`}?v=${Date.now()}`;
        if (dom.resultVideo) {
          dom.resultVideo.src = refreshedSrc;
          dom.resultVideo.load();
        }
        if (dom.btnDownloadVideo) dom.btnDownloadVideo.href = refreshedSrc;
        if (dom.btnShareVideo) dom.btnShareVideo.href = refreshedSrc;
        if (dom.generatedScriptText && data.script) {
          dom.generatedScriptText.textContent = String(data.script).trim();
        }
        renderShotTimeline(data);
        showToast("تم تحديث الصوت والكلام على الفيديو بنجاح! 🎙️✨");
      } catch (err) {
        showToast(err.message || "حدث خطأ أثناء تحديث نص المشاهد.");
      } finally {
        dom.btnApplyCutsEdit.disabled = false;
        dom.btnApplyCutsEdit.innerHTML = origHtml;
      }
    });
  }

  function resetToNewProduction() {
    state.selectedFile = null;
    if (dom.videoFileInput) dom.videoFileInput.value = "";
    if (dom.dropzoneIdleContent) dom.dropzoneIdleContent.style.display = "block";
    if (dom.dropzoneSelectedContent) dom.dropzoneSelectedContent.style.display = "none";
    if (dom.studioErrorBox) dom.studioErrorBox.style.display = "none";
    if (dom.studioErrorMessage) dom.studioErrorMessage.textContent = "";
    if (dom.resultContainer) dom.resultContainer.style.display = "none";
    if (dom.resultVideo) {
      dom.resultVideo.removeAttribute("src");
      dom.resultVideo.load();
    }
    if (dom.generatedScriptCard) dom.generatedScriptCard.style.display = "none";
    if (dom.generatedScriptText) dom.generatedScriptText.textContent = "";
    if (dom.shotsTimelineSection) dom.shotsTimelineSection.style.display = "none";
    if (dom.shotsTimelineList) dom.shotsTimelineList.innerHTML = "";
    setTimelinePanelOpen(false);
    setCapcutPanelOpen(false);
    stopMusicPreview();
    if (dom.resultOverlayPill) dom.resultOverlayPill.style.display = "none";
    if (dom.resultOverlayText) dom.resultOverlayText.textContent = "";
    if (dom.bottomTextBadge) dom.bottomTextBadge.textContent = "";
    if (dom.overlayFontBadge) dom.overlayFontBadge.style.display = "none";
    if (dom.propertySpecsBadge) dom.propertySpecsBadge.style.display = "none";
    if (dom.resultMusicPill) dom.resultMusicPill.style.display = "none";
    if (dom.resultMusicText) dom.resultMusicText.textContent = "";
    if (dom.resultMusicBadge) dom.resultMusicBadge.style.display = "none";
    if (dom.resultCaptionsPill) dom.resultCaptionsPill.style.display = "none";
    if (dom.resultCaptionsText) dom.resultCaptionsText.textContent = "";
    if (dom.resultCaptionsBadge) dom.resultCaptionsBadge.style.display = "none";
    if (dom.resultMontagePill) dom.resultMontagePill.style.display = "none";
    if (dom.resultMontageText) dom.resultMontageText.textContent = "";
    if (dom.promptTextarea) dom.promptTextarea.value = "";
    if (dom.promptCharCount) dom.promptCharCount.textContent = "0 حرف";
    if (dom.customCaptionTextarea) dom.customCaptionTextarea.value = "";
    if (dom.capcutSplitPreview) dom.capcutSplitPreview.style.display = "none";
    if (dom.splitChunksList) dom.splitChunksList.innerHTML = "";
    if (dom.attachedRecIndicator) dom.attachedRecIndicator.style.display = "none";
    dom.videoDropzone?.scrollIntoView({ behavior: "smooth" });
    showToast("جاهز لإنتاج فيديو جديد 📹");
  }

  // ---------------------------------------------------------------------------
  // 7b. CapCut-Style Animated Caption Studio & AI Smart Split Preview
  // ---------------------------------------------------------------------------
  function setupCaptionTemplatesStudio() {
    if (dom.captionTemplatesGrid) {
      const cards = dom.captionTemplatesGrid.querySelectorAll(".capcut-tpl-card");
      cards.forEach((card) => {
        card.addEventListener("click", () => {
          const tpl = card.getAttribute("data-template") || "";
          state.selectedCaptionTemplate = tpl;
          cards.forEach((c) => {
            const isSel = c === card;
            c.classList.toggle("active", isSel);
            c.setAttribute("aria-pressed", isSel ? "true" : "false");
          });
          if (dom.capcutActiveBadge) {
            const titleEl = card.querySelector(".tpl-title");
            if (tpl) {
              dom.capcutActiveBadge.textContent = `✨ القالب: ${titleEl ? titleEl.textContent : tpl}`;
              dom.capcutActiveBadge.classList.add("is-enabled");
            } else {
              dom.capcutActiveBadge.textContent = "بدون قالب متحرك";
              dom.capcutActiveBadge.classList.remove("is-enabled");
            }
          }
        });
      });
    }

    if (dom.captionPositionSelect) {
      dom.captionPositionSelect.addEventListener("change", () => {
        state.captionPosition = dom.captionPositionSelect.value || "";
      });
    }
    if (dom.captionSizeSelect) {
      dom.captionSizeSelect.addEventListener("change", () => {
        state.captionSize = dom.captionSizeSelect.value || "medium";
      });
    }

    // Auto-select Karaoke Highlight when user starts typing custom caption text if no template is active
    if (dom.customCaptionTextarea && dom.captionTemplatesGrid) {
      dom.customCaptionTextarea.addEventListener("input", () => {
        const val = dom.customCaptionTextarea.value.trim();
        if (val && !state.selectedCaptionTemplate) {
          const defaultCard = dom.captionTemplatesGrid.querySelector('[data-template="karaoke_highlight"]');
          if (defaultCard) defaultCard.click();
        }
      });
    }

    if (dom.btnPreviewSmartSplit) {
      dom.btnPreviewSmartSplit.addEventListener("click", async () => {
        const text = (dom.customCaptionTextarea?.value || dom.promptTextarea?.value || "").trim();
        if (!text) {
          showToast("اكتب نص الكابشن أولاً لمعاينة التقسيم الذكي ✍️");
          dom.customCaptionTextarea?.focus();
          return;
        }
        const tpl = state.selectedCaptionTemplate || "karaoke_highlight";
        const origLabel = dom.btnPreviewSmartSplit.innerHTML;
        dom.btnPreviewSmartSplit.disabled = true;
        dom.btnPreviewSmartSplit.innerHTML = "<span>⏳ جاري التقسيم الذكي...</span>";
        try {
          const resp = await fetch("/api/captions/split", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, template: tpl, duration: 15.0 }),
          });
          const data = await resp.json();
          if (!resp.ok || data.status !== "ok") {
            throw new Error(data.message || data.error || "تعذر تقسيم النص.");
          }
          if (dom.splitPreviewEngine) {
            dom.splitPreviewEngine.textContent = data.engine === "gemini" ? "Gemini AI ✨" : "تقسيم ذكي فوري ⚡";
          }
          if (dom.splitChunksList) {
            dom.splitChunksList.innerHTML = "";
            (data.chunks || []).forEach((chunk) => {
              const chip = document.createElement("div");
              chip.className = "split-chunk-chip";
              const st = Number(chunk.start_sec || 0).toFixed(1);
              const et = Number(chunk.end_sec || 0).toFixed(1);
              const timeSpan = document.createElement("span");
              timeSpan.className = "split-chunk-time";
              timeSpan.textContent = `${st}s–${et}s`;
              const textSpan = document.createElement("span");
              const words = String(chunk.text || "").split(/\s+/);
              words.forEach((w, i) => {
                if (i > 0) textSpan.appendChild(document.createTextNode(" "));
                if (chunk.emphasis && w === chunk.emphasis) {
                  const em = document.createElement("span");
                  em.className = "split-chunk-emph";
                  em.textContent = w;
                  textSpan.appendChild(em);
                } else {
                  textSpan.appendChild(document.createTextNode(w));
                }
              });
              chip.appendChild(timeSpan);
              chip.appendChild(textSpan);
              dom.splitChunksList.appendChild(chip);
            });
          }
          if (dom.capcutSplitPreview) {
            dom.capcutSplitPreview.style.display = "block";
          }
          showToast(`تم تقسيم النص بذكاء إلى ${(data.chunks || []).length} مقاطع متناسقة ✨`);
        } catch (err) {
          showToast(err.message || "حدث خطأ أثناء معاينة التقسيم.");
        } finally {
          dom.btnPreviewSmartSplit.disabled = false;
          dom.btnPreviewSmartSplit.innerHTML = origLabel;
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // 8. Initialization Lifecycle on DOMContentLoaded
  // ---------------------------------------------------------------------------
  async function init() {
    setupSessionAuth();
    setupVideoUpload();
    setupPromptTextarea();
    setupOptInToggles();
    setupUserGuide();
    setupScreenOverlayDesigner();
    loadOverlayCatalog();
    setupMusicTrackPicker();
    setupCollapsiblePanels();
    setupCaptionTemplatesStudio();
    loadMusicTracks();
    setupRecommendationsManager();
    setupVoiceoverPicker();
    setupSettingsModal();
    setupProductionAction();
    setupCutsTextEditor();
    await checkExistingSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
