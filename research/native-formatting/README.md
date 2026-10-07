# Controlled native formatting evidence

Read [the evidence note](../../specs/11-native-formatting-evidence.md) for measured results, inferences, and coverage limits.
`reader.py` is a conservative research reader for the supplied single-paragraph
InPage100 header profile, not a production or complete format parser.

The contribution contains minimal formatting excerpts and hashes. Original
documents stay local. The author reported successful saving and reopening.
No native UI automation is necessary to reproduce the byte checks.

## Run the excerpt tests

Python 3.10+:

```text
python -m unittest discover -s . -p test_reader.py -v
```

The fifteen tests need only this directory's files. They read native excerpts
from `evidence.json` and reject malformed envelopes. They do not establish
native rendering or general run ownership.

## Verify the original native documents

From this directory:

```text
python verify.py PATH_TO_FROZEN_SAMPLES --report new-report.json
```

Provide the exact fifteen originals with the hashes in `evidence.json`.
`olefile` 0.47 is bundled in `vendor/`. Files are read only. The optional report
path must be new; existing output files are not overwritten. The report omits
document text, metadata, font memory, and local absolute paths.

## Reproduce the independent container check

With SheetJS `cfb` 1.2.2 available, Node.js 18+:

```text
node compare_cfb.mjs PATH_TO_CFB_JS PATH_TO_FROZEN_SAMPLES new-cfb-report.json
```

The script checks all original file hashes, reconstructs each InPage100 stream
with a second reader, and compares it with the olefile-derived stream hash.

## Reproduce the upstream comparison

With the pinned upstream source and TypeScript 5.x available:

```text
node compare_upstream.mjs format-extractor.ts typescript.js EXTRACTED_STREAMS_DIR new-upstream-report.json
```

Each extracted-stream directory must be named after its input without `.inp`,
and contain `stream-0001.bin`. Stream hashes and the canonical-LF source hash
are validated. Saved reports record the actual results; no dependency is
downloaded or application launched by these scripts.

The whole-text settings are corroborated by the supplied experiment labels.
The body/CR ownership is inferred for this profile. An independent native
inline test and general structural reader are still outstanding.
