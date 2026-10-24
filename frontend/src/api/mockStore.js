import { SEED_WORKERS, INITIAL_CUSTOMER } from './mockData';
import { JOB_STATUS, OFFER_STATUS } from '../types';
import { calcDistanceKm, calcEtaMinutes, computeTrust } from '../lib/utils';
import { storage } from '../lib/storage';

const WORKERS_KEY = 'rb_mock_workers_v1';
const JOBS_KEY = 'rb_mock_jobs_v1';
const OFFERS_KEY = 'rb_mock_offers_v1';
const REVIEWS_KEY = 'rb_mock_reviews_v1';
const SOS_KEY = 'rb_mock_sos_v1';
const REPORTS_KEY = 'rb_mock_reports_v1';

// Helper to simulate network latency for realistic feel
const delay = (ms = 220) => new Promise((resolve) => setTimeout(resolve, ms));

function getWorkers() {
  const existing = storage.get(WORKERS_KEY);
  if (!existing || !Array.isArray(existing) || existing.length === 0) {
    storage.set(WORKERS_KEY, SEED_WORKERS);
    return SEED_WORKERS;
  }
  return existing;
}

function saveWorkers(workers) {
  storage.set(WORKERS_KEY, workers);
}

function getJobs() {
  return storage.get(JOBS_KEY, []);
}

function saveJobs(jobs) {
  storage.set(JOBS_KEY, jobs);
}

function getOffers() {
  return storage.get(OFFERS_KEY, []);
}

function saveOffers(offers) {
  storage.set(OFFERS_KEY, offers);
}

