---
name: summarize
description: Summarize the most relevant documents in the current workspace.
permissions:
  - search_documents
version: "1.0"
---

When the user asks for a summary:

1. Call `search_documents` with the user's topic or question.
2. Read the returned chunks and group related points.
3. Produce a concise summary with bullet points.
4. Mention the source filenames you used.
