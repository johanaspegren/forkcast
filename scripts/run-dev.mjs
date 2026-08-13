import { spawn } from "node:child_process";

import { readRuntimePorts, writeRuntimePorts } from "./port-runtime.mjs";
import { findFreePort, parsePort } from "./ports.mjs";

const runtimePorts = readRuntimePorts();
const backendPort = parsePort(process.env.BACKEND_PORT, parsePort(runtimePorts.backendPort, 8000));
const defaultFrontendPort = parsePort(process.env.FRONTEND_PORT, 5173);
const selectedFrontendPort = await findFreePort(defaultFrontendPort);

if (selectedFrontendPort !== defaultFrontendPort) {
  console.log(`[forkcast] Frontend port ${defaultFrontendPort} is busy; using ${selectedFrontendPort}.`);
}

writeRuntimePorts({ frontendPort: selectedFrontendPort, backendPort });
console.log(`[forkcast] Frontend proxy target backend port: ${backendPort}.`);

const args = ["--host", "0.0.0.0", "--port", String(selectedFrontendPort)];
const child = spawn("vite", args, {
  stdio: "inherit",
  env: {
    ...process.env,
    FRONTEND_PORT: String(selectedFrontendPort),
    BACKEND_PORT: String(backendPort)
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
