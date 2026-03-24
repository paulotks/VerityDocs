from __future__ import annotations


def find_similar(description: str, existing: list[str]) -> list[str]:
    words = {w for w in description.lower().split() if len(w) > 3}
    matches = []
    for e in existing:
        e_words = set(e.lower().split())
        if words and len(words & e_words) >= max(1, min(3, len(words) // 2)):
            matches.append(e)
    return matches
