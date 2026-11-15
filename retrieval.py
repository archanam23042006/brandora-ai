import math
import re

ALWAYS = {"TONE-01"}
TOP_N = 5
STOP = {"the", "and", "for", "are", "not", "with", "that", "this", "you", "your", "our",
        "any", "can", "use", "such", "unless", "all", "from", "have", "has", "was", "will"}


def _tok(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP]


def relevant_rules(body, rules):
    """Rank rules by TF-IDF cosine similarity to the content. Returns (chosen_rules, scores)."""
    if len(rules) <= TOP_N or not body.strip():
        return rules, {}
    docs = [_tok(r["title"] + " " + r["text"]) for r in rules]
    query = _tok(body)
    df = {}
    for d in docs + [query]:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    n = len(docs) + 1

    def vec(tokens):
        tf = {}
        for w in tokens:
            tf[w] = tf.get(w, 0) + 1
        return {w: c * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in tf.items()}

    def cos(a, b):
        dot = sum(v * b.get(w, 0) for w, v in a.items())
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    q = vec(query)
    sims = [cos(vec(d), q) for d in docs]
    order = sorted(range(len(rules)), key=lambda i: -sims[i])
    chosen = [rules[i] for i in order[:TOP_N]]
    ids = {r["id"] for r in chosen}
    for r in rules:
        if r["id"] in ALWAYS and r["id"] not in ids:
            chosen.append(r)
    return chosen, {rules[i]["id"]: round(sims[i], 3) for i in range(len(rules))}