import json
import sys

from analyze import analyze

cv, job, path, model = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 8
cases = json.load(open(path, encoding="utf-8"))

scores = []
for _ in range(n):
    result, raw = analyze(cases["cvs"][cv], cases["jobs"][job], model=model)
    scores.append(result.match_score if result else None)
    print(scores[-1], flush=True)
print("all:", scores)