---
name: date-today
description: This skill should be used when the user asks to "what day is it".
version: 1.0.0
---

# How to run

Run a Django Command named `today` in the `python/` via manage.py.

Execute as follows with the `uv` program.

```bash
cd python
python -c "import datetime; print(datetime.date.today())"
```

## Sample Output

```
2026-06-16 Tue 167
```
