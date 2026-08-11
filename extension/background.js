// ── JARVIS BROWSER AGENT — background.js ─────────────────────────────
// Polls the Jarvis backend for commands and executes them in Chrome.

let BACKEND = '';
let SECRET  = '';
let connected = false;
let currentTab = { url: '', title: '' };

// ── LOAD SETTINGS ─────────────────────────────────────────────────────
async function loadSettings() {
  const s = await chrome.storage.local.get(['jarvis_url', 'jarvis_secret']);
  BACKEND = (s.jarvis_url || '').replace(/\/$/, '');
  SECRET  = s.jarvis_secret  || '';
}

// ── HEADERS ───────────────────────────────────────────────────────────
function headers(extra = {}) {
  return { 'Content-Type': 'application/json', 'X-Jarvis-Token': SECRET, ...extra };
}

// ── SHARED TYPING LOGIC ───────────────────────────────────────────────
// Injected into the page for the type / type_selector / type_label actions.
// Handles three kinds of field:
//   • <input>/<textarea>  → native value setter + InputEvent (works with
//     React / controlled inputs — a plain `el.value = x` does NOT trigger
//     React's onChange).
//   • contenteditable     → execCommand insertText (Gmail, X/Twitter,
//     Notion-style editors). This fires the real input pipeline, so
//     framework-controlled editors pick the text up.
const TYPE_INTO_FN = [
  "function typeInto(el, value) {",
  "  if (!el) return false;",
  "  el.focus();",
  "  if (el.isContentEditable) {",
  "    document.execCommand('selectAll', false, null);",
  "    document.execCommand('insertText', false, value);",
  "    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));",
  "    el.dispatchEvent(new Event('change', { bubbles: true }));",
  "    return true;",
  "  }",
  "  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;",
  "  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;",
  "  if (setter) setter.call(el, value); else el.value = value;",
  "  el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));",
  "  el.dispatchEvent(new Event('change', { bubbles: true }));",
  "  return true;",
  "}"
].join('\n');

// ── CROSS-FRAME HELPERS ────────────────────────────────────────────────
// Some login forms (Outlook, Google auth, etc.) render inside cross-origin
// iframes — top-frame-only queries find nothing. Run a script in every frame
// of the tab (top frame + all iframes) and return all frame results so the
// caller can pick the first hit. Requires only `scripting` + <all_urls>.
async function execAllFrames(tabId, func, args) {
  return await chrome.scripting.executeScript({
    target: { tabId, allFrames: true },
    func,
    args
  }).catch(() => []);
}

// Shared injected function: find a button/link/role element by visible text.
const CLICK_TEXT_FN = (text) => {
  const all = [...document.querySelectorAll('button,a,[role=button],[role=menuitem],input[type=submit],input[type=button]')];
  const el = all.find(e => e.innerText?.trim().toLowerCase().includes(text.toLowerCase()) || e.value?.toLowerCase().includes(text.toLowerCase()) || e.getAttribute('aria-label')?.toLowerCase().includes(text.toLowerCase()) || e.getAttribute('title')?.toLowerCase().includes(text.toLowerCase()));
  if (el) { el.click(); return 'clicked: ' + el.innerText?.trim(); }
  const any = [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && e.innerText?.trim().toLowerCase().includes(text.toLowerCase()));
  if (any) { any.click(); return 'clicked any: ' + any.innerText?.trim(); }
  return null;
};

// Shared injected function: find an input by label text / placeholder /
// aria-label and type into it. Works in any frame's document.
const TYPE_LABEL_FN = new Function('labelText', 'val', TYPE_INTO_FN + `
  const labels = [...document.querySelectorAll('label')];
  const label = labels.find(l => l.innerText?.toLowerCase().includes(labelText.toLowerCase()));
  let el = label ? document.getElementById(label.htmlFor) || label.querySelector('input,textarea,[contenteditable]') : null;
  if (!el) el = document.querySelector('input[placeholder*="' + labelText + '" i], textarea[placeholder*="' + labelText + '" i], [contenteditable][placeholder*="' + labelText + '" i]');
  if (!el) el = document.querySelector('[aria-label*="' + labelText + '" i]');
  if (!el) return null;
  return typeInto(el, val) ? true : false;
`);

