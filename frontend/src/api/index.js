import { apiClient } from './client';
import { mockStore } from './mockStore';

// Determines whether we run offline with mock store or connect to live FastAPI backend
const isMock = import.meta.env.VITE_USE_MOCK !== 'false';

console.info(`[RepairBuddy API] Running in ${isMock ? 'MOCK' : 'LIVE'} mode.`);

export const api = {
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
    return apiClient.get(`/offers`, { params: { jobId } });
  },

  async createOffer(payload) {
    if (isMock) return mockStore.createOffer(payload);
    return apiClient.post('/offers', payload);
  },

  async counterOffer(offerId, payload) {
    if (isMock) return mockStore.counterOffer(offerId, payload);
    return apiClient.post(`/offers/${offerId}/counter`, payload);
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

  // Reviews, SOS, Reports
  async submitReview(payload) {
    if (isMock) return mockStore.submitReview(payload);
    return apiClient.post('/reviews', payload);
  },

  async triggerSos(payload) {
    if (isMock) return mockStore.triggerSos(payload);
    return apiClient.post('/sos', payload);
  },

  async reportUser(payload) {
    if (isMock) return mockStore.reportUser(payload);
    return apiClient.post('/reports', payload);
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

  async approveWorkerVerification(workerUid) {
    if (isMock) return mockStore.approveWorkerVerification(workerUid);
    return apiClient.post(`/admin/verifications/${workerUid}/approve`);
  },

  async getPendingVerifications() {
    if (isMock) return mockStore.getPendingVerifications();
    try {
      const res = await apiClient.get('/admin/verifications/pending');
      return Array.isArray(res) ? res : (res?.data || []);
    } catch {
      return [];
    }
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
