const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1080 } });
  for (const [src, out] of process.argv.slice(2).map(a => a.split(':'))) {
    await p.goto('file://' + path.resolve(src));
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(800);
    await p.screenshot({ path: out, type: out.endsWith('.png') ? 'png' : 'jpeg', quality: out.endsWith('.png') ? undefined : 90 });
  }
  await b.close();
})();
