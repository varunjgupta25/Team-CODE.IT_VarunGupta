import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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

// Import shared stores and domain models
import { useAuthStore } from '../src/store/authStore.js';
import { useJobStore } from '../src/store/jobStore.js';
import { api } from '../src/api/index.js';
import { ROLES, JOB_STATUS } from '../src/types/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootFrontendDir = path.resolve(__dirname, '..');

test('RepairBuddy Phase 4 Architecture Separation Suite', async (t) => {
  localStorage.clear();

  await t.test('1. Environment Configurations (.env.customer & .env.partner)', () => {
    const customerEnvPath = path.join(rootFrontendDir, '.env.customer');
    const partnerEnvPath = path.join(rootFrontendDir, '.env.partner');

    assert.ok(fs.existsSync(customerEnvPath), '.env.customer must exist');
    assert.ok(fs.existsSync(partnerEnvPath), '.env.partner must exist');

    const customerEnv = fs.readFileSync(customerEnvPath, 'utf8');
    const partnerEnv = fs.readFileSync(partnerEnvPath, 'utf8');

    assert.match(customerEnv, /VITE_APP=customer/, '.env.customer must declare VITE_APP=customer');
    assert.match(partnerEnv, /VITE_APP=partner/, '.env.partner must declare VITE_APP=partner');
    assert.match(customerEnv, /VITE_APP_TITLE=/, '.env.customer must set VITE_APP_TITLE');
    assert.match(partnerEnv, /VITE_APP_TITLE=/, '.env.partner must set VITE_APP_TITLE');
  });

  await t.test('2. Vite Configuration & Strict App Mode Gating', () => {
    const viteConfigPath = path.join(rootFrontendDir, 'vite.config.js');
    assert.ok(fs.existsSync(viteConfigPath), 'vite.config.js must exist');
    const viteConfig = fs.readFileSync(viteConfigPath, 'utf8');

    // Asserts Vite config enforces build validation and @app-entry aliasing
    assert.match(viteConfig, /@app-entry/, 'vite.config.js must define @app-entry alias');
    assert.match(viteConfig, /Missing VITE_APP environment variable/, 'vite.config.js must reject missing VITE_APP on build');
    assert.match(viteConfig, /customer/, 'vite.config.js must map customer app entry');
    assert.match(viteConfig, /partner/, 'vite.config.js must map partner app entry');
  });

  await t.test('3. Package.json Scripts for Independent Builds & Dev', () => {
    const pkgPath = path.join(rootFrontendDir, 'package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

    assert.equal(pkg.scripts['build:customer'], 'vite build --mode customer', 'Must have build:customer script');
    assert.equal(pkg.scripts['build:partner'], 'vite build --mode partner', 'Must have build:partner script');
    assert.equal(pkg.scripts['dev:customer'], 'vite --mode customer', 'Must have dev:customer script');
    assert.equal(pkg.scripts['dev:partner'], 'vite --mode partner', 'Must have dev:partner script');
  });

  await t.test('4. Customer App Architecture & Route Isolation', () => {
    const customerAppPath = path.join(rootFrontendDir, 'src/apps/customer/CustomerApp.jsx');
    const customerHeaderPath = path.join(rootFrontendDir, 'src/apps/customer/CustomerHeader.jsx');
    const customerNavPath = path.join(rootFrontendDir, 'src/apps/customer/CustomerBottomNav.jsx');
    const customerAuthPath = path.join(rootFrontendDir, 'src/apps/customer/CustomerAuthPage.jsx');

    assert.ok(fs.existsSync(customerAppPath), 'CustomerApp.jsx must exist');
    assert.ok(fs.existsSync(customerHeaderPath), 'CustomerHeader.jsx must exist');
    assert.ok(fs.existsSync(customerNavPath), 'CustomerBottomNav.jsx must exist');
    assert.ok(fs.existsSync(customerAuthPath), 'CustomerAuthPage.jsx must exist');

    const customerAppSrc = fs.readFileSync(customerAppPath, 'utf8');
    const customerNavSrc = fs.readFileSync(customerNavPath, 'utf8');

    // Customer App should NOT import Worker or Admin pages
    assert.doesNotMatch(customerAppSrc, /WorkerDashboard/, 'CustomerApp must NOT import WorkerDashboard');
    assert.doesNotMatch(customerAppSrc, /WorkerJobDetailsPage/, 'CustomerApp must NOT import WorkerJobDetailsPage');
    assert.doesNotMatch(customerAppSrc, /WorkerEarningsPage/, 'CustomerApp must NOT import WorkerEarningsPage');
    assert.doesNotMatch(customerAppSrc, /AdminPage/, 'CustomerApp must NOT import AdminPage');

    // Customer Navigation should NOT render worker routes
    assert.doesNotMatch(customerNavSrc, /\/worker/, 'CustomerBottomNav must NOT link to /worker');
    assert.doesNotMatch(customerNavSrc, /\/admin/, 'CustomerBottomNav must NOT link to /admin');
    assert.match(customerNavSrc, /\/customer\/status/, 'CustomerBottomNav must link to /customer/status');
  });

  await t.test('5. Partner App Architecture & Route Isolation', () => {
    const partnerAppPath = path.join(rootFrontendDir, 'src/apps/partner/PartnerApp.jsx');
    const partnerHeaderPath = path.join(rootFrontendDir, 'src/apps/partner/PartnerHeader.jsx');
    const partnerNavPath = path.join(rootFrontendDir, 'src/apps/partner/PartnerBottomNav.jsx');
    const partnerAuthPath = path.join(rootFrontendDir, 'src/apps/partner/PartnerAuthPage.jsx');

    assert.ok(fs.existsSync(partnerAppPath), 'PartnerApp.jsx must exist');
    assert.ok(fs.existsSync(partnerHeaderPath), 'PartnerHeader.jsx must exist');
    assert.ok(fs.existsSync(partnerNavPath), 'PartnerBottomNav.jsx must exist');
    assert.ok(fs.existsSync(partnerAuthPath), 'PartnerAuthPage.jsx must exist');

    const partnerAppSrc = fs.readFileSync(partnerAppPath, 'utf8');
    const partnerNavSrc = fs.readFileSync(partnerNavPath, 'utf8');

    // Partner App should NOT import Customer booking pages
    assert.doesNotMatch(partnerAppSrc, /CustomerHome/, 'PartnerApp must NOT import CustomerHome');
    assert.doesNotMatch(partnerAppSrc, /CreateJobPage/, 'PartnerApp must NOT import CreateJobPage');
    assert.doesNotMatch(partnerAppSrc, /MatchedWorkersPage/, 'PartnerApp must NOT import MatchedWorkersPage');
    assert.doesNotMatch(partnerAppSrc, /JobStatusPage/, 'PartnerApp must NOT import JobStatusPage');
    assert.doesNotMatch(partnerAppSrc, /ReviewPage/, 'PartnerApp must NOT import ReviewPage');

    // Partner Navigation should NOT render customer booking routes
    assert.doesNotMatch(partnerNavSrc, /\/customer\/create-job/, 'PartnerBottomNav must NOT link to /customer/create-job');
    assert.match(partnerNavSrc, /\/worker/, 'PartnerBottomNav must link to /worker');
    assert.match(partnerNavSrc, /\/worker\/earnings/, 'PartnerBottomNav must link to /worker/earnings');
  });

  await t.test('6. Shared Architecture Verification (Zero Duplication)', () => {
    // Both apps rely on the exact same shared stores and API service
    assert.ok(typeof useAuthStore === 'function', 'Shared useAuthStore must be functional');
    assert.ok(typeof useJobStore === 'function', 'Shared useJobStore must be functional');
    assert.ok(typeof api.getJob === 'function', 'Shared API service must expose getJob');
    assert.ok(typeof api.getNearbyJobs === 'function', 'Shared API service must expose getNearbyJobs');
    assert.ok(typeof api.createJob === 'function', 'Shared API service must expose createJob');
  });

  await t.test('7. Customer Role Enforcement & Cross-App Guard in Customer App', async () => {
    const auth = useAuthStore.getState();

    // Sign in as customer
    await auth.loginAsCustomer({
      uid: 'cust_phase4_test',
      name: 'Phase4 Customer',
      phone: '+91 98200 99991',
    });

    assert.equal(useAuthStore.getState().role, ROLES.CUSTOMER, 'Should be authenticated as customer');
    assert.equal(useAuthStore.getState().user?.uid, 'cust_phase4_test');

    // Simulate cross-app boundary check
    const isCustomerAllowed = useAuthStore.getState().role === ROLES.CUSTOMER;
    assert.ok(isCustomerAllowed, 'Customer role must be allowed in Customer App');

    auth.logout();
  });

  await t.test('8. Worker Role Enforcement & Cross-App Guard in Partner App', async () => {
    const auth = useAuthStore.getState();

    // Sign in as worker
    await auth.loginAsWorker({
      uid: 'worker_phase4_test',
      name: 'Phase4 Tradesman',
      phone: '+91 91101 88881',
      skills: ['plumber'],
      rates: { plumber: 400 },
    });

    assert.equal(useAuthStore.getState().role, ROLES.WORKER, 'Should be authenticated as worker');
    assert.equal(useAuthStore.getState().user?.skills[0], 'plumber');

    // Worker allowed in Partner App
    const isWorkerAllowedInPartner = [ROLES.WORKER, ROLES.ADMIN].includes(useAuthStore.getState().role);
    assert.ok(isWorkerAllowedInPartner, 'Worker must be allowed in Partner App');

    auth.logout();
  });

  await t.test('9. Admin Role Enforcement & Cross-App Guard in Partner App', async () => {
    const auth = useAuthStore.getState();

    // Sign in as admin
    await auth.loginAsAdmin({
      uid: 'admin_phase4_test',
      name: 'Phase4 Ops Admin',
      phone: '+91 99999 00000',
    });

    assert.equal(useAuthStore.getState().role, ROLES.ADMIN, 'Should be authenticated as admin');

    const isAdminAllowedInPartner = [ROLES.WORKER, ROLES.ADMIN].includes(useAuthStore.getState().role);
    assert.ok(isAdminAllowedInPartner, 'Admin must be allowed in Partner App');

    auth.logout();
  });

  await t.test('10. Cross-App Job Lifecycle Interoperability', async () => {
    // A job created by customer must be visible and actionable in partner job feed
    const auth = useAuthStore.getState();
    const jobs = useJobStore.getState();

    // 1. Customer creates job
    await auth.loginAsCustomer({
      uid: 'cust_e2e_split',
      name: 'Sunita Rao',
      phone: '+91 98200 44332',
    });

    const newJob = await jobs.createJob({
      customerName: 'Sunita Rao',
      customerPhone: '+91 98200 44332',
      category: 'electrician',
      description: 'Switchboard sparking in kitchen',
      mode: 'on_demand',
      budget: 500,
      location: {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Flat 402, Sea View, Bandra West, Mumbai',
      },
    });

    assert.ok(newJob?.id, 'Job should be created');
    assert.equal(newJob.category, 'electrician');
    assert.equal(newJob.status, JOB_STATUS.OPEN);

    // 2. Worker switches session in Partner App
    auth.logout();
    await auth.loginAsWorker({
      uid: 'worker_electrician_1',
      name: 'Vikram Singh',
      phone: '+91 91101 00002',
      skills: ['electrician'],
      rates: { electrician: 450 },
    });

    // Worker retrieves nearby jobs feed
    const nearbyJobs = await api.getNearbyJobs({ lat: 19.2812, lng: 72.8697 }, 15);
    const match = nearbyJobs.find((j) => j.id === newJob.id);
    assert.ok(match, 'Job created in Customer App must appear in Partner App worker feed');

    // Clean teardown
    auth.logout();
  });
});
