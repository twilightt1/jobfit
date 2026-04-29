from __future__ import annotations

import re

SKILL_ALIASES = {
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    "aws": "aws",
    "ci cd": "ci/cd",
    "ci/cd": "ci/cd",
    "fast api": "fastapi",
    "fastapi": "fastapi",
    "gcp": "gcp",
    "js": "javascript",
    "javascript": "javascript",
    "llm": "large language models",
    "llms": "large language models",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "natural language processing": "natural language processing",
    "nlp": "natural language processing",
    "node": "node.js",
    "node js": "node.js",
    "node.js": "node.js",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "py": "python",
    "python": "python",
    "react js": "react",
    "react": "react",
    "ts": "typescript",
    "typescript": "typescript",
}

STOPWORDS = {
    "and",
    "are",
    "build",
    "experience",
    "for",
    "have",
    "knowledge",
    "must",
    "our",
    "role",
    "strong",
    "that",
    "the",
    "this",
    "with",
    "years",
    "you",
}

_ALIAS_GROUPS: dict[str, set[str]] = {}
for alias, canonical in SKILL_ALIASES.items():
    _ALIAS_GROUPS.setdefault(canonical, set()).add(alias)


def normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9+#./]+", " ", value.lower())
    return " ".join(cleaned.split())


def normalize_skill(skill: str) -> str:
    normalized = normalize_text(skill)
    return SKILL_ALIASES.get(normalized, normalized)


def normalize_skill_list(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized_skills: list[str] = []

    for skill in skills:
        canonical = normalize_skill(skill)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        normalized_skills.append(canonical)

    return normalized_skills


def skill_aliases_for(skill: str) -> set[str]:
    canonical = normalize_skill(skill)
    return _ALIAS_GROUPS.get(canonical, {canonical})


def extract_keywords(value: str) -> set[str]:
    tokens = normalize_text(value).split()
    return {
        token
        for token in tokens
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
    }
