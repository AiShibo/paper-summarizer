"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "../..");
const html = fs.readFileSync(path.join(ROOT, "site/index.html"), "utf8");
const css = fs.readFileSync(path.join(ROOT, "site/styles.css"), "utf8");
const app = fs.readFileSync(path.join(ROOT, "site/app.js"), "utf8");

test("frontend has the keyboard and status landmarks used by the app", () => {
  [
    "main-content",
    "search",
    "data-notice",
    "advanced-filters",
    "active-filters",
    "results",
    "paper-list",
    "empty-state",
    "error-state",
    "annotation-dialog",
    "saved-search-dialog",
    "toast",
  ].forEach((id) => assert.match(html, new RegExp(`id="${id}"`), id));
  assert.match(html, /class="skip-link"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /aria-busy="true"/);
});

test("frontend does not load network fonts, scripts, or decorative assets", () => {
  assert.doesNotMatch(html, /(?:src|href)="https?:\/\//i);
  assert.doesNotMatch(css, /@import\s+url/i);
});

test("every DOM id cached by the client exists in the document", () => {
  const cachedIds = [...app.matchAll(/byId\("([^"]+)"\)/g)].map((match) => match[1]);
  const documentIds = new Set(
    [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1])
  );
  assert.ok(cachedIds.length > 40);
  assert.deepEqual(
    cachedIds.filter((id) => !documentIds.has(id)),
    []
  );
});

test("responsive, dark, reduced-motion, and forced-color treatments exist", () => {
  assert.match(css, /:root\[data-theme="dark"\]/);
  assert.match(css, /@media \(max-width: 600px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /@media \(forced-colors: active\)/);
  assert.match(css, /overflow-x: hidden/);
});
