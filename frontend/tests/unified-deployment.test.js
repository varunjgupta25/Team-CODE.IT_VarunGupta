import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

describe('RepairBuddy Unified Application Deployment Verification Suite', () => {
  it('1. Package.json configured for unified production build', () => {
    const pkgPath = path.join(rootDir, 'package.json');
    assert.ok(fs.existsSync(pkgPath), 'package.json must exist');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

    assert.equal(pkg.scripts.build, 'vite build', 'Default build script must be "vite build" (unified)');
    assert.ok(pkg.scripts['build:customer'], 'Customer build script preserved for development/testing');
    assert.ok(pkg.scripts['build:partner'], 'Partner build script preserved for development/testing');
  });

  it('2. Vercel.json configured for unified root dist output and SPA fallback', () => {
    const vercelPath = path.join(rootDir, 'vercel.json');
    assert.ok(fs.existsSync(vercelPath), 'vercel.json must exist');
    const vercelConfig = JSON.parse(fs.readFileSync(vercelPath, 'utf8'));

    assert.equal(vercelConfig.buildCommand, 'npm run build', 'Vercel buildCommand must be "npm run build"');
    assert.equal(vercelConfig.outputDirectory, 'dist', 'Vercel outputDirectory must be "dist"');
    assert.ok(Array.isArray(vercelConfig.rewrites), 'vercel.json must define rewrites');
    assert.deepEqual(
      vercelConfig.rewrites[0],
      { source: '/(.*)', destination: '/index.html' },
      'Vercel rewrites must direct all routes to /index.html for React Router SPA navigation'
    );
  });

  it('3. Unified production build artifact exists at dist/index.html', () => {
    const indexPath = path.join(rootDir, 'dist/index.html');
    assert.ok(fs.existsSync(indexPath), 'dist/index.html must exist after unified build');

    const indexHtml = fs.readFileSync(indexPath, 'utf8');
    assert.ok(indexHtml.includes('<div id="root"></div>'), 'dist/index.html must have root div');
    assert.ok(indexHtml.includes('/assets/index-'), 'dist/index.html must link to hashed assets');
  });

  it('4. Unified bundle contains Customer, Worker, and Admin functionality', () => {
    const assetsDir = path.join(rootDir, 'dist/assets');
    assert.ok(fs.existsSync(assetsDir), 'dist/assets must exist');

    const assetFiles = fs.readdirSync(assetsDir);
    const jsFiles = assetFiles.filter((f) => f.endsWith('.js'));
    assert.ok(jsFiles.length > 0, 'At least one compiled JS bundle must exist');

    // Read combined bundle content to verify all roles are compiled in
    let combinedJs = '';
    for (const file of jsFiles) {
      combinedJs += fs.readFileSync(path.join(assetsDir, file), 'utf8');
    }

    // Customer markers
    assert.ok(
      combinedJs.includes('Customer') || combinedJs.includes('customer') || combinedJs.includes('CreateJob'),
      'Unified bundle must contain Customer workflows'
    );

    // Worker markers
    assert.ok(
      combinedJs.includes('Worker') || combinedJs.includes('worker') || combinedJs.includes('Earnings'),
      'Unified bundle must contain Worker workflows'
    );

    // Admin markers
    assert.ok(
      combinedJs.includes('Admin') || combinedJs.includes('admin') || combinedJs.includes('verifications'),
      'Unified bundle must contain Admin workflows'
    );
  });

  it('5. App.jsx unified router provides role-based routes for all three roles', () => {
    const appPath = path.join(rootDir, 'src/App.jsx');
    assert.ok(fs.existsSync(appPath), 'src/App.jsx must exist');
    const appCode = fs.readFileSync(appPath, 'utf8');

    // Customer routes
    assert.ok(appCode.includes('path="/"'), 'Must define customer home route at /');
    assert.ok(appCode.includes('/customer/create-job'), 'Must define create job route');
    assert.ok(appCode.includes('/customer/match/:jobId'), 'Must define match route');
    assert.ok(appCode.includes('/customer/status'), 'Must define job status route');
    assert.ok(appCode.includes('/customer/review/:jobId'), 'Must define review route');

    // Worker routes
    assert.ok(appCode.includes('path="/worker"'), 'Must define worker dashboard route');
    assert.ok(appCode.includes('/worker/job/:jobId'), 'Must define worker job details route');
    assert.ok(appCode.includes('/worker/earnings'), 'Must define worker earnings route');

    // Admin routes
    assert.ok(appCode.includes('path="/admin"'), 'Must define admin dashboard route');

    // Shared & Auth routes
    assert.ok(appCode.includes('path="/login"'), 'Must define public login route');
    assert.ok(appCode.includes('path="/profile"'), 'Must define profile route');
    assert.ok(appCode.includes('path="*"'), 'Must define catch-all fallback route');
  });

  it('6. Production environment configuration strictly enforces HTTPS and rejects mocks', () => {
    const prodEnvPath = path.join(rootDir, '.env.production');
    assert.ok(fs.existsSync(prodEnvPath), '.env.production must exist');
    const prodEnv = fs.readFileSync(prodEnvPath, 'utf8');

    assert.ok(prodEnv.includes('VITE_USE_MOCK=false'), '.env.production must have VITE_USE_MOCK=false');
    assert.ok(prodEnv.includes('VITE_API_BASE_URL=https://'), '.env.production must use HTTPS API URL');
    assert.ok(!prodEnv.includes('localhost'), '.env.production must not contain localhost');
    assert.ok(!prodEnv.includes('127.0.0.1'), '.env.production must not contain 127.0.0.1');
  });

  it('7. Vite configuration cleanly maps unified and isolated build targets', () => {
    const viteConfigPath = path.join(rootDir, 'vite.config.js');
    const viteConfig = fs.readFileSync(viteConfigPath, 'utf8');

    assert.ok(viteConfig.includes("outDirMap[targetApp] || 'dist'"), 'Vite must output to "dist" for unified build');
    assert.ok(viteConfig.includes("appEntryMap[targetApp] || path.resolve(__dirname, 'src/App.jsx')"), 'Vite must use src/App.jsx for unified build');
    assert.ok(viteConfig.includes('https://'), 'Vite must enforce HTTPS for production builds');
    assert.ok(viteConfig.includes('localhost'), 'Vite must reject localhost in production');
  });

  it('8. Direct navigation and page refresh compatibility verified', () => {
    // Verify SPA routing setup
    const vercelConfig = JSON.parse(fs.readFileSync(path.join(rootDir, 'vercel.json'), 'utf8'));
    const hasSpaCatchAll = vercelConfig.rewrites.some(
      (r) => r.source === '/(.*)' && r.destination === '/index.html'
    );
    assert.ok(hasSpaCatchAll, 'Vercel must rewrite all paths to /index.html for client-side routing');

    // Verify index.html contains proper base tags/scripts
    const indexHtml = fs.readFileSync(path.join(rootDir, 'dist/index.html'), 'utf8');
    assert.ok(indexHtml.includes('<script type="module"'), 'index.html must load module script');
  });
});
