---
lang: html
keywords: audio player, audio element, wav, OfflineAudioContext, Web Audio, seek, play pause, generated audio, mediaelement
---

# Custom Audio Player

A play/pause/seek bar for the `<audio>` element, driven by the currentTime/duration events. The sample track is synthesized in-browser into a WAV blob so the demo needs no hosted file.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audio player</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  .player { display: flex; align-items: center; gap: 1rem; border: 1px solid #ddd; border-radius: 10px; padding: 1rem; }
  button { padding: .5rem 1rem; cursor: pointer; }
  input[type=range] { flex: 1; }
  #time { font-variant-numeric: tabular-nums; color: #555; min-width: 6rem; }
</style>
</head>
<body>
<h1>Audio player</h1>
<div class="player">
  <button id="play" aria-label="Play">&#9654;</button>
  <input id="seek" type="range" min="0" max="100" value="0" aria-label="Seek">
  <span id="time">0:00 / 0:00</span>
</div>
<p>This demo synthesizes a 4-note WAV at runtime with the Web Audio API, so there is no audio file to host.</p>
<script>
  const audio = new Audio();
  const playBtn = document.getElementById('play');
  const seek = document.getElementById('seek');
  const time = document.getElementById('time');
  const fmt = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;

  // Build a 16-bit PCM WAV from a note sequence.
  async function synth() {
    const ac = new OfflineAudioContext(1, 44100 * 4, 44100);
    [261.63, 329.63, 392, 523.25].forEach((freq, i) => {
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = freq; o.type = 'sine';
      const t0 = i * 0.6;
      g.gain.setValueAtTime(0, t0);
      g.gain.linearRampToValueAtTime(.3, t0 + .05);
      g.gain.linearRampToValueAtTime(0, t0 + .5);
      o.connect(g).connect(ac.destination);
      o.start(t0); o.stop(t0 + .55);
    });
    const buf = await ac.startRendering();
    const data = buf.getChannelData(0);
    const wav = new ArrayBuffer(44 + data.length * 2);
    const dv = new DataView(wav);
    const write = (off, str) => [...str].forEach((c, i) => dv.setUint8(off + i, c.charCodeAt(0)));
    write(0, 'RIFF'); dv.setUint32(4, 36 + data.length * 2, true); write(8, 'WAVE'); write(12, 'fmt ');
    dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
    dv.setUint32(24, 44100, true); dv.setUint32(28, 44100 * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
    write(36, 'data'); dv.setUint32(40, data.length * 2, true);
    for (let i = 0; i < data.length; i++) dv.setInt16(44 + i * 2, data[i] * 32767, true);
    audio.src = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }));
  }

  playBtn.addEventListener('click', async () => {
    if (!audio.src) await synth();
    audio.paused ? audio.play() : audio.pause();
  });
  audio.addEventListener('play', () => { playBtn.textContent = '❚❚'; playBtn.setAttribute('aria-label', 'Pause'); });
  audio.addEventListener('pause', () => { playBtn.textContent = '▶'; playBtn.setAttribute('aria-label', 'Play'); });
  audio.addEventListener('timeupdate', () => {
    seek.max = audio.duration || 100;
    seek.value = audio.currentTime;
    time.textContent = `${fmt(audio.currentTime)} / ${fmt(audio.duration)}`;
  });
  seek.addEventListener('input', () => { audio.currentTime = seek.value; });
</script>
</body>
</html>
```

Gotchas:
- `play()` returns a promise — a blocked autoplay rejects it; wrap in try/catch or the error is unhandled.
- Writing `seek.value` in `timeupdate` while the user drags the range creates a fight — guard with a `seeking` flag or the thumb jitters.
- The WAV header byte counts must match the data (`data.length * 2` for 16-bit mono) or players reject the file with a generic decode error.
- `OfflineAudioContext` renders as fast as possible; `await startRendering()` before reading samples, and note `start(t0)` uses render-time, not wall-clock.
- `audio.duration` is `NaN` until metadata loads — guard `audio.duration || 100` for the range max.
- Keyboard support for custom players: the native controls give you Space/arrow keys free — replicating that by hand is where players break a11y.