// ── TRACK CURRENT TAB ─────────────────────────────────────────────────
chrome.tabs.onActivated.addListener(async (info) => {
  try {
    const tab = await chrome.tabs.get(info.tabId);
    currentTab = { url: tab.url || '', title: tab.title || '' };
    if (BACKEND) {
      fetch(`${BACKEND}/api/browser/tab`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify(currentTab)
      }).catch(() => {});
    }
  } catch {}
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.active) {
    currentTab = { url: tab.url || '', title: tab.title || '' };
  }
});

// ── TAB HELPERS ───────────────────────────────────────────────────────
async function findTabByTarget(target) {
  const tabs = await chrome.tabs.query({});
  if (target == null || target === '') return tabs.find(t => t.active) || tabs[0] || null;
  const s = String(target).trim().toLowerCase();
  if (/^\d+$/.test(s)) {
    const i = parseInt(s, 10);
    return tabs.find(t => t.index === i) || tabs[i] || null;
  }
  return tabs.find(t => (t.url || '').toLowerCase().includes(s))
      || tabs.find(t => (t.title || '').toLowerCase().includes(s)) || null;
}

// ── EXECUTE A SINGLE STEP ─────────────────────────────────────────────
async function execStep(step) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return { ok: false, error: 'No active tab' };

  try {
    switch (step.action) {

      case 'navigate':
        await chrome.tabs.update(tab.id, { url: step.url });
        await waitForLoad(tab.id);
        return { ok: true, done: 'navigated to ' + step.url };

      case 'new_tab':
        const newTab = await chrome.tabs.create({ url: step.url || 'about:blank' });
        await waitForLoad(newTab.id);
        return { ok: true, done: 'opened new tab' };

      case 'read_page': {
        const [res] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => ({
            url: location.href,
            title: document.title,
            text: document.body?.innerText?.slice(0, 12000) || '',
            inputs: [...document.querySelectorAll('input,textarea,select')]
              .map(el => ({ tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder, value: el.value }))
              .slice(0, 30),
            links: [...document.querySelectorAll('a[href]')]
              .map(el => ({ text: el.innerText?.trim(), href: el.href }))
              .filter(l => l.text)
              .slice(0, 80)
          })
        });
        const data = res.result || {};
        // Peek into iframes too — login forms (Outlook, Google, etc.) live in
        // cross-origin frames the top-frame query can't see. Surface their
        // inputs so the model knows the fields exist, then type/click handles
        // them via execAllFrames.
        try {
          const frames = await chrome.scripting.executeScript({
            target: { tabId: tab.id, allFrames: true },
            func: () => {
              if (window === window.top) return null;
              return {
                frameUrl: location.href.slice(0, 200),
                inputs: [...document.querySelectorAll('input,textarea,select')]
                  .map(el => ({ tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder, value: el.value }))
                  .slice(0, 15),
                text: (document.body?.innerText || '').slice(0, 1200)
              };
            }
          });
          const fds = (frames || []).map(f => f.result).filter(Boolean);
          if (fds.length) {
            data.frames = fds;
            for (const f of fds) {
              data.inputs = (data.inputs || []).concat(f.inputs).slice(0, 30);
            }
          }
        } catch {}
        return { ok: true, data };
      }

      case 'screenshot': {
        const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'jpeg', quality: 60 });
        return { ok: true, screenshot: dataUrl };
      }

      case 'click_text': {
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: CLICK_TEXT_FN,
          args: [step.text]
        });
        if (r.result) return { ok: true, done: r.result };
        // Element may live in an iframe (Outlook / Google auth forms)
        const f = await execAllFrames(tab.id, CLICK_TEXT_FN, [step.text]);
        const hit = f.find(r => r.result);
        if (hit) return { ok: true, done: hit.result + ' (in iframe)' };
        return { ok: false, error: `"${step.text}" not found` };
      }

      case 'click_selector': {
        const fn = (sel) => { const el = document.querySelector(sel); if (el) { el.click(); return true; } return false; };
        const f = await execAllFrames(tab.id, fn, [step.selector]);
        const hit = f.find(r => r.result === true);
        return { ok: !!hit, done: hit ? 'clicked' : 'selector not found' };
      }

      case 'type_selector': {
        const fn = new Function('sel', 'val', TYPE_INTO_FN + `
          const el = document.querySelector(sel);
          if (!el) return false;
          return typeInto(el, val);
        `);
        const f = await execAllFrames(tab.id, fn, [step.selector, step.value]);
        const hit = f.find(r => r.result === true);
        return { ok: !!hit, done: hit ? 'typed' : 'selector not found' };
      }

      case 'type_label': {
        // Find an input/textarea/contenteditable by its label text, type.
        // Runs across all frames (top + iframes) so Outlook/Google login
        // fields inside cross-origin iframes are reachable.
        const f = await execAllFrames(tab.id, TYPE_LABEL_FN, [step.label, step.value]);
        const hit = f.find(r => r.result === true);
        if (hit) return { ok: true, done: 'typed in "' + step.label + '"' };
        const miss = f.find(r => r.result === false);
        if (miss) return { ok: false, error: 'found "' + step.label + '" but could not type into it' };
        return { ok: false, error: 'label "' + step.label + '" not found' };
      }

      case 'type': {
        // Type into whatever field is currently focused on the page. Focus
        // can live inside an iframe, so scan every frame's activeElement.
        if (!step.value) return { ok: false, error: 'no text provided to type' };
        const fn = new Function('value', TYPE_INTO_FN + `
          const el = document.activeElement;
          if (!el || el === document.body || el === document.documentElement) return 'none';
          if (el.tagName === 'INPUT') {
            const t = (el.type || 'text').toLowerCase();
            if (['button','submit','reset','checkbox','radio','range','color','file','hidden','image'].includes(t)) return 'not-editable';
          }
          if (el.tagName !== 'TEXTAREA' && el.tagName !== 'INPUT' && !el.isContentEditable) return 'not-editable';
          return typeInto(el, value) ? 'typed' : 'failed';
        `);
        const f = await execAllFrames(tab.id, fn, [step.value]);
        const typed = f.find(r => r.result === 'typed');
        const st = typed ? 'typed' : (f.find(r => r.result)?.result || 'none');
        if (st === 'typed') return { ok: true, done: 'typed into focused field' };
        if (st === 'none') return { ok: false, error: 'no field is focused — click one first' };
        return { ok: false, error: 'focused element is not a text field' };
      }

      case 'search': {
        const q = (step.query || '').trim();
        // Known sites: jump straight to the site's search-results URL instead of
        // fighting autocomplete widgets + submit handlers. Google/YouTube swallow
        // programmatic submits (Google even tags the tab with a ?zx= marker),
        // so typing into the box is unreliable — the results URL always works.
        // new_tab/navigate already wait for the page to load before this runs.
        let directUrl = null;
        try {
          const host = new URL(tab.url || '').hostname;
          const enc = encodeURIComponent(q);
          if (/(^|\.)youtube\.com$/.test(host)) directUrl = 'https://www.youtube.com/results?search_query=' + enc;
          else if (/(^|\.)google\.\w/.test(host)) directUrl = 'https://www.google.com/search?q=' + enc;
          else if (/(^|\.)wikipedia\.org$/.test(host)) directUrl = 'https://' + host + '/w/index.php?search=' + enc;
          else if (/(^|\.)bing\.com$/.test(host)) directUrl = 'https://www.bing.com/search?q=' + enc;
          else if (/(^|\.)duckduckgo\.com$/.test(host)) directUrl = 'https://duckduckgo.com/?q=' + enc;
          else if (/(^|\.)amazon\.\w/.test(host)) directUrl = 'https://' + host + '/s?k=' + enc;
          else if (/(^|\.)reddit\.com$/.test(host)) directUrl = 'https://' + host + '/search/?q=' + enc;
          else if (/(^|\.)github\.com$/.test(host)) directUrl = 'https://github.com/search?q=' + enc;
          else if (/(^|\.)(twitter|x)\.com$/.test(host)) directUrl = 'https://' + host + '/search?q=' + enc;
        } catch {}
        if (q && directUrl) {
          try {
            await chrome.tabs.update(tab.id, { url: directUrl });
            return { ok: true, done: 'searched (results URL): ' + q.slice(0, 50) };
          } catch {}
        }
        // Unknown site: type into the page's own search box (native setter +
        // InputEvent + suggestion click + Enter + submit), direct-nav last resort.
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: async (query) => {
            const qq = (query || '').trim(); if (!qq) return null;
            const inputs = [...document.querySelectorAll('input,textarea')]
              .filter(el => el.offsetParent !== null);
            const pick = inputs.find(el => /search|query|\bq\b/i.test(
                    (el.getAttribute('name')||'') + ' ' + (el.placeholder||'') + ' ' + (el.getAttribute('id')||'')))
              || inputs.find(el => el.type === 'search')
              || inputs[0];
            if (!pick) return 'no search input found';
            pick.focus();
            // Set value using native setter + InputEvent (works for React/controlled inputs)
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
              || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
            if (setter) setter.call(pick, qq); else pick.value = qq;
            pick.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: qq }));
            pick.dispatchEvent(new Event('change', { bubbles: true }));
            // Give autocomplete suggestions a moment to render, then try, in order:
            //   1) click the top suggestion (Wikipedia/Google style) -> direct nav
            //   2) Enter on the input (what SPA search listens for)
            //   3) real form submit / submit button
            await new Promise(res => setTimeout(res, 400));
            const before = location.href;
            const sug = document.querySelector(
              '.suggestions-results a, .suggestions-result, .autocomplete-suggestion, ' +
              'li[role="option"] a, .oo-ui-menuSelectWidget [role="option"]');
            if (sug) { try { sug.click(); return 'searched (top suggestion): ' + qq; } catch {} }
            pick.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
            pick.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
            pick.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
            await new Promise(res => setTimeout(res, 300));
            if (location.href !== before) return 'searched (enter navigated): ' + qq;
            const form = pick.closest('form');
            if (form && typeof form.requestSubmit === 'function') {
              try { form.requestSubmit(); return 'searched (form submit): ' + qq; } catch {}
            }
            if (form) {
              const btn = form.querySelector('[type=submit],button[type=submit],input[type=submit]');
              if (btn) { btn.click(); return 'searched (submit button): ' + qq; }
            }
            // Last resort: if the page didn't navigate, jump straight to the
            // site's search-results URL (guaranteed to run the query).
            const h = location.hostname;
            let direct = null;
            try {
              if (/(^|\.)youtube\.com$/.test(h)) direct = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(qq);
              else if (/(^|\.)google\.\w/.test(h)) direct = 'https://www.google.com/search?q=' + encodeURIComponent(qq);
              else if (/(^|\.)wikipedia\.org$/.test(h)) direct = 'https://' + h + '/w/index.php?search=' + encodeURIComponent(qq);
              else if (/(^|\.)bing\.com$/.test(h)) direct = 'https://www.bing.com/search?q=' + encodeURIComponent(qq);
              else if (/(^|\.)duckduckgo\.com$/.test(h)) direct = 'https://duckduckgo.com/?q=' + encodeURIComponent(qq);
              else if (/(^|\.)amazon\.\w/.test(h)) direct = 'https://' + h + '/s?k=' + encodeURIComponent(qq);
              else if (/(^|\.)reddit\.com$/.test(h)) direct = 'https://' + h + '/search/?q=' + encodeURIComponent(qq);
              else if (/(^|\.)github\.com$/.test(h)) direct = 'https://github.com/search?q=' + encodeURIComponent(qq);
              else if (/(^|\.)(twitter|x)\.com$/.test(h)) direct = 'https://' + h + '/search?q=' + encodeURIComponent(qq);
            } catch {}
            if (direct) return 'nav:' + direct;
            return 'typed but could not submit: ' + qq;
          },
          args: [step.query]
        });
        const res = r?.result || 'search failed';
        const ok = !!res && !res.startsWith('no search input') && !res.startsWith('search failed');
        if (typeof res === 'string' && res.startsWith('nav:')) {
          try {
            await chrome.tabs.update(tab.id, { url: res.slice(4) });
            return { ok: true, done: 'searched (direct nav): ' + q.slice(0, 50) };
          } catch {}
        }
        return { ok, done: res };
      }

      case 'run_js': {
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: new Function(step.code),
        });
        return { ok: true, data: r.result };
      }

      case 'scroll': {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (x, y) => window.scrollBy(x, y),
          args: [step.x || 0, step.y || 500]
        });
        return { ok: true, done: 'scrolled' };
      }

      case 'wait':
        await sleep(step.ms || 1000);
        return { ok: true, done: `waited ${step.ms || 1000}ms` };

      case 'press_key': {
        // Dispatch to the focused element in every frame — the field may be
        // inside an iframe, and only that frame's document sees it as focused.
        const fn = (key) => {
          document.activeElement?.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
          document.activeElement?.dispatchEvent(new KeyboardEvent('keypress', { key, bubbles: true }));
          document.activeElement?.dispatchEvent(new KeyboardEvent('keyup', { key, bubbles: true }));
          return true;
        };
        await execAllFrames(tab.id, fn, [step.key]);
        return { ok: true, done: `pressed ${step.key}` };
      }

      case 'list_tabs': {
        const tabs = await chrome.tabs.query({});
        const list = tabs
          .filter(t => t.url && t.url.startsWith('http'))
          .map(t => ({ index: t.index, url: t.url, title: t.title || '', active: !!t.active }))
          .slice(0, 40);
        return { ok: true, done: JSON.stringify(list) };
      }

      case 'read_tab': {
        const target = await findTabByTarget(step.tab);
        if (!target) return { ok: false, error: `tab "${step.tab}" not found` };
        const [res] = await chrome.scripting.executeScript({
          target: { tabId: target.id },
          func: () => ({ url: location.href, title: document.title, text: (document.body?.innerText || '').slice(0, 8000) })
        });
        const r = res.result || {};
        return { ok: true, done: `[${r.title}] ${r.url}\n${(r.text || '').slice(0, 8000)}` };
      }

      case 'switch_tab': {
        const target = await findTabByTarget(step.tab);
        if (!target) return { ok: false, error: `tab "${step.tab}" not found` };
        await chrome.tabs.update(target.id, { active: true });
        await chrome.windows.update(target.windowId, { focused: true }).catch(() => {});
        return { ok: true, done: `switched to "${target.title || target.url}"` };
      }

      case 'close_tab': {
        if (step.tab) {
          const target = await findTabByTarget(step.tab);
          if (!target) return { ok: false, error: `tab "${step.tab}" not found` };
          await chrome.tabs.remove(target.id);
          return { ok: true, done: `closed "${target.title || target.url}"` };
        }
        await chrome.tabs.remove(tab.id);
        return { ok: true, done: 'closed current tab' };
      }

      case 'go_back':
        await chrome.tabs.goBack(tab.id);
        await waitForLoad(tab.id);
        return { ok: true, done: 'went back' };

      case 'go_forward':
        await chrome.tabs.goForward(tab.id);
        await waitForLoad(tab.id);
        return { ok: true, done: 'went forward' };

      case 'new_window': {
        await chrome.windows.create({ url: step.url || 'about:blank' });
        return { ok: true, done: 'opened new window' };
      }

      case 'group_tabs': {
        const kw = (step.keyword || '').toLowerCase();
        const tabs = (await chrome.tabs.query({}))
          .filter(t => t.url && t.url.startsWith('http') &&
                  (!kw || (t.title || '').toLowerCase().includes(kw) || (t.url || '').toLowerCase().includes(kw)));
        if (tabs.length < 2) return { ok: true, done: kw ? `only ${tabs.length} tab matches "${kw}"` : 'not enough tabs to group' };
        const groupId = await chrome.tabs.group({ tabIds: tabs.map(t => t.id) });
        if (kw) await chrome.tabGroups.update(groupId, { title: kw }).catch(() => {});
        return { ok: true, done: `grouped ${tabs.length} tabs${kw ? ` into "${kw}"` : ''}` };
      }

      case 'save_session': {
        const tabs = (await chrome.tabs.query({})).filter(t => t.url && t.url.startsWith('http'));
        const urls = tabs.map(t => t.url);
        const r = await fetch(`${BACKEND}/api/browser/session`, {
          method: 'POST', headers: headers(), body: JSON.stringify({ urls })
        }).catch(() => null);
        return { ok: !!r, done: `saved ${urls.length} tabs${r ? '' : ' (backend unreachable)'}` };
      }

      case 'restore_session': {
        const r = await fetch(`${BACKEND}/api/browser/session`, { headers: headers() }).catch(() => null);
        const urls = r ? (await r.json()).urls : [];
        if (!urls || !urls.length) return { ok: false, error: 'no saved session found' };
        await chrome.tabs.create({ url: urls[0] });
        for (const u of urls.slice(1)) await chrome.tabs.create({ url: u });
        return { ok: true, done: `restored ${urls.length} tabs` };
      }

      case 'save_tab': {
        const [res] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => ({ url: location.href, title: document.title, text: (document.body?.innerText || '').slice(0, 3000) })
        });
        const r = res.result || {};
        const post = await fetch(`${BACKEND}/api/research-log`, {
          method: 'POST', headers: headers(),
          body: JSON.stringify({ title: r.title, url: r.url, text: r.text, label: step.label || '' })
        }).catch(() => null);
        return { ok: !!post, done: post ? `saved "${r.title}" to research log` : 'backend unreachable — could not save' };
      }

      case 'collect_tabs': {
        const tabs = (await chrome.tabs.query({})).filter(t => t.url && t.url.startsWith('http'));
        const urls = tabs.map(t => t.url);
        const r = await fetch(`${BACKEND}/api/bulk-scrape`, {
          method: 'POST', headers: headers(),
          body: JSON.stringify({ urls, label: step.label || 'tabs' })
        }).catch(() => null);
        if (!r) return { ok: false, error: 'backend unreachable' };
        const d = await r.json().catch(() => ({}));
        return { ok: true, done: `scraped ${d.saved || 0} of ${urls.length} open tabs into the research log` };
      }

      default:
        return { ok: false, error: `Unknown action: ${step.action}` };
    }
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ── EXECUTE A TASK (sequence of steps) ────────────────────────────────
async function runTask(task) {
  const log = [];
  for (const step of task.steps || []) {
    const result = await execStep(step);
    log.push({ step: step.action, ...result });
    if (!result.ok && !step.optional) break;
    // Auto-wait after navigate/click actions
    if (['navigate', 'new_tab', 'click_text', 'click_selector'].includes(step.action) && !task.steps.find((s,i) => task.steps.indexOf(s) > task.steps.indexOf(step) && s.action === 'wait')) {
      await sleep(1200);
    }
  }
  return log;
}

