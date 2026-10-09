# Local CERT data only

RiskOps AI intentionally does not ship, download, or redistribute CERT source files, answer keys, derived records, or trained model artifacts.

## Verified source record

- Publisher/provenance: Carnegie Mellon University Software Engineering Institute (CERT Division), with ExactData, LLC and DARPA I2O sponsorship.
- Official landing page: <https://www.sei.cmu.edu/library/insider-threat-test-dataset/>
- Archive: DOI <https://doi.org/10.1184/R1/12841247.v1>, KiltHub/Figshare article 12841247, version 1 (metadata modified 2023-05-30).
- Selected release: `r4.2.tar.bz2` (official archive listing: 4,824,287,500 bytes).
- License displayed in the archive metadata: CC BY 4.0. Preserve attribution and review the official archive/README before use; this repository's MIT license applies to code only.
- Labels: the separate `answers.tar.bz2` archive contains `insiders.csv`; SEI describes it as the answer key with malicious scenarios and synthetic-user identifiers. RiskOps expands its `start`–`end` windows into **evaluation-only** user-day labels.

CERT calls this a synthetic test dataset. It is not production employee telemetry, and benchmark results must not be presented as production performance.

## Expected paths

Download directly from the official source, validate the provided checksums, and extract only to ignored folders:

```text
data/raw/r4.2/logon.csv
data/raw/r4.2/device.csv
data/raw/r4.2/file.csv
data/raw/r4.2/email.csv
data/answers/insiders.csv
```

The release README inside `r4.2.tar.bz2` is authoritative for exact column names and conventions. At startup the pipeline validates the presence of `date` and `user` for every event file, `activity` for logon/device, and `dataset`, `user`, `start`, `end` in `insiders.csv`. It never needs `http.csv`, psychometric, or LDAP data for the baseline.

Run from the project root after setup:

```powershell
$env:PYTHONPATH = "src"
python -m riskops.pipeline
```
