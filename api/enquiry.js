// fineway enquiry form -> EasyVisaFlow (EVF) leads.
// Vercel serverless function. The browser posts here; only this code talks to EVF.
//
// Env vars (Vercel project settings, never in code):
//   EVF_LEADS_KEY         EVF website-leads key. Unset = MOCK MODE (logs payload, returns fake reference).
//   EVF_LEADS_URL         Default https://easyvisaflow.com/api/public/leads
//   TURNSTILE_SITE_KEY    Cloudflare Turnstile public site key (sent to the browser via GET).
//   TURNSTILE_SECRET_KEY  Cloudflare Turnstile secret. Required once EVF_LEADS_KEY is set.
//   EVF_BOOKING_URL       Optional. https://easyvisaflow.com/book/<jki-slug> - shows the "Book a consultation" link.
//   PRIVACY_NOTICE_URL    Optional. Default https://<this host>/#privacy

'use strict';
const crypto = require('crypto');

const EVF_DEFAULT_URL = 'https://easyvisaflow.com/api/public/leads';
const TIMEOUT_MS = 10000;
const PURPOSES = ['visit', 'work', 'study', 'retire', 'join_family', 'business', 'remote_work', 'pr', 'other'];
const UTM_KEYS = ['source', 'medium', 'campaign', 'term', 'content'];
const ISO2 = /^[A-Z]{2}$/;
const E164 = /^\+[1-9]\d{6,14}$/;
const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const env = (k) => (process.env[k] || '').trim();
const isLive = () => env('EVF_LEADS_KEY') !== '';

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return JSON.parse(req.body);
  let raw = '';
  for await (const chunk of req) {
    raw += chunk;
    if (raw.length > 20000) throw new Error('too large');
  }
  return raw ? JSON.parse(raw) : {};
}

function str(v, max) {
  if (typeof v !== 'string') return '';
  return v.trim().slice(0, max + 1);
}

// Returns { lead } or { field, error }. Builds the EVF body from an allow-list only.
function validate(input, ctx) {
  const fullName = str(input.fullName, 200);
  if (!fullName) return { field: 'fullName', error: 'Please enter your name.' };
  if (fullName.length > 200) return { field: 'fullName', error: 'Please shorten your name to 200 characters.' };

  const email = str(input.email, 320).toLowerCase();
  const phone = str(input.phone, 20).replace(/[\s()-]/g, '');
  if (!email && !phone) return { field: 'email', error: 'Please give an email address or a phone number.' };
  if (email && !EMAIL.test(email)) return { field: 'email', error: 'This email address looks incomplete.' };
  if (phone && !E164.test(phone)) return { field: 'phone', error: 'Please check the phone number and country code.' };

  const enquirerType = input.enquirerType === 'company' ? 'company' : input.enquirerType === 'private' ? 'private' : '';
  const companyName = str(input.companyName, 200);
  if (enquirerType === 'company' && !companyName) return { field: 'companyName', error: 'Please enter the company name.' };

  const purpose = PURPOSES.includes(input.purpose) ? input.purpose : '';
  const countryOfResidence = ISO2.test(input.countryOfResidence || '') ? input.countryOfResidence : '';
  const preferredLanguage = /^[a-z]{2}$/.test(input.preferredLanguage || '') ? input.preferredLanguage : '';

  const message = str(input.message, 4000);
  if (message.length > 4000) return { field: 'message', error: 'Please shorten your message to 4,000 characters.' };

  if (input.privacyConsent !== true) return { field: 'privacyConsent', error: 'Please confirm you have read the privacy notice.' };

  const lead = { fullName, privacyConsent: true, privacyNoticeUrl: ctx.privacyNoticeUrl };
  if (email) lead.email = email;
  if (phone) lead.phone = phone;
  if (enquirerType) lead.enquirerType = enquirerType;
  if (enquirerType === 'company') lead.companyName = companyName;
  if (purpose) lead.purpose = purpose;
  if (countryOfResidence) lead.countryOfResidence = countryOfResidence;
  if (preferredLanguage) lead.preferredLanguage = preferredLanguage;
  if (message) lead.message = message;

  const pageUrl = str(input.pageUrl, 2000);
  try { if (pageUrl && new URL(pageUrl).host === ctx.host) lead.pageUrl = pageUrl; } catch (_) { /* ignore */ }

  if (input.utm && typeof input.utm === 'object') {
    const utm = {};
    for (const k of UTM_KEYS) { const v = str(input.utm[k], 200); if (v) utm[k] = v; }
    if (Object.keys(utm).length) lead.utm = utm;
  }
  return { lead };
}

