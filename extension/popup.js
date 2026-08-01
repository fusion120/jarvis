// ── JARVIS AGENT POPUP — popup.js ────────────────────────────────────
// External file because Manifest V3 blocks inline <script> in popups.

document.getElementById('btn-save').addEventListener('click', save);
document.getElementById('btn-test').addEventListener('click', testConn);

// Load saved settings on open
chrome.storage.local.get(['jarvis_url','jarvis_secret'], s => {
  if(s.jarvis_url)    document.getElementById('url').value    = s.jarvis_url;
  if(s.jarvis_secret) document.getElementById('secret').value = s.jarvis_secret;
});

// Show current tab
chrome.tabs.query({active:true,currentWindow:true}, tabs => {
  if(tabs[0]) {
    const t = tabs[0];
    document.getElementById('tab-row').textContent = '📄 ' + (t.title||t.url||'').slice(0,50);
  }
});

function save() {
  const url    = document.getElementById('url').value.trim().replace(/\/$/,'');
  const secret = document.getElementById('secret').value.trim();
  chrome.storage.local.set({jarvis_url: url, jarvis_secret: secret}, () => {
    // Tell the background service worker NOW so it starts polling immediately
    // (it only reads storage when it starts up — without this message it polls
    //  with an empty URL until you reload the extension).
    try { chrome.runtime.sendMessage({ type: 'SAVE_SETTINGS', backend: url, secret: secret }); } catch(e) {}
    showMsg('Saved! Testing connection...', 'ok');
    setTimeout(testConn, 500);
  });
}

async function testConn() {
  const url = document.getElementById('url').value.trim().replace(/\/$/,'');
  if(!url) { showMsg('Enter your backend URL first', 'err'); return; }

  setDot('yellow', 'Testing...');
  showMsg('', '');

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const r = await fetch(url + '/', { signal: controller.signal });
    clearTimeout(timer);
    const d = await r.json();
    if(d.status === 'online') {
      setDot('green', 'Connected ✓ — Jarvis is live');
      showMsg('Connection successful! Browser commands will work.', 'ok');
    } else {
      setDot('grey', 'Backend responded but looks wrong');
      showMsg('Unexpected response: ' + JSON.stringify(d).slice(0,80), 'err');
    }
  } catch(e) {
    const msg = e.name === 'AbortError' ? 'Timed out — Render might be sleeping' : e.message;
    setDot('grey', 'Cannot reach backend');
    showMsg('Failed: ' + msg + '. Wake up Render first by opening the URL in a tab.', 'err');
  }
}

function setDot(color, text) {
  const dot  = document.getElementById('dot');
  const stat = document.getElementById('status-text');
  dot.className = 'dot ' + color;
  stat.textContent = text;
}

function showMsg(text, type) {
  const el = document.getElementById('msg');
  el.textContent = text;
  el.className = 'msg' + (type ? ' '+type : '');
}
