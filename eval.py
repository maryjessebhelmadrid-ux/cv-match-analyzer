import argparse
import hashlib
import json
import os
import re
import statistics

from analyze import DEFAULT_MODEL, SYSTEM_PROMPT, analyze

CACHE_PATH = "data/cache.json"


def band_of(score: int) -> str:
    if score <= 40:
        return "low"
    if score <= 70:
        return "mid"
    return "high"


def norm(text: str) -> str:
    """Lowercase and collapse whitespace so tiny formatting differences don't count as errors."""
    return re.sub(r"\s+", " ", text.lower()).strip().rstrip(".")


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def load_cache():
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    return {}


def save_cache(cache):
    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))


def get_output(cache, model, cv, job, run_index):
    key = hashlib.sha256(
        f"{model}|{SYSTEM_PROMPT}|{cv}|{job}|{run_index}".encode()
    ).hexdigest()
    if key not in cache:
        result, _raw = analyze(cv, job, model=model)
        if result is None:
            return None  # don't cache failures, so a rerun can try again
        cache[key] = result.model_dump()
        save_cache(cache)
    return cache[key]


def keyword_recall(keywords, text):
    if not keywords:
        return None  # nothing was expected, so recall is not defined
    text = text.lower()
    hits = 0
    for k in keywords:
        options = k if isinstance(k, list) else [k]
        if any(o.lower() in text for o in options):
            hits += 1
    return hits / len(keywords)


def score_output(out, pair, cv_text):
    skills_text = " ".join(s["skill"] + " " + s["evidence"] for s in out["matched_skills"])
    missing_text = " ".join(m["requirement"] for m in out["missing_requirements"])
    quotes = [norm(s["evidence"]) for s in out["matched_skills"]]
    faithful = (
        sum(1 for q in quotes if q in norm(cv_text)) / len(quotes) if quotes else None
    )
    return {
        "score": out["match_score"],
        "band_ok": band_of(out["match_score"]) == pair["band"],
        "skill_recall": keyword_recall(pair["must_match"], skills_text),
        "gap_recall": keyword_recall(pair["must_miss"], missing_text),
        "faithfulness": faithful,
    }


def fmt(v):
    return "-" if v is None else f"{v:.2f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--cases", default="data/cases.json")
    args = parser.parse_args()

    cases = json.load(open(args.cases, encoding="utf-8"))
    cache = load_cache()

    total_runs = 0
    valid_runs = 0
    all_scored = []
    stdevs = []

    print(f"Model: {args.model} | runs per pair: {args.runs}\n")
    print(f"{'pair':<10}{'want':<6}{'scores':<16}{'band_ok':<9}{'skill':<7}{'gap':<7}{'faith':<7}")

    for pair in cases["pairs"]:
        cv_text = cases["cvs"][pair["cv"]]
        job_text = cases["jobs"][pair["job"]]
        scored = []
        for i in range(args.runs):
            total_runs += 1
            out = get_output(cache, args.model, cv_text, job_text, i)
            if out is None:
                continue
            valid_runs += 1
            scored.append(score_output(out, pair, cv_text))
        all_scored.extend(scored)

        scores = [s["score"] for s in scored]
        if len(scores) >= 2:
            stdevs.append(statistics.pstdev(scores))

        print(
            f"{pair['cv'] + '/' + pair['job']:<10}{pair['band']:<6}{str(scores):<16}"
            f"{fmt(mean([1.0 if s['band_ok'] else 0.0 for s in scored])):<9}"
            f"{fmt(mean([s['skill_recall'] for s in scored])):<7}"
            f"{fmt(mean([s['gap_recall'] for s in scored])):<7}"
            f"{fmt(mean([s['faithfulness'] for s in scored])):<7}"
        )

    summary = {
        "model": args.model,
        "runs_per_pair": args.runs,
        "validity_rate": valid_runs / total_runs,
        "band_agreement": mean([1.0 if s["band_ok"] else 0.0 for s in all_scored]),
        "skill_recall": mean([s["skill_recall"] for s in all_scored]),
        "gap_recall": mean([s["gap_recall"] for s in all_scored]),
        "faithfulness": mean([s["faithfulness"] for s in all_scored]),
        "mean_score_stdev": mean(stdevs),
    }

    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        if isinstance(v, float):
            v = round(v, 3)
        print(f"{k:<18}{v}")

    os.makedirs("results", exist_ok=True)
    set_name = os.path.splitext(os.path.basename(args.cases))[0]
    out_path = f"results/{args.model}_{set_name}.json"
    json.dump(summary, open(out_path, "w", encoding="utf-8"), indent=2)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()