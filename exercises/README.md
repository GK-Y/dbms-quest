# Exercise Authoring Notes

The live attempt files are generated in `attempts/`. This directory is reserved
for future per-question fixtures when the real source data is provided.

Expected shape for a future exercise fixture:

```json
{
  "id": 1757,
  "slug": "recyclable-and-low-fat-products",
  "prompt": "Paraphrased local prompt...",
  "setup_sql": "CREATE TABLE ...",
  "expected_sql": "SELECT ...",
  "solution_sql": "SELECT ...",
  "hint": "Use WHERE with two conditions."
}
```

Keep problem text paraphrased unless the source export is explicitly intended
for personal offline study.
