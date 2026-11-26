# Part 4: explicit metric and period evidence

Base checkout: c99b025. Local branch: fix/part4-period-evidence.

## Problem

The final NVIDIA screenshot asks for FY2025 basic weighted-average shares.
A FY2023 row wins the cross-encoder score and the old fallback displays it
with 46% confidence, while the correct FY2025 row is second. Normalized
table reading was previously reached only for selected query patterns.

## Changes

- `retrieval/table_evidence.py` reads explicit label/column/value/unit pairs
  without issuer-specific branches. It keeps basic/diluted and segment
  qualifiers distinct, handles monetary/share/EPS/percentage units, and
  rejects missing, duplicate or conflicting requested columns.
- `extractor.py` uses this reader before sentence extraction for recognized
  metric questions on normalized tables. Unsupported evidence abstains;
  it does not fall back to a plausible-looking row. Mixed percentage tables
  retain the existing explicit-column reader.
- The EPS and total-revenue retrieval hints no longer depend on JPM/LLY names.
- `reranker.py` and `engine.py` pass issuer metadata into evidence checks.
  The existing verified-answer ordering now covers the general metric path
  before top-k truncation. Raw cross-encoder scores are not probabilities.
- `api.py` revalidates precomputed table answers against the original chunk.
  Confidence 0.99 from a caller cannot make an unsupported year eligible.
- Missing requested years receive zero evidence for recognized numeric metric
  questions. Narrative questions retain their previous fallback behavior.

Defaults remain 10 candidates, 256 passage tokens, batch size 2, threshold 0.30.
No index, vector, chunk or label changes are required for the demonstrated bug.

## Evidence and limits

The two fixture files pin actual text and chunk IDs from the approved local
14,022-chunk corpus. They test extraction, not Qdrant retrieval quality.

The 13-issuer check contains 10 expected numerical answers and 3 expected
abstentions: Intel's selected total-assets row has no year column; TSM's
selected revenue row has a percentage unit; VinFast's selected assets row has
duplicate 2024 columns and unknown units. Passing these checks does NOT mean
all queries or all tables for those companies are solved.

Six existing demo queries still have matching answer evidence in the corpus.
The NVIDIA regression selects FY2025: 24,555 million shares; the Apple EPS
regression selects FY2025: $7.49 per share rather than the entire multi-year row.

Limitations: matching is conservative lexical/alias matching, not an unrestricted
financial semantic parser. Quarter questions require explicit fiscal-quarter
evidence; the system does not infer a fiscal calendar from a filing date.
Currency support in the new reader is USD; unknown units and other currencies
are not converted. Data normalization defects must be reviewed upstream, not
silently patched by the extractor. Different share-split/restatement bases across
filings remain a source-level issue and are not normalized by this change.

## Recheck

Local targeted run (Python 3.11, 26 November 2026): **27 passed, 25 subtests
passed**, covering the existing answer-evidence tests, general metric tests,
reranker score inversion and API rejection of wrong-year precomputed answers.
The cross-encoder scores in regression tests are controlled; this result does
not replace a live-model benchmark.

Final full unit run: **97 passed, 2 warnings, 25 subtests passed in 9.31s**.
Run with the existing model cache and HF_HUB_OFFLINE=1. Warnings concern
Starlette/httpx deprecation and local Qdrant payload indexes. The earlier
online run was interrupted; the completed offline run is the reported result.
Bare-year narrative queries keep the existing fallback; the new strict
single-column path applies when a fiscal annual/quarter period is recognized.

Run `python -m pytest tests/unit -q` in the project environment.
The report-web launcher also runs the three targeted regression files before
starting the web. Restart it, then rerun the NVIDIA and Apple EPS screenshots
and six demo queries. Rerun the labeled evaluation under a NEW tag such as
`part4-period-fix`; do not overwrite `team-tung` results or claim the previous
MRR/NDCG/latency numbers apply to this changed ranking logic.

No changes have been pushed to the group's integration branch.
