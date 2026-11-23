import json

from analyze import analyze

cases = json.load(open("data/cases.json", encoding="utf-8"))
result, raw = analyze(cases["cvs"]["C1"], cases["jobs"]["J1"], retries=0)

print("VALID:", result is not None)
print(raw[:1500])