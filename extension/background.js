// ── JARVIS BROWSER AGENT — background.js ─────────────────────────────
// Polls the Jarvis backend for commands and executes them in Chrome.

let BACKEND = '';
let SECRET  = '';
let connected = false;
let currentTab = { url: '', title: '' };
let polling = false;

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
        return { ok: true, data: res.result };
      }

      case 'screenshot': {
        const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'jpeg', quality: 60 });
        return { ok: true, screenshot: dataUrl };
      }

      case 'click_text': {
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (text) => {
            const all = [...document.querySelectorAll('button,a,[role=button],[role=menuitem],input[type=submit],input[type=button]')];
            const el = all.find(e => e.innerText?.trim().toLowerCase().includes(text.toLowerCase()) || e.value?.toLowerCase().includes(text.toLowerCase()) || e.getAttribute('aria-label')?.toLowerCase().includes(text.toLowerCase()) || e.getAttribute('title')?.toLowerCase().includes(text.toLowerCase()));
            if (el) { el.click(); return 'clicked: ' + el.innerText?.trim(); }
            // fallback: any element
            const any = [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && e.innerText?.trim().toLowerCase().includes(text.toLowerCase()));
            if (any) { any.click(); return 'clicked any: ' + any.innerText?.trim(); }
            return null;
          },
          args: [step.text]
        });
        return r.result ? { ok: true, done: r.result } : { ok: false, error: `"${step.text}" not found` };
      }

      case 'click_selector': {
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (sel) => { const el = document.querySelector(sel); if (el) { el.click(); return true; } return false; },
          args: [step.selector]
        });
        return { ok: !!r.result, done: r.result ? 'clicked' : 'selector not found' };
      }

      case 'type_selector': {
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (sel, val) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            el.focus();
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
          },
          args: [step.selector, step.value]
        });
        return { ok: !!r.result, done: r.result ? 'typed' : 'selector not found' };
      }

      case 'type_label': {
        // Find an input/textarea by its label text
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (labelText, val) => {
            // Try label element
            const labels = [...document.querySelectorAll('label')];
            const label = labels.find(l => l.innerText?.toLowerCase().includes(labelText.toLowerCase()));
            let el = label ? document.getElementById(label.htmlFor) || label.querySelector('input,textarea') : null;
            // Try placeholder
            if (!el) el = document.querySelector(`input[placeholder*="${labelText}" i], textarea[placeholder*="${labelText}" i]`);
            // Try aria-label
            if (!el) el = document.querySelector(`[aria-label*="${labelText}" i]`);
            if (!el) return false;
            el.focus();
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
          },
          args: [step.label, step.value]
        });
        return { ok: !!r.result, done: r.result ? `typed in "${step.label}"` : `label "${step.label}" not found` };
      }

      case 'search': {
        // Type into the site's search box and submit its form (real submit,
        // more reliable than a synthetic Enter for YouTube/Gmail/etc).
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (query) => {
            const q = (query || '').trim(); if (!q) return null;
            const inputs = [...document.querySelectorAll('input,textarea')]
              .filter(el => el.offsetParent !== null);
            const pick = inputs.find(el => /search|query|\bq\b/i.test((el.getAttribute('name')||'') + ' ' + (el.placeholder||'') + ' ' + (el.getAttribute('id')||'')))
              || inputs.find(el => el.type === 'search')
              || inputs[0];
            if (!pick) return 'no search input found';
            pick.focus();
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
              || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
            if (setter) setter.call(pick, q); else pick.value = q;
            pick.dispatchEvent(new Event('input', { bubbles: true }));
            pick.dispatchEvent(new Event('change', { bubbles: true }));
            const form = pick.closest('form');
            if (form && typeof form.requestSubmit === 'function') { form.requestSubmit(); return 'searched (form submit): ' + q; }
            const btn = (form && form.querySelector('[type=submit],button'))
              || document.querySelector('button[aria-label*="search" i],button[aria-label*="Search" i]');
            if (btn) { btn.click(); return 'searched (button): ' + q; }
            pick.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
            pick.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
            return 'searched (enter): ' + q;
          },
          args: [step.query]
        });
        return { ok: !!r.result, done: r.result || 'search failed' };
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
        const [r] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (key) => {
            document.activeElement?.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
            document.activeElement?.dispatchEvent(new KeyboardEvent('keypress', { key, bubbles: true }));
            document.activeElement?.dispatchEvent(new KeyboardEvent('keyup', { key, bubbles: true }));
            return true;
          },
          args: [step.key]
        });
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
              text: document.body?.innerText?.slice(0, 6000) || ''
            })
          });
          pageData = res.result;
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
  if (msg.type === 'GET_STATUS') {
    reply({ connected, currentTab, backend: BACKEND });
  }
  if (msg.type === 'SAVE_SETTINGS') {
    BACKEND = msg.backend.replace(/\/$/, '');
    SECRET  = msg.secret;
    chrome.storage.local.set({ jarvis_url: BACKEND, jarvis_secret: SECRET });
    reply({ ok: true });
  }
  return true;
});

// ── START POLLING ─────────────────────────────────────────────────────
(async () => {
  await loadSettings();
  setInterval(poll, 2000);
})();
