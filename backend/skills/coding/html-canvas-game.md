---
lang: html
keywords: canvas game, snake game, game loop, collision detection, keyboard game, grid movement, setInterval, restart game, score
---

# Canvas Game: Snake

A complete snake game on a 20x20 canvas grid: queue-buffered direction input, wall + self collision, food spawning that avoids the snake, score, and Space to restart. The pattern extends to any grid-based game.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Snake game</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; text-align: center; }
  canvas { border: 1px solid #333; background: #0d1117; }
  #score { font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<h1>Snake</h1>
<p id="score">Score: 0</p>
<canvas id="game" width="320" height="320" aria-label="Snake game — use arrow keys"></canvas>
<p>Arrow keys to steer, Space to restart.</p>
<script>
  const canvas = document.getElementById('game');
  const ctx = canvas.getContext('2d');
  const N = 20, SIZE = canvas.width / N; // 20x20 grid
  let snake = [{ x: 10, y: 10 }];
  let dir = { x: 1, y: 0 };
  let nextDir = dir;
  let food = { x: 15, y: 10 };
  let score = 0;
  let timer = null;

  function spawnFood() {
    for (;;) {
      food = { x: Math.floor(Math.random() * N), y: Math.floor(Math.random() * N) };
      if (!snake.some(s => s.x === food.x && s.y === food.y)) return;
    }
  }

  function step() {
    dir = nextDir;
    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
    if (head.x < 0 || head.y < 0 || head.x >= N || head.y >= N ||
        snake.some(s => s.x === head.x && s.y === head.y)) {
      clearInterval(timer); timer = null;
      ctx.fillStyle = '#f44';
      ctx.font = '20px system-ui';
      ctx.fillText('GAME OVER — Space to restart', 26, SIZE * N / 2);
      return;
    }
    snake.unshift(head);
    if (head.x === food.x && head.y === food.y) {
      score++; document.getElementById('score').textContent = 'Score: ' + score;
      spawnFood();
    } else {
      snake.pop();
    }
    draw();
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#4caf50';
    for (const s of snake) ctx.fillRect(s.x * SIZE, s.y * SIZE, SIZE - 1, SIZE - 1);
    ctx.fillStyle = '#f44';
    ctx.fillRect(food.x * SIZE, food.y * SIZE, SIZE, SIZE);
  }

  addEventListener('keydown', e => {
    const k = { ArrowUp: { x: 0, y: -1 }, ArrowDown: { x: 0, y: 1 }, ArrowLeft: { x: -1, y: 0 }, ArrowRight: { x: 1, y: 0 } }[e.key];
    if (k) {
      e.preventDefault();
      if (!(k.x === -nextDir.x && k.y === -nextDir.y)) nextDir = k; // no 180° reversal
    }
    if (e.key === ' ' && !timer) {
      e.preventDefault();
      snake = [{ x: 10, y: 10 }]; dir = nextDir = { x: 1, y: 0 }; score = 0;
      document.getElementById('score').textContent = 'Score: 0';
      spawnFood(); draw();
      timer = setInterval(step, 120);
    }
  });

  spawnFood(); draw();
  timer = setInterval(step, 120);
</script>
</body>
</html>
```

Gotchas:
- `setInterval` at 120ms is the tick; tab throttling pauses it — real games use `requestAnimationFrame` + accumulated delta time for frame-rate-independent speed.
- The queue-buffered `nextDir` prevents instant 180° self-bite; checking against `nextDir` (not `dir`) covers rapid double-presses between ticks.
- Collision checks the head against every segment INCLUDING ones the tail vacates this tick — compare against the snake minus its tail for fair self-collision.
- Food spawning must loop until it lands off the snake, or it can spawn inside the body and be impossible to eat.
- Canvas coordinates are pixels — grid math must multiply by `SIZE`; forgetting it renders the whole game in a 20px corner.
- Keep focus on the page (not inside an input) or arrow keys scroll instead of steering; `e.preventDefault()` on arrows stops the scroll.
