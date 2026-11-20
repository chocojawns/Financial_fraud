# Fraud disclosure discovery: proof of concept

**Status: real text-mining baseline, not a financial-sector fraud-loss estimate.**

## What was run and why

The supplied `item_1a_results.json` contains 142 healthcare/industrial filing
records. 134 contain text marked successful by the original extraction.
The remaining 8 were excluded from text-percentage denominators.
This POC tests whether risk-factor text can support the proposed financial-impact
question before spending time or money on a larger collection or LLM analysis.

The program reads text, counts literal fraud language and a broader indicator
list, and looks for monetary expressions in the same sentence as a fraud indicator.
It saves one filing-level row and linked source excerpts. It makes **no OpenAI calls**.

## Measured results

| Supplied sector | Input records | Readable records | Literal fraud language | Broader indicators | Same-sentence monetary candidates |
|---|---:|---:|---:|---:|---:|
| health_care | 59 | 58 | 52 (89.7%) | 55 | 0 |
| industrials | 83 | 76 | 41 (53.9%) | 60 | 0 |

Across the readable records, 93 contain literal fraud language and 115
contain the broader indicator vocabulary. The text contains 1099 recognized
monetary expressions overall, but only 0 meet the strict fraud/money
same-sentence rule. These are text-mining counts, not incident counts or dollars.

## What this tells us

1. Fraud discussion is common enough in this supplied text to study disclosure.
2. A broad vocabulary changes the results substantially. Misappropriation can,
   for example, concern intellectual property rather than a company fraud loss.
3. Finding dollar figures is different from attributing them to fraud. This
   method does not establish a fraud-loss total.
4. Item 1A alone appears insufficient for the financial-impact question in this
   sample. Next examine financial-statement notes, MD&A, and relevant 8-K exhibits.

## Specific direction to test next

**Do financial companies quantify fraud as a business cost, or primarily describe
it as a risk—and how does that differ across banking, payments, and insurance?**

The next small pilot should distinguish a company as victim, alleged perpetrator,
fraud-prevention provider, or a business discussing regulatory exposure. It should
separate realized losses, potential liabilities, reimbursements, recoveries, fines,
and prevention costs. Ordinary customer defaults remain outside the question
unless the disclosure explicitly attributes them to fraud.

This is a proposed direction, not a result about those financial subsectors.

## What I would change before presenting substantive findings

- Manually review 10–15 excerpts to assess whether the vocabulary captures the
  intended type of fraud. The complete evidence table is `evidence.csv`.
- Test a few Financials companies' full 10-Ks and event disclosures. Review notes
  and MD&A rather than assuming Item 1A provides financial amounts.
- Once the labels are clear, use an LLM to classify longer passages and extract
  supported amounts. Check the output against a manually reviewed sample.
- If explicit amounts remain too sparse, make disclosure specificity/transparency
  the measured outcome rather than estimating total fraud losses.

## Presentation readiness

This baseline is ready to explain the method, show actual counts, and justify a
next experiment. It is not ready to establish industry losses, trends, or AI effects.
For a graded research presentation, complete the manual review and small Financials
pilot first, then finalize the question. Set the presentation date after those
checks rather than promising a date before knowing whether the data support it.

## Limits

The supplied dataset is healthcare/industrials, not Financials. Sector labels and
extractions were supplied by the user and have not been independently verified.
There is no claim that this is a complete/random S&P 500 sample. Accession dates
are not incident dates or fiscal years; this is not a longitudinal trend analysis.
Literal mentions are not verified fraud. Missing text is not zero exposure.
Same-sentence matching misses tables, shared units, and amounts in other sections.
Repeated values must not be added across filings. No causal or significance claim
is made from the sector percentages.

## Reproduce

Place the original JSON in `inputs/item_1a_results.json`, then run `discovery.py`.
The input checksum is in `manifest.json`. The baseline is built from the supplied
text and works even if SEC access is unavailable. The program then attempts the
Financials collection separately and labels any access failure.
