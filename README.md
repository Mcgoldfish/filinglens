# Filing Lens

[Open FilingLens](https://mcgoldfish.github.io/filinglens/) · [Source repository](https://github.com/Mcgoldfish/filinglens)

Standalone public repository prepared from the current McQuerious edition. The portfolio remains a project guide; this repository contains the application, search worker, indexed collection and ingestion tools. Run `npm test` and `npm run dev` (Node.js 20+). To rebuild the collection, install `requirements.txt` with Python first. No open-source license has been selected; public visibility does not grant a general source-code reuse license. Source annual reports retain their original ownership and source links.

A search-first annual report website inspired by a simple topic-search workflow.

## Run

`node server.cjs` serves the buildless site on http://127.0.0.1:4173.

`node check-search.cjs` checks report identity and search behavior against the actual collection.

## Data

The 2026-10-13 constituent reference is the Wikipedia Nasdaq-100 company list. It is not an independently certified current Nasdaq list. Alphabet's two share classes use one report. The collection has 100 company records, with an explicit status for every company. Currently 28 have indexed annual reports and 72 remain unavailable after archive access and verification failures. It does not cover the entire Nasdaq-100's report text.

Reports are real annual reports downloaded through published AnnualReports.com links. Archive years from download filenames are displayed (they can differ from the fiscal reporting year), and may be older than the latest filing. Extracted PDF text can contain reading-order and whitespace errors; source links include the PDF page number. Report identity is checked by exchange and ticker in the archive filename and a company-name check in the report front matter. Do not substitute a same-ticker report from a different exchange.

`ingest.py` rebuilds the collection with Python and pypdf. It limits outgoing request starts and lists download or verification failures instead of inventing content. `--cached-only` rebuilds from previously validated reports without attempting more archive downloads. `.report-cache` is ignored by Git.

## Features

- Keyword search with all-word matching on a page; quotation marks specify phrases.
- Highlighted passages, company/industry/year filters, relevance/year/company sorting.
- Source-page detail and original PDF links.
- Shareable search URLs and local saved searches.
- Saved searches retain counts for manual comparison after a refreshed snapshot; no scheduled updates or alerts.

The compressed collection is loaded and searched in a Web Worker. No API keys, user accounts, or server database are required. Local saved searches are confined to the browser.
