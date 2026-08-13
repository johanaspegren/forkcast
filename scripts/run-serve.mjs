import { spawn } from "node:child_process";

import { findFreePort, parsePort } from "./ports.mjs";
import { getRuntimeFilePath, writeRuntimePorts } from "./port-runtime.mjs";

const defaultPort = parsePort(process.env.BACKEND_PORT, 8000);
const selectedPort = await findFreePort(defaultPort);

if (selectedPort !== defaultPort) {
  console.log(`[forkcast] Backend port ${defaultPort} is busy; using ${selectedPort}.`);
}

writeRuntimePorts({ backendPort: selectedPort });
console.log(`[forkcast] Backend runtime port saved to ${getRuntimeFilePath()}.`);

const args = [
  "-m",
  "uvicorn",
  "backend.forkcast.main:app",
  "--host",
  "0.0.0.0",
  "--port",
  String(selectedPort)
];

const child = spawn(".venv/bin/python", args, {
  stdio: "inherit",
  env: {
    ...process.env,
    BACKEND_PORT: String(selectedPort)
  }
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    child.kill(signal);
  });
}

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
