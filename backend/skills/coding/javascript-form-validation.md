---
lang: javascript
keywords: form validation, constraint validation, validity, checkValidity, setCustomValidity, pattern, required, novalidate, reportValidity, validationMessage
---

# Form validation with the Constraint Validation API

The browser validates forms natively via HTML attributes (`required`, `minlength`, `pattern`) and exposes the result through `input.validity` and `input.validationMessage`. Reach for it instead of hand-rolled regex checks; use `setCustomValidity` for business rules the attributes can't express.

```javascript
// browser
// <form id="signup" novalidate> — novalidate so we control the UX
const form = document.getElementById("signup");

// Per-field validation on blur/input
for (const input of form.querySelectorAll("input, select, textarea")) {
  input.addEventListener("blur", () => validateField(input));
  input.addEventListener("input", () => {
    if (input.dataset.touched === "1") validateField(input);
  });
}

function validateField(input) {
  // Custom business rule before checking built-ins
  if (input.id === "confirm") {
    const pw = form.elements.password.value;
    input.setCustomValidity(input.value !== pw ? "Passwords must match" : "");
  }
  input.dataset.touched = "1";
  const ok = input.checkValidity();           // runs all constraints
  input.classList.toggle("invalid", !ok);
  const tip = input.nextElementSibling;        // <small> for the message
  if (tip) tip.textContent = input.validationMessage;
  return ok;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();                          // demo: don't actually submit
  const fields = [...form.elements]
    .filter((el) => el.matches("input,select,textarea"));
  const allOk = fields.every((el) => validateField(el));
  if (!allOk) {
    form.querySelector(":invalid")?.focus();
  } else {
    console.log("submitting", Object.fromEntries(new FormData(form)));
  }
});
```

```html
<!-- browser -->
<!-- <form id="signup" novalidate>
  <input name="email" type="email" required><small></small>
  <input name="password" minlength="8" required><small></small>
  <input name="confirm" required><small></small>
  <button>Sign up</button>
</form> -->
```

Gotchas:
- With `novalidate` the browser won't block submit or show bubbles — you must call `checkValidity`/`reportValidity` yourself.
- `input.validity` has typed flags (`validity.rangeOverflow`, `validity.patternMismatch`, …) — switch on them for targeted messages.
- `setCustomValidity("")` clears a custom error; any non-empty string makes the field permanently invalid until cleared.
- `:invalid` CSS fires on page load for empty `required` fields — pair with `:not(:focus)` and a `.invalid` class toggled on interaction.
- `pattern` matches the whole value (anchored), unlike regex `.test()` without anchors.
- `checkValidity()` returns a boolean but doesn't scroll/focus; `reportValidity()` shows the native bubble — choose per UX.