// ── POLL BACKEND FOR COMMANDS ─────────────────────────────────────────
async function poll() {
  if (!BACKEND) return;
  try {
    const r = await fetch(`${BACKEND}/api/browser/poll`, {
      headers: headers(),
      signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) { connected = false; return; }
    connected = true;
    const data = await r.json();

    if (data.task) {
      // Execute task
      const log = await runTask(data.task);
      // Get current page state for AI context
      let pageData = null;
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
          const [res] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => ({
              url: location.href,
              title: document.title,
              text: document.body?.innerText?.slice(0, 12000) || '',
              inputs: [...document.querySelectorAll('input,textarea,select')]
                .map(el => ({ tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder }))
                .slice(0, 20),
              links: [...document.querySelectorAll('a')]
                .map(a => ({ text: (a.innerText || a.getAttribute('title') || '').trim(), href: a.href }))
                .filter(l => l.text && l.href && l.href.startsWith('http'))
                .slice(0, 60)
            })
          });
          pageData = res.result || {};
          // Include iframe inputs (login forms inside cross-origin frames)
          try {
            const frames = await chrome.scripting.executeScript({
              target: { tabId: tab.id, allFrames: true },
              func: () => {
                if (window === window.top) return null;
                return {
                  frameUrl: location.href.slice(0, 200),
                  inputs: [...document.querySelectorAll('input,textarea,select')]
                    .map(el => ({ tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder }))
                    .slice(0, 15)
                };
              }
            });
            const fds = (frames || []).map(f => f.result).filter(Boolean);
            if (fds.length) {
              pageData.frames = fds;
              for (const f of fds) {
                pageData.inputs = (pageData.inputs || []).concat(f.inputs).slice(0, 25);
              }
            }
          } catch {}
        }
      } catch {}

      await fetch(`${BACKEND}/api/browser/result`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ task_id: data.task.id, log, page: pageData })
      });

      // Show Chrome notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
        title: 'Jarvis',
        message: `Task done: ${log.map(l => l.done || l.error).filter(Boolean).join(' → ')}`
      });
    }
  } catch (e) {
    connected = false;
  }
}

