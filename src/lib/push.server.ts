/**
 * Minimal Web Push sender (RFC 8291 aes128gcm + RFC 8292 VAPID) using only
 * Web Crypto — safe for the workerd server runtime, no Node APIs.
 */

function b64urlToBytes(s: string): Uint8Array {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const b64 = (s + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function bytesToB64url(b: ArrayBuffer | Uint8Array): string {
  const bytes = b instanceof Uint8Array ? b : new Uint8Array(b);
  let bin = "";
  for (const byte of bytes) bin += String.fromCharCode(byte);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let off = 0;
  for (const p of parts) {
    out.set(p, off);
    off += p.length;
  }
  return out;
}

const te = new TextEncoder();

async function hkdf(salt: Uint8Array, ikm: Uint8Array, info: Uint8Array, len: number): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", ikm as BufferSource, "HKDF", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt: salt as BufferSource, info: info as BufferSource },
    key,
    len * 8,
  );
  return new Uint8Array(bits);
}

/** Sign a VAPID JWT (ES256) with the PKCS8 private key from the secret. */
async function vapidJwt(endpoint: string, subject: string, privPkcs8: string, pubRaw: string): Promise<string> {
  const aud = new URL(endpoint).origin;
  const header = bytesToB64url(te.encode(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const body = bytesToB64url(
    te.encode(JSON.stringify({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: subject })),
  );
  const unsigned = `${header}.${body}`;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    b64urlToBytes(privPkcs8) as BufferSource,
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["sign"],
  );
  const sigDer = new Uint8Array(
    await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, te.encode(unsigned) as BufferSource),
  );
  // Web Crypto already returns raw r||s (64 bytes); only convert real DER.
  const sig = sigDer.length === 64 ? sigDer : derToRawEcdsa(sigDer);
  return `${unsigned}.${bytesToB64url(sig)}`;
}

/** Convert a DER-encoded ECDSA signature to the raw r||s form JWS expects. */
function derToRawEcdsa(der: Uint8Array): Uint8Array {
  // 0x30 len 0x02 rlen r... 0x02 slen s...
  let off = 2;
  if (der[1]! & 0x80) off = 2 + (der[1]! & 0x7f); // long-form length
  const readInt = (at: number): Uint8Array => {
    const len = der[at + 1]!;
    let start = at + 2;
    const end = start + len;
    while (end - start > 32 && der[start] === 0) start++;
    return der.subarray(start, end);
  };
  const r = readInt(off);
  const s = readInt(off + 2 + der[off + 1]!);
  const raw = new Uint8Array(64);
  raw.set(r, 32 - r.length);
  raw.set(s, 64 - s.length);
  return raw;
}

export interface PushTarget {
  endpoint: string;
  p256dh: string;
  auth: string;
}

/**
 * Encrypt and POST one web-push message. Returns true on success; false when
 * the subscription is gone (404/410) and should be deleted.
 */
export async function sendWebPush(
  target: PushTarget,
  payload: string,
  vapid: { subject: string; privPkcs8: string; pubRaw: string },
): Promise<boolean> {
  const uaPublic = b64urlToBytes(target.p256dh); // 65-byte uncompressed point
  const authSecret = b64urlToBytes(target.auth);

  // Ephemeral ECDH key pair
  const eph = (await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, [
    "deriveBits",
  ])) as CryptoKeyPair;
  const uaKey = await crypto.subtle.importKey(
    "raw",
    uaPublic as BufferSource,
    { name: "ECDH", namedCurve: "P-256" },
    false,
    [],
  );
  const shared = new Uint8Array(
    await crypto.subtle.deriveBits({ name: "ECDH", public: uaKey }, eph.privateKey, 256),
  );
  const ephPubRaw = new Uint8Array(
    await crypto.subtle.exportKey("raw", eph.publicKey),
  );

  // RFC 8291 key derivation
  const keyInfo = concat(te.encode("WebPush: info\0"), uaPublic, ephPubRaw);
  const ikm = await hkdf(authSecret, shared, keyInfo, 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, te.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, te.encode("Content-Encoding: nonce\0"), 12);

  // Plaintext: payload + 0x02 padding delimiter (single record)
  const plain = concat(te.encode(payload), new Uint8Array([2]));
  const aesKey = await crypto.subtle.importKey("raw", cek as BufferSource, "AES-GCM", false, ["encrypt"]);
  const cipher = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce as BufferSource }, aesKey, plain as BufferSource),
  );

  // aes128gcm content-coding header: salt | rs(4) | idlen(1) | keyid(eph pub)
  const rs = new Uint8Array([0, 0, 16, 0]);
  const body = concat(salt, rs, new Uint8Array([65]), ephPubRaw, cipher);

  const jwt = await vapidJwt(target.endpoint, vapid.subject, vapid.privPkcs8, vapid.pubRaw);
  const res = await fetch(target.endpoint, {
    method: "POST",
    headers: {
      TTL: "600",
      Urgency: "high",
      "Content-Encoding": "aes128gcm",
      "Content-Type": "application/octet-stream",
      Authorization: `vapid t=${jwt}, k=${vapid.pubRaw}`,
    },
    body: body as unknown as BodyInit,
  });
  if (res.status === 404 || res.status === 410) return false;
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`push send failed ${res.status}: ${text.slice(0, 200)}`);
  }
  return true;
}
