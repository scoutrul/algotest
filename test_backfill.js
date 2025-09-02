const { chromium } = require('playwright');

async function testBackfill() {
  console.log('Starting backfill test...');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // Listen for console messages
  page.on('console', msg => {
    console.log('PAGE LOG:', msg.text());
  });

  // Listen for network requests
  page.on('request', request => {
    if (request.url().includes('/api/v1/candles')) {
      console.log('API REQUEST:', request.url());
    }
  });

  try {
    console.log('Navigating to frontend...');
    await page.goto('http://localhost:5175');

    // Wait for page to load
    await page.waitForTimeout(3000);

    // Check if chart is loaded
    const chartElement = await page.$('[data-testid="chart"]') || await page.$('canvas');
    if (chartElement) {
      console.log('Chart element found');
    } else {
      console.log('Chart element not found');
    }

    // Wait for backfill to potentially happen
    console.log('Waiting for backfill...');
    await page.waitForTimeout(5000);

    // Try to scroll left to trigger backfill
    console.log('Trying to scroll left...');
    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(2000);

    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(2000);

    console.log('Test completed');

  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
}

testBackfill();
