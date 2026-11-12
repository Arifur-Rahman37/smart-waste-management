"""Intelligent priority classification (bonus feature).

A transparent, rule-based NLP scorer: it looks at the waste category and at
keywords in the title/description and returns a priority + explanation.
"""
import re

CATEGORY_BASE = {
    "Hazardous Waste": 3, "Dead Animal": 2, "Blocked Drain / Waste in Drain": 2,
    "Illegal Dumping": 1, "Overflowing Bin": 1, "Delayed Collection": 1,
    "Construction Debris": 1, "Other": 0,
}
KEYWORDS = {
    3: ["toxic", "chemical", "hazard", "medical", "syringe", "hospital", "fire",
        "burning", "explosive", "acid", "poison", "asbestos", "flood", "outbreak"],
    2: ["school", "market", "disease", "mosquito", "dengue", "rotten", "stink",
        "smell", "blocked", "drain", "road", "children", "dead", "rats", "rat"],
    1: ["overflow", "overflowing", "dump", "days", "week", "weeks", "pile",
        "garbage", "trash", "delay", "delayed", "not collected"],
}

def classify_priority(title: str, description: str, category: str):
    text = f"{title} {description}".lower()
    score = CATEGORY_BASE.get(category, 0)
    hits = []
    for weight, words in KEYWORDS.items():
        for w in words:
            if re.search(rf"\b{re.escape(w)}", text):
                score += weight * 0.6
                hits.append(w)
    # long-lasting problem -> escalate
    if re.search(r"\b(\d+)\s*(days|weeks)\b", text) or "week" in text:
        score += 1
    if score >= 5:
        p = "Critical"
    elif score >= 3.5:
        p = "High"
    elif score >= 2:
        p = "Medium"
    else:
        p = "Low"
    reason = f"category '{category}'" + (f", keywords: {', '.join(sorted(set(hits))[:6])}" if hits else "")
    return p, round(score, 1), reason
