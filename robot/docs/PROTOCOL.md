# Jarvis Buddy — Serial Protocol (v1)

The Uno talks to the desktop agent over **USB serial at 115200 baud, 8-N-1**, one
newline-terminated ASCII command per line. Every command is answered with one ack line.

The agent **waits for the ack before sending the next command** — this is what makes the
buddy's actions deterministic.

## Acks
| Prefix | Meaning |
|---|---|
| `OK …` | accepted, executed |
| `ERR …` | rejected (bad args, out of range, unknown command) |
| `READY …` | sent once on boot (firmware loaded) |
| `PONG` | answer to `PING` |

## Commands

### `PING`
Heartbeat. → `PONG`

### `POS <pan> <tilt>`
Snap both servos to angles. Clamped to `0..180`. Center = `90 90`.
```
POS 90 90        → OK pan=90 tilt=90
```

### `MOVE <pan> <tilt> [<ms>]`
Smooth move to angles over `ms` (default `400`). The firmware paces the motion so it
reaches the target in about that time.
```
MOVE 30 120 800  → OK moving pan=30 tilt=120 in 800ms
```

### `EYE <expression>`
Switch the OLED face. Expressions:
| Name | Look |
|---|---|
| `idle` | normal round eyes, natural random blinks |
| `happy` | upward-arc eyes (^ ^) |
| `sad` | downward-arc eyes (u u) |
| `curious` | pupils shifted to one side, raised brows |
| `blink` | a single quick blink (also triggered by `BLINK`) |
| `sleep` | closed line eyes |
| `x` | X eyes (surprised/shocked) |
| `talk` | animated mouth under the eyes for ~3s, then back to `idle` |
```
EYE happy       → OK eye=happy
EYE talk        → OK eye=talk
```

### `BLINK`
One quick blink then back to the current expression. → `OK blink`

### `BLIP <freq> <ms>`
Play a buzzer tone. `freq` Hz, `ms` duration (10–1000).
```
BLIP 880 80     → OK beep 880hz 80ms
```

### `STATUS`
Report state for the Desktop page. → `OK pan=.. tilt=.. expr=.. up=<seconds>`

### `RST`
Re-home both servos to center (90,90). → `OK reset`

## Examples
```
PING
EYE happy
BLIP 1318 60
BLIP 1568 60
MOVE 60 75 500
STATUS
```

## Error handling
Unknown commands → `ERR unknown: "<raw>"`. Bad numbers → `ERR bad args`. The firmware
never panics; the agent treats any `ERR` as a failed step and stops the batch.
