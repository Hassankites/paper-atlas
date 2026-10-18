# M0 result — does Zotero show annotations written by another program?

Date: 2026-10-18
Environment: Zotero 10.0.2 (BuildID 20260826142222), Windows 11, data dir under a
non-ASCII path (`C:\Users\喜欢红糖馒头的内涵\Zotero`), Python 3.12.10, PyMuPDF 1.28.2.

## Question

If `annotate.py` writes standard PDF highlights into a file, does Zotero (a) display
them, (b) import them into its database, and (c) render the colour and comment?

## What we did

1. `scripts/probe_annotations.py` copied a real library PDF and added two `/Highlight`
   annotations with `/Contents`, `/Zotero:AuthorName`, `/Zotero:Key` and a `/C` RGB array.
2. The user dragged the copy into Zotero and opened it in the reader.
3. `--check-db` counted the imported rows.

## Result

| Check | Result |
| --- | --- |
| Highlights visible in the reader | yes, two |
| Imported into `itemAnnotations` | yes, `isExternal = 1` for both |
| Author shown as `Paper Atlas` | yes (from `/Zotero:AuthorName`) |
| Comment text | correct, not cleared |
| Colour | **wrong at first**: black. Root cause: `/Zotero:Color` was written as a *string*; Zotero parses that key as a number array and ignored it. Removing it and keeping only `/C` produced yellow. |

Re-run on NICE-SLAM (20 annotations, five roles): all visible, five distinct colours,
`added 20 / skipped 20` on the second run, no duplicates, user-created highlights
untouched.

## Not yet verified

`File → Import Annotations` (the `transfer = true` path that turns external annotations
into editable, synced Zotero annotations) has **not** been exercised end to end. The
code path is confirmed in Zotero's source (`pdfWorker/manager.js`,
`resource/document-worker/worker.js`), but no GUI run has confirmed it on 10.0.2.

Status: acceptance criterion 5 is pending one GUI click by the user.

## Consequence for the design

The zero-setup path is real: write `/Highlight` + `/Contents` + `/Zotero:AuthorName` +
`/Zotero:Key` + `/C`, never `/Zotero:Color` as a string, and never a comment that echoes
the highlighted text. Zotero's `isExternal = 1` means these do not sync as items, but the
PDF travels with file sync.
