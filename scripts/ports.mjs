import net from "node:net";

function canListen(port, host) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();

    server.once("error", () => {
      resolve(false);
    });

    server.listen({ port, host }, () => {
      server.close(() => resolve(true));
    });
  });
}

export async function findFreePort(startPort, host = "127.0.0.1", maxTries = 200) {
  for (let port = startPort; port < startPort + maxTries; port += 1) {
    // Linear probing keeps ports predictable while still avoiding collisions.
    if (await canListen(port, host)) {
      return port;
    }
  }

  throw new Error(`No free port found in range ${startPort}-${startPort + maxTries - 1}`);
}

export function parsePort(value, fallback) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
    return fallback;
  }
  return parsed;
}
