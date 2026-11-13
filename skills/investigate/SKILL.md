---
name: investigate
description: Answer a question by searching the workspace and citing sources.
permissions:
  - search_documents
version: "1.0"
---

When investigating a question:

1. Call `search_documents` with focused queries.
2. If results are thin, try a shorter or differently worded query.
3. Base the answer only on retrieved content.
4. Cite each claim with the source filename and chunk number.
