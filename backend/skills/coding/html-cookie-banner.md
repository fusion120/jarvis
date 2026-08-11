---
lang: html
keywords: cookie consent, cookie banner, gdpr, consent, samesite, localStorage consent, accept reject, analytics opt-in
---

# Cookie Consent Banner

The GDPR-style consent flow: a fixed banner, Accept/Reject, the decision persisted in `localStorage`, and a first-party cookie written only after acceptance. Analytics (simulated) start only when the user opts in.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cookie consent</title>
<style>
  body { font: 16px/1.6 system-ui; margin: 0; }
  #banner { position: fixed; bottom: 1rem; left: 1rem; right: 1rem; max-width: 36rem; margin: auto;
            background: #fff; border: 1px solid #ddd; border-radius: 10px; box-shadow: 0 4px 20px rgb(0 0 0 / .15);
            padding: 1rem; display: flex; gap: 1rem; align-items: center; }
  #banner[hidden] { display: none; }
  button { padding: .5rem .9rem; cursor: pointer; border-radius: 6px; border: 1px solid #888; background: #fff; }
  #accept { background: #07c; color: #fff; border-color: #07c; }
</style>
</head>
<body>
<main style="max-width:40rem;margin:auto;padding:2rem 1rem">
  <h1>Cookie consent</h1>
  <p>Consent state is stored in localStorage; a first-party cookie is only written after the user accepts. Analytics (simulated here) start only on consent.</p>
</main>
<div id="banner" role="region" aria-label="Cookie consent">
  <p style="margin:0">We use cookies to improve your experience. See our <a href="#">privacy policy</a>.</p>
  <button id="accept">Accept</button>
  <button id="reject">Reject</button>
</div>
<script>
  const banner = document.getElementById('banner');
  const decide = consent => {
    localStorage.setItem('cookie-consent', consent);
    if (consent === 'accepted') {
      document.cookie = 'analytics=1; max-age=31536000; path=/; samesite=lax';
      console.log('Analytics would start now');
    } else {
      document.cookie = 'analytics=1; max-age=0; path=/';
    }
    banner.hidden = true;
  };
  document.getElementById('accept').addEventListener('click', () => decide('accepted'));
  document.getElementById('reject').addEventListener('click', () => decide('rejected'));
  // Hide immediately if a decision already exists.
  if (localStorage.getItem('cookie-consent')) banner.hidden = true;
</script>
</body>
</html>
```

Gotchas:
- Hide the banner on load when consent exists (ideally check in a head script) — a flash of the banner on every visit is a UX bug and a consent smell.
- Write the cookie ONLY after acceptance; rejection must delete existing analytics cookies, not just skip writing.
- `samesite=lax` (or `secure`) is the modern default; a cookie without SameSite is blocked as third-party by some browsers.
- localStorage holds the decision; cookies hold the actual signal. Don't put the consent flag itself in a cookie that analytics could read.
- Compliance needs a way to change the decision later (a "cookie settings" link) — one-shot banners alone don't satisfy GDPR.
- Don't track clicks or behavior on the banner itself until consent is given — pre-consent analytics is the violation.
