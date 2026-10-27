/**
 * Algerian Real Estate Mobile Studio - Client Application Logic (web/static/app.js)
 * Author: MohammedBoure
 * Role: Mobile Front-End & Real Estate UI/UX Lead (agy51)
 * Branch: frontend/agy51-one-click-ux-and-session-persistence
 */

(() => {
  'use strict';

  // ---------------------------------------------------------------------------
  // Session Persistence Constants, SaaS Personas & Voice Preferences
  // ---------------------------------------------------------------------------
  const ACTIVE_JOB_KEY = 'active_job_id';
  const PREF_VOICE_KEY = 'preferred_voice';
  const CURRENT_USER_KEY = 'saas_current_user_id';
  const USER_VIDEOS_KEY = 'saas_user_videos_map';

  // 10 Diverse Pre-seeded Merchant Personas + 1 Master Admin
  const PRESEEDED_ACCOUNTS = [
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
      videos_today: 1,
      videos_this_week: 4,
      token: "tok_dar_al_nokhba",
      default_phone: "0550 11 22 33",
      default_text: "📞 0550 11 22 33 | دار النخبة - عقارات راقية في قلب الجزائر"
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
      videos_today: 2,
      videos_this_week: 9,
      token: "tok_auto_algerie",
      default_phone: "0661 44 55 66",
      default_text: "🚗 أوتو الجزائر | سيارات مضمونة وبأفضل الأسعار - 0661 44 55 66"
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
      token: "tok_anaqat_el_awras",
      default_phone: "0770 99 88 77",
      default_text: "👗 قفطان وملابس تقليدية راقية | توصيل مجاني لكافة الولايات"
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
      videos_today: 3,
      videos_this_week: 14,
      token: "tok_techno_phone",
      default_phone: "0540 22 33 44",
      default_text: "📱 تكنو فون | أحدث الهواتف الذكية مع الضمان - 0540 22 33 44"
    },
    {
      id: "usr_el_kasbah_resto",
      username: "el_kasbah_resto",
      business_name: "مطعم القصبة العريق",
      business_category: "مطعم ومأكولات أصيلة",
      role: "merchant",
      status: "active",
      expires_at: "2027-01-15",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 1,
      videos_this_week: 3,
      token: "tok_el_kasbah_resto",
      default_phone: "021 73 00 11",
      default_text: "🍽️ مطعم القصبة | أطباق تقليدية جزائرية بنكهة الأصالة"
    },
    {
      id: "usr_zumurrud_jewelry",
      username: "zumurrud_jewelry",
      business_name: "مجوهرات الزمرد",
      business_category: "مجوهرات وذهب",
      role: "merchant",
      status: "active",
      expires_at: "2026-12-31",
      daily_quota: 4,
      weekly_quota: 20,
      videos_today: 0,
      videos_this_week: 2,
      token: "tok_zumurrud_jewelry",
      default_phone: "0555 88 77 66",
      default_text: "💎 مجوهرات الزمرد | تشكيلات ذهب وألماس فاخرة لعرائسنا"
    },
    {
      id: "usr_abeer_parfums",
      username: "abeer_parfums",
      business_name: "عبير باريس للعطور",
      business_category: "عطور وتجميل",
      role: "merchant",
      status: "active",
      expires_at: "2026-11-20",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 1,
      videos_this_week: 6,
      token: "tok_abeer_parfums",
      default_phone: "0662 33 22 11",
      default_text: "✨ عطور فرنسية وشرقية أصلية | ثبات يدوم طويلاً"
    },
    {
      id: "usr_golden_furniture",
      username: "golden_furniture",
      business_name: "الموبليا الذهبية",
      business_category: "أثاث وديكور راقي",
      role: "merchant",
      status: "active",
      expires_at: "2027-02-28",
      daily_quota: 6,
      weekly_quota: 30,
      videos_today: 2,
      videos_this_week: 8,
      token: "tok_golden_furniture",
      default_phone: "0560 44 33 22",
      default_text: "🛋️ صالونات وغرف نوم عصرية بأجود أنواع الخشب التركي"
    },
    {
      id: "usr_atlas_tours",
      username: "atlas_tours",
      business_name: "أطلس تورز للرحلات",
      business_category: "سياحة وأسفار",
      role: "merchant",
      status: "active",
      expires_at: "2026-12-25",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 0,
      videos_this_week: 4,
      token: "tok_atlas_tours",
      default_phone: "0551 00 99 88",
      default_text: "✈️ رحلات سياحية وعمرة بأفضل البرامج والأسعار الفندقية"
    },
    {
      id: "usr_force_fitness",
      username: "force_fitness",
      business_name: "أكاديمية القوة فيتنس",
      business_category: "نادي رياضي ورشاقة",
      role: "merchant",
      status: "active",
      expires_at: "2026-11-15",
      daily_quota: 5,
      weekly_quota: 25,
      videos_today: 1,
      videos_this_week: 5,
      token: "tok_force_fitness",
      default_phone: "0771 22 11 00",
      default_text: "💪 اشترك الآن في أكبر قاعة كمال أجسام ورشاقة مع كوتش متخصص"
    },
    {
      id: "usr_admin",
      username: "admin",
      business_name: "مدير النظام العام",
      business_category: "مسؤول المنصة",
      role: "admin",
      status: "active",
      expires_at: "2030-12-31",
      daily_quota: 999,
      weekly_quota: 9999,
      videos_today: 10,
      videos_this_week: 56,
      token: "tok_admin_master",
      default_phone: "021 00 00 00",
      default_text: "👑 نظام إدارة منصة إنتاج الفيديو الذكي"
    }
  ];

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

    // SaaS Multi-Tenant & Personas State
    currentUser: null,
    accounts: [...PRESEEDED_ACCOUNTS],
    activeTab: "studio",
    userVideos: {},

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
    selectedVoice: "ar-XA-Standard-A",
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

    // Prominent Main Screen Voice Selector Cards
    voiceSelectionCard: document.getElementById("voiceSelectionCard"),
    mainVoiceCardsGrid: document.getElementById("mainVoiceCardsGrid"),
    voiceCardStandardA: document.getElementById("voiceCardStandardA"),
    voiceCardStandardB: document.getElementById("voiceCardStandardB"),
    voiceCardStandardC: document.getElementById("voiceCardStandardC"),
    voiceCardStandardD: document.getElementById("voiceCardStandardD"),

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

    // SaaS Header Controls & Tab Navigation
    saasHeaderControls: document.getElementById("saasHeaderControls"),
    activePersonaBadge: document.getElementById("activePersonaBadge"),
    personaRoleIcon: document.getElementById("personaRoleIcon"),
    personaBusinessName: document.getElementById("personaBusinessName"),
    personaCategoryBadge: document.getElementById("personaCategoryBadge"),
    accountSwitcherSelect: document.getElementById("accountSwitcherSelect"),
    tabBtnStudio: document.getElementById("tabBtnStudio"),
    tabBtnMerchant: document.getElementById("tabBtnMerchant"),
    tabBtnAdmin: document.getElementById("tabBtnAdmin"),
    tabContentStudio: document.getElementById("tabContentStudio"),
    tabContentMerchant: document.getElementById("tabContentMerchant"),
    tabContentAdmin: document.getElementById("tabContentAdmin"),

    // Quota Warning & Badge (Studio)
    quotaWarningBanner: document.getElementById("quotaWarningBanner"),
    quotaStatusIcon: document.getElementById("quotaStatusIcon"),
    quotaTitleText: document.getElementById("quotaTitleText"),
    quotaDetailsLine: document.getElementById("quotaDetailsLine"),
    quotaDailyRemaining: document.getElementById("quotaDailyRemaining"),
    quotaDailyTotal: document.getElementById("quotaDailyTotal"),
    quotaWeeklyRemaining: document.getElementById("quotaWeeklyRemaining"),
    quotaWeeklyTotal: document.getElementById("quotaWeeklyTotal"),
    quotaExpiryText: document.getElementById("quotaExpiryText"),
    quotaMiniBarFill: document.getElementById("quotaMiniBarFill"),

    // Visual Style & Fixed Text (Studio)
    visualOrientationGroup: document.getElementById("visualOrientationGroup"),
    orientationSelectorGrid: document.getElementById("orientationSelectorGrid"),
    orientationCardPortrait: document.getElementById("orientationCardPortrait"),
    orientationCardLandscape: document.getElementById("orientationCardLandscape"),
    orientationCardSquare: document.getElementById("orientationCardSquare"),
    fixedTextSettingsCard: document.getElementById("fixedTextSettingsCard"),
    fixedTextInput: document.getElementById("fixedTextInput"),
    textPositionSelect: document.getElementById("textPositionSelect"),
    textStyleSelect: document.getElementById("textStyleSelect"),

    // Voice Audition Live Buttons (Studio)
    btnSampleStandardA: document.getElementById("btnSampleStandardA"),
    btnSampleStandardB: document.getElementById("btnSampleStandardB"),
    btnSampleStandardC: document.getElementById("btnSampleStandardC"),
    btnSampleStandardD: document.getElementById("btnSampleStandardD"),

    // Quick Merchant Category Template Chips (Studio)
    merchantTemplateChipsWrap: document.getElementById("merchantTemplateChipsWrap"),
    merchantTemplateChips: document.getElementById("merchantTemplateChips"),
    chipRealEstate: document.getElementById("chipRealEstate"),
    chipAuto: document.getElementById("chipAuto"),
    chipFashion: document.getElementById("chipFashion"),
    chipTech: document.getElementById("chipTech"),
    chipRestaurant: document.getElementById("chipRestaurant"),

    // Merchant Dashboard (Tab 2)
    merchantProfileCard: document.getElementById("merchantProfileCard"),
    merchantDashAvatarIcon: document.getElementById("merchantDashAvatarIcon"),
    merchantDashBusinessName: document.getElementById("merchantDashBusinessName"),
    merchantDashUsername: document.getElementById("merchantDashUsername"),
    merchantDashCategory: document.getElementById("merchantDashCategory"),
    merchantDashExpiry: document.getElementById("merchantDashExpiry"),
    merchantDashStatus: document.getElementById("merchantDashStatus"),
    merchantQuotaMetersGrid: document.getElementById("merchantQuotaMetersGrid"),
    merchantDailyProgressFill: document.getElementById("merchantDailyProgressFill"),
    merchantDailyProgressText: document.getElementById("merchantDailyProgressText"),
    merchantWeeklyProgressFill: document.getElementById("merchantWeeklyProgressFill"),
    merchantWeeklyProgressText: document.getElementById("merchantWeeklyProgressText"),
    merchantLibraryCard: document.getElementById("merchantLibraryCard"),
    merchantVideoGrid: document.getElementById("merchantVideoGrid"),
    merchantVideoCountBadge: document.getElementById("merchantVideoCountBadge"),
    btnGoToStudioFromDash: document.getElementById("btnGoToStudioFromDash"),

    // Admin Dashboard (Tab 3)
    adminStatsCard: document.getElementById("adminStatsCard"),
    statTotalMerchants: document.getElementById("statTotalMerchants"),
    statVideosToday: document.getElementById("statVideosToday"),
    statActiveSubs: document.getElementById("statActiveSubs"),
    statTotalVideos: document.getElementById("statTotalVideos"),
    adminUsersCard: document.getElementById("adminUsersCard"),
    btnOpenCreateMerchantModal: document.getElementById("btnOpenCreateMerchantModal"),
    adminUsersTable: document.getElementById("adminUsersTable"),
    adminUsersTableBody: document.getElementById("adminUsersTableBody"),

    // Modals
    createMerchantModal: document.getElementById("createMerchantModal"),
    createMerchantTitle: document.getElementById("createMerchantTitle"),
    createMerchantForm: document.getElementById("createMerchantForm"),
    newMerchantUsername: document.getElementById("newMerchantUsername"),
    newMerchantBusinessName: document.getElementById("newMerchantBusinessName"),
    newMerchantCategory: document.getElementById("newMerchantCategory"),
    newMerchantExpiry: document.getElementById("newMerchantExpiry"),
    newMerchantDailyQuota: document.getElementById("newMerchantDailyQuota"),
    newMerchantWeeklyQuota: document.getElementById("newMerchantWeeklyQuota"),
    btnSaveNewMerchant: document.getElementById("btnSaveNewMerchant"),
    btnCloseCreateMerchantModal: document.getElementById("btnCloseCreateMerchantModal"),
    btnCancelCreateMerchant: document.getElementById("btnCancelCreateMerchant"),
    editQuotaModal: document.getElementById("editQuotaModal"),
    editQuotaTitle: document.getElementById("editQuotaTitle"),
    editQuotaForm: document.getElementById("editQuotaForm"),
    editQuotaUserId: document.getElementById("editQuotaUserId"),
    editQuotaDaily: document.getElementById("editQuotaDaily"),
    editQuotaWeekly: document.getElementById("editQuotaWeekly"),
    btnSaveEditQuota: document.getElementById("btnSaveEditQuota"),
    btnCloseEditQuotaModal: document.getElementById("btnCloseEditQuotaModal"),
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

    // Verify user quota & account status
    const currentUser = state.currentUser;
    if (currentUser && currentUser.role === "merchant") {
      const isSuspended = currentUser.status === "suspended";
      const isExpired = new Date(currentUser.expires_at) < new Date();
      const dailyRemaining = (currentUser.daily_quota || 5) - (currentUser.videos_today || 0);
      const weeklyRemaining = (currentUser.weekly_quota || 25) - (currentUser.videos_this_week || 0);

      if (isSuspended) {
        showToast("حساب التاجر موقوف حالياً. يرجى مراجعة إدارة المنصة.");
        return;
      }
      if (isExpired) {
        showToast("انتهت صلاحية اشتراك هذا الحساب! يرجى تجديد الصلاحية.");
        return;
      }
      if (dailyRemaining <= 0 || weeklyRemaining <= 0) {
        showToast("لقد استنفذت الحصة المتاحة لإنتاج الفيديوهات (اليومية أو الأسبوعية)!");
        return;
      }
    }

    // 2. Prepare FormData matching 1-Click zero-effort mode or advanced overrides
    const formData = new FormData();
    formData.append("video", state.selectedFile);

    // Visual Orientation Selection
    const orientationInput = document.querySelector('input[name="video_orientation"]:checked');
    const orientationVal = orientationInput ? orientationInput.value : "portrait";
    formData.append("video_orientation", orientationVal);

    // Fixed Text Overlay Settings
    const fixedTextVal = (dom.fixedTextInput?.value || "").trim();
    if (fixedTextVal) {
      formData.append("fixed_text", fixedTextVal);
    }
    const textPositionVal = dom.textPositionSelect?.value || "lower_third";
    formData.append("text_position", textPositionVal);
    const textStyleVal = dom.textStyleSelect?.value || "modern_white";
    formData.append("text_style", textStyleVal);

    // SaaS User Identity & Token
    if (currentUser) {
      if (currentUser.token) formData.append("token", currentUser.token);
      if (currentUser.id) formData.append("user_id", currentUser.id);
      if (currentUser.username) formData.append("username", currentUser.username);
    }

    // Linguistic visual and speech intent prompt descriptions
    const visualDesc = (dom.visualDescription?.value || "").trim();
    const speechDesc = (dom.speechDescription?.value || "").trim();
    if (visualDesc) {
      formData.append("visual_description", visualDesc);
    }
    if (speechDesc) {
      formData.append("speech_description", speechDesc);
    }

    // Prominent Voice selection binding (guaranteed for 1-Click & Advanced modes)
    const voiceToUse = state.selectedVoice || localStorage.getItem(PREF_VOICE_KEY) || dom.voiceSelect?.value || "ar-XA-Standard-A";
    formData.append("voice", voiceToUse);

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
        formData.set("voice", dom.voiceSelect.value);
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
          headers: currentUser && currentUser.token ? { "Authorization": `Bearer ${currentUser.token}` } : {},
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

        // Record generation in merchant quota and library
        recordSuccessfulGeneration(currentUser, finalData, orientationVal, visualDesc || speechDesc);

        setTimeout(() => {
          displayFinalResult(finalData);
        }, 400);

      } else {
        // Fallback direct upload-and-process
        const response = await fetch("/api/upload-and-process", {
          method: "POST",
          headers: currentUser && currentUser.token ? { "Authorization": `Bearer ${currentUser.token}` } : {},
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

        // Record generation in merchant quota and library
        recordSuccessfulGeneration(currentUser, data, orientationVal, visualDesc || speechDesc);

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

  function recordSuccessfulGeneration(currentUser, jobResult, orientationVal, promptTitle) {
    if (!currentUser) return;
    currentUser.videos_today = (currentUser.videos_today || 0) + 1;
    currentUser.videos_this_week = (currentUser.videos_this_week || 0) + 1;
    updateQuotaBanner(currentUser);

    const videoRecord = {
      id: (jobResult && jobResult.job_id) || `vid_${Date.now()}`,
      url: (jobResult && (jobResult.video_url || jobResult.final_video_url)) || "",
      title: promptTitle || currentUser.business_name || "فيديو تسويقي ذكي",
      duration: (jobResult && jobResult.duration_seconds) ? `${jobResult.duration_seconds}s` : "0:25s",
      date: new Date().toISOString().split("T")[0],
      orientation: orientationVal || "9:16"
    };

    if (!state.userVideos[currentUser.username]) {
      state.userVideos[currentUser.username] = [];
    }
    state.userVideos[currentUser.username].unshift(videoRecord);
    try {
      localStorage.setItem(USER_VIDEOS_KEY, JSON.stringify(state.userVideos));
    } catch (e) {}

    if (state.activeTab === "merchant") {
      renderMerchantDashboard();
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
  // Prominent Voice Selector Setup & LocalStorage Persistence
  // ---------------------------------------------------------------------------
  function setupVoiceSelector() {
    const radios = document.querySelectorAll('input[name="prominentVoice"]');
    const savedVoice = localStorage.getItem(PREF_VOICE_KEY) || "ar-XA-Standard-A";
    state.selectedVoice = savedVoice;

    // Apply saved voice to UI
    applyVoiceSelectionToUI(savedVoice);

    // Bind change event to each radio card
    radios.forEach((radio) => {
      radio.addEventListener("change", (e) => {
        if (e.target.checked) {
          const val = e.target.value;
          state.selectedVoice = val;
          localStorage.setItem(PREF_VOICE_KEY, val);
          applyVoiceSelectionToUI(val);
        }
      });
    });

    // Also sync if advanced voiceSelect changes
    if (dom.voiceSelect) {
      dom.voiceSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val && val !== "auto") {
          state.selectedVoice = val;
          localStorage.setItem(PREF_VOICE_KEY, val);
          applyVoiceSelectionToUI(val);
        }
      });
    }
  }

  function applyVoiceSelectionToUI(voiceValue) {
    if (!voiceValue) return;

    // 1. Sync Radio buttons and Card active states
    const radios = document.querySelectorAll('input[name="prominentVoice"]');
    radios.forEach((radio) => {
      const card = radio.closest(".voice-card");
      if (radio.value === voiceValue) {
        radio.checked = true;
        if (card) card.classList.add("active");
      } else {
        radio.checked = false;
        if (card) card.classList.remove("active");
      }
    });

    // 2. Sync Advanced Dropdown if present
    if (dom.voiceSelect && dom.voiceSelect.value !== voiceValue) {
      dom.voiceSelect.value = voiceValue;
    }
  }

  // ---------------------------------------------------------------------------
  // SaaS Multi-Tenant Personas & Audio Preview Engine
  // ---------------------------------------------------------------------------
  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  let currentAuditionAudio = null;
  let currentPlayingVoice = null;
  let webAudioCtx = null;

  function stopVoiceAudition() {
    if (currentAuditionAudio) {
      try {
        currentAuditionAudio.pause();
        currentAuditionAudio.currentTime = 0;
      } catch (e) {}
      currentAuditionAudio = null;
    }
    if (webAudioCtx) {
      try {
        webAudioCtx.close();
      } catch (e) {}
      webAudioCtx = null;
    }
    currentPlayingVoice = null;

    // Reset button states
    const previewBtns = document.querySelectorAll(".btn-voice-preview");
    previewBtns.forEach((btn) => {
      btn.classList.remove("playing");
      const textSpan = btn.querySelector(".preview-text");
      const iconSpan = btn.querySelector(".preview-icon");
      if (textSpan) textSpan.textContent = "استمع للصوت";
      if (iconSpan) iconSpan.textContent = "▶";
    });
  }

  async function playVoiceAudition(voiceId, buttonEl) {
    if (currentPlayingVoice === voiceId) {
      stopVoiceAudition();
      return;
    }

    stopVoiceAudition();
    currentPlayingVoice = voiceId;

    buttonEl.classList.add("playing");
    const textSpan = buttonEl.querySelector(".preview-text");
    const iconSpan = buttonEl.querySelector(".preview-icon");
    if (textSpan) textSpan.textContent = "إيقاف الصوت";
    if (iconSpan) iconSpan.textContent = "⏹️";

    const sampleUrl = `/api/voices/${encodeURIComponent(voiceId)}/sample`;
    const audio = new Audio(sampleUrl);
    currentAuditionAudio = audio;

    let fallbackTriggered = false;
    const triggerWebAudioFallback = () => {
      if (fallbackTriggered) return;
      fallbackTriggered = true;
      playWebAudioHarmonicPreview(voiceId);
    };

    audio.onended = () => {
      stopVoiceAudition();
    };

    audio.onerror = () => {
      triggerWebAudioFallback();
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        triggerWebAudioFallback();
      });
    }

    setTimeout(() => {
      if (currentPlayingVoice === voiceId && !fallbackTriggered && (!audio.currentTime || audio.paused)) {
        triggerWebAudioFallback();
      }
    }, 1200);
  }

  function playWebAudioHarmonicPreview(voiceId) {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) {
        setTimeout(stopVoiceAudition, 1500);
        return;
      }
      webAudioCtx = new AudioContextClass();

      let baseFreq = 260; // female default (Standard A)
      if (voiceId.includes("Standard-B") || voiceId.toLowerCase().includes("charon")) {
        baseFreq = 140; // deep male (Standard B)
      } else if (voiceId.includes("Standard-C") || voiceId.toLowerCase().includes("fenrir")) {
        baseFreq = 185; // energetic male (Standard C)
      } else if (voiceId.includes("Standard-D") || voiceId.toLowerCase().includes("kore")) {
        baseFreq = 290; // calm female (Standard D)
      }

      const osc = webAudioCtx.createOscillator();
      const gain = webAudioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(baseFreq, webAudioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(baseFreq * 1.25, webAudioCtx.currentTime + 0.4);
      osc.frequency.exponentialRampToValueAtTime(baseFreq, webAudioCtx.currentTime + 0.9);

      gain.gain.setValueAtTime(0.08, webAudioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, webAudioCtx.currentTime + 1.8);

      osc.connect(gain);
      gain.connect(webAudioCtx.destination);
      osc.start();
      osc.stop(webAudioCtx.currentTime + 1.8);

      setTimeout(() => {
        stopVoiceAudition();
      }, 1900);
    } catch (e) {
      setTimeout(stopVoiceAudition, 1500);
    }
  }

  function setupVoiceAudition() {
    const auditionButtons = [
      { id: "btnSampleStandardA", voice: "ar-XA-Standard-A" },
      { id: "btnSampleStandardB", voice: "ar-XA-Standard-B" },
      { id: "btnSampleStandardC", voice: "ar-XA-Standard-C" },
      { id: "btnSampleStandardD", voice: "ar-XA-Standard-D" }
    ];

    auditionButtons.forEach(({ id, voice }) => {
      const btn = dom[id];
      if (btn) {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          playVoiceAudition(voice, btn);
        });
      }
    });
  }

  function setupSaaSTabs() {
    const tabs = [
      { btn: dom.tabBtnStudio, content: dom.tabContentStudio, name: "studio" },
      { btn: dom.tabBtnMerchant, content: dom.tabContentMerchant, name: "merchant" },
      { btn: dom.tabBtnAdmin, content: dom.tabContentAdmin, name: "admin" }
    ];

    tabs.forEach(({ btn, name }) => {
      if (!btn) return;
      btn.addEventListener("click", () => {
        switchTab(name);
      });
    });

    if (dom.btnGoToStudioFromDash) {
      dom.btnGoToStudioFromDash.addEventListener("click", () => {
        switchTab("studio");
      });
    }
  }

  function switchTab(tabName) {
    state.activeTab = tabName;

    const allBtns = [dom.tabBtnStudio, dom.tabBtnMerchant, dom.tabBtnAdmin];
    const allContents = [dom.tabContentStudio, dom.tabContentMerchant, dom.tabContentAdmin];

    allBtns.forEach((btn) => {
      if (btn) btn.classList.remove("active");
    });
    allContents.forEach((content) => {
      if (content) {
        content.classList.remove("active");
        content.style.display = "none";
      }
    });

    if (tabName === "studio" && dom.tabBtnStudio && dom.tabContentStudio) {
      dom.tabBtnStudio.classList.add("active");
      dom.tabContentStudio.classList.add("active");
      dom.tabContentStudio.style.display = "block";
    } else if (tabName === "merchant" && dom.tabBtnMerchant && dom.tabContentMerchant) {
      dom.tabBtnMerchant.classList.add("active");
      dom.tabContentMerchant.classList.add("active");
      dom.tabContentMerchant.style.display = "block";
      renderMerchantDashboard();
    } else if (tabName === "admin" && dom.tabBtnAdmin && dom.tabContentAdmin) {
      dom.tabBtnAdmin.classList.add("active");
      dom.tabContentAdmin.classList.add("active");
      dom.tabContentAdmin.style.display = "block";
      renderAdminDashboard();
    }
  }

  async function loadAccounts() {
    // 1. Try to fetch accounts from backend API
    try {
      const res = await fetch("/api/auth/demo-accounts");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          state.accounts = data;
        } else {
          state.accounts = [...PRESEEDED_ACCOUNTS];
        }
      } else {
        state.accounts = [...PRESEEDED_ACCOUNTS];
      }
    } catch (e) {
      state.accounts = [...PRESEEDED_ACCOUNTS];
    }

    // 2. Load cached videos or initialize
    try {
      const stored = localStorage.getItem(USER_VIDEOS_KEY);
      if (stored) {
        state.userVideos = JSON.parse(stored);
      }
    } catch (e) {
      state.userVideos = {};
    }

    // 3. Populate Account Switcher Select
    if (dom.accountSwitcherSelect) {
      dom.accountSwitcherSelect.innerHTML = "";
      state.accounts.forEach((acc) => {
        const opt = document.createElement("option");
        opt.value = acc.id || acc.username;
        const roleIcon = acc.role === "admin" ? "👑" : "🏢";
        opt.textContent = `${roleIcon} ${acc.business_name} (${acc.business_category})`;
        dom.accountSwitcherSelect.appendChild(opt);
      });

      dom.accountSwitcherSelect.addEventListener("change", (e) => {
        switchAccount(e.target.value);
      });
    }

    // 4. Determine Active User
    const savedUserId = localStorage.getItem(CURRENT_USER_KEY);
    let activeUser = state.accounts.find(
      (a) => a.id === savedUserId || a.username === savedUserId
    );
    if (!activeUser) {
      activeUser = state.accounts[0];
    }
    state.currentUser = activeUser;

    if (dom.accountSwitcherSelect) {
      dom.accountSwitcherSelect.value = activeUser.id || activeUser.username;
    }

    applyActiveUserToUI(activeUser);
  }

  function switchAccount(userId) {
    const user = state.accounts.find(
      (a) => a.id === userId || a.username === userId
    );
    if (!user) return;

    state.currentUser = user;
    localStorage.setItem(CURRENT_USER_KEY, user.id || user.username);

    if (dom.accountSwitcherSelect) {
      dom.accountSwitcherSelect.value = user.id || user.username;
    }

    applyActiveUserToUI(user);
    showToast(`تم التبديل إلى حساب: ${user.business_name}`);
  }

  function applyActiveUserToUI(user) {
    if (!user) return;

    // Header badge
    if (dom.personaBusinessName) dom.personaBusinessName.textContent = user.business_name;
    if (dom.personaCategoryBadge) dom.personaCategoryBadge.textContent = user.business_category;
    if (dom.personaRoleIcon) {
      dom.personaRoleIcon.textContent = user.role === "admin" ? "👑" : "🏢";
    }
    if (dom.activePersonaBadge) {
      if (user.role === "admin") {
        dom.activePersonaBadge.classList.add("admin");
      } else {
        dom.activePersonaBadge.classList.remove("admin");
      }
    }

    // Admin Tab Visibility
    if (dom.tabBtnAdmin) {
      if (user.role === "admin") {
        dom.tabBtnAdmin.style.display = "inline-flex";
      } else {
        dom.tabBtnAdmin.style.display = "none";
        if (state.activeTab === "admin") {
          switchTab("studio");
        }
      }
    }

    // Quota Banner in Studio
    updateQuotaBanner(user);

    // Default text in fixedTextInput if empty
    if (dom.fixedTextInput && (!dom.fixedTextInput.value || dom.fixedTextInput.value.trim() === "")) {
      if (user.default_text) {
        dom.fixedTextInput.value = user.default_text;
      }
    }

    // Update Merchant Dashboard if active
    if (state.activeTab === "merchant") {
      renderMerchantDashboard();
    } else if (state.activeTab === "admin") {
      renderAdminDashboard();
    }
  }

  function updateQuotaBanner(user) {
    if (!user) return;
    const dailyTotal = user.daily_quota || 5;
    const weeklyTotal = user.weekly_quota || 25;
    const usedToday = user.videos_today || 0;
    const usedWeek = user.videos_this_week || 0;

    const dailyRemaining = Math.max(0, dailyTotal - usedToday);
    const weeklyRemaining = Math.max(0, weeklyTotal - usedWeek);

    if (dom.quotaDailyRemaining) dom.quotaDailyRemaining.textContent = String(dailyRemaining);
    if (dom.quotaDailyTotal) dom.quotaDailyTotal.textContent = String(dailyTotal);
    if (dom.quotaWeeklyRemaining) dom.quotaWeeklyRemaining.textContent = String(weeklyRemaining);
    if (dom.quotaWeeklyTotal) dom.quotaWeeklyTotal.textContent = String(weeklyTotal);
    if (dom.quotaExpiryText) {
      const isExpired = new Date(user.expires_at) < new Date();
      dom.quotaExpiryText.textContent = isExpired
        ? `منتهي (${user.expires_at})`
        : `نشط حتى ${user.expires_at}`;
      if (isExpired) {
        dom.quotaExpiryText.style.color = "#ef4444";
      } else {
        dom.quotaExpiryText.style.color = "";
      }
    }

    const pct = Math.round((dailyRemaining / dailyTotal) * 100);
    if (dom.quotaMiniBarFill) {
      dom.quotaMiniBarFill.style.width = `${pct}%`;
      if (pct <= 0) {
        dom.quotaMiniBarFill.style.background = "#ef4444";
      } else if (pct <= 30) {
        dom.quotaMiniBarFill.style.background = "#f59e0b";
      } else {
        dom.quotaMiniBarFill.style.background = "#10b981";
      }
    }

    if (dom.quotaWarningBanner) {
      dom.quotaWarningBanner.classList.remove("warning", "exhausted");
      if (dailyRemaining <= 0 || weeklyRemaining <= 0 || user.status === "suspended") {
        dom.quotaWarningBanner.classList.add("exhausted");
      } else if (dailyRemaining <= 1) {
        dom.quotaWarningBanner.classList.add("warning");
      }
    }
  }

  function renderMerchantDashboard() {
    const user = state.currentUser;
    if (!user) return;

    if (dom.merchantDashBusinessName) dom.merchantDashBusinessName.textContent = user.business_name;
    if (dom.merchantDashUsername) dom.merchantDashUsername.textContent = user.username;
    if (dom.merchantDashCategory) dom.merchantDashCategory.textContent = user.business_category;
    if (dom.merchantDashExpiry) dom.merchantDashExpiry.textContent = user.expires_at;
    if (dom.merchantDashStatus) {
      const isSuspended = user.status === "suspended";
      dom.merchantDashStatus.textContent = isSuspended ? "موقوف مؤقتاً" : "حساب نشط";
      dom.merchantDashStatus.className = `badge-status-pill ${isSuspended ? "suspended" : "active"}`;
    }

    const dailyTotal = user.daily_quota || 5;
    const weeklyTotal = user.weekly_quota || 25;
    const usedToday = user.videos_today || 0;
    const usedWeek = user.videos_this_week || 0;
    const dailyRem = Math.max(0, dailyTotal - usedToday);
    const weeklyRem = Math.max(0, weeklyTotal - usedWeek);

    if (dom.merchantDailyProgressText) {
      dom.merchantDailyProgressText.textContent = `${dailyRem} / ${dailyTotal} فيديوهات متبقية اليوم (${usedToday} تم إنتاجها)`;
    }
    if (dom.merchantDailyProgressFill) {
      const dailyPct = Math.round((dailyRem / dailyTotal) * 100);
      dom.merchantDailyProgressFill.style.width = `${dailyPct}%`;
    }

    if (dom.merchantWeeklyProgressText) {
      dom.merchantWeeklyProgressText.textContent = `${weeklyRem} / ${weeklyTotal} فيديو متبقي هذا الأسبوع (${usedWeek} تم إنتاجها)`;
    }
    if (dom.merchantWeeklyProgressFill) {
      const weeklyPct = Math.round((weeklyRem / weeklyTotal) * 100);
      dom.merchantWeeklyProgressFill.style.width = `${weeklyPct}%`;
    }

    renderMerchantVideoLibrary(user.username);
  }

  function renderMerchantVideoLibrary(username) {
    if (!dom.merchantVideoGrid) return;
    const videos = state.userVideos[username] || [];

    if (dom.merchantVideoCountBadge) {
      dom.merchantVideoCountBadge.textContent = `${videos.length} فيديو`;
    }

    if (videos.length === 0) {
      dom.merchantVideoGrid.innerHTML = `
        <div class="library-empty-state">
          <div class="empty-state-icon">🎬</div>
          <div class="empty-state-title">لا توجد مقاطع فيديو مسجلة لهذا الحساب بعد</div>
          <div class="empty-state-desc">ابدأ الآن بتسجيل أول فيديو لمتجرك وسيقوم الذكاء الاصطناعي بإخراجه تلقائياً!</div>
        </div>
      `;
      return;
    }

    dom.merchantVideoGrid.innerHTML = "";
    videos.forEach((v) => {
      const card = document.createElement("div");
      card.className = "merchant-video-card";
      card.innerHTML = `
        <video src="${v.url || ""}" controls preload="metadata" playsinline></video>
        <div class="video-card-body">
          <div class="video-card-title">${escapeHtml(v.title || "فيديو تسويقي")}</div>
          <div class="video-card-meta">
            <span>⏱️ ${v.duration || "0:25s"}</span>
            <span>📅 ${v.date || "اليوم"}</span>
            <span>📐 ${v.orientation || "9:16"}</span>
          </div>
          <a href="${v.url || "#"}" download class="btn-download-video-card" target="_blank">
            <span>⬇️ تحميل الفيديو (MP4)</span>
          </a>
        </div>
      `;
      dom.merchantVideoGrid.appendChild(card);
    });
  }

  function renderAdminDashboard() {
    const totalMerchants = state.accounts.filter((a) => a.role === "merchant").length;
    const activeSubs = state.accounts.filter((a) => a.role === "merchant" && a.status === "active").length;
    let totalVideosToday = 0;
    let totalVideosAll = 0;

    state.accounts.forEach((a) => {
      totalVideosToday += a.videos_today || 0;
      const userVidCount = (state.userVideos[a.username] || []).length;
      totalVideosAll += Math.max(userVidCount, a.videos_this_week || 0);
    });

    if (dom.statTotalMerchants) dom.statTotalMerchants.textContent = String(totalMerchants);
    if (dom.statVideosToday) dom.statVideosToday.textContent = String(totalVideosToday);
    if (dom.statActiveSubs) dom.statActiveSubs.textContent = String(activeSubs);
    if (dom.statTotalVideos) dom.statTotalVideos.textContent = String(totalVideosAll);

    if (dom.adminUsersTableBody) {
      dom.adminUsersTableBody.innerHTML = "";
      state.accounts.filter((a) => a.role === "merchant").forEach((acc) => {
        const tr = document.createElement("tr");
        const isSuspended = acc.status === "suspended";
        tr.innerHTML = `
          <td>
            <strong>${escapeHtml(acc.business_name)}</strong>
            <div style="font-size: 0.72rem; color: #94a3b8;">@${escapeHtml(acc.username)}</div>
          </td>
          <td>${escapeHtml(acc.business_category)}</td>
          <td>${acc.daily_quota} / يوم</td>
          <td>${acc.weekly_quota} / أسبوع</td>
          <td>${acc.expires_at}</td>
          <td>
            <span class="table-badge ${isSuspended ? "suspended" : "active"}">
              ${isSuspended ? "موقوف" : "نشط"}
            </span>
          </td>
          <td>
            <div class="table-actions-cell">
              <button type="button" class="table-action-btn toggle" data-user="${acc.id || acc.username}">
                ${isSuspended ? "▶ تفعيل" : "⏸ إيقاف"}
              </button>
              <button type="button" class="table-action-btn renew" data-user="${acc.id || acc.username}">
                +30 يوم
              </button>
              <button type="button" class="table-action-btn edit" data-user="${acc.id || acc.username}">
                ✏️ الحصص
              </button>
            </div>
          </td>
        `;
        dom.adminUsersTableBody.appendChild(tr);
      });

      dom.adminUsersTableBody.querySelectorAll(".table-action-btn.toggle").forEach((btn) => {
        btn.addEventListener("click", () => toggleUserStatus(btn.dataset.user));
      });
      dom.adminUsersTableBody.querySelectorAll(".table-action-btn.renew").forEach((btn) => {
        btn.addEventListener("click", () => renewUserSubscription(btn.dataset.user));
      });
      dom.adminUsersTableBody.querySelectorAll(".table-action-btn.edit").forEach((btn) => {
        btn.addEventListener("click", () => openEditQuotaModal(btn.dataset.user));
      });
    }
  }

  function toggleUserStatus(userId) {
    const user = state.accounts.find((a) => a.id === userId || a.username === userId);
    if (!user) return;
    user.status = user.status === "active" ? "suspended" : "active";
    showToast(`تم تغيير حالة الحساب إلى: ${user.status === "active" ? "نشط" : "موقوف"}`);
    renderAdminDashboard();
    if (state.currentUser && (state.currentUser.id === userId || state.currentUser.username === userId)) {
      applyActiveUserToUI(user);
    }
  }

  function renewUserSubscription(userId) {
    const user = state.accounts.find((a) => a.id === userId || a.username === userId);
    if (!user) return;
    const currentExp = new Date(user.expires_at || new Date());
    currentExp.setDate(currentExp.getDate() + 30);
    user.expires_at = currentExp.toISOString().split("T")[0];
    showToast(`تم تجديد الاشتراك بنجاح حتى ${user.expires_at}`);
    renderAdminDashboard();
    if (state.currentUser && (state.currentUser.id === userId || state.currentUser.username === userId)) {
      applyActiveUserToUI(user);
    }
  }

  function openEditQuotaModal(userId) {
    const user = state.accounts.find((a) => a.id === userId || a.username === userId);
    if (!user) return;
    if (dom.editQuotaUserId) dom.editQuotaUserId.value = user.id || user.username;
    if (dom.editQuotaDaily) dom.editQuotaDaily.value = user.daily_quota;
    if (dom.editQuotaWeekly) dom.editQuotaWeekly.value = user.weekly_quota;
    if (dom.editQuotaModal) dom.editQuotaModal.style.display = "flex";
  }

  function setupMerchantTemplateChips() {
    const templates = [
      {
        btn: dom.chipRealEstate,
        visual: "جولة تبدأ من المدخل الرئيسي والصالون الملكي وتنتقل إلى الشرفة مع إبراز المطبخ العصري والتشطيبات الفاخرة.",
        speech: "رحب بالمشاهدين واشرح مميزات الموقع الهادئ، الإطلالة البانورامية، التشطيبات الراقية وسعرها المغري."
      },
      {
        btn: dom.chipAuto,
        visual: "لقطات تفصيلية حول السيارة تبدأ من الواجهة الأمامية وشبك التهوية ثم إلى المقصورة الفاخرة ولوحة القيادة والجنوط الرياضية.",
        speech: "استعرض مواصفات السيارة العصرية، وقوة المحرك واقتصاده في استهلاك الوقود، والضمان المتاح مع خطة الدفع الميسرة."
      },
      {
        btn: dom.chipFashion,
        visual: "استعراض انسيابي لتفاصيل القماش الفاخر، التطريز التقليدي المتقن، والألوان الجذابة مع إبراز الإكسسوارات المرافقة.",
        speech: "أبرز أصالة التصميم الجزائري واللمسة العصرية، جودة الخياطة الرفيعة، وتوفر القياسات مع إمكانية التوصيل الفوري."
      },
      {
        btn: dom.chipTech,
        visual: "إظهار الهاتف أو الجهاز الذكي من كافة الزوايا، فحص نحافة الشاشة، الكاميرات الاحترافية وسرعة استجابة النظام.",
        speech: "قدم أقوى عروض الإلكترونيات مع الضمان الرسمي لمدة عام كامل وهدايا مجانية قيمة مع كل طلب."
      },
      {
        btn: dom.chipRestaurant,
        visual: "مشاهد قريبة جذابة للأطباق الساخنة والتقديم الشهي وديكورات المطعم الدافئة والجلسات العائلية المريحة.",
        speech: "ادعُ الزبائن لتذوق أشهى المأكولات المحضرة بأجود المكونات الطازجة وعش تجربة عائلية استثنائية."
      }
    ];

    templates.forEach(({ btn, visual, speech }) => {
      if (!btn) return;
      btn.addEventListener("click", () => {
        document.querySelectorAll(".btn-merchant-chip").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");

        if (dom.visualDescription) dom.visualDescription.value = visual;
        if (dom.speechDescription) dom.speechDescription.value = speech;
        showToast("تم تطبيق قالب الوصف بنجاح!");
      });
    });
  }

  function setupOrientationSelector() {
    const radios = document.querySelectorAll('input[name="video_orientation"]');
    radios.forEach((radio) => {
      radio.addEventListener("change", (e) => {
        document.querySelectorAll(".orientation-card").forEach((c) => c.classList.remove("active"));
        const parentCard = e.target.closest(".orientation-card");
        if (parentCard) parentCard.classList.add("active");
      });
    });
  }

  function setupAdminModals() {
    if (dom.btnOpenCreateMerchantModal) {
      dom.btnOpenCreateMerchantModal.addEventListener("click", () => {
        if (dom.createMerchantForm) dom.createMerchantForm.reset();
        if (dom.newMerchantExpiry) {
          const nextYear = new Date();
          nextYear.setFullYear(nextYear.getFullYear() + 1);
          dom.newMerchantExpiry.value = nextYear.toISOString().split("T")[0];
        }
        if (dom.createMerchantModal) dom.createMerchantModal.style.display = "flex";
      });
    }

    if (dom.btnCloseCreateMerchantModal) {
      dom.btnCloseCreateMerchantModal.addEventListener("click", () => {
        if (dom.createMerchantModal) dom.createMerchantModal.style.display = "none";
      });
    }
    if (dom.btnCancelCreateMerchant) {
      dom.btnCancelCreateMerchant.addEventListener("click", () => {
        if (dom.createMerchantModal) dom.createMerchantModal.style.display = "none";
      });
    }

    if (dom.createMerchantForm) {
      dom.createMerchantForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = (dom.newMerchantUsername?.value || "").trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
        const businessName = (dom.newMerchantBusinessName?.value || "").trim();
        const category = dom.newMerchantCategory?.value || "تجارة عامة";
        const expiry = dom.newMerchantExpiry?.value || "2027-12-31";
        const daily = parseInt(dom.newMerchantDailyQuota?.value || "5", 10);
        const weekly = parseInt(dom.newMerchantWeeklyQuota?.value || "25", 10);

        if (!username || !businessName) {
          showToast("يرجى ملء جميع الحقول المطلوبة!");
          return;
        }

        const newAccount = {
          id: `usr_${username}`,
          username: username,
          business_name: businessName,
          business_category: category,
          role: "merchant",
          status: "active",
          expires_at: expiry,
          daily_quota: daily,
          weekly_quota: weekly,
          videos_today: 0,
          videos_this_week: 0,
          token: `tok_${username}`,
          default_phone: "0550 00 00 00",
          default_text: `📞 0550 00 00 00 | ${businessName}`
        };

        try {
          await fetch("/api/admin/users", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${state.currentUser?.token || ""}`
            },
            body: JSON.stringify(newAccount)
          });
        } catch (err) {}

        state.accounts.push(newAccount);

        if (dom.accountSwitcherSelect) {
          const opt = document.createElement("option");
          opt.value = newAccount.id;
          opt.textContent = `🏢 ${newAccount.business_name} (${newAccount.business_category})`;
          dom.accountSwitcherSelect.appendChild(opt);
        }

        if (dom.createMerchantModal) dom.createMerchantModal.style.display = "none";
        renderAdminDashboard();
        showToast(`تم إنشاء حساب التاجر (${businessName}) بنجاح!`);
      });
    }

    if (dom.btnCloseEditQuotaModal) {
      dom.btnCloseEditQuotaModal.addEventListener("click", () => {
        if (dom.editQuotaModal) dom.editQuotaModal.style.display = "none";
      });
    }

    if (dom.editQuotaForm) {
      dom.editQuotaForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userId = dom.editQuotaUserId?.value;
        const daily = parseInt(dom.editQuotaDaily?.value || "5", 10);
        const weekly = parseInt(dom.editQuotaWeekly?.value || "25", 10);

        const user = state.accounts.find((a) => a.id === userId || a.username === userId);
        if (user) {
          user.daily_quota = daily;
          user.weekly_quota = weekly;

          try {
            await fetch(`/api/admin/users/${encodeURIComponent(userId)}`, {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${state.currentUser?.token || ""}`
              },
              body: JSON.stringify({ daily_quota: daily, weekly_quota: weekly })
            });
          } catch (err) {}

          if (dom.editQuotaModal) dom.editQuotaModal.style.display = "none";
          renderAdminDashboard();
          if (state.currentUser && (state.currentUser.id === userId || state.currentUser.username === userId)) {
            applyActiveUserToUI(user);
          }
          showToast("تم تحديث الحصص بنجاح!");
        }
      });
    }
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
    setupVoiceSelector();
    setupVoiceAudition();
    setupSaaSTabs();
    setupOrientationSelector();
    setupMerchantTemplateChips();
    setupAdminModals();
    await loadAccounts();
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
