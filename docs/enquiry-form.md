# Enquiry form → EasyVisaFlow

The form in the "Book a free consultation" section posts to `/api/enquiry`
(`api/enquiry.js`, a Vercel function). Only that function talks to EVF; the key
never reaches the browser or the repo.

## Modes

| `EVF_LEADS_KEY` | Behaviour |
|---|---|
| not set | **Test mode.** Validates, logs the exact EVF payload to the Vercel function log, returns `LEA-MOCK-xxxx`. The form shows a small "Test mode" note. |
| set | **Live.** Verifies Turnstile, then POSTs to EVF. Refuses (503) if `TURNSTILE_SECRET_KEY` is missing. |

## Environment variables (Vercel → fineway → Settings → Environment Variables)

| Name | Needed for live | Value |
|---|---|---|
| `EVF_LEADS_KEY` | yes | From EVF → Settings → Integrations → Website leads |
| `EVF_LEADS_URL` | no | Default `https://easyvisaflow.com/api/public/leads` |
| `TURNSTILE_SITE_KEY` | yes | Cloudflare → Turnstile → widget → Site key (public) |
| `TURNSTILE_SECRET_KEY` | yes | Same widget → Secret key |
| `EVF_BOOKING_URL` | no | `https://easyvisaflow.com/book/<jki-slug>`; shows the "Book a consultation" links |
| `PRIVACY_NOTICE_URL` | no | Default `https://<host>/#privacy` |

Set them for the environment that serves the page (Preview for branch
`fineway-blue`, Production for `main`), then redeploy.

## Spam protection

- Honeypot field `website`: if filled, fake success, EVF is not called.
- Cloudflare Turnstile, verified server-side before EVF is called.
- Same-origin check on POST; EVF rate-limits per key and IP hash.

## Error handling

| EVF answer | Visitor sees |
|---|---|
| 201 | Form replaced by the confirmation, with the reference |
| 400 + field | Message under that field |
| 401 / 403 | Generic error + email (key problem logged) |
| 429 | "Too many requests, please email us" |
| 5xx / 10 s timeout | One automatic retry with the same Idempotency-Key, then generic error + email |

## The exact request the function sends

```
curl -i https://easyvisaflow.com/api/public/leads \
  -H "Authorization: Bearer $EVF_LEADS_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 3b241101-e2bb-4255-8caf-4136c566a962" \
  -d '{"fullName":"Klaus Weber","privacyConsent":true,"privacyNoticeUrl":"https://fineway.vercel.app/#privacy","email":"klaus@example.de","phone":"+4915112345678","enquirerType":"private","purpose":"retire","countryOfResidence":"DE","preferredLanguage":"en","message":"We want to retire to Cape Town next year.","pageUrl":"https://fineway.vercel.app/?utm_source=newsletter","utm":{"source":"newsletter"}}'
```

Fields sent only when filled: `email`, `phone`, `enquirerType`, `companyName`
(company only), `purpose`, `countryOfResidence`, `preferredLanguage`, `message`,
`pageUrl` (same host only), `utm`. Nothing else is ever forwarded.

## Placeholders to fill

- `CONTACT_EMAIL` near the top of the form script in `index.html` (shown when sending fails).
- The privacy notice: `#privacy` currently points to the footer link, not a real notice.
