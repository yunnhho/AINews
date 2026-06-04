"""Claude API 프롬프트 정의."""

NEWS_SYSTEM = (
    "You are an expert AI/LLM news editor for AI Pulse, a Korean tech card platform. "
    "Always respond with valid JSON only — no markdown, no code blocks, no extra text."
)

NEWS_USER = """\
Summarize the following AI/tech article into a structured Korean card.

Title: {title}
Content (first 3000 chars): {content}

Respond with JSON exactly:
{{
  "title": "<Korean title, max 100 chars>",
  "summary": "<2-3 sentence Korean summary>",
  "key_points": ["<What happened>", "<Why it matters>", "<Impact/significance>"],
  "category": "<CODING|DESIGN|GENERAL>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"],
  "difficulty": "<BEGINNER|INTERMEDIATE|ADVANCED>"
}}

Rules:
- title/summary/key_points must be in Korean
- tags must be English, lowercase, hyphenated (e.g. "large-language-model")
- key_points: exactly 3-5 items\
"""

TECHNIQUE_SYSTEM = (
    "You are an expert AI/ML technique explainer for AI Pulse, a Korean tech card platform. "
    "Always respond with valid JSON only — no markdown, no code blocks, no extra text."
)

TECHNIQUE_USER = """\
Analyze the following technical article/GitHub release and create a structured Korean explanation.

Title: {title}
Content (first 3000 chars): {content}

Respond with JSON exactly:
{{
  "title": "<Korean title of the technique, max 100 chars>",
  "summary": "<1-2 sentence Korean summary>",
  "problem": "<Korean: what problem does this solve?>",
  "idea": "<Korean: what is the core idea/approach?>",
  "caveats": ["<Korean caution 1>", "<Korean caution 2>"],
  "prerequisites": "<Korean comma-separated prerequisites, or null>",
  "category": "<CODING|DESIGN|GENERAL>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"],
  "difficulty": "<BEGINNER|INTERMEDIATE|ADVANCED>"
}}

Rules:
- title/summary/problem/idea/caveats must be in Korean
- tags must be English, lowercase, hyphenated
- caveats: 2-3 items\
"""

TRANSLATE_SYSTEM = (
    "You are a professional technical translator performing back-translation. "
    "Translate the given Korean text to natural English, preserving technical terms. "
    "Output only the English translation."
)

BACKTRANSLATE_USER = """\
Translate this Korean text back to English. Provide only the English translation, no explanation.

Korean: {text}\
"""
