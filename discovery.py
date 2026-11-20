"""Run this file: no arguments, no prompts, no API key required."""
from pathlib import Path

import _edgar_scanner as scanner
from edgar_inventory import DEFAULT_USER_AGENT, fetch_company
from poc_analysis import run_poc, write_financials_report

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / 'inputs' / 'item_1a_results.json'


def main():
    print('Fraud discovery — automatic text collection and a reproducible POC.')
    print('SEC contact: andrew@johnson.vet. No OpenAI calls or API key needed.')
    if INPUT_FILE.exists():
        print('First: method POC on your supplied healthcare/industrial Item 1A texts.')
        run_poc(INPUT_FILE, ROOT / 'reports' / 'proof_of_concept')
    output = ROOT / 'data' / 'financials_discovery.jsonl'
    report = ROOT / 'reports' / 'financials_discovery.md'
    try:
        fetch_company('19617', DEFAULT_USER_AGENT)
    except Exception as error:
        write_financials_report(None, report, error=str(error))
        print('SEC collection blocked:', error)
        print('Saved status report:', report)
        print('If running in Codex Cloud, allow data.sec.gov and www.sec.gov in environment settings.')
        return 1
    print('Collecting the bundled Financials companies, 2020–2026, annual/quarterly/current reports.')
    result = scanner.main(['--sp500-financials', '--forms', '10-K', '10-K/A',
                           '10-Q', '10-Q/A', '8-K', '8-K/A',
                           '--output', str(output)])
    write_financials_report(output, report)
    print('Discovery report:', report)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
