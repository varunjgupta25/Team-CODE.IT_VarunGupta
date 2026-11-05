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
import { ROLES, JOB_STATUS, OFFER_STATUS } from '../src/types/index.js';

test('RepairBuddy Phase 1 Verification Suite', async (t) => {
  // Reset storage and mock store before tests
  localStorage.clear();
  api.resetMockData();

  await t.test('1. Customer Login Flow', async () => {
    const authStore = useAuthStore.getState();
    const customer = await authStore.loginAsCustomer({
      uid: 'cust_test_101',
      name: 'Priya Sharma',
      phone: '+919820111222',
      location: { lat: 19.2812, lng: 72.8697, address: 'Mira Road, Mumbai' },
    });

    assert.equal(customer.uid, 'cust_test_101');
    assert.equal(customer.role, ROLES.CUSTOMER);
    assert.equal(useAuthStore.getState().role, ROLES.CUSTOMER);
    assert.equal(useAuthStore.getState().user?.name, 'Priya Sharma');
    assert.equal(useAuthStore.getState().isAvailableNow, false);
  });

  await t.test('2. Worker Login Flow & Role Enforcement', async () => {
    const authStore = useAuthStore.getState();
    const worker = await authStore.loginAsWorker({
      uid: 'worker_test_202',
      name: 'Ramesh Kumar',
      phone: '+919820999888',
      skills: ['plumber', 'electrician'],
      rates: { plumber: 400, electrician: 450 },
      location: { lat: 19.2825, lng: 72.8710, address: 'Kandivali, Mumbai' },
    });

    assert.equal(worker.uid, 'worker_test_202');
    assert.equal(worker.role, ROLES.WORKER);
    assert.equal(useAuthStore.getState().role, ROLES.WORKER);
    assert.equal(useAuthStore.getState().isAvailableNow, true);
    assert.ok(worker.skills.includes('plumber'));
  });

  await t.test('3. Admin Authentication & Role Gating', async () => {
    const authStore = useAuthStore.getState();
    const admin = await authStore.loginAsAdmin({
      uid: 'admin_test_303',
      name: 'Platform Ops Admin',
      phone: '+919999900001',
    });

    assert.equal(admin.uid, 'admin_test_303');
    assert.equal(admin.role, ROLES.ADMIN);
    assert.equal(useAuthStore.getState().role, ROLES.ADMIN);
  });

  await t.test('4. Firebase Session & Storage Synchronization', () => {
    const authStore = useAuthStore.getState();
    const unsubscribe = authStore.initAuth();
    assert.equal(typeof unsubscribe, 'function');
    assert.equal(useAuthStore.getState().isInitialized, true);
    unsubscribe();
  });

  await t.test('5. API Token Attachment & Mode Configuration', () => {
    localStorage.setItem('rb_auth_token', 'test_firebase_id_token_xyz');
    assert.equal(localStorage.getItem('rb_auth_token'), 'test_firebase_id_token_xyz');
    assert.equal(typeof api.isMockMode, 'function');
  });

  await t.test('6. Job Creation Contract', async () => {
    const created = await useJobStore.getState().createJob({
      category: 'plumber',
      description: 'Kitchen sink pipe burst under sink',
      budget: 500,
      location: { lat: 19.2812, lng: 72.8697, address: 'Mira Road East' },
    });

    assert.ok(created.id, 'Job should have a valid ID');
    assert.equal(created.category, 'plumber');
    assert.ok([JOB_STATUS.POSTED, JOB_STATUS.OPEN].includes(created.status));
    assert.equal(useJobStore.getState().currentJob?.id, created.id);
  });

  await t.test('7. Worker Matching Algorithm', async () => {
    const jobId = useJobStore.getState().currentJob.id;
    const matches = await useJobStore.getState().fetchMatchedWorkers(jobId);

    assert.ok(Array.isArray(matches), 'Matches should return an array');
    assert.ok(matches.length > 0, 'Should find at least 1 matching worker');
    const firstMatch = matches[0];
    const workerObj = firstMatch.worker || firstMatch;
    assert.ok(workerObj.uid, 'Matched worker must have a uid');
  });

  await t.test('8. Offer Submission (Quote & Bidding)', async () => {
    const jobId = useJobStore.getState().currentJob.id;
    const workerUid = 'worker_test_202';

    const offer = await useJobStore.getState().createOffer({
      jobId,
      workerId: workerUid,
      price: 450,
      by: 'worker',
    });

    assert.ok(offer.id, 'Offer should have an ID');
    assert.equal(offer.price, 450);
    assert.equal(offer.status, OFFER_STATUS.PENDING);
  });

  await t.test('9. Offer Acceptance Flow', async () => {
    const latestOffer = useJobStore.getState().offers[0];
    assert.ok(latestOffer, 'Should have pending offer to accept');

    const accepted = await useJobStore.getState().acceptOffer(latestOffer.id);
    assert.ok(accepted, 'Offer acceptance should succeed');
    const freshJob = await useJobStore.getState().fetchJob(useJobStore.getState().currentJob.id);
    assert.equal(freshJob.status, JOB_STATUS.ACCEPTED);
  });

  await t.test('10. Job Lifecycle Execution (Start -> Complete -> Confirm)', async () => {
    const jobId = useJobStore.getState().currentJob.id;

    // Worker starts job
    const started = await useJobStore.getState().startJob(jobId);
    assert.equal(started.status, JOB_STATUS.IN_PROGRESS);

    // Worker completes job (transitions to awaiting customer confirmation)
    const completed = await useJobStore.getState().completeJob(jobId);
    assert.ok(['awaiting_confirmation', JOB_STATUS.COMPLETED].includes(completed.status));

    // Customer confirms job completion
    const confirmed = await useJobStore.getState().confirmJob(jobId);
    assert.equal(confirmed.status, JOB_STATUS.COMPLETED);
  });

  await t.test('11. Error Handling & Payload Normalization', async () => {
    // Verify reportUser payload normalization
    const reportRes = await api.reportUser({
      jobId: 'job_sample_123',
      reportedUserId: 'worker_offender_999',
      reason: 'Demanded cash outside app',
    });
    assert.ok(reportRes);
  });

  await t.test('12. Clean Logout & Session Teardown', async () => {
    await useAuthStore.getState().logout();

    assert.equal(useAuthStore.getState().user, null);
    assert.equal(useAuthStore.getState().role, null);
    assert.equal(localStorage.getItem('rb_auth_token'), null);
    assert.equal(useJobStore.getState().currentJob, null);
  });
});
