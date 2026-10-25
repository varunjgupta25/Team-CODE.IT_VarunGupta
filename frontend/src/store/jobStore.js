import { create } from 'zustand';
import { api } from '../api';
import { useToastStore } from './toastStore';

export const useJobStore = create((set, get) => ({
  currentJob: null,
  matchedWorkers: [],
  offers: [],
  nearbyJobs: [],
  isLoading: false,
  isMatchingLoading: false,
  isOffersLoading: false,
  pollingInterval: null,

  // Set or update current job
  setCurrentJob: (job) => set({ currentJob: job }),

  // POST /jobs
  createJob: async (jobData) => {
    set({ isLoading: true });
    try {
      const newJob = await api.createJob(jobData);
      set({ currentJob: newJob, isLoading: false });
      useToastStore.getState().success('Job posted successfully! Finding nearest verified workers...');
      return newJob;
    } catch (err) {
      set({ isLoading: false });
      useToastStore.getState().error(err.message || 'Failed to create job');
      throw err;
    }
  },

  // GET /jobs/{id}
  fetchJob: async (jobId) => {
    try {
      const job = await api.getJob(jobId);
      set({ currentJob: job });
      return job;
    } catch (err) {
      console.warn('Error fetching job:', err);
      return null;
    }
  },

  // GET /workers/match?jobId=
  fetchMatchedWorkers: async (jobId) => {
    set({ isMatchingLoading: true });
    try {
      const workers = await api.getMatchedWorkers(jobId);
      set({ matchedWorkers: workers, isMatchingLoading: false });
      return workers;
    } catch {
      set({ isMatchingLoading: false });
      useToastStore.getState().error('Could not match workers at this time');
      return [];
    }
  },

  // GET /offers?jobId=
  fetchOffers: async (jobId) => {
    try {
      const offers = await api.getOffers(jobId);
      set({ offers });
      return offers;
    } catch (err) {
      console.warn('Error fetching offers:', err);
      return [];
    }
  },

  // GET /jobs/nearby
  fetchNearbyJobs: async (coords) => {
    set({ isLoading: true });
    try {
      const raw = await api.getNearbyJobs(coords);
      const jobs = (raw || []).map((item) => {
        if (item && item.job) {
          return {
            ...item.job,
            distanceKm: item.distanceKm,
            etaMinutes: item.etaMinutes,
            within30: item.within30 ?? (item.etaMinutes <= 30),
          };
        }
        return item;
      });
      set({ nearbyJobs: jobs, isLoading: false });
      return jobs;
    } catch (err) {
      set({ isLoading: false });
      console.warn('Error fetching nearby jobs:', err);
      return [];
    }
  },

  // POST /offers
  createOffer: async ({ jobId, workerId, price, by }) => {
    try {
      const offer = await api.createOffer({ jobId, workerId, price, by });
      await get().fetchOffers(jobId);
      await get().fetchJob(jobId);
      useToastStore.getState().success(by === 'customer' ? 'Offer sent to worker!' : 'Quote submitted!');
      return offer;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to submit offer');
      throw err;
    }
  },

  // POST /offers/{id}/counter
  counterOffer: async (offerId, { price, by }) => {
    const { currentJob } = get();
    try {
      const counter = await api.counterOffer(offerId, { price, by });
      if (currentJob?.id) {
        await get().fetchOffers(currentJob.id);
        await get().fetchJob(currentJob.id);
      }
      useToastStore.getState().info(`Counter offer of ₹${price} sent!`);
      return counter;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to send counter offer');
      throw err;
    }
  },

  // POST /offers/{id}/accept
  acceptOffer: async (offerId) => {
    const { currentJob } = get();
    try {
      const res = await api.acceptOffer(offerId);
      if (currentJob?.id) {
        await get().fetchOffers(currentJob.id);
        await get().fetchJob(currentJob.id);
      }
      useToastStore.getState().success('Offer accepted! Worker is on the way.');
      return res;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to accept offer');
      throw err;
    }
  },

  // POST /offers/{id}/reject
  rejectOffer: async (offerId) => {
    const { currentJob } = get();
    try {
      const res = await api.rejectOffer(offerId);
      if (currentJob?.id) {
        await get().fetchOffers(currentJob.id);
        await get().fetchJob(currentJob.id);
      }
      useToastStore.getState().info('Offer declined');
      return res;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to reject offer');
      throw err;
    }
  },

  // POST /jobs/{id}/start
  startJob: async (jobId) => {
    try {
      const updatedJob = await api.startJob(jobId);
      set({ currentJob: updatedJob });
      useToastStore.getState().success('Job started! Timer running.');
      return updatedJob;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to start job');
      throw err;
    }
  },

  // POST /jobs/{id}/complete
  completeJob: async (jobId) => {
    try {
      const updatedJob = await api.completeJob(jobId);
      set({ currentJob: updatedJob });
      useToastStore.getState().success('Job completed successfully!');
      return updatedJob;
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to complete job');
      throw err;
    }
  },

  // POST /sos
  triggerSos: async (jobId, location) => {
    try {
      const res = await api.triggerSos({ jobId, location });
      useToastStore.getState().error('EMERGENCY SOS ALERT RECORDED. Safety dispatch alerted.');
      return res;
    } catch (err) {
      useToastStore.getState().error('SOS trigger failed. Call local emergency 112 directly!');
      throw err;
    }
  },

  // POST /reports
  reportUser: async (jobId, reportedUserId, reason) => {
    try {
      const res = await api.reportUser({ jobId, reportedUserId, reason });
      useToastStore.getState().info('Report submitted for review.');
      return res;
    } catch (err) {
      useToastStore.getState().error('Failed to submit report');
      throw err;
    }
  },

  // 5-second polling implementation for job status and offers
  startPolling: (jobId) => {
    get().stopPolling();
    if (!jobId) return;

    // Immediately poll once
    get().fetchJob(jobId);
    get().fetchOffers(jobId);

    const interval = setInterval(() => {
      get().fetchJob(jobId);
      get().fetchOffers(jobId);
    }, 5000);

    set({ pollingInterval: interval });
  },

  stopPolling: () => {
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
      set({ pollingInterval: null });
    }
  },
}));
