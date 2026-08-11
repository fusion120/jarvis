---
lang: python
keywords: template, jinja2, render, string.Template, placeholder, generate, html, email, substitution
---

# Template rendering: string.Template and Jinja2

Generating emails, configs, or HTML from data is a template job. `string.Template` covers
simple `$name` substitution with zero deps; Jinja2 adds loops, conditionals, filters,
inheritance, and automatic HTML escaping.

```python
# pip install jinja2
from string import Template

from jinja2 import Environment, FileSystemLoader, select_autoescape


# 1) stdlib string.Template — simple variable substitution
t = Template("Hello $name, you have $count new messages.")
print(t.substitute(name="Ada", count=3))

# Safe variant: missing keys stay as-is instead of raising KeyError
print(t.safe_substitute(name="Ada"))


# 2) jinja2 — real control flow + escaping
env = Environment(autoescape=select_autoescape(["html", "xml"]))

card = env.from_string(
    "{% for item in items %}<li>{{ item | upper }}</li>{% endfor %}"
)
print(card.render(items=["a", "b", "c"]))

welcome = env.from_string(
    "<p>Hi {{ user }},</p><p>Verify: {{ link | escape }}</p>"
)
print(welcome.render(user="<script>bad()</script>", link='?next="/admin"'))


# 3) render from a templates/ directory with includes and inheritance
env_dir = Environment(
    autoescape=select_autoescape(["html"]),
    loader=FileSystemLoader("templates"),
)
```

Gotchas:
- `$` in `string.Template` is the escape: `$$` renders a literal dollar; a lone `$` with an
  invalid name raises `ValueError` — use `safe_substitute` when input is untrusted.
- Never use `str.format` or f-strings to build HTML/email from user input — autoescaping
  (Jinja2) is the difference between a template and an XSS sink.
- `select_autoescape(["html", "xml"])` only auto-escapes `.html`/`.xml` *templates*, so name
  your files with those extensions or escaping silently won't happen.
- Jinja2 escapes `<`, `>`, `&`, quotes, but not necessarily every context — use the `| e`
  filter and the right quoting in attributes, and never mark user input `| safe`.
- A missing variable in Jinja2 renders as `Undefined` (empty) rather than raising — that hides
  typos; enable `undefined=StrictUndefined` in the `Environment` when you want errors.
- `string.Template` only does `$name` substitution — no loops or conditionals; reach for Jinja2
  (or `jinja2`'s sandboxed mode for untrusted templates) past that.
