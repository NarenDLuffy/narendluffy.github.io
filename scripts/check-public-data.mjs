#!/usr/bin/env node
/**
 * Public-build data guard.
 *
 * Fails the build if anything that is classified as device-only or secret
 * (see docs/data-classification.md) is about to be shipped in the public
 * bundle. Runs before every build and again in CI before the Pages upload.
 *
 * Usage:
 *   node scripts/check-public-data.mjs            # scans public/
 *   node scripts/check-public-data.mjs dist       # scans public/ and dist/
 */
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join, relative, basename } from "node:path";

const ROOT = process.cwd();

/** Files that must never live inside a publicly served directory. */
const FORBIDDEN_NAME = [
  /\.private\./i,
  /\.secret\./i,
  /^\.env($|\.)/i,
  /^presence.*\.json$/i,
  /^checkins?.*\.json$/i,
  /^attendees?.*\.json$/i,
  /^company[-_.]?(users|members|roster).*\.json$/i,
];

/** JSON keys that indicate personal or company-presence payloads. */
const FORBIDDEN_JSON_KEYS = [
  "presence",
  "presences",
  "checkins",
  "checkIns",
  "attendees",
  "roster",
  "members",
  "email",
  "emails",
  "phone",
  "displayName",
  "userId",
  "groupId",
  "companyDomain",
];

/**
 * Patterns that must never appear in built output (secret material).
 *
 * These match an actual credential *value*, not just its prefix: the generated
 * backend client files legitimately contain key-format checks such as
 * `value.startsWith('sb_secret_')`, which are not secrets and must not fail
 * the build. A real leaked key always has a key body after the prefix.
 */
const FORBIDDEN_BUILD_PATTERNS = [
  { label: "service-role key env name", re: /SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*["'`][^"'`]+/ },
  { label: "service_role JWT claim", re: /"role"\s*:\s*"service_role"/ },
  { label: "private key block", re: /BEGIN (?:RSA )?PRIVATE KEY/ },
  { label: "Stripe live secret key", re: /sk_live_[A-Za-z0-9]{12,}/ },
  { label: "Supabase secret key", re: /sb_secret_[A-Za-z0-9_-]{12,}/ },
  { label: "Lovable API key", re: /LOVABLE_API_KEY\s*[:=]\s*["'`][^"'`]+/ },
];


const TEXT_EXT = /\.(json|js|mjs|cjs|css|html|txt|map)$/i;

const errors = [];

function walk(dir, onFile) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, onFile);
    else onFile(full);
  }
}

function collectKeys(value, out = new Set()) {
  if (Array.isArray(value)) {
    for (const v of value) collectKeys(v, out);
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) {
      out.add(k);
      collectKeys(v, out);
    }
  }
  return out;
}

function checkPublicDir(dir) {
  if (!existsSync(dir)) return;
  walk(dir, (file) => {
    const rel = relative(ROOT, file);
    const name = basename(file);

    if (FORBIDDEN_NAME.some((re) => re.test(name))) {
      errors.push(`${rel}: file name is classified as device-only/secret and must not be served publicly.`);
      return;
    }

    if (!name.endsWith(".json")) return;
    let parsed;
    try {
      parsed = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      return; // not valid JSON, nothing structured to inspect
    }
    const keys = collectKeys(parsed);
    const hits = FORBIDDEN_JSON_KEYS.filter((k) => keys.has(k));
    if (hits.length) {
      errors.push(
        `${rel}: contains sensitive key(s) [${hits.join(", ")}]. Presence / personal data must stay on the device or behind a runtime API.`,
      );
    }
  });
}

function checkBuildDir(dir) {
  if (!existsSync(dir)) return;
  walk(dir, (file) => {
    const rel = relative(ROOT, file);
    if (FORBIDDEN_NAME.some((re) => re.test(basename(file)))) {
      errors.push(`${rel}: build output contains a device-only/secret file.`);
      return;
    }
    if (!TEXT_EXT.test(file)) return;
    const text = readFileSync(file, "utf8");
    for (const { label, re } of FORBIDDEN_BUILD_PATTERNS) {
      if (re.test(text)) {
        errors.push(`${rel}: build output contains secret material (${label}).`);
      }
    }

  });
}

checkPublicDir(join(ROOT, "public"));
for (const extra of process.argv.slice(2)) checkBuildDir(join(ROOT, extra));

if (errors.length) {
  console.error("\nPublic data guard FAILED:\n");
  for (const e of errors) console.error("  - " + e);
  console.error("\nSee docs/data-classification.md for the rules.\n");
  process.exit(1);
}

console.log("Public data guard passed: no device-only or secret data in the public build.");
