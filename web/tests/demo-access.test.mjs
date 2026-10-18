import test from "node:test";
import assert from "node:assert/strict";
import { createAccessToken, demoConfigured, demoEnabled, demoInviteRequired, passwordMatches, validAccessToken, demoSessionSeconds } from "../lib/demo-access.ts";

test("public demo gate validates configuration, password, expiry and signed cookies", () => {
  const keys = ["BID3_PUBLIC_DEMO", "BID3_PUBLIC_DEMO_BUILD", "BID3_DEMO_REQUIRE_INVITE", "BID3_DEMO_PASSWORD", "BID3_DEMO_SIGNING_KEY", "BID3_DEMO_ORIGIN"];
  const previous = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  try {
    keys.forEach(key => delete process.env[key]);
    assert.equal(demoEnabled(), false);
    assert.equal(demoInviteRequired(), true);
    process.env.BID3_DEMO_REQUIRE_INVITE = "false";
    assert.equal(demoInviteRequired(), true);
    process.env.BID3_DEMO_REQUIRE_INVITE = "0";
    assert.equal(demoInviteRequired(), false);
    process.env.BID3_PUBLIC_DEMO_BUILD = "1";
    assert.equal(demoEnabled(), true);
    assert.equal(demoConfigured(), false);
    assert.equal(passwordMatches(""), false);
    assert.equal(validAccessToken(""), false);
    assert.throws(() => createAccessToken());
    process.env.BID3_DEMO_PASSWORD = "demo-test-password-not-a-real-secret";
    process.env.BID3_DEMO_SIGNING_KEY = "test-signing-key-long-enough-not-a-real-secret";
    process.env.BID3_DEMO_ORIGIN = "https://demo.example.test:8443";
    assert.equal(demoConfigured(), true);
    assert.equal(passwordMatches("wrong"), false);
    assert.equal(passwordMatches(process.env.BID3_DEMO_PASSWORD), true);
    const now = 1792290000000;
    const token = createAccessToken(now);
    assert.equal(validAccessToken(token, now), true);
    assert.equal(validAccessToken(token, now + demoSessionSeconds * 1000), false);
    assert.equal(validAccessToken(token, now - 1000), false);
    assert.equal(validAccessToken(token.slice(0, -1) + "!", now), false);
    assert.equal(validAccessToken(token.replace(/^\d/, "0"), now), false);
    assert.equal(validAccessToken("x".repeat(1000), now), false);
    process.env.BID3_DEMO_SIGNING_KEY += "rotated";
    assert.equal(validAccessToken(token, now), false);
  } finally {
    keys.forEach(key => previous[key] === undefined ? delete process.env[key] : process.env[key] = previous[key]);
  }
});
