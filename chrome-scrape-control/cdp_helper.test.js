const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const helperPath = path.join(__dirname, "cdp_helper.js");
const helper = require(helperPath);

test("selectPageTarget returns the single page target", () => {
  const target = helper.selectPageTarget([
    { type: "service_worker", url: "https://worker.example" },
    { type: "page", url: "https://www.booking.com/hotel/example" },
  ]);

  assert.equal(target.url, "https://www.booking.com/hotel/example");
});

test("selectPageTarget rejects when there is no page target", () => {
  assert.throws(
    () => helper.selectPageTarget([{ type: "service_worker" }]),
    /exactly one Booking.com tab open/i,
  );
});

test("selectPageTarget rejects when there are multiple page targets", () => {
  assert.throws(
    () =>
      helper.selectPageTarget([
        { type: "page", url: "https://www.booking.com/hotel/one" },
        { type: "page", url: "https://www.booking.com/hotel/two" },
      ]),
    /found 2/i,
  );
});

test("createCommandSender rejects timed out commands and closes the socket", async () => {
  let closeCalled = false;
  const ws = {
    send() {},
    close() {
      closeCalled = true;
    },
  };

  const { sendCommand } = helper.createCommandSender(ws, 5);

  await assert.rejects(
    sendCommand("Runtime.evaluate", { expression: "1" }),
    /Timed out waiting for CDP command Runtime\.evaluate after 5ms\./,
  );
  assert.equal(closeCalled, true);
});

test("scrape copy stays identical to the shared helper", () => {
  const shared = fs.readFileSync(path.join(__dirname, "cdp_helper.js"), "utf8");
  const scrapeCopy = fs.readFileSync(
    path.join(__dirname, "..", "scrape", "cdp_helper.js"),
    "utf8",
  );

  assert.equal(scrapeCopy, shared);
});