async function verifyTurnstile(token, ip) {
  const body = new URLSearchParams({ secret: env('TURNSTILE_SECRET_KEY'), response: token || '' });
  if (ip) body.set('remoteip', ip);
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST', body, signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const j = await r.json();
    return j.success === true;
  } catch (e) {
    console.error('[enquiry] turnstile verify failed:', e.message);
    return false;
  }
}

async function postToEvf(lead, idemKey) {
  const r = await fetch(env('EVF_LEADS_URL') || EVF_DEFAULT_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env('EVF_LEADS_KEY')}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': idemKey,
    },
    body: JSON.stringify(lead),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  let j = {};
  try { j = await r.json(); } catch (_) { /* non-JSON */ }
  return { status: r.status, body: j };
}

module.exports = async function handler(req, res) {
  const host = req.headers['x-forwarded-host'] || req.headers.host || '';

  // GET: public config for the form (no secrets).
  if (req.method === 'GET') {
    return send(res, 200, {
      turnstileSiteKey: env('TURNSTILE_SITE_KEY') || null,
      bookingUrl: env('EVF_BOOKING_URL') || null,
      mock: !isLive(),
    });
  }
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'GET, POST');
    return send(res, 405, { ok: false, error: 'method_not_allowed' });
  }

  // Same-origin only.
  const origin = req.headers.origin;
  if (origin) {
    try { if (new URL(origin).host !== host) return send(res, 403, { ok: false, error: 'forbidden' }); }
    catch (_) { return send(res, 403, { ok: false, error: 'forbidden' }); }
  }

  let input;
  try { input = await readJson(req); } catch (_) { return send(res, 400, { ok: false, error: 'Invalid request.' }); }

  // Honeypot: pretend success, never call EVF.
  if (str(input.website, 200)) {
    return send(res, 201, { ok: true, reference: `LEA-${new Date().getFullYear()}-${String(crypto.randomInt(1000, 9999))}` });
  }

  const ctx = { host, privacyNoticeUrl: env('PRIVACY_NOTICE_URL') || `https://${host}/#privacy` };
  const v = validate(input, ctx);
  if (v.error) return send(res, 400, { ok: false, field: v.field, error: v.error });

  const idemKey = UUID.test(input.idempotencyKey || '') ? input.idempotencyKey : crypto.randomUUID();
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();

  // ---- MOCK MODE: no EVF key yet ----
  if (!isLive()) {
    if (env('TURNSTILE_SECRET_KEY') && !(await verifyTurnstile(input.turnstileToken, ip))) {
      return send(res, 400, { ok: false, field: 'turnstile', error: 'Please complete the check above the button.' });
    }
    console.log('[enquiry][MOCK] would POST to EVF', JSON.stringify({ idempotencyKey: idemKey, lead: v.lead }));
    const ref = `LEA-MOCK-${String(crypto.randomInt(0, 10000)).padStart(4, '0')}`;
    return send(res, 201, { ok: true, reference: ref, mock: true });
  }

  // ---- LIVE ----
  if (!env('TURNSTILE_SECRET_KEY')) {
    console.error('[enquiry] EVF_LEADS_KEY is set but TURNSTILE_SECRET_KEY is missing - refusing to forward.');
    return send(res, 503, { ok: false, error: 'unavailable' });
  }
  if (!(await verifyTurnstile(input.turnstileToken, ip))) {
    return send(res, 400, { ok: false, field: 'turnstile', error: 'Please complete the check above the button.' });
  }

  let result;
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      result = await postToEvf(v.lead, idemKey);
      if (result.status < 500) break;
      console.error(`[enquiry] EVF ${result.status} (attempt ${attempt})`);
    } catch (e) {
      result = { status: 504, body: {} };
      console.error(`[enquiry] EVF request failed (attempt ${attempt}):`, e.name);
    }
  }

  const { status, body } = result;
  if (status === 201 || status === 200) return send(res, 201, { ok: true, reference: body.reference || null });
  if (status === 400) return send(res, 400, { ok: false, field: body.field || null, error: body.error || 'Please check your details.' });
  if (status === 429) return send(res, 429, { ok: false, error: 'rate_limited' });
  if (status === 401 || status === 403) console.error(`[enquiry] EVF rejected the key (${status}). Check EVF_LEADS_KEY.`);
  return send(res, 502, { ok: false, error: 'unavailable' });
};

module.exports.validate = validate; // for tests
