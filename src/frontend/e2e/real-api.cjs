const { chromium } = require('playwright-core')
const assert = require('node:assert/strict')

async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  try {
    const page = await browser.newPage()
    const failures = []
    page.on('pageerror', (error) => failures.push(error.message))
    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' })
    await page.getByTestId('summary-BLD-A').waitFor()
    await page.getByTestId('summary-BLD-B').waitFor()
    assert.equal(await page.getByText('Nguồn API', { exact: true }).count(), 1)

    await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'domcontentloaded' })
    await page.getByTestId('device-A-01').waitFor()
    await page.getByLabel('Lọc theo tòa nhà').selectOption('BLD-A')
    await page.getByTestId('device-A-02').waitFor()
    await page.waitForFunction(() => !document.querySelector('[data-testid="device-B-01"]'))
    assert.equal(await page.getByText('Dữ liệu từ API', { exact: true }).count(), 1)

    await page.goto('http://127.0.0.1:5173/devices/A-01/history', { waitUntil: 'domcontentloaded' })
    await page.getByText('Không có dữ liệu', { exact: true }).waitFor()
    await page.goto('http://127.0.0.1:5173/alerts', { waitUntil: 'domcontentloaded' })
    await page.getByText('Không có dữ liệu', { exact: true }).waitFor()
    assert.deepEqual(failures, [])
    process.stdout.write('Chrome loaded API-backed overview, filtered devices, empty history and alerts.\n')
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
