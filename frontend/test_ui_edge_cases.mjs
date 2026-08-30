/**
 * ============================================================
 * Lahore Pulse AI — Frontend UI Edge-Case Test Suite
 * ============================================================
 * Tests every page at multiple viewport sizes for:
 *   1. HTTP reachability
 *   2. Console errors
 *   3. Horizontal scrollbar overflow (scrollWidth > innerWidth)
 *   4. Key structural elements (nav, main, headings, landmarks)
 *   5. Responsive layout integrity
 * ============================================================
 */

import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

const VIEWPORTS = [
  { name: 'Mobile-S',      width: 375,  height: 812 },
  { name: 'Tablet',         width: 768,  height: 1024 },
  { name: 'Laptop-SM',      width: 1024, height: 768 },
  { name: 'Laptop-LG',      width: 1280, height: 800 },
  { name: 'Desktop-FHD',    width: 1440, height: 900 },
];

const PAGES = [
  { path: '/',              label: 'Landing Page',   needsAuth: false },
  { path: '/login',         label: 'Login Page',     needsAuth: false },
  { path: '/citizen',       label: 'Citizen Hub',    needsAuth: true  },
  { path: '/air-quality',   label: 'Air Quality',    needsAuth: true  },
  { path: '/city-map',      label: 'City Map',       needsAuth: true  },
  { path: '/alerts',        label: 'Alerts',         needsAuth: true  },
  { path: '/data-trust',    label: 'Data Trust',     needsAuth: true  },
  { path: '/reports',       label: 'Reports',        needsAuth: true  },
  { path: '/my-lahore',     label: 'My Lahore',      needsAuth: true  },
  { path: '/insights',      label: 'Insights',       needsAuth: true  },
];

// ── Result collectors ──────────────────────────────────────
const results = [];
let totalPass = 0;
let totalFail = 0;
let totalSkip = 0;

function record(viewport, page, test, pass, detail = '') {
  const status = pass === true ? 'PASS' : pass === false ? 'FAIL' : 'SKIP';
  if (pass === true) totalPass++;
  else if (pass === false) totalFail++;
  else totalSkip++;
  results.push({ viewport, page, test, status, detail });
}

// ── Helpers ────────────────────────────────────────────────

async function citizenLogin(page) {
  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 15000 });
    // Try clicking the Citizen demo button
    const citizenBtn = await page.$('text=Citizen');
    if (citizenBtn) {
      await citizenBtn.click();
      await page.waitForTimeout(2000);
      return true;
    }
    // Try alternative selectors
    const altBtn = await page.$('[class*="citizen" i], [data-role*="citizen" i], button:has-text("Citizen")');
    if (altBtn) {
      await altBtn.click();
      await page.waitForTimeout(2000);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

async function checkConsoleErrors(page) {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));
  return errors;
}

async function checkOverflow(page, vpWidth) {
  try {
    const overflow = await page.evaluate((w) => {
      return {
        bodyScrollWidth: document.body.scrollWidth,
        docScrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        hasHorizontalScroll: document.body.scrollWidth > window.innerWidth || document.documentElement.scrollWidth > window.innerWidth,
      };
    }, vpWidth);
    return overflow;
  } catch {
    return { hasHorizontalScroll: false, bodyScrollWidth: 0, docScrollWidth: 0, innerWidth: vpWidth };
  }
}

async function checkStructure(page) {
  return page.evaluate(() => {
    const has = (sel) => document.querySelectorAll(sel).length;
    return {
      navCount: has('nav'),
      mainCount: has('main'),
      headerCount: has('header'),
      headingCount: has('h1, h2, h3'),
      h1Count: has('h1'),
      buttonCount: has('button'),
      linkCount: has('a'),
      imgCount: has('img'),
      formCount: has('form'),
      sectionCount: has('section'),
      hasRoot: has('#root') || has('#app') || has('#__next'),
      // Check for footer
      footerCount: has('footer'),
      // Check for interactive elements
      inputCount: has('input'),
      selectCount: has('select'),
      textareaCount: has('textarea'),
    };
  });
}

