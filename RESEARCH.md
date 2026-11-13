# Step 1: Item 1C discovery

Study scope: all SEC financial SIC filers (6000–6799), filing dates 2020–2026.
This is broader than S&P 500 Financials and includes insurance and real estate.

**Current implementation is a pilot scanner, not a completed industry dataset.**
It scans CIKs directly, local HTML, or the 10-K rows of an input inventory. The existing inventory
script defaults to six banks and recent SEC metadata; it does not discover the
whole industry or guarantee coverage back to 2020. Industry-wide discovery and
historical metadata collection are the next collection step. Do not interpret
pilot output as an industry rate.

Direct `--ciks` mode now follows overlapping SEC historical submissions files,
so it is not restricted to `filings.recent`. All-industry CIK discovery is still
outstanding. An input inventory retains whatever historical coverage it contains.

## VS Code: no arguments required

Run `scan_item1c.py` with the Run Python File in Terminal button. It prompts for
CIKs (default SoFi) and a real contact email unless `SEC_USER_AGENT` is already
set. Default scope is 2020–2026 filing dates, capped at five latest eligible
filings. This guided run does not enable paid OpenAI calls.

The default output is now `data/item1c.jsonl` relative to the script directory,
not the terminal's working directory. Explicit relative `--output` paths remain
relative to the terminal's working directory.

## What the scanner does

1. Finds a candidate 10-K Item 1C section between its cybersecurity heading and
   Item 1D or Item 2. The longest qualifying candidate is used to avoid TOC entries.
2. Finds fraud, scams, account takeover, identity theft, synthetic identity,
   unauthorized transactions, social engineering, phishing, business email
   compromise, ransomware, deepfakes, and AI terms. These are candidate search
   terms; a match does not establish fraud.
3. Saves surrounding text, the full extracted section, source metadata, content
   hash, and overlapping Inline XBRL tag names/context references.
4. Optionally sends candidate passages to OpenAI for classification. It validates
   JSON fields and checks that supporting quotes occur in the supplied passage.

Item 1C compliance began with fiscal years ending on or after December 15, 2023.
Earlier years need a separate Item 1A/MD&A/notes search for longitudinal analysis.
Missing Item 1C is not evidence of no fraud. An 8-K's Item 1.06 concerns material
cybersecurity incidents; Item 8.01 is Other Events. There is no current 8-K Item
1.05. This first scanner does not extract 8-K sections yet.

## Run on local HTML

No installation or credentials required; Python 3.10+:

```bash
cd Financial_fraud
python3 scan_item1c.py --html /path/to/company-10k.htm
```

## Run a network pilot

Provide a real contact email in the SEC User-Agent. This fetches filing HTML
into memory, without retaining raw downloaded filing files. Extracted research
evidence is saved locally. Requests are sequential and paced.

```bash
export SEC_USER_AGENT='FraudResearch your-email@example.com'
python3 edgar_inventory.py --ciks 1818874 --forms 10-K --since 2020-01-01
python3 scan_item1c.py --inventory data/filings.csv --limit 5
```

Or skip the CSV step and retrieve historical metadata directly:

```bash
python3 scan_item1c.py --ciks 1818874 --email YOUR_EMAIL --limit 1
```

Output: `data/item1c.jsonl`, one JSON object per attempted filing. Failed fetches,
missing sections, extracted sections with zero matches, and extracted sections
with matches remain distinguishable. Runs append; use a different `--output`
for each research run to avoid counting duplicate attempts. `--limit 0` processes
all eligible rows in the supplied inventory; it does not expand the universe.

## Optional OpenAI analysis

Put `OPENAI_API_KEY` in secure environment settings, not source code or chat.
Select an available model supporting Chat Completions JSON object output:

```bash
python3 scan_item1c.py --ciks 1818874 --limit 1 \
  --llm --model YOUR_MODEL_NAME --output data/item1c-llm-pilot.jsonl
```

No API calls occur without `--llm`. Calls are billable; start with one filing.
Model, prompt version, usage, classification, and quotes accompany each result.
A valid quote does not prove the interpretation is correct: review findings.
No full-industry paid run has been executed or estimated yet.

Required network destinations: `data.sec.gov`, `www.sec.gov`, and, for optional
analysis, `api.openai.com`. Current environment settings must permit them.

## Interpretation and extraction limits

- HTML extraction is heuristic and must be spot-checked on actual filings before
  scaling. Unusual headings, amendments, incorporated disclosures, malformed
  markup, and abbreviated sections can be missed.
- Matching includes AI and general cyber terms for exploration. These are not
  automatically fraud disclosures. Fixed character windows can cut context;
  compare against the complete saved section before concluding.
- Search terms can miss disclosures phrased differently. Review a sample of
  zero-match sections before estimating prevalence.
- Tags are extracted from visible `ix:nonNumeric` and `ix:nonFraction` elements.
  A surrounding text-block tag is not necessarily a fraud-specific accounting
  concept. Untagged passages are retained with an empty tag list.
- Continued Inline XBRL fact chains are flagged by `continued_at` but are not
  resolved. Taxonomy definitions, numeric transformations, units, and full XBRL
  context/dimension resolution are a later step. Never treat extracted tag
  names as verified financial measures.
- Local HTML input is presumed to be a 10-K; the supplied file's form is not
  independently verified. This tool does not count distinct real-world events.

## Validation

```bash
python3 -m unittest discover -s tests -v
```

Offline fixtures test TOC avoidance, section boundaries, tag association, missing
sections, zero keyword matches, quote validation, and the local CLI. They do not
establish live SEC or OpenAI readiness.
