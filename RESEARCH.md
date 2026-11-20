# Current direction

The immediate goal is a proof of concept that explains what the program does,
shows real text-mining counts and examples, and identifies a defensible question.
It is not a finished fraud-loss estimator.

- Run `discovery.py` without arguments or prompts.
- SEC contact is hard-coded as andrew@johnson.vet.
- No OpenAI key or headless model is needed at this stage.
- Current user machine is Windows; Debian is also supported.
- Financials collection uses a bundled, attributed 76-company snapshot.
- User-supplied healthcare/industrial Item 1A texts provide a separate method POC.

The measured baseline and proposed next experiment are in
`reports/proof_of_concept/DISCOVERY.md`. These findings are not Financials results.
The raw source text has not been independently verified against live filings.

A promising question to test is whether financial companies quantify fraud as a
business cost or primarily describe it as a risk, and how that varies across
banking, payments, and insurance. First review a small set of full financial
statements/notes, MD&A, and relevant event disclosures. If comparable amounts
are sparse, focus on disclosure specificity and transparency.

Separate company victimization, alleged company misconduct, regulatory exposure,
and fraud-prevention services. Keep realized losses, potential liabilities,
reimbursements, recoveries, fines, and prevention costs distinct. Ordinary defaults
are excluded unless explicitly linked to fraud. No unreviewed amounts are summed.

No deadline was supplied. The POC can support a methods/progress presentation;
substantive results require manual review and a successful Financials pilot before
setting a final presentation date.
