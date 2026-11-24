# CV Match Analyzer

A small LLM tool that compares a CV against a job posting using the Claude API. It returns a structured JSON result: a match score, matched skills with quotes from the CV as evidence, missing requirements, and suggested CV edits. The repo also includes an evaluation script that measures how well the analyzer behaves on a hand-labeled test set.

I built this to practice both halves of applied LLM work: building a feature, and measuring whether it works.

## Example output

```json
{
  "match_score": 52,
  "summary": "Relevant Python and REST API foundations, but no experience with LLMs or evaluation scripts, which are core to the posting.",
  "matched_skills": [
    {"skill": "REST APIs", "evidence": "Built a Flask REST API with SQLite for a lab inventory system."}
  ],
  "missing_requirements": [
    {"requirement": "Familiarity with LLMs or prompt engineering", "importance": "must_have"}
  ],
  "suggested_cv_edits": [
    {"section": "Projects", "suggestion": "Lead with the Flask REST API project, since REST API experience is a stated requirement."}
  ]
}
```

(Shortened for readability; the real output has more entries.)

## How it works

- `schema.py` defines the output format with Pydantic. Output that doesn't match is rejected, and the analyzer retries once.
- `analyze.py` sends the CV and job posting to the model with a system prompt that requires verbatim quotes as evidence, only requirements stated in the posting, and no invented skills.
- `eval.py` runs the analyzer over labeled CV/job pairs and reports metrics. Results are cached, so re-running costs nothing unless the prompt or model changes.

## Setup

Requires Python 3.11+ and an Anthropic API key.

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash. On Mac/Linux: source .venv/bin/activate
pip install anthropic python-dotenv pydantic
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

## Usage

Analyze one CV against one job (plain-text files):

```bash
python analyze.py data/sample_cv.txt data/sample_job.txt
```

Run the evaluation:

```bash
python eval.py --runs 3                                          # main test set
python eval.py --runs 3 --cases data/cases_hard.json             # harder set
python eval.py --runs 3 --model claude-sonnet-5-5                # another model
```

Each run saves a summary to `results/`.

## How it is evaluated

Every test pair is labeled by hand with an expected score band, skills the CV clearly has, and requirements it clearly lacks. A `note` field records the reason for each label.

| Metric | What it checks |
|---|---|
| Validity rate | Share of outputs that parse and match the schema |
| Band agreement | Score falls in the labeled band (low 0-40, mid 41-70, high 71-100) |
| Skill recall | Labeled skills appear in the model's matched skills |
| Gap recall | Labeled gaps appear in the model's missing requirements |
| Faithfulness | Every evidence quote actually appears in the CV (case and whitespace ignored) |
| Score stdev | How much the score varies across repeated runs of the same pair |

Skill and gap recall use keyword matching, with alternative spellings allowed (for example `["sql", "postgres"]`).

## Results

Three runs per pair. Test CVs and jobs are synthetic.

| | Haiku, main set (12 pairs) | Sonnet, main set (12 pairs) | Haiku, hard set (6 pairs) | Sonnet, hard set (6 pairs) |
|---|---|---|---|---|
| Validity | 1.0 | 1.0 | 1.0 | 1.0 |
| Band agreement | 0.944 | 1.0 | 0.833 (1.0 after relabeling one pair) | 0.833 |
| Skill / gap recall, faithfulness | 1.0 | 1.0 | 1.0 | 1.0 |
| Score stdev | 1.58 | 0.17 | 2.93 | 0.63 |

**Prompt change (Haiku, main set):** my first scoring rubric used different band boundaries than the evaluation, so band agreement was 0.861. Aligning the rubric with the evaluation bands raised it to 0.944 (31 to 34 of 36 runs). The change was made after seeing the first results.

**Main findings:**
- Sonnet's scores were much more stable across repeated runs than Haiku's, on both sets.
- Both models kept quotes faithful and caught the negation trap ("has not built anything in Python yet") and the synonym trap (PostgreSQL counted as SQL).
- The two models disagree on one hard-set pair (H5/HJ5, a networking CV against an IT assistant posting): Haiku scores it about 62 and Sonnet about 82. Both name the same two gaps and weigh them differently. I originally labeled it `high`, then relabeled it `mid` after reading Haiku's reasoning. The original hard-set score for Haiku, before the relabel, was 0.833.

**Cost:** all Haiku runs (development, prompt iteration and every evaluation above) cost about $0.07 in total, per the Anthropic Console usage page.

## Limitations

- The test sets are small (12 and 6 pairs), so a difference of one or two runs is noise. Only the consistency gap between the models is large enough to take seriously.
- The main set was rewritten once to remove ambiguous cases after an early run, and the prompt was tuned using Haiku's output on it. Scores on that set are optimistic.
- One hard-set label was changed after seeing model reasoning (documented above). A single Sonnet call on that pair scored 62 while 11 other calls scored 82-85. I don't know why.
- Keyword matching checks words, not meaning, so it can miss correct answers that are phrased differently, or credit a keyword that appears in an unrelated context.
- The hard set doesn't yet cover skill lists with no supporting evidence, a single relevant line buried in an unrelated CV, must-have versus nice-to-have requirements, or overqualified candidates.

## Possible next steps

- Add the missing hard-case types and more pairs.
- Add an LLM-as-judge check for the suggested CV edits, which currently aren't scored at all.
- Report the share of outputs within one band of the label, alongside exact agreement.