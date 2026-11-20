# S&P 500 fraud and cybersecurity discovery

Run one file. No arguments, prompts, OpenAI key, cache, or pictures.

**Windows / VS Code:**

```powershell
python discovery.py
```

**Debian:**

```bash
python3 discovery.py
```

Python 3.10 or newer. No packages to install. SEC contact is hard-coded as
**andrew@johnson.vet**.

## What it does

1. Reads the bundled 500-company S&P 500 snapshot and sector labels.
2. Finds all available **8-K and 8-K/A filings from 2020 through today**, including
   historical SEC submissions metadata.
3. Searches the full primary 8-K text for fraud/cybersecurity language and item numbers.
4. Saves source excerpts and compares disclosure counts across all 11 sectors.

**Item 1.06** covers material cybersecurity incidents. There is no current 8-K
Item 1.05. Items 4.02, 5.02, 7.01, 8.01, and 9.01 can contain relevant context,
but they are not exclusive to fraud. Those item numbers alone do not count as a
fraud/cyber match. Primary documents are searched regardless of item number.
Exhibits/attachments, PDFs/images, and confidential reports are not searched.

The full scan can take hours. Requests are sequential at no more than two per
second. No filing files or cache are saved. Each run starts fresh and keeps its
outputs in a new timestamped folder. Ctrl+C stops collection and saves a partial
summary. An access denial stops the run rather than repeating it for 500 companies.

## Results

Open the newest folder under `results/`:

- **DISCOVERY.md** — written method, sector comparison, limitations, and next steps.
- **sector_summary.csv** — filing counts and company disclosure percentages by sector.
- **findings.csv** — candidate passages, item context, company, sector, date, and SEC link.
- **filings.csv** — a record of each attempted 8-K document, including zero matches and errors.
- **coverage.csv** — complete, partial, failed, and unstarted companies.

These are **disclosure counts**, not confirmed fraud events, attacks, or losses.
Amendments and repeated reports can describe the same event. Company percentages
use fully scanned companies only. Partial coverage must not be treated as no fraud.
Review the excerpts before drawing conclusions or comparing sector rankings.

`companies.csv` is a third-party fixed-panel snapshot retrieved November 20, 2026,
not independently verified official or historical membership. Source, license,
and checksum are in `companies_source.json`. Multiple share classes with the same
CIK are scanned once. Item 1.06 reporting began in December 2023; changes across
that date can reflect new reporting rules rather than more incidents.

## GitHub

Use **main**. To update an existing checkout:

```powershell
git switch main
git pull origin main
python discovery.py
```

If GitHub resets your connection, download **Code → Download ZIP** from main,
extract it, and open that folder in VS Code.

## SEC access

This cloud environment has previously denied SEC requests. Its network settings
must allow `data.sec.gov` and `www.sec.gov`. No API key is needed for SEC access.
The program reports failures explicitly and does not bypass access restrictions.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests simulate SEC responses. They do not establish live SEC availability.