export const mockStore = {
  // Reset or reseed data
  reseed() {
    storage.set(WORKERS_KEY, SEED_WORKERS);
    storage.set(JOBS_KEY, []);
    storage.set(OFFERS_KEY, []);
    storage.set(REVIEWS_KEY, []);
    storage.set(SOS_KEY, []);
    storage.set(REPORTS_KEY, []);
  },

  // Workers
  async getWorkers() {
    await delay();
    return getWorkers();
  },

  async updateWorker(uid, updates) {
    await delay(100);
    const workers = getWorkers();
    const index = workers.findIndex((w) => w.uid === uid);
    if (index !== -1) {
      workers[index] = { ...workers[index], ...updates };
      saveWorkers(workers);
      return workers[index];
    }
    return null;
  },

  // POST /jobs
  async createJob(jobPayload) {
    await delay();
    const jobs = getJobs();
    const newJob = {
      id: `job_${Date.now()}`,
      customerId: jobPayload.customerId || INITIAL_CUSTOMER.uid,
      customerName: jobPayload.customerName || INITIAL_CUSTOMER.name,
      customerPhone: jobPayload.customerPhone || INITIAL_CUSTOMER.phone,
      category: jobPayload.category,
      description: jobPayload.description,
      mode: jobPayload.mode || 'on_demand', // 'on_demand' or 'scheduled'
      scheduledAt: jobPayload.scheduledAt || null,
      location: jobPayload.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
      budget: jobPayload.budget ? Number(jobPayload.budget) : null,
      status: JOB_STATUS.OPEN,
      acceptedWorkerId: null,
      finalPrice: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    jobs.unshift(newJob);
    saveJobs(jobs);
    return newJob;
  },

  // GET /jobs/{id}
  async getJob(jobId) {
    await delay(150);
    const jobs = getJobs();
    const job = jobs.find((j) => j.id === jobId);
    if (!job) {
      throw new Error(`Job not found: ${jobId}`);
    }
    return job;
  },

  // GET /jobs/nearby
  async getNearbyJobs(workerCoords = { lat: 19.2812, lng: 72.8697 }, radiusKm = 10) {
    await delay();
    const jobs = getJobs();
    // Filter open or negotiating jobs
    return jobs
      .filter((j) => [JOB_STATUS.OPEN, JOB_STATUS.NEGOTIATING].includes(j.status))
      .map((j) => {
        const distanceKm = calcDistanceKm(
          workerCoords.lat,
          workerCoords.lng,
          j.location.lat,
          j.location.lng
        );
        const etaMinutes = calcEtaMinutes(distanceKm);
        return {
          ...j,
          distanceKm,
          etaMinutes,
          within30: etaMinutes <= 30,
        };
      })
      .filter((j) => j.distanceKm <= radiusKm)
      .sort((a, b) => a.distanceKm - b.distanceKm);
  },

  // GET /workers/match?jobId=
  async getMatchedWorkers(jobId) {
    await delay(250);
    const jobs = getJobs();
    const job = jobs.find((j) => j.id === jobId);
    if (!job) throw new Error('Job not found for matching');

    const workers = getWorkers();
    const jobLat = job.location.lat;
    const jobLng = job.location.lng;

    // Filter rule: verified ONLY, available now, skill matched, within worker radius
    const matched = workers
      .filter((w) => {
        if (!w.verified) return false; // PRD F21: Unverified workers NEVER appear in matching
        if (!w.isAvailableNow) return false;
        if (!w.skills.includes(job.category)) return false;
        const distance = calcDistanceKm(jobLat, jobLng, w.location.lat, w.location.lng);
        return distance <= (w.serviceRadiusKm || 8);
      })
      .map((w) => {
        const distanceKm = calcDistanceKm(jobLat, jobLng, w.location.lat, w.location.lng);
        const etaMinutes = calcEtaMinutes(distanceKm);
        const rate = w.rates[job.category] || 350;
        const trust = computeTrust(w);

        // PRD F9: Weighted Rank Formula:
        // Distance 40%, Rating 30%, Price vs Budget 20%, Jobs done 10%
        const distanceScore = Math.max(0, 1 - distanceKm / 10);
        const ratingScore = (w.rating || 4.5) / 5;
        let priceScore = 0.8;
        if (job.budget && job.budget > 0) {
          const diff = Math.abs(rate - job.budget);
          priceScore = Math.max(0, 1 - diff / job.budget);
        }
        const jobsScore = Math.min(1, (w.jobsDone || 0) / 100);

        const rankScore =
          distanceScore * 0.4 +
          ratingScore * 0.3 +
          priceScore * 0.2 +
          jobsScore * 0.1;

        return {
          uid: w.uid,
          name: w.name,
          phone: w.phone,
          avatarUrl: w.avatarUrl,
          skills: w.skills,
          rate,
          rating: w.rating,
          jobsDone: w.jobsDone,
          verified: w.verified,
          distanceKm,
          etaMinutes,
          within30: etaMinutes <= 30, // PRD F10
          trustScore: trust.score,
          trustTier: trust.tier,
          badgeColor: trust.badgeColor,
          rankScore,
          about: w.about,
        };
      })
      .sort((a, b) => b.rankScore - a.rankScore);

    return matched;
  },

  // GET /offers?jobId=
  async getOffersForJob(jobId) {
    await delay(120);
    const offers = getOffers();
    return offers
      .filter((o) => o.jobId === jobId)
      .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
  },

  // POST /offers
  async createOffer({ jobId, workerId, price, by }) {
    await delay();
    const jobs = getJobs();
    const jobIndex = jobs.findIndex((j) => j.id === jobId);
    if (jobIndex === -1) throw new Error('Job not found');

    const offers = getOffers();
    const newOffer = {
      id: `off_${Date.now()}`,
      jobId,
      workerId,
      price: Number(price),
      by, // 'customer' or 'worker'
      status: OFFER_STATUS.PENDING,
      createdAt: new Date().toISOString(),
    };

    offers.push(newOffer);
    saveOffers(offers);

    // Update job status to negotiating if it was open
    if (jobs[jobIndex].status === JOB_STATUS.OPEN) {
      jobs[jobIndex].status = JOB_STATUS.NEGOTIATING;
      jobs[jobIndex].updatedAt = new Date().toISOString();
      saveJobs(jobs);
    }

    return newOffer;
  },

  // POST /offers/{id}/counter
  async counterOffer(offerId, { price, by }) {
    await delay();
    const offers = getOffers();
    const targetOffer = offers.find((o) => o.id === offerId);
    if (!targetOffer) throw new Error('Offer not found to counter');

    // PRD F14: Offers alternate turns: only the other party may counter
    if (targetOffer.by === by) {
      throw new Error(`You cannot counter your own offer. Awaiting response from ${by === 'customer' ? 'worker' : 'customer'}.`);
    }

    // Mark previous offer as superseded/rejected
    targetOffer.status = OFFER_STATUS.REJECTED;

    // Create new counter offer
    const counter = {
      id: `off_${Date.now()}`,
      jobId: targetOffer.jobId,
      workerId: targetOffer.workerId,
      price: Number(price),
      by, // Alternated party
      status: OFFER_STATUS.PENDING,
      createdAt: new Date().toISOString(),
    };

    offers.push(counter);
    saveOffers(offers);
    return counter;
  },

  // POST /offers/{id}/accept
  async acceptOffer(offerId) {
    await delay();
    const offers = getOffers();
    const targetOffer = offers.find((o) => o.id === offerId);
    if (!targetOffer) throw new Error('Offer not found');

    // PRD F15: Accepting an offer sets the worker, the final price, status to accepted,
    // and auto-rejects all other pending offers on that job!
    const jobs = getJobs();
    const jobIndex = jobs.findIndex((j) => j.id === targetOffer.jobId);
    if (jobIndex === -1) throw new Error('Job not found');

    targetOffer.status = OFFER_STATUS.ACCEPTED;

    // Auto-reject any other pending offers on this job
    offers.forEach((o) => {
      if (o.jobId === targetOffer.jobId && o.id !== targetOffer.id && o.status === OFFER_STATUS.PENDING) {
        o.status = OFFER_STATUS.REJECTED;
      }
    });
    saveOffers(offers);

    jobs[jobIndex].status = JOB_STATUS.ACCEPTED;
    jobs[jobIndex].acceptedWorkerId = targetOffer.workerId;
    jobs[jobIndex].finalPrice = targetOffer.price;
    jobs[jobIndex].updatedAt = new Date().toISOString();
    saveJobs(jobs);

    return { offer: targetOffer, job: jobs[jobIndex] };
  },

  // POST /offers/{id}/reject
  async rejectOffer(offerId) {
    await delay();
    const offers = getOffers();
    const targetOffer = offers.find((o) => o.id === offerId);
    if (!targetOffer) throw new Error('Offer not found');

    targetOffer.status = OFFER_STATUS.REJECTED;
    saveOffers(offers);

    return targetOffer;
  },

  // POST /jobs/{id}/start
  async startJob(jobId) {
    await delay();
    const jobs = getJobs();
    const job = jobs.find((j) => j.id === jobId);
    if (!job) throw new Error('Job not found');

    if (job.status !== JOB_STATUS.ACCEPTED) {
      throw new Error(`Cannot start job from current status: ${job.status}`);
    }

    job.status = JOB_STATUS.IN_PROGRESS;
    job.startedAt = new Date().toISOString();
    job.updatedAt = new Date().toISOString();
    saveJobs(jobs);
    return job;
  },

  // POST /jobs/{id}/complete
  async completeJob(jobId) {
    await delay();
    const jobs = getJobs();
    const job = jobs.find((j) => j.id === jobId);
    if (!job) throw new Error('Job not found');

    if (job.status !== JOB_STATUS.IN_PROGRESS) {
      throw new Error(`Cannot complete job from current status: ${job.status}`);
    }

    job.status = JOB_STATUS.COMPLETED;
    job.completedAt = new Date().toISOString();
    job.updatedAt = new Date().toISOString();
    saveJobs(jobs);

    // Update worker jobsDone
    if (job.acceptedWorkerId) {
      const workers = getWorkers();
      const worker = workers.find((w) => w.uid === job.acceptedWorkerId);
      if (worker) {
        worker.jobsDone = (worker.jobsDone || 0) + 1;
        saveWorkers(workers);
      }
    }

    return job;
  },

  // POST /reviews
  async submitReview({ jobId, workerId, rating, comment }) {
    await delay();
    const reviews = storage.get(REVIEWS_KEY, []);
    const newReview = {
      id: `rev_${Date.now()}`,
      jobId,
      workerId,
      rating: Number(rating),
      comment: comment || '',
      createdAt: new Date().toISOString(),
    };
    reviews.push(newReview);
    storage.set(REVIEWS_KEY, reviews);

    // Update worker rolling average rating (PRD F23)
    const workers = getWorkers();
    const worker = workers.find((w) => w.uid === workerId);
    if (worker) {
      const totalRatings = reviews.filter((r) => r.workerId === workerId);
      const sum = totalRatings.reduce((acc, curr) => acc + curr.rating, 0);
      worker.rating = Math.round((sum / totalRatings.length) * 10) / 10;
      saveWorkers(workers);
    }

    return newReview;
  },

  // POST /sos
  async triggerSos({ jobId, location }) {
    await delay(150);
    const alerts = storage.get(SOS_KEY, []);
    const alert = {
      id: `sos_${Date.now()}`,
      jobId,
      location: location || { lat: 19.2812, lng: 72.8697 },
      timestamp: new Date().toISOString(),
    };
    alerts.push(alert);
    storage.set(SOS_KEY, alerts);
    return { success: true, alertId: alert.id, timestamp: alert.timestamp };
  },

  // POST /reports
  async reportUser({ jobId, reportedUserId, reason }) {
    await delay(150);
    const reports = storage.get(REPORTS_KEY, []);
    const rep = {
      id: `rep_${Date.now()}`,
      jobId,
      reportedUserId,
      reason,
      createdAt: new Date().toISOString(),
    };
    reports.push(rep);
    storage.set(REPORTS_KEY, reports);

    // Increment penalty count on reported worker
    const workers = getWorkers();
    const worker = workers.find((w) => w.uid === reportedUserId);
    if (worker) {
      worker.reportCount = (worker.reportCount || 0) + 1;
      saveWorkers(workers);
    }

    return { success: true, reportId: rep.id };
  },
};
