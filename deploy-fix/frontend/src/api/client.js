import axios from "axios";

// Relative base URL — Vite's dev proxy (see vite.config.js) forwards
// /api and /media to the FastAPI backend, so this works unmodified in
// both dev and behind a reverse proxy in production.
const http = axios.create({ baseURL: "/" });

// Attach the session token (if present) to every request. Most Sprint
// 1-7 endpoints don't require auth yet — see the root README's Sprint 8
// section — so this is additive, not a hard gate.
http.interceptors.request.use((config) => {
  const token = localStorage.getItem("pulse_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  listEpisodes: () => http.get("/api/v1/episodes").then((r) => r.data),

  getEpisode: (id) => http.get(`/api/v1/episodes/${id}`).then((r) => r.data),

  createEpisode: (payload) =>
    http.post("/api/v1/episodes", payload).then((r) => r.data),

  uploadMedia: (id, file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post(`/api/v1/episodes/${id}/media`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (onProgress && evt.total) {
            onProgress(Math.round((evt.loaded / evt.total) * 100));
          }
        },
      })
      .then((r) => r.data);
  },

  mediaStatus: (id) =>
    http.get(`/api/v1/episodes/${id}/media-status`).then((r) => r.data),

  transcribe: (id, mediaFileId) =>
    http
      .post(`/api/v1/episodes/${id}/transcribe`, null, {
        params: mediaFileId ? { media_file_id: mediaFileId } : {},
      })
      .then((r) => r.data),

  analyze: (id) =>
    http.post(`/api/v1/episodes/${id}/analyze`).then((r) => r.data),

  updateReview: (id, reviewId, statusValue) =>
    http
      .post(`/api/v1/episodes/${id}/reviews`, {
        review_id: reviewId,
        status: statusValue,
      })
      .then((r) => r.data),

  exportMarkersUrl: (id) => `/api/v1/episodes/${id}/export/markers`,

  // --- Night 4: color grading + brand settings ---
  listLuts: () => http.get("/api/v1/luts").then((r) => r.data),

  uploadLut: (name, file) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post("/api/v1/luts", form, {
        params: { name },
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  applyLut: (episodeId, lutName, renderFull = false) =>
    http
      .post(`/api/v1/episodes/${episodeId}/apply-lut`, {
        lut_name: lutName,
        render_full: renderFull,
      })
      .then((r) => r.data),

  styleTransfer: (episodeId, referenceImageFile, renderFull = false) => {
    const form = new FormData();
    form.append("reference_image", referenceImageFile);
    return http
      .post(`/api/v1/episodes/${episodeId}/style-transfer`, form, {
        params: { render_full: renderFull },
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  colorSpecs: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/color-specs`).then((r) => r.data),

  deliverySpecs: () => http.get("/api/v1/delivery-specs").then((r) => r.data),

  getBrandSettings: () => http.get("/api/v1/brand-settings").then((r) => r.data),

  updateBrandSettings: (payload) =>
    http.put("/api/v1/brand-settings", payload).then((r) => r.data),

  uploadBrandLogo: (file) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post("/api/v1/brand-settings/logo", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  uploadBrandIntroMusic: (file) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post("/api/v1/brand-settings/intro-music", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  uploadBrandOutroMusic: (file) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post("/api/v1/brand-settings/outro-music", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  // --- Night 5: campaign / marketing pack ---
  generateCampaign: (episodeId) =>
    http.post(`/api/v1/episodes/${episodeId}/generate-campaign`).then((r) => r.data),

  getCampaign: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/campaign`).then((r) => r.data),

  getHypeScores: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/hype-score`).then((r) => r.data),

  getViralPredictions: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/viral-prediction`).then((r) => r.data),

  // --- Sprint 6: PR module ---
  generatePressKit: (episodeId) =>
    http.post(`/api/v1/episodes/${episodeId}/generate-press-kit`).then((r) => r.data),

  getJournalistMatches: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/journalist-matches`).then((r) => r.data),

  listJournalistLeads: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/journalist-leads`).then((r) => r.data),

  createJournalistLead: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/journalist-leads`, payload).then((r) => r.data),

  sendPitches: (episodeId, journalistLeadIds) =>
    http
      .post(`/api/v1/episodes/${episodeId}/send-pitches`, { journalist_lead_ids: journalistLeadIds })
      .then((r) => r.data),

  listEmbargoes: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/embargoes`).then((r) => r.data),

  createEmbargo: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/embargoes`, payload).then((r) => r.data),

  listCoverage: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/coverage`).then((r) => r.data),

  addCoverage: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/coverage`, payload).then((r) => r.data),

  // --- Sprint 6: Reddit distribution ---
  searchSubreddits: (q) =>
    http.get("/api/v1/reddit/subreddits/search", { params: { q } }).then((r) => r.data),

  analyzeSubreddit: (name) =>
    http.get(`/api/v1/reddit/subreddits/analyze/${name.replace(/^r\//, "")}`).then((r) => r.data),

  generateRedditContent: (episodeId) =>
    http.post(`/api/v1/episodes/${episodeId}/reddit/generate`).then((r) => r.data),

  listRedditPosts: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/reddit/posts`).then((r) => r.data),

  createRedditPost: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/reddit/posts`, payload).then((r) => r.data),

  scheduleRedditPost: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/reddit/schedule`, payload).then((r) => r.data),

  getRedditPerformance: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/reddit/performance`).then((r) => r.data),

  suggestCommentReply: (commentBody, episodeContext) =>
    http
      .post("/api/v1/reddit/comment/suggest", { comment_body: commentBody, episode_context: episodeContext })
      .then((r) => r.data),

  getKarmaHistory: () => http.get("/api/v1/reddit/karma").then((r) => r.data),

  logKarma: (payload) => http.post("/api/v1/reddit/karma", payload).then((r) => r.data),

  // --- Sprint 6: Postiz distribution ---
  listPlatformIntegrations: () => http.get("/api/v1/platforms/integrations").then((r) => r.data),

  getRedditPlatformStatus: () => http.get("/api/v1/platforms/reddit/status").then((r) => r.data),

  schedulePosts: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/schedule-posts`, payload).then((r) => r.data),

  getPostStatus: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/post-status`).then((r) => r.data),

  // --- Sprint 7: Film features ---
  getActs: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/acts`).then((r) => r.data),

  getTrailerCutList: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/trailer-cut-list`).then((r) => r.data),

  exportTrailer: (episodeId, version) => {
    // Triggers a browser download directly rather than fetching JSON.
    const url = `/api/v1/episodes/${episodeId}/export-trailer`;
    return http
      .post(url, { version }, { responseType: "blob" })
      .then((r) => {
        const blobUrl = URL.createObjectURL(new Blob([r.data], { type: "text/csv" }));
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = `episode-${episodeId}-trailer-${version}s.csv`;
        a.click();
        URL.revokeObjectURL(blobUrl);
      });
  },

  getFestivalMatches: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/festival-matches`).then((r) => r.data),

  updateFestivalMatch: (episodeId, matchId, payload) =>
    http.patch(`/api/v1/episodes/${episodeId}/festival-matches/${matchId}`, payload).then((r) => r.data),

  generateFestivalSubmission: (episodeId) =>
    http.post(`/api/v1/episodes/${episodeId}/festival-submission`).then((r) => r.data),

  getTerritorySchedule: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/territory-schedule`).then((r) => r.data),

  addTerritoryRelease: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/territory-schedule`, payload).then((r) => r.data),

  getDeliverySpecsForEpisode: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/delivery-specs`).then((r) => r.data),

  getSyncLicensingReport: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/sync-licensing-report`).then((r) => r.data),

  // --- Sprint 7: Executive dashboard ---
  getDashboard: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/dashboard`).then((r) => r.data),

  getRisks: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/risks`).then((r) => r.data),

  getFinances: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/finances`).then((r) => r.data),

  addBudgetItem: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/finances`, payload).then((r) => r.data),

  getTimeline: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/timeline`).then((r) => r.data),

  addMilestone: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/timeline`, payload).then((r) => r.data),

  // --- Sprint 8: auth ---
  login: (email, password) => http.post("/api/v1/auth/login", { email, password }).then((r) => r.data),

  requestMagicLink: (email) => http.post("/api/v1/auth/magic-link/request", { email }).then((r) => r.data),

  verifyMagicLink: (token) => http.post("/api/v1/auth/magic-link/verify", { token }).then((r) => r.data),

  acceptInvite: (payload) => http.post("/api/v1/auth/accept-invite", payload).then((r) => r.data),

  getMe: () => http.get("/api/v1/auth/me").then((r) => r.data),

  logout: () => http.post("/api/v1/auth/logout").then((r) => r.data),

  createInvite: (email, role) => http.post("/api/v1/auth/invites", { email, role }).then((r) => r.data),

  listInvites: () => http.get("/api/v1/auth/invites").then((r) => r.data),

  revokeInvite: (inviteId) => http.delete(`/api/v1/auth/invites/${inviteId}`),

  // --- Sprint 8: user management ---
  listUsers: () => http.get("/api/v1/users").then((r) => r.data),

  updateUser: (userId, payload) => http.patch(`/api/v1/users/${userId}`, payload).then((r) => r.data),

  getUserActivity: (userId) => http.get(`/api/v1/users/${userId}/activity`).then((r) => r.data),

  // --- Sprint 8: Fame module ---
  getFameScore: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/fame/score`).then((r) => r.data),

  getFameHistory: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/fame/history`).then((r) => r.data),

  getFameProjection: (episodeId, horizonDays) =>
    http.get(`/api/v1/episodes/${episodeId}/fame/projection`, { params: { horizon_days: horizonDays } }).then((r) => r.data),

  listMentions: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/fame/mentions`).then((r) => r.data),

  searchRedditMentions: (episodeId, q) =>
    http.get(`/api/v1/episodes/${episodeId}/fame/mentions/search-reddit`, { params: { q } }).then((r) => r.data),

  addMention: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/fame/mentions`, payload).then((r) => r.data),

  analyzeMentionSentiment: (episodeId, mentionId) =>
    http.post(`/api/v1/episodes/${episodeId}/fame/mentions/${mentionId}/analyze-sentiment`).then((r) => r.data),

  listCompetitors: (episodeId) => http.get(`/api/v1/episodes/${episodeId}/fame/competitors`).then((r) => r.data),

  addCompetitor: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/fame/competitors`, payload).then((r) => r.data),

  listCulturalFootprint: (episodeId) =>
    http.get(`/api/v1/episodes/${episodeId}/fame/cultural-footprint`).then((r) => r.data),

  addCulturalFootprintItem: (episodeId, payload) =>
    http.post(`/api/v1/episodes/${episodeId}/fame/cultural-footprint`, payload).then((r) => r.data),
};

export default api;
