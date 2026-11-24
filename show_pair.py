import json
import sys

from analyze import analyze

cv, job = sys.argv[1], sys.argv[2]
path = sys.argv[3] if len(sys.argv) > 3 else "data/cases.json"
cases = json.load(open(path, encoding="utf-8"))

result, raw = analyze(cases["cvs"][cv], cases["jobs"][job])
print("score:", result.match_score)
print(result.summary)
print("MATCHED:", [s.skill for s in result.matched_skills])
print("MISSING:", [m.requirement for m in result.missing_requirements])