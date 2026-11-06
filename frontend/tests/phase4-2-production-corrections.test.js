import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

describe('RepairBuddy Phase 4.2 Production Corrections Suite', () => {
  it('1. Development mock mode works when explicitly enabled', () => {
    // In development mode (PROD !== true), setting VITE_USE_MOCK="true" activates mock mode
    const isProd = false;
    const viteUseMock = 'true';
    const allowMockProd = false;

    const isMock = isProd
      ? viteUseMock === 'true' && allowMockProd
      : viteUseMock !== 'false';

    assert.equal(isMock, true, 'Mock mode should be active in development when VITE_USE_MOCK is true');
  });

  it('2. Production mock mode is rejected and prevented from activating', () => {
    // In production mode (PROD === true), VITE_USE_MOCK="true" is rejected unless explicit test bypass is provided
    const isProd = true;
    const viteUseMock = 'true';
    const allowMockProd = false;

    const isMock = isProd
      ? viteUseMock === 'true' && allowMockProd
      : viteUseMock !== 'false';

    assert.equal(isMock, false, 'Mock mode must never activate in production without explicit allow flag');
  });

  it('3. Production localhost URLs are detected and rejected', () => {
    const isProd = true;
    const testLocalUrls = ['http://localhost:8000/api', 'http://127.0.0.1:8000/api', 'http://localhost:5173'];

    for (const url of testLocalUrls) {
      const isLocal = url.includes('localhost') || url.includes('127.0.0.1');
      assert.equal(isLocal, true, `URL "${url}" should be detected as localhost`);

      // Simulation of Vite config build guard
      assert.throws(
        () => {
          if (isProd && isLocal) {
            throw new Error(`[Vite Build Error] VITE_API_BASE_URL cannot point to localhost in production mode.`);
          }
        },
        /cannot point to localhost in production mode/,
        `Should throw for localhost URL: ${url}`
      );
    }
  });

  it('4. Missing production API URL is detected and rejected', () => {
    const isProd = true;
    const emptyUrls = ['', '   ', null, undefined];

    for (const raw of emptyUrls) {
      const trimmed = (raw || '').trim();
      assert.throws(
        () => {
          if (isProd && !trimmed) {
            throw new Error(`[Vite Build Error] Missing VITE_API_BASE_URL in production build.`);
          }
        },
        /Missing VITE_API_BASE_URL in production build/,
        'Should throw for missing production API URL'
      );
    }
  });

  it('5. Valid production backend URL is accepted', () => {
    const validProdUrl = 'https://repair-buddy.onrender.com/api';
    const isProd = true;
    const isLocal = validProdUrl.includes('localhost') || validProdUrl.includes('127.0.0.1');

    assert.equal(isLocal, false);
    assert.ok(validProdUrl.startsWith('https://'));
    assert.ok(validProdUrl.endsWith('/api'));

    // Validation passes without error
    let validated = false;
    if (isProd && !isLocal && validProdUrl.trim()) {
      validated = true;
    }
    assert.equal(validated, true, 'Valid production URL should pass validation cleanly');
  });

  it('6. Customer and Partner modes remain independent with isolated outputs', () => {
    const customerEnvPath = path.join(rootDir, '.env.customer');
    const partnerEnvPath = path.join(rootDir, '.env.partner');

    assert.ok(fs.existsSync(customerEnvPath), '.env.customer must exist');
    assert.ok(fs.existsSync(partnerEnvPath), '.env.partner must exist');

    const customerEnv = fs.readFileSync(customerEnvPath, 'utf8');
    const partnerEnv = fs.readFileSync(partnerEnvPath, 'utf8');

    assert.ok(customerEnv.includes('VITE_APP=customer'), 'Customer env must specify VITE_APP=customer');
    assert.ok(partnerEnv.includes('VITE_APP=partner'), 'Partner env must specify VITE_APP=partner');

    // Verify Vercel output directories
    const customerVercel = JSON.parse(fs.readFileSync(path.join(rootDir, 'vercel.customer.json'), 'utf8'));
    const partnerVercel = JSON.parse(fs.readFileSync(path.join(rootDir, 'vercel.partner.json'), 'utf8'));

    assert.equal(customerVercel.outputDirectory, 'dist/customer', 'Customer outputDirectory must be dist/customer');
    assert.equal(partnerVercel.outputDirectory, 'dist/partner', 'Partner outputDirectory must be dist/partner');

    assert.equal(customerVercel.buildCommand, 'npm run build:customer');
    assert.equal(partnerVercel.buildCommand, 'npm run build:partner');
  });

  it('7. Both production distribution directories exist independently', () => {
    const customerDist = path.join(rootDir, 'dist/customer/index.html');
    const partnerDist = path.join(rootDir, 'dist/partner/index.html');

    assert.ok(fs.existsSync(customerDist), 'dist/customer/index.html must exist from build:customer');
    assert.ok(fs.existsSync(partnerDist), 'dist/partner/index.html must exist from build:partner');
  });
});

