---
name: django-today
description: This skill should be used when the user asks to "django today", "julian date", or "what is today".
version: 1.0.0
---

# How to run

Run a Django Command named `today` in the `python/` via manage.py.

Execute as follows with the `uv` program.

```bash
cd python
uv run manage.py today
```

## Sample Output

```
2026-06-16 Tue 167
```

## Note

Django isn't actually used in this project.
This skill is just an example of how to invoke a Django Command.
