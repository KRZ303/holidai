const fs = require("node:fs");

const DEBUG_ENDPOINT = "http://localhost:9222/json";
const CDP_COMMAND_TIMEOUT_MS = 30_000;

function buildPageTargetError(pageTargets) {
  return `Expected exactly one Chrome page target, found ${pageTargets.length}. Leave exactly one Booking.com tab open in the debug browser session and close every other tab or window before retrying.`;
}

function selectPageTarget(targets) {
  const pageTargets = targets.filter((target) => target.type === "page");
  if (pageTargets.length !== 1) {
    throw new Error(buildPageTargetError(pageTargets));
  }
  return pageTargets[0];
}

async function getActivePage(fetchImpl = fetch) {
  const res = await fetchImpl(DEBUG_ENDPOINT);
  const targets = await res.json();
  return selectPageTarget(targets);
}

function connectWS(url, WebSocketImpl = WebSocket) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocketImpl(url);
    ws.onopen = () => resolve(ws);
    ws.onerror = (err) => reject(err);
  });
}

function createCommandSender(ws, timeoutMs = CDP_COMMAND_TIMEOUT_MS) {
  let messageId = 1;
  const pendingRequests = new Map();

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pendingRequests.has(msg.id)) {
      const entry = pendingRequests.get(msg.id);
      pendingRequests.delete(msg.id);
      clearTimeout(entry.timer);
      if (msg.error) {
        entry.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      } else {
        entry.resolve(msg.result);
      }
    }
  };

  function sendCommand(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = messageId++;
      const timer = setTimeout(() => {
        pendingRequests.delete(id);
        try {
          ws.close();
        } catch (closeError) {
          // Ignore close errors during timeout cleanup.
        }
        reject(new Error(`Timed out waiting for CDP command ${method} after ${timeoutMs}ms.`));
      }, timeoutMs);

      pendingRequests.set(id, { resolve, reject, timer });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  return { sendCommand, pendingRequests };
}

async function run(action = process.argv[2], param = process.argv[3]) {
  let ws;
  try {
    const page = await getActivePage();
    ws = await connectWS(page.webSocketDebuggerUrl);
    const { sendCommand } = createCommandSender(ws);

    if (action === "navigate") {
      const url = param;
      console.error(`Navigating active tab to: ${url}`);
      await sendCommand("Page.navigate", { url });
      await new Promise((resolve) => setTimeout(resolve, 6000));
      console.log(JSON.stringify({ success: true }));
      ws.close();
      process.exit(0);
    }

    if (action === "eval") {
      let script = "";
      if (param) {
        script = param;
      } else {
        script = fs.readFileSync(0, "utf-8");
      }

      let expression = script.trim();
      if (expression.startsWith("async () =>") || expression.startsWith("() =>")) {
        expression = `(${expression})()`;
      }

      const result = await sendCommand("Runtime.evaluate", {
        expression,
        returnByValue: true,
        awaitPromise: true,
        userGesture: true,
      });

      if (result.exceptionDetails) {
        console.error("JS Execution Exception:", result.exceptionDetails);
        process.exit(1);
      }

      const value = result.result.value;
      if (typeof value === "object") {
        console.log(JSON.stringify(value));
      } else {
        console.log(value);
      }
      ws.close();
      process.exit(0);
    }

    console.error("Unknown action:", action);
    ws.close();
    process.exit(1);
  } catch (err) {
    if (ws) {
      try {
        ws.close();
      } catch (closeError) {
        // Ignore close errors during failure cleanup.
      }
    }
    console.error("CDP Helper Error:", err.message);
    process.exit(1);
  }
}

if (require.main === module) {
  run();
}

module.exports = {
  CDP_COMMAND_TIMEOUT_MS,
  createCommandSender,
  getActivePage,
  run,
  selectPageTarget,
};
