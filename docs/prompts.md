
# Prompt Templates

## 1) Page Summary (One Sentence)

```
You see one page of a technical engineering manual.
Summarize it in EXACTLY one sentence.
Be concise, neutral, and informative.
```

## 2) Document Summary (Multi-Paragraph)

```
You will be given one-sentence summaries of each page of a technical manual.
Compose a clear, multi-paragraph summary capturing the manual's main themes and scope.
Avoid repetition and keep a neutral, helpful tone.
```

## Notes

- Keep temperature low (e.g., 0.0–0.3) for consistency.
- For very long pages, truncate text safely before sending to the model.
- Consider light normalization on outputs (trim whitespace, enforce sentence end).
