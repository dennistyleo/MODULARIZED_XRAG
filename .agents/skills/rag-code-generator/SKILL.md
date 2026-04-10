---
name: rag-code-generator
description: Generates RAG module code using Gemini 3 Flash.
---

# RAG Code Generator Skill

## Code Requirements
- Model: gemini-3-flash-preview
- Timeout: 30 seconds
- Retry: 3 times

## Output Schema
- domain: CONTRACT, FINANCIAL, TECHNICAL, AEROSPACE, GENERAL
- nodes: array of {id, name, value, confidence}
- assessment: {conf, tier, reason}
