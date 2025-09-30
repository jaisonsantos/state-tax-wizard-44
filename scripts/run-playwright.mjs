#!/usr/bin/env node
import { spawn } from 'node:child_process';

if (process.env.ENABLE_REPORT_DOWNLOAD_TEST !== '1') {
  console.log('Playwright report download smoke skipped (set ENABLE_REPORT_DOWNLOAD_TEST=1 to enable).');
  process.exit(0);
}

const args = ['playwright', 'test'];
if (process.env.PLAYWRIGHT_CONFIG) {
  args.push('--config', process.env.PLAYWRIGHT_CONFIG);
}

const runner = spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', args, {
  stdio: 'inherit',
  shell: false,
});

runner.on('exit', (code) => {
  process.exit(code ?? 1);
});
