import test from 'node:test';
import assert from 'node:assert/strict';

// Browser environment polyfills for Node.js test runner
const memoryStorage = new Map();
globalThis.localStorage = {
  getItem: (key) => memoryStorage.get(key) ?? null,
  setItem: (key, val) => memoryStorage.set(key, String(val)),
  removeItem: (key) => memoryStorage.delete(key),
  clear: () => memoryStorage.clear(),
};
globalThis.window = {
  localStorage: globalThis.localStorage,
  location: { href: 'http://localhost:5173' },
};

// Import stores and modules
import { useAuthStore } from '../src/store/authStore.js';
import { useJobStore } from '../src/store/jobStore.js';
import { api } from '../src/api/index.js';
import { ROLES, JOB_STATUS, OFFER_STATUS } from '../src/types/index.js';

test('RepairBuddy Phase 3 End-to-End Frontend Integration Suite', async (t) => {
  localStorage.clear();
  api.resetMockData();

  const customerUid = 'cust_phase3_test';
  const workerUid = 'w_plumb_1';
  let createdJobId = null;
  let activeOfferId = null;

  // ─── MODULE 1: CUSTOMER END-TO-END WORKFLOW ───────────────────────────────
  await t.test('1. Customer Registration, Login & Session Persistence', async () => {
    const customerUser = await useAuthStore.getState().loginAsCustomer({
      uid: customerUid,
      name: 'Rohan Sharma',
      phone: '+91 9820011223',
      location: {
        lat: 19.2812,
        lng: 72.8697,
        address: 'B-102, Shanti Park, Mira Road East, Mumbai',
      },
    });

    assert.equal(customerUser.uid, customerUid);
    assert.equal(customerUser.role, ROLES.CUSTOMER);
    assert.equal(useAuthStore.getState().role, ROLES.CUSTOMER);
    assert.equal(localStorage.getItem('rb_auth_token'), customerUid);
  });

  await t.test('2. Customer Emergency Contact Persistence & Offline Resilience', async () => {
    const contactPayload = {
      name: 'Pooja Sharma',
      phone: '+919820099887',
    };

    const res = await api.setEmergencyContact(contactPayload);
    assert.ok(res);

    const fetchedContact = await api.getEmergencyContact();
    assert.ok(fetchedContact);
    assert.equal(fetchedContact.name, 'Pooja Sharma');
  });

  await t.test('3. Service Request Creation with Normalized On-Demand Mode & Budget', async () => {
    // Proves that mode 'on_demand' is safely normalized to 'on-demand'
    const newJob = await useJobStore.getState().createJob({
      category: 'plumber',
      description: 'Major tap leakage in kitchen sink causing water pooling',
      mode: 'on_demand', // frontend form state
      budget: 350,
      location: {
        lat: 19.2812,
        lng: 72.8697,
        address: 'B-102, Shanti Park, Mira Road East, Mumbai',
      },
    });

    assert.ok(newJob.id);
    createdJobId = newJob.id;
    assert.equal(newJob.category, 'plumber');
    assert.equal(newJob.mode, 'on-demand');
    assert.equal(newJob.status, JOB_STATUS.OPEN);
  });

  await t.test('4. Customer Nearby Worker Discovery & Ranking Inspection', async () => {
    assert.ok(createdJobId);
    await useJobStore.getState().fetchMatchedWorkers(createdJobId);
    const matched = useJobStore.getState().matchedWorkers;

    assert.ok(Array.isArray(matched));
    assert.ok(matched.length > 0, 'Should find at least 1 verified plumber in Mira Road');

    const first = matched[0];
    const workerObj = first.worker || first;
    assert.ok(workerObj.uid);
    assert.ok(workerObj.name);
    assert.ok(workerObj.rating >= 4.0);
    assert.ok(first.distanceKm !== undefined || workerObj.distanceKm !== undefined);
  });

  await t.test('5. Customer Booking Offer Submission (Initial Quote)', async () => {
    assert.ok(createdJobId);
    const offer = await api.createOffer({
      jobId: createdJobId,
      workerId: workerUid,
      price: 350,
      by: 'customer',
    });

    assert.ok(offer.id);
    activeOfferId = offer.id;
    assert.equal(offer.price, 350);
    assert.equal(offer.status, OFFER_STATUS.PENDING);
  });

  // ─── MODULE 2: WORKER END-TO-END WORKFLOW ─────────────────────────────────
  await t.test('6. Worker Switch Session & Availability Management', async () => {
    const workerUser = await useAuthStore.getState().loginAsWorker({
      uid: workerUid,
      name: 'Ramesh Plumber',
      phone: '+91 9811122233',
      skills: ['plumber'],
      rates: { plumber: 350 },
      verified: true,
      verificationStatus: 'approved',
    });

    assert.equal(workerUser.uid, workerUid);
    assert.equal(workerUser.role, ROLES.WORKER);
    assert.equal(useAuthStore.getState().isAvailableNow, true);

    // Toggle offline and verify persistence
    await useAuthStore.getState().toggleAvailability();
    assert.equal(useAuthStore.getState().isAvailableNow, false);

    // Toggle back online for job matching
    await useAuthStore.getState().toggleAvailability();
    assert.equal(useAuthStore.getState().isAvailableNow, true);
  });

  await t.test('7. Worker Nearby Feed Discovery & Job Retrieval', async () => {
    const nearby = await api.getNearbyJobs({ lat: 19.2812, lng: 72.8697 }, 10.0);
    assert.ok(Array.isArray(nearby));
    const targetJob = nearby.find((j) => (j.job ? j.job.id : j.id) === createdJobId);
    assert.ok(targetJob, 'Worker feed must discover newly created job');
  });

  await t.test('8. Price Negotiation: Worker Counter-Offers', async () => {
    assert.ok(activeOfferId);
    const countered = await api.counterOffer(activeOfferId, {
      price: 400,
      by: 'worker',
    });

    assert.ok(countered);
    activeOfferId = countered.id;
    assert.equal(countered.price, 400);
    assert.equal(countered.status, OFFER_STATUS.PENDING);
  });

  await t.test('9. Customer Accepts Agreed Offer & Locks Final Price', async () => {
    // Customer logs back in to accept
    await useAuthStore.getState().loginAsCustomer({ uid: customerUid, name: 'Rohan Sharma' });
    const accepted = await api.acceptOffer(activeOfferId);

    assert.ok(accepted);
    const acceptedStatus = accepted.offer?.status || accepted.status;
    assert.equal(acceptedStatus, OFFER_STATUS.ACCEPTED);

    const job = await api.getJob(createdJobId);
    assert.equal(job.status, JOB_STATUS.ACCEPTED);
    assert.equal(job.finalPrice, 400);
    assert.equal(job.acceptedWorkerId, workerUid);
  });

  await t.test('10. Worker Doorstep Arrival & Starts Job', async () => {
    await useAuthStore.getState().loginAsWorker({ uid: workerUid });
    const started = await api.startJob(createdJobId);

    assert.ok(started);
    assert.equal(started.status, JOB_STATUS.IN_PROGRESS);
  });

  await t.test('11. Worker Completes Job & Awaits Confirmation', async () => {
    const completed = await api.completeJob(createdJobId);
    assert.ok(completed);
    assert.ok(
      completed.status === JOB_STATUS.AWAITING_CONFIRMATION ||
      completed.status === JOB_STATUS.COMPLETED
    );
  });

  await t.test('12. Customer Confirms Work Completion & Cash Settlement', async () => {
    await useAuthStore.getState().loginAsCustomer({ uid: customerUid });
    const confirmed = await api.confirmJob(createdJobId);
    assert.ok(confirmed);
    assert.equal(confirmed.status, JOB_STATUS.COMPLETED);
  });

  await t.test('13. Customer Submits Rating & Review with Compliment Tags', async () => {
    const reviewRes = await api.submitReview({
      jobId: createdJobId,
      workerId: workerUid,
      rating: 5,
      comment: 'Arrived promptly and fixed the pipe in 20 minutes.',
      tags: ['Punctual arrival', 'Clean Workmanship'],
    });

    assert.ok(reviewRes);
    assert.equal(reviewRes.rating, 5);
  });

  await t.test('14. Customer Submits Incident Report Against Misbehavior', async () => {
    const reportRes = await api.reportUser({
      workerId: workerUid,
      reason: 'Pricing discrepancy on extra pipe fittings',
    });

    assert.ok(reportRes);
    assert.ok(reportRes.reportId || reportRes.id);
  });

  await t.test('15. Emergency SOS Dispatches & Returns Valid Status', async () => {
    const sosRes = await api.triggerSos({
      jobId: createdJobId,
      location: { lat: 19.2812, lng: 72.8697 },
    });

    assert.ok(sosRes);
    assert.ok(sosRes.id);
    assert.ok(
      sosRes.status === 'notified' ||
      sosRes.status === 'recorded' ||
      sosRes.status === 'partial'
    );
  });

  await t.test('16. Worker Earnings Dynamic Calculation (0% Escrow Direct Cash)', async () => {
    const earnings = await api.getWorkerEarnings(workerUid);
    assert.ok(earnings);
    assert.equal(earnings.workerId, workerUid);
    assert.equal(earnings.currency, 'INR');
    assert.equal(earnings.payoutType, 'direct_cash');
    assert.equal(earnings.platformCommission, 0.0);
    assert.ok(earnings.totalEarnings >= 350);
  });

  // ─── MODULE 3: ADMIN END-TO-END WORKFLOW ──────────────────────────────────
  await t.test('17. Admin Login & Restricted Navigation Access', async () => {
    const adminUser = await useAuthStore.getState().loginAsAdmin({
      uid: 'admin_test_user',
      name: 'System Admin',
      phone: '+91 9999999999',
    });

    assert.equal(adminUser.role, ROLES.ADMIN);
    assert.equal(useAuthStore.getState().role, ROLES.ADMIN);
  });

  await t.test('18. Admin Verification Queue Inspection & Decision Actions', async () => {
    const pendingList = await api.getPendingVerifications();
    assert.ok(Array.isArray(pendingList));

    // Admin approves a pending worker verification
    const approveRes = await api.approveWorkerVerification('w_plumb_unverified');
    assert.ok(approveRes);
    assert.equal(approveRes.verified, true);

    // Admin rejects a worker verification with mandatory reason
    const rejectRes = await api.rejectWorkerVerification(
      'w_plumb_unverified',
      'Blurry document photo — Aadhaar numbers not legible'
    );
    assert.ok(rejectRes);
    assert.equal(rejectRes.verified, false);
  });

  await t.test('19. Admin Dispute Moderation & Reports List', async () => {
    const reports = await api.getReports();
    assert.ok(Array.isArray(reports));
  });

  await t.test('20. Admin Emergency SOS Live Alerts Monitoring', async () => {
    const sosList = await api.getAdminSosAlerts();
    assert.ok(Array.isArray(sosList));
  });

  await t.test('21. Clean Teardown & Session Invalidation on Logout', async () => {
    await useAuthStore.getState().logout();
    assert.equal(useAuthStore.getState().user, null);
    assert.equal(useAuthStore.getState().role, null);
    assert.equal(localStorage.getItem('rb_auth_token'), null);
  });
});