async function checkKeyVisibility(page) {
  return page.evaluate(() => {
    const elements = document.querySelectorAll('h1, h2, h3, nav, main, button, a');
    let visibleCount = 0;
    let hiddenCount = 0;
    elements.forEach(el => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
        visibleCount++;
      } else {
        hiddenCount++;
      }
    });
    return { visibleCount, hiddenCount };
  });
}

// ── Main test runner ───────────────────────────────────────

async function runTests() {
  console.log('');
  console.log('╔══════════════════════════════════════════════════════════════════╗');
  console.log('║   LAHORE PULSE AI — Frontend UI Edge-Case Test Suite           ║');
  console.log('║   Aggressive Multi-Viewport Responsive Testing                 ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝');
  console.log('');

  // Check server first
  try {
    const resp = await fetch(BASE);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    console.log(`  ✅ Frontend server is UP at ${BASE}`);
  } catch (e) {
    console.error(`  ❌ Frontend server is DOWN at ${BASE}: ${e.message}`);
    console.error('  Please start the dev server first: npm run dev');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });

  // ── Phase 1: Quick login to establish session ──────────
  console.log('\n── Phase 1: Authentication ──');
  const authContext = await browser.newContext();
  const authPage = await authContext.newPage();
  const loggedIn = await citizenLogin(authPage);
  console.log(`  ${loggedIn ? '✅' : '⚠️'} Citizen demo login: ${loggedIn ? 'SUCCESS' : 'BUTTON NOT FOUND — proceeding without auth'}`);
  
  // Capture the storage state so we can reuse it
  const storageState = await authContext.storageState();
  await authContext.close();

  // ── Phase 2: Run every page × viewport ─────────────────
  console.log('\n── Phase 2: Multi-Viewport Page Testing ──');
  console.log(`  Viewports: ${VIEWPORTS.map(v => v.name + ' (' + v.width + ')').join(', ')}`);
  console.log(`  Pages: ${PAGES.map(p => p.label).join(', ')}`);
  console.log('');

  for (const vp of VIEWPORTS) {
    console.log(`┌─── Viewport: ${vp.name} (${vp.width}×${vp.height}) ───`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      storageState,
    });

    for (const pg of PAGES) {
      const pageLabel = `${vp.name} / ${pg.label}`;
      const page = await context.newPage();

      // Collect console errors
      const consoleErrors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });
      page.on('pageerror', err => consoleErrors.push(err.message));

      let httpStatus = 0;
      let loaded = false;

      try {
        const response = await page.goto(`${BASE}${pg.path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 15000,
        });
        httpStatus = response?.status() || 0;
        loaded = httpStatus >= 200 && httpStatus < 400;

        // Wait for dynamic content — allow data-fetching pages to fully render
        await page.waitForTimeout(1000);
        // Wait for loading spinner to disappear, then for headings to appear
        try {
          await page.waitForSelector('.loading-state', { state: 'hidden', timeout: 8000 });
        } catch {
          // Some pages may not have a loading state
        }
        try {
          await page.waitForSelector('h1, h2, h3', { timeout: 6000 });
        } catch {
          // Heading may not exist on some pages — that's what we test
        }
      } catch (e) {
        consoleErrors.push(`Navigation error: ${e.message}`);
      }

      // Test: HTTP Status
      const httpOk = httpStatus >= 200 && httpStatus < 400;
      record(vp.name, pg.label, 'HTTP Status', httpOk, `HTTP ${httpStatus}`);

      if (!loaded) {
        record(vp.name, pg.label, 'Console Errors', false, `Page failed to load: HTTP ${httpStatus}`);
        record(vp.name, pg.label, 'Horizontal Overflow', 'skip');
        record(vp.name, pg.label, 'Structure', 'skip');
        record(vp.name, pg.label, 'Visibility', 'skip');
        console.log(`  │  ❌ ${pg.label.padEnd(16)} HTTP ${httpStatus} — SKIPPED remaining tests`);
        await page.close();
        continue;
      }

      // Test: Horizontal scrollbar overflow
      const overflow = await checkOverflow(page, vp.width);
      const noOverflow = !overflow.hasHorizontalScroll;
      record(vp.name, pg.label, 'Horizontal Overflow', noOverflow,
        noOverflow
          ? `OK (body=${overflow.bodyScrollWidth}, doc=${overflow.docScrollWidth}, inner=${overflow.innerWidth})`
          : `OVERFLOW: body=${overflow.bodyScrollWidth} > inner=${overflow.innerWidth}`);

      // Detect if page is stuck in loading state
      const isLoading = await page.evaluate(() => {
        const loadingEls = document.querySelectorAll('.skeleton, .skeleton-hero, .skeleton-group, .status-dot--loading');
        const loadingText = document.body.innerText.includes('Loading') || document.body.innerText.includes('loading');
        return { hasSkeleton: loadingEls.length > 0, loadingText };
      });

      // Test: Structure
      const structure = await checkStructure(page);
      const hasStructure = structure.navCount > 0 || structure.mainCount > 0 || structure.headerCount > 0 || structure.hasRoot > 0;
      record(vp.name, pg.label, 'Structure (nav/main/header)', hasStructure,
        `nav=${structure.navCount} main=${structure.mainCount} header=${structure.headerCount} root=${structure.hasRoot ? 'yes' : 'no'}`);

      // Test: Headings exist (note: loading-state pages won't have headings)
      const hasHeadings = structure.headingCount > 0;
      const headingDetail = hasHeadings
        ? `h1=${structure.h1Count} total=${structure.headingCount}`
        : `h1=0 total=0${isLoading.hasSkeleton ? ' (stuck in loading state — skeleton visible)' : ''}`;
      record(vp.name, pg.label, 'Headings (h1-h3)', hasHeadings, headingDetail);

      // Test: Interactive elements
      const hasInteractivity = structure.buttonCount > 0 || structure.linkCount > 0;
      record(vp.name, pg.label, 'Interactive Elements', hasInteractivity,
        `buttons=${structure.buttonCount} links=${structure.linkCount} inputs=${structure.inputCount}`);

      // Test: Visibility
      const visibility = await checkKeyVisibility(page);
      const hasVisibleElements = visibility.visibleCount > 3;
      record(vp.name, pg.label, 'Element Visibility', hasVisibleElements,
        `visible=${visibility.visibleCount} hidden=${visibility.hiddenCount}`);

      // Test: No broken images (exclude map tiles and data URIs)
      const imgCheck = await page.evaluate(() => {
        const imgs = [...document.querySelectorAll('img')];
        const broken = imgs.filter(img => {
          // Skip data URIs and about:blank
          if (img.src.startsWith('data:') || img.src === 'about:blank') return false;
          return !img.complete || img.naturalWidth === 0;
        });
        return {
          total: imgs.length,
          broken: broken.length,
          brokenSrcs: broken.map(i => { try { return new URL(i.src).pathname; } catch { return i.src; } }).slice(0, 5),
        };
      });
      const noBrokenImages = imgCheck.broken === 0;
      record(vp.name, pg.label, 'No Broken Images', noBrokenImages || imgCheck.total === 0,
        imgCheck.total > 0
          ? imgCheck.broken > 0
            ? `${imgCheck.broken}/${imgCheck.total} broken: ${imgCheck.brokenSrcs.join(', ')}`
            : `${imgCheck.total} images OK`
          : 'No images');

      // Test: Console errors (filter out known benign messages)
      const realErrors = consoleErrors.filter(e => {
        // Filter common dev-server warnings
        if (e.includes('[vite]') || e.includes('HMR') || e.includes('favicon')) return false;
        if (e.includes('Download the React DevTools') || e.includes('DevTools')) return false;
        if (e.includes('404') && e.includes('favicon')) return false;
        if (e.includes('NetInfo') || e.includes('deprecated')) return false;
        return true;
      });
      const noErrors = realErrors.length === 0;
      record(vp.name, pg.label, 'No Console Errors', noErrors,
        noErrors ? 'Clean' : `${realErrors.length} errors: ${realErrors.slice(0, 2).join('; ').substring(0, 120)}`);

      // Status line
      const pagePassed = httpOk && noOverflow && hasStructure;
      const loadingTag = isLoading.hasSkeleton ? ' ⏳LOADING' : '';
      const emoji = pagePassed ? '✅' : '⚠️';
      console.log(`  │  ${emoji} ${pg.label.padEnd(16)} HTTP ${httpStatus} | overflow=${overflow.hasHorizontalScroll ? 'YES' : 'no'} | structure=${hasStructure} | errors=${realErrors.length}${loadingTag}`);

      await page.close();
    }

    console.log(`└───────────────────────────────────────────`);
    await context.close();
  }

  await browser.close();

  // ── Phase 3: Summary ───────────────────────────────────
  printSummary();
}

function printSummary() {
  console.log('');
  console.log('╔══════════════════════════════════════════════════════════════════╗');
  console.log('║                        TEST SUMMARY                            ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝');
  console.log('');
  console.log(`  Total assertions: ${results.length}`);
  console.log(`  ✅ Passed:  ${totalPass}`);
  console.log(`  ❌ Failed:  ${totalFail}`);
  console.log(`  ⏭️  Skipped: ${totalSkip}`);
  console.log('');

  // Per-viewport summary
  const byViewport = {};
  for (const r of results) {
    if (!byViewport[r.viewport]) byViewport[r.viewport] = { pass: 0, fail: 0, skip: 0 };
    byViewport[r.viewport][r.status === 'PASS' ? 'pass' : r.status === 'FAIL' ? 'fail' : 'skip']++;
  }
  console.log('  Per-ViewPort:');
  for (const [vp, counts] of Object.entries(byViewport)) {
    const total = counts.pass + counts.fail + counts.skip;
    const emoji = counts.fail === 0 ? '✅' : '❌';
    console.log(`    ${emoji} ${vp.padEnd(16)} ${counts.pass}/${total} passed`);
  }
  console.log('');

  // Per-page summary
  const byPage = {};
  for (const r of results) {
    if (!byPage[r.page]) byPage[r.page] = { pass: 0, fail: 0, skip: 0 };
    byPage[r.page][r.status === 'PASS' ? 'pass' : r.status === 'FAIL' ? 'fail' : 'skip']++;
  }
  console.log('  Per-Page:');
  for (const [pg, counts] of Object.entries(byPage)) {
    const total = counts.pass + counts.fail + counts.skip;
    const emoji = counts.fail === 0 ? '✅' : '❌';
    console.log(`    ${emoji} ${pg.padEnd(16)} ${counts.pass}/${total} passed`);
  }
  console.log('');

  // Per-test-type summary
  const byTest = {};
  for (const r of results) {
    if (!byTest[r.test]) byTest[r.test] = { pass: 0, fail: 0, skip: 0 };
    byTest[r.test][r.status === 'PASS' ? 'pass' : r.status === 'FAIL' ? 'fail' : 'skip']++;
  }
  console.log('  Per-Test-Type:');
  for (const [test, counts] of Object.entries(byTest)) {
    const total = counts.pass + counts.fail + counts.skip;
    const emoji = counts.fail === 0 ? '✅' : counts.fail > total / 2 ? '❌' : '⚠️';
    console.log(`    ${emoji} ${test.padEnd(36)} ${counts.pass}/${total} passed`);
  }
  console.log('');

  // List all failures
  const failures = results.filter(r => r.status === 'FAIL');
  if (failures.length > 0) {
    console.log('  ❌ FAILURES:');
    for (const f of failures) {
      console.log(`    • [${f.viewport}] ${f.page} — ${f.test}: ${f.detail}`);
    }
    console.log('');
  }

  // Final verdict
  if (totalFail === 0) {
    console.log('  🎉 ALL TESTS PASSED — Frontend is responsive and error-free!');
  } else {
    console.log(`  ⚠️  ${totalFail} test(s) FAILED — review the failures above.`);
  }
  console.log('');

  // Exit code
  process.exit(totalFail > 0 ? 1 : 0);
}

// ── Run ────────────────────────────────────────────────────
runTests().catch(e => {
  console.error('FATAL ERROR:', e);
  process.exit(2);
});
