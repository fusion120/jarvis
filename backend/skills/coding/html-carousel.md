---
lang: html
keywords: carousel, slider, slideshow, autoplay, dots indicator, prev next, transform track, aria-roledescription, pause on hover
---

# Carousel / Slider

A simple image-style carousel: a flex track translated by `transform`, prev/next buttons, dot indicators, and autoplay that pauses on hover. Use for hero highlight rotators, not for critical content — carousels hide information.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carousel</title>
<style>
  .carousel { position: relative; max-width: 30rem; margin: 2rem auto; overflow: hidden; border-radius: 10px; }
  .track { display: flex; transition: transform .4s ease; }
  .slide { flex: 0 0 100%; aspect-ratio: 16/9; display: grid; place-items: center; color: #fff; font-size: 2rem; }
  .btn { position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; border: 0; background: rgb(0 0 0 / .4); color: #fff; font-size: 1.5rem; padding: .5rem .75rem; cursor: pointer; border-radius: 50%; }
  .prev { left: .5rem; } .next { right: .5rem; }
  .dots { position: absolute; bottom: .5rem; left: 0; right: 0; display: flex; justify-content: center; gap: .4rem; }
  .dots button { width: 10px; height: 10px; border-radius: 50%; border: 0; background: rgb(255 255 255 / .6); cursor: pointer; padding: 0; }
  .dots button.active { background: #fff; }
</style>
</head>
<body>
<div class="carousel" aria-roledescription="carousel" aria-label="Highlights">
  <div class="track" id="track">
    <div class="slide" style="background:#07c">Slide 1</div>
    <div class="slide" style="background:#a50">Slide 2</div>
    <div class="slide" style="background:#0a5">Slide 3</div>
  </div>
  <button class="btn prev" aria-label="Previous slide">&#8249;</button>
  <button class="btn next" aria-label="Next slide">&#8250;</button>
  <div class="dots" id="dots"></div>
</div>
<script>
  const track = document.getElementById('track');
  const slides = [...track.children];
  const dotsBox = document.getElementById('dots');
  let i = 0, timer;
  slides.forEach((s, n) => {
    const b = document.createElement('button');
    b.setAttribute('aria-label', 'Go to slide ' + (n + 1));
    b.addEventListener('click', () => go(n));
    dotsBox.append(b);
  });
  const dots = [...dotsBox.children];
  function go(n) {
    i = (n + slides.length) % slides.length;
    track.style.transform = `translateX(-${i * 100}%)`;
    dots.forEach((d, k) => d.classList.toggle('active', k === i));
  }
  document.querySelector('.prev').addEventListener('click', () => go(i - 1));
  document.querySelector('.next').addEventListener('click', () => go(i + 1));
  const carousel = document.querySelector('.carousel');
  function play() { timer = setInterval(() => go(i + 1), 3000); }
  carousel.addEventListener('mouseenter', () => clearInterval(timer));
  carousel.addEventListener('mouseleave', play);
  go(0); play();
</script>
</body>
</html>
```

Gotchas:
- The track must be `flex` with `flex: 0 0 100%` slides; `translateX` percentages refer to the track width, so `-${i * 100}%` steps exactly one slide.
- Autoplay must pause on hover AND focus (`mouseenter`/`focusin`) and be disabled entirely under `prefers-reduced-motion`.
- Recreate the timer on `mouseleave` — clearing without restarting leaves the carousel dead.
- Don't use `scrollLeft` on a wrapping container for equal-width slides; transform-based stepping is predictable and animatable.
- Mark the region `aria-roledescription="carousel"`; a plain changing div is invisible to screen readers, and rapidly rotating content is an AT hazard.
- If slides carry different widths or content, cap slide count (3-4) and add prev/next keyboard support.
