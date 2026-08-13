import fs from "node:fs";
import path from "node:path";

const runtimeFilePath = path.join(process.cwd(), ".forkcast-ports.json");

export function readRuntimePorts() {
  try {
    const raw = fs.readFileSync(runtimeFilePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export function writeRuntimePorts(nextState) {
  const current = readRuntimePorts();
  const state = { ...current, ...nextState };
  fs.writeFileSync(runtimeFilePath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

export function getRuntimeFilePath() {
  return runtimeFilePath;
}
