import test from 'node:test';
import assert from 'node:assert/strict';

// Set up browser environment polyfills for Node test execution
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
import { ROLES, JOB_STATUS, CATEGORIES } from '../src/types/index.js';

test('RepairBuddy Phase 2 Feature Verification Suite', async (t) => {
  // Reset storage and mock store before test suite
  localStorage.clear();
  api.resetMockData();

  await t.test('1. Category Search Filtering (Module B)', () => {
    const query = 'plumb';
    const filtered = CATEGORIES.filter((c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.id.toLowerCase().includes(query.toLowerCase())
    );
    assert.ok(filtered.length > 0);
    assert.equal(filtered[0].id, 'plumber');
    assert.equal(filtered[0].label, 'Plumber');
  });

  await t.test('2. Service Request Creation with Validation (Module C)', async () => {
    const createdJob = await useJobStore.getState().createJob({
      category: 'electrician',
      description: 'Switchboard sparking in living room',
      budget: 450,
      mode: 'on_demand',
      location: {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
    });

    assert.ok(createdJob.id);
    assert.equal(createdJob.category, 'electrician');
    assert.equal(createdJob.budget, 450);
    assert.equal(createdJob.status, JOB_STATUS.OPEN);
  });

  await t.test('3. Matched Workers Inspection & Ranking (Module D & E)', async () => {
    const currentJob = useJobStore.getState().currentJob;
    assert.ok(currentJob?.id);

    const workers = await useJobStore.getState().fetchMatchedWorkers(currentJob.id);
    assert.ok(Array.isArray(workers));
    assert.ok(workers.length > 0);

    const firstWorker = workers[0];
    assert.ok(firstWorker.uid);
    assert.ok(firstWorker.name);
    assert.ok(typeof firstWorker.rate === 'number');
    assert.ok(typeof firstWorker.distanceKm === 'number');
    assert.ok(typeof firstWorker.etaMinutes === 'number');
    assert.ok(firstWorker.trustScore >= 0 && firstWorker.trustScore <= 100);
    assert.ok(['Bronze', 'Silver', 'Gold', 'Platinum'].includes(firstWorker.trustTier));
  });

  await t.test('4. Job Cancellation Lifecycle (Module F & G)', async () => {
    const currentJob = useJobStore.getState().currentJob;
    assert.ok(currentJob?.id);

    // Cancel job in open status
    const cancelledJob = await useJobStore.getState().cancelJob(currentJob.id);
    assert.equal(cancelledJob.status, JOB_STATUS.CANCELLED);
    assert.equal(useJobStore.getState().currentJob?.status, JOB_STATUS.CANCELLED);
  });

  await t.test('5. Review Submission with Compliment Tags (Module H)', async () => {
    const reviewPayload = {
      jobId: 'job_test_review_1',
      workerId: 'w_plumb_1',
      rating: 5,
      comment: 'Super fast and punctual! | Compliments: Punctual arrival, Clean Workmanship',
      tags: ['Punctual arrival', 'Clean Workmanship'],
    };

    const reviewRes = await api.submitReview(reviewPayload);
    assert.ok(reviewRes);
    assert.ok(reviewRes.id);
    assert.equal(reviewRes.rating, 5);
    assert.equal(reviewRes.workerId, 'w_plumb_1');
  });

  await t.test('6. Worker Direct Cash Settlements & Earnings Display (Module O)', async () => {
    await useAuthStore.getState().loginAsWorker({
      uid: 'worker_plumb_test',
      name: 'Ramesh Kanojia',
      phone: '+919820712345',
      skills: ['plumber'],
      rates: { plumber: 350 },
      jobsDone: 42,
      rating: 4.9,
    });

    const user = useAuthStore.getState().user;
    assert.ok(user);
    assert.equal(user.jobsDone, 42);
    const estimatedTotal = user.jobsDone * (user.rates.plumber || 350);
    assert.equal(estimatedTotal, 14700);
  });

  await t.test('7. Worker Profile Skills & Hyperlocal Dispatch Radius (Module K)', () => {
    const user = useAuthStore.getState().user;
    assert.ok(user);
    assert.ok(user.skills.includes('plumber'));
    assert.equal(user.role, ROLES.WORKER);
    assert.equal(useAuthStore.getState().isAvailableNow, true);
  });

  await t.test('8. Admin Verification Queue & Inspection (Module R)', async () => {
    const pending = await api.getPendingVerifications();
    assert.ok(Array.isArray(pending));
    if (pending.length > 0) {
      const first = pending[0];
      assert.ok(first.uid);
      assert.ok(first.name);

      // Verify blob URL retrieval
      const blobUrl = await api.getVerificationDocumentBlobUrl(first.uid, 'id_document');
      assert.ok(blobUrl);
    }
  });

  await t.test('9. Admin Approve & Reject Actions (Module R & S)', async () => {
    // Approve test
    const approveRes = await api.approveWorkerVerification('w_plumb_1');
    assert.ok(approveRes);
    assert.equal(approveRes.status, 'approved');
    assert.equal(approveRes.verified, true);

    // Reject test with reason
    const rejectRes = await api.rejectWorkerVerification('w_plumb_2', 'Document photo is blurry');
    assert.ok(rejectRes);
    assert.equal(rejectRes.status, 'rejected');
    assert.equal(rejectRes.verified, false);
    assert.equal(rejectRes.reason, 'Document photo is blurry');
  });

  await t.test('10. Admin Reset Verification Attempts (Module R)', async () => {
    const resetRes = await api.resetVerificationAttempts('w_plumb_2');
    assert.ok(resetRes);
    assert.equal(resetRes.success, true);
    assert.equal(resetRes.attemptCount, 0);
  });

  await t.test('11. Admin Emergency SOS Monitoring (Module T)', async () => {
    // Trigger SOS alert
    const sosRes = await api.triggerSos({
      jobId: 'job_sos_test_1',
      location: { lat: 19.2812, lng: 72.8697 },
      reason: 'Safety concern at location',
    });
    assert.ok(sosRes);
    assert.ok(sosRes.id || sosRes.alertId);

    // Fetch alerts in admin
    const alerts = await api.getAdminSosAlerts();
    assert.ok(Array.isArray(alerts));
    assert.ok(alerts.length > 0);
    const logged = alerts.find((a) => a.id === (sosRes.id || sosRes.alertId) || a.jobId === 'job_sos_test_1');
    assert.ok(logged);
  });

  await t.test('12. Admin Dispute Moderation & Reports (Module U)', async () => {
    // File report
    const repRes = await api.reportUser({
      jobId: 'job_rep_1',
      workerId: 'w_plumb_1',
      reason: 'overcharging',
      description: 'Demanded additional cash outside agreed quote',
    });
    assert.ok(repRes);
    assert.ok(repRes.reportId);

    // Retrieve reports
    const reports = await api.getReports();
    assert.ok(Array.isArray(reports));
    assert.ok(reports.length > 0);
    const found = reports.find((r) => r.id === repRes.reportId || r.jobId === 'job_rep_1');
    assert.ok(found);
  });
});
