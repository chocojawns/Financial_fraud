# EDGAR filing inventory

New: [Item 1C fraud/cyber disclosure scanner](RESEARCH.md) extracts candidate
passages and enclosing Inline XBRL tags, with optional OpenAI classification.

A small, standard-library Python starter to see which filings are available.
It reads SEC company submissions JSON and populates a CSV. It does **not**
download filing documents, search their text, or call an LLM.

## Run

Python 3.10+; no packages or API keys required. Identify your application and
provide a real contact email as requested by the SEC:

```bash
git clone https://github.com/chocojawns/Financial_fraud.git
cd Financial_fraud
git switch feature/edgar-item1c-research
export SEC_USER_AGENT='FraudResearch your-email@example.com'
python3 edgar_inventory.py
```

Open `data/filings.csv` in a spreadsheet. Columns include company, CIK, SIC,
form, filing date, report date, accession number, and a clickable EDGAR URL.
Each successful run replaces the CSV; a failed company request leaves any
existing CSV untouched and returns a nonzero exit status.

The default sample is JPMorgan Chase, Bank of America, Wells Fargo, Citigroup,
Goldman Sachs, and Morgan Stanley. This is **not** a complete sector census.
Supply other company CIKs to expand the sample:

```bash
python3 edgar_inventory.py --ciks 19617 70858 --since 2024-01-01 --forms 10-K 8-K
```

## Scope and research limits

- Uses SIC 6000–6799 as an initial financial-services filter. This includes
  insurance and real estate and may omit fintech companies classified elsewhere.
  Override with `--sic-min` and `--sic-max` for a narrower range.
- Reads only `filings.recent` from each company's submissions endpoint. SEC
  limits this recent collection; the date filter does not guarantee complete
  coverage back to the requested date. Older metadata archives are not fetched.
- Exact form filters omit amendments such as `10-K/A` unless explicitly supplied.
- Lists available filings; it does not establish that they mention fraud.
- Item 1.06 is a section of an 8-K, not a separate form. Finding that section
  or fraud disclosures requires a later text-analysis step.
- No financial amounts or claims about fraud's economic ranking are inferred.

SEC endpoints: `https://data.sec.gov/submissions/CIK##########.json`.
See [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
and [automated access guidance](https://www.sec.gov/about/developer-resources).
Requests are sequential and paced. On access errors, check the identifying
User-Agent and network policy; do not bypass SEC access controls.

## Validate

```bash
python3 -m unittest discover -s tests -v
```

These offline tests cover filtering and source URLs. They do not verify live
SEC connectivity. Future OpenAI analysis can consume selected filing text after
you choose the companies and disclosures worth examining.

## VS Code on Windows

Clone the repository, select the feature branch, and open the folder in VS Code.
The scripts use only Python's standard library. In the PowerShell terminal:

```powershell
$env:SEC_USER_AGENT = 'FraudResearch your-email@example.com'
python edgar_inventory.py --ciks 1818874 --forms 10-K --since 2020-01-01
python scan_item1c.py --inventory data/filings.csv --limit 1
python -m unittest discover -s tests -v
```

Replace the contact email with your own. For optional LLM analysis, set
`OPENAI_API_KEY` securely in your local environment and choose your model as
described in [RESEARCH.md](RESEARCH.md). The scripts do not automatically load
`.env` files. Do not commit API keys or generated research outputs.
