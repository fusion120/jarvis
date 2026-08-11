---
lang: javascript
keywords: promise, then, catch, finally, reject, resolve, unhandledrejection, promise chain, error handling, microtask
---

# Promises & error handling

Promises represent a value that arrives later, and `.then/.catch/.finally` compose chains that funnel every failure into one handler. Reach for promises whenever an API returns one (fetch, fs.promises, timers) instead of raw callbacks, and always end chains with a catch.

```javascript
const { setTimeout: sleep } = require("node:timers/promises");

// Promise-returning function
function fetchUser(id) {
  return new Promise((resolve, reject) => {
    if (!Number.isInteger(id)) {
      reject(new TypeError("id must be an integer"));
      return;
    }
    sleep(10).then(() => {
      if (id === 404) {
        reject(Object.assign(new Error("not found"), { code: "ENOUSER" }));
      } else {
        resolve({ id, name: `User ${id}` });
      }
    });
  });
}

// Chain with mapping and a single catch + finally
fetchUser(42)
  .then((user) => ({ ...user, upper: user.name.toUpperCase() }))
  .then((user) => console.log(user.upper))      // "USER 42"
  .catch((err) => {
    console.error(`failed: ${err.code ?? err.message}`);
  })
  .finally(() => console.log("done"));          // always runs

// Error type discrimination
async function main() {
  try {
    const u = await fetchUser(404);
    console.log(u);
  } catch (err) {
    if (err.code === "ENOUSER") console.log("friendly 404 message");
    else throw err;                             // rethrow unknown errors
  }
}
main();

// Promise.resolve / reject helpers
Promise.reject(new Error("boom")).catch((e) => console.log(e.message));

// Never let rejections go unhandled
process.on("unhandledRejection", (reason) => {
  console.error("UNHANDLED", reason);
  process.exit(1);
});
```

Gotchas:
- A rejected promise with no `.catch` and no `await` triggers `unhandledRejection` (crashes Node by default).
- Throw inside a `.then` automatically rejects the chain — you don't need `reject()`.
- Calling `resolve` then `reject` is a no-op: the first settle wins, so `return` after `reject`.
- `.catch` after `.finally` still works, but `.finally` does NOT catch; place it last.
- Errors inside `await`ed try/catch are caught, but errors in `setTimeout` callbacks need wrapping in the promise.
- `async` functions always return a promise: forgetting `await` on a call silently discards the eventual rejection (add `.catch` or await).
