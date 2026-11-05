import { apiClient } from './client.js';
import { mockStore } from './mockStore.js';

const env = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};

// Determines whether we run offline with mock store or connect to live FastAPI backend
// In production builds, default to LIVE unless explicitly forced via VITE_USE_MOCK === 'true'
const isMock =
  env.VITE_USE_MOCK === 'true' ||
  (!env.PROD && env.VITE_USE_MOCK !== 'false');

console.info(`[RepairBuddy API] Running in ${isMock ? 'MOCK' : 'LIVE'} mode.`);

export const api = {
  // Export active mode for UI diagnostics
  isMockMode: () => isMock,

  // Jobs
  async createJob(payload) {
    if (isMock) return mockStore.createJob(payload);
    return apiClient.post('/jobs', payload);
  },

  async getJob(jobId) {
    if (isMock) return mockStore.getJob(jobId);
    return apiClient.get(`/jobs/${jobId}`);
  },

  async getNearbyJobs(workerCoords, radiusKm) {
    if (isMock) return mockStore.getNearbyJobs(workerCoords, radiusKm);
    return apiClient.get('/jobs/nearby', { params: { ...workerCoords, radiusKm } });
  },

  // Workers Match
  async getMatchedWorkers(jobId) {
    if (isMock) return mockStore.getMatchedWorkers(jobId);
    return apiClient.get('/workers/match', { params: { jobId } });
  },

  // Offers & Negotiation
  async getOffers(jobId) {
    if (isMock) return mockStore.getOffersForJob(jobId);
    return apiClient.get('/offers', { params: { jobId } });
  },

  async createOffer(payload) {
    if (isMock) return mockStore.createOffer(payload);
    return apiClient.post('/offers', payload);
  },

  async counterOffer(offerId, payload) {
    if (isMock) return mockStore.counterOffer(offerId, payload);
    const counterBody = {
      price: Number(payload.price),
    };
    return apiClient.post(`/offers/${offerId}/counter`, counterBody);
  },

  async acceptOffer(offerId) {
    if (isMock) return mockStore.acceptOffer(offerId);
    return apiClient.post(`/offers/${offerId}/accept`);
  },

  async rejectOffer(offerId) {
    if (isMock) return mockStore.rejectOffer(offerId);
    return apiClient.post(`/offers/${offerId}/reject`);
  },

  // Job Lifecycle Transitions
  async startJob(jobId) {
    if (isMock) return mockStore.startJob(jobId);
    return apiClient.post(`/jobs/${jobId}/start`);
  },

  async completeJob(jobId) {
    if (isMock) return mockStore.completeJob(jobId);
    return apiClient.post(`/jobs/${jobId}/complete`);
  },

  async confirmJob(jobId) {
    if (isMock) return mockStore.confirmJob(jobId);
    return apiClient.post(`/jobs/${jobId}/confirm`);
  },

  async cancelJob(jobId) {
    if (isMock) return mockStore.cancelJob?.(jobId);
    return apiClient.post(`/jobs/${jobId}/cancel`);
  },

  // Reviews, SOS, Reports
  async submitReview(payload) {
    if (isMock) return mockStore.submitReview(payload);
    return apiClient.post('/reviews', payload);
  },

  async triggerSos(payload) {
    if (isMock) return mockStore.triggerSos(payload);
    return apiClient.post('/sos', payload);
  },

  async setEmergencyContact(payload) {
    if (isMock) return mockStore.setEmergencyContact(payload);
    return apiClient.put('/users/me/emergency-contact', payload);
  },

  async getEmergencyContact() {
    if (isMock) return mockStore.getEmergencyContact();
    return apiClient.get('/users/me/emergency-contact');
  },

  async getAdminSosAlerts() {
    if (isMock) return mockStore.getAdminSosAlerts();
    const res = await apiClient.get('/admin/sos');
    return Array.isArray(res) ? res : (res?.data || []);
  },

  async reportUser(payload) {
    // FastAPI ReportCreate strictly requires workerId and reason
    const normalized = {
      ...payload,
      workerId: payload.workerId || payload.reportedUserId,
    };
    if (isMock) return mockStore.reportUser(normalized);
    return apiClient.post('/reports', normalized);
  },

  // Worker Profile Updates & Verification
  async getWorker(workerId) {
    if (isMock) return mockStore.getWorker(workerId);
    return apiClient.get(`/workers/${workerId}`);
  },

  async verifyWorker(payload) {
    if (isMock) return mockStore.verifyWorker(payload);
    return apiClient.post('/workers/verify', payload);
  },

  async uploadWorkerVerification(formData) {
    if (isMock) return mockStore.uploadWorkerVerification(formData);
    return apiClient.post('/workers/verify/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  async approveWorkerVerification(workerUid) {
    if (isMock) return mockStore.approveWorkerVerification(workerUid);
    return apiClient.post(`/admin/verifications/${workerUid}/approve`);
  },

  async rejectWorkerVerification(workerUid, reason) {
    if (isMock) return mockStore.rejectWorkerVerification(workerUid, reason);
    return apiClient.post(`/admin/verifications/${workerUid}/reject`, { reason });
  },

  async getVerificationDocumentBlobUrl(workerUid, docType) {
    if (isMock) return mockStore.getVerificationDocumentBlobUrl(workerUid, docType);
    const response = await apiClient.get(`/admin/verifications/${workerUid}/documents/${docType}`, {
      responseType: 'blob',
    });
    return URL.createObjectURL(response);
  },

  async getPendingVerifications() {
    if (isMock) return mockStore.getPendingVerifications();
    const res = await apiClient.get('/admin/verifications/pending');
    return Array.isArray(res) ? res : (res?.data || []);
  },

  async registerWorker(payload) {
    if (isMock) return payload;
    return apiClient.post('/workers/register', payload);
  },

  async registerCustomer(payload) {
    if (isMock) return payload;
    return apiClient.post('/customers/register', payload);
  },

  async updateWorkerAvailability(workerId, isAvailable) {
    if (isMock) return mockStore.updateWorker(workerId, { isAvailableNow: isAvailable });
    return apiClient.patch(`/workers/${workerId}`, { isAvailableNow: isAvailable });
  },

  // Routes
  async getRoute(jobId, workerId) {
    if (isMock) return mockStore.getRoute(jobId, workerId);
    return apiClient.get('/route', { params: { jobId, workerId } });
  },

  // Reset helper for testing demo resets
  resetMockData() {
    if (isMock) mockStore.reseed();
  },
};
