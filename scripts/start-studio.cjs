// Use the project's virtualenv when present, otherwise the system Python.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const windows = process.platform === 'win32';
const candidates = ['venv', '.venv'].map(dir => path.join(root, dir, windows ? 'Scripts/python.exe' : 'bin/python'));
const python = candidates.find(file => fs.existsSync(file)) || (windows ? 'python' : 'python3');
const args = ['-m', 'uvicorn', 'studio.server:studio_app', '--host', '127.0.0.1', '--port', '8787'];
if (process.argv.includes('--reload')) args.push('--reload');
const child = spawn(python, args, { cwd: root, stdio: 'inherit' });
child.on('error', err => {
  console.error(`No se pudo iniciar Python: ${err.message}. Instalá Python y ejecutá pip install -r requirements.txt.`);
  process.exitCode = 1;
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', code => { process.exitCode = code || 0; });
