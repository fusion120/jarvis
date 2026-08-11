---
lang: html
keywords: 3d transform, flip card, perspective, rotateY, preserve-3d, backface-visibility, css 3d, flip on hover
---

# 3D Transforms: Flip Card

A card that flips on hover/focus: `perspective` on the scene gives depth, `preserve-3d` keeps both faces in one 3D space, `backface-visibility: hidden` hides the mirrored reverse.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3D flip card</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 34rem; margin: 3rem auto; padding: 0 1rem; }
  .scene { perspective: 1000px; width: 16rem; height: 20rem; margin: 0 auto; }
  .card { position: relative; width: 100%; height: 100%; transform-style: preserve-3d;
          transition: transform .6s cubic-bezier(.4, .2, .2, 1); }
  .card:hover, .card:focus-within { transform: rotateY(180deg); }
  .face { position: absolute; inset: 0; backface-visibility: hidden; border-radius: 12px;
          display: grid; place-items: center; color: #fff; padding: 1rem; text-align: center; }
  .front { background: #07c; }
  .back { background: #b07; transform: rotateY(180deg); }
</style>
</head>
<body>
<h1>3D flip card</h1>
<div class="scene">
  <div class="card" tabindex="0" role="button" aria-label="Flip card to reveal answer">
    <div class="face front">Question: what makes the back face invisible?</div>
    <div class="face back">Answer: backface-visibility: hidden.</div>
  </div>
</div>
<p>Hover or focus to flip. <code>perspective</code> on the scene gives depth; <code>preserve-3d</code> keeps both faces in the same 3D space.</p>
</body>
</html>
```

Gotchas:
- Without `perspective` on an ancestor, `rotateY(180deg)` still runs but looks flat — the depth illusion comes from the scene's perspective, not the rotating element.
- `transform-style: preserve-3d` belongs on the ROTATING container, and it's ignored if the same element also has `overflow: hidden` or `clip-path`.
- `backface-visibility: hidden` is what hides the mirrored back; without it, the back face shows reversed text.
- The back face itself needs `rotateY(180deg)` or it appears upside-down when the card flips.
- `:focus-within` makes the flip keyboard-reachable; add `tabindex` + `role`/`aria-label` or keyboard users get an unlabeled div.
- Face children need `position: absolute; inset: 0` to match the card exactly — a static child won't center over the flip.
