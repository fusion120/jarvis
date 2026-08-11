---
lang: html
keywords: tabs, tablist, tabpanel, aria-selected, roving tabindex, arrow keys, accessible tabs, tabpanel, tab navigation
---

# Accessible Tabs

When content needs to be split into tabs, implement the ARIA tabs pattern: a `tablist` of buttons, `tabpanel`s, and arrow-key navigation with roving `tabindex`. This is the pattern the W3C APG specifies.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARIA tabs</title>
<style>
  [role=tablist] { display: flex; gap: .25rem; border-bottom: 2px solid #ccc; }
  [role=tab] { padding: .5rem 1rem; border: 0; background: none; cursor: pointer; }
  [role=tab][aria-selected=true] { border-bottom: 3px solid #07c; font-weight: 700; }
  [role=tabpanel] { padding: 1rem 0; }
  [hidden] { display: none; }
</style>
</head>
<body>
  <div role="tablist" aria-label="Product info">
    <button role="tab" id="tab-desc" aria-controls="panel-desc" aria-selected="true">Description</button>
    <button role="tab" id="tab-spec" aria-controls="panel-spec" aria-selected="false" tabindex="-1">Specs</button>
  </div>
  <div role="tabpanel" id="panel-desc" aria-labelledby="tab-desc">Long description here.</div>
  <div role="tabpanel" id="panel-spec" aria-labelledby="tab-spec" hidden>Weight, dimensions...</div>
  <script>
    const tabs = [...document.querySelectorAll('[role=tab]')];
    const panels = [...document.querySelectorAll('[role=tabpanel]')];
    function select(tab, focus = false) {
      tabs.forEach(t => {
        const on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        if (on && focus) t.focus();
      });
      panels.forEach(p => { p.hidden = p.id !== tab.getAttribute('aria-controls'); });
    }
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => select(tab));
      tab.addEventListener('keydown', e => {
        const dir = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (!dir) return;
        e.preventDefault();
        select(tabs[(i + dir + tabs.length) % tabs.length], true);
      });
    });
  </script>
</body>
</html>
```

Gotchas:
- The visible tab and its panel must be linked both ways: `aria-controls` on the tab, `aria-labelledby` on the panel.
- Use roving `tabindex`: selected tab is `0`, others `-1`, so Tab lands on the group and arrows move inside — not Tab-to-every-tab.
- Arrow keys wrap (`(i + dir + len) % len`); support ArrowRight/Left (and Up/Down for vertical tablists) and Home/End.
- Hide inactive panels with the `hidden` attribute (not `display:none` classes) so the state is consistent for AT.
- Don't auto-rotate or auto-activate on hover — activation must be click/arrow only, or keyboard and SR users get surprise switches.
- If a panel's content is slow to build, lazy-render on first activation rather than preloading all tabs.
