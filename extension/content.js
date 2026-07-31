// ── JARVIS CONTENT SCRIPT ─────────────────────────────────────────────
// Injected into every page. Listens for messages from background.js.

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.type === 'READ_PAGE') {
    reply({
      url: location.href,
      title: document.title,
      text: document.body?.innerText?.slice(0, 8000) || '',
      html: document.documentElement.outerHTML.slice(0, 20000)
    });
  }
  return true;
});