// ── HELPERS ───────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function waitForLoad(tabId) {
  return new Promise((resolve) => {
    const timeout = setTimeout(resolve, 8000);
    const listener = (id, info) => {
      if (id === tabId && info.status === 'complete') {
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        setTimeout(resolve, 500); // Extra settle time
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
  });
}

// ── MESSAGE FROM POPUP ─────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.type === 'GET_STATUS' || msg.type === 'WAKE') {
    pollLoop();  // Wakes/restarts polling when the user opens the popup or dashboard
    reply({ connected, currentTab, backend: BACKEND });
  }
  if (msg.type === 'SAVE_SETTINGS') {
    BACKEND = msg.backend.replace(/\/$/, '');
    SECRET  = msg.secret;
    chrome.storage.local.set({ jarvis_url: BACKEND, jarvis_secret: SECRET });
    pollLoop();
    reply({ ok: true });
  }
  return true;
});

// ── START POLLING ─────────────────────────────────────────────────────
// A self-sustaining loop (one poll at a time, then a fresh 2s timer) so
// there's always a pending timer. chrome.alarms is the backstop: Chrome
// force-kills MV3 service workers after ~5 min of continuous runtime, and
// only an alarm (or a runtime message) can wake it again. The alarm fires
// every 30s, so even after a kill, polling resumes within half a minute.
let polling = false;
async function pollLoop() {
  if (polling) return;
  polling = true;
  try {
    await poll();
  } catch (e) {
    connected = false;
  } finally {
    polling = false;
  }
  setTimeout(pollLoop, 2000);
}

(async () => {
  await loadSettings();
  pollLoop();
  try {
    chrome.alarms.create('jarvis-poll', { periodInMinutes: 0.5 });
  } catch (e) {}
})();

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jarvis-poll') pollLoop();
});
