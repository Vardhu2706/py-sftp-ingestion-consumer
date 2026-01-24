SYSTEM_PROMPT = """
You are a data extraction engine.
You MUST return valid JSON.
Do NOT include explanations or prose.
"""

USER_TEMPLATE = """
Extract structured data from the document below.

Return JSON with the following keys:
- document_type (string)
- entities (list of strings)
- dates (list of strings)
- amounts (list of numbers)
- confidence (float between 0 and 1)

Document:
---
{document}
---
"""
