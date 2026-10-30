# Incretin LAI Radar

One tracker, two drugs: a Retatrutide | CagriSema switch in the header (`#reta/<page>`, `#cagri/<page>`; a bare `#<page>`
opens retatrutide). Each drug has its own data file (`reta_data.json`, `cagri_data.json`) with the same shape, plus a `meta`
block (name, originator, footer sources) that supplies every drug-specific word on the page. The retatrutide notes below
apply to both files.

## Retatrutide

Bilingual (EN/KR) competitor tracker for long-acting retatrutide: microspheres, lipid depots, in-situ gels, hydrogels
and implants dosed once a month or less often. Lilly's weekly retatrutide, oral drugs, generics and other triple-agonist
molecules are out of scope as competitors. Same format as the Presbyopia, Intranasal and Tirzepatide Radars, plus a page
on the patent holder.

1. **Competitors**: programme cards in stage lanes (in human testing → inactive), technology × stage table, Korea/Global
   and technology filters, target dosing interval, patents, and the trial registries checked.
2. **Patents**: long-acting retatrutide patent families and broader platform families that list retatrutide.
3. **Lilly timeline**: four key figures, a Gantt of Lilly's own retatrutide patent families on one year axis (first
   filing → expiry, the possible extension dashed, the molecule patent emphasised), and a year-by-year road map with a
   Today rule between what is done and what is planned.
4. **PK data**: the page question answered in one sentence, then (1) a by-day table of how the dose comes out or how the
   level holds, with day 28 marked as the monthly target, and (2) a comparison against the weekly product and approved
   depots on exposure (rBA) and peak.
5. **News**: dated events since Jan 2025.

`index.html` is one static file with all data built in - deploy it as-is. Internal use only.

## Files

| File | Role |
|---|---|
| `reta_data.json`, `cagri_data.json` | Per drug: all ledes, cards, patents, Lilly patent families (`estate`), milestones (`plan`) and news |
| `template.html` | Page design and rendering code |
| `build.py` | `python build.py [--as-of YYYY-MM-DD]` validates the data and renders `index.html`; `--check` validates only |

## Updating

Edit `reta_data.json`, run `python build.py`, commit both the JSON and `index.html`.

- Card `lane`: `clinic` needs a registered trial; `animal` = published animal/PK data; `patent` = patent or announcement only;
  `stopped` = ceased or dormant.
- Every card, milestone and news item needs English and Korean text and a source URL. News is sorted newest first and
  dated by the article's own printed date.
- `keyfacts` are the four tiles at the top of page 3: keep `value` short and language-neutral where possible.
- `estate[].short` labels a chart row (max 24 chars); `granted` and `title` feed the details table. `kind` is `compound`, `use`, `formulation` or `process`. `expiry` is the 20-year date (Google Patents' estimate
  or filing + 20 years); `extMax` is the furthest a term extension could reach and stays an estimate until one is granted.
- `plan[].done` is `false` for anything after `asOf`; the build refuses a "done" milestone dated in the future.
- `pk`: `answer` is the one-sentence reply to the page question, with the human target. `pk.table` is the by-day table:
  `days` columns, the `target` day (28), optional `guide` row (even monthly release), and `rows` with one value per day
  (0–100, a `[lo, hi]` range, or `null`), `end`, `peak`, `sub` and `src`; `muted` for comparison rows. Programmes with no
  by-day numbers go in `none`, never as empty rows. `pk.refs` is the comparison against the weekly product: one `target`
  row, then rows grouped by `refGroups`. Tag any value read off a chart or simulated with `kind` (`figure`, `simulated`);
  never type a value that is not in a source.
- Ledes carry `{n}`, `{p}` and `{q}` placeholders for the card, patent and platform counts; reread them when facts change.

## Ask panel

The "Ask" button (bottom right) opens a chat that sends the reader's question to `api/ask.js`, a Vercel function.
The function adds both drugs' data (English only, about 13k tokens) and asks Google's Gemini API on the free tier,
then returns an answer of up to about 150 words that names the page and card it used. Nothing is stored; the chat
history lives only in the reader's tab.

- Set `GEMINI_API_KEY` in Vercel (Project → Settings → Environment Variables), from a key made in Google AI Studio.
  Never put the key in the repo. Without it the panel says the assistant is not connected.
- Optional `GEMINI_MODEL` (default `gemini-3.8-flash`).
- Keep the Google project without a billing account: the free tier can then never charge, and when the daily free
  allowance runs out (reset at midnight US Pacific time) the panel says so until the next day.
- Free-tier terms: Google may use questions and answers to improve its products and people may review them, so the
  panel tells readers not to type confidential information. Apps offered to users in the EEA, UK or Switzerland need
  the paid tier.
- The function only accepts calls from this site's own pages and allows about 8 questions a minute per visitor.

Initial research: 2026-10-29, from ClinicalTrials.gov, Espacenet, Google Patents (rate-limited part-way), Lilly's SEC
filings and releases, Camurus releases, Korean and US trade press. China CDE, Korea MFDS/CRIS, EU CTIS and jRCT could not
be read automatically and are shown as not checked. Open questions at first build:

- Whether the triple agonist in Lilly's 2025 Camurus licence is retatrutide (no compound named anywhere).
- Which drugs G2GBio's ADA 2026 poster tested beside retatrutide (CagriSema or semaglutide - outlets differ).
- Korean and Japanese expiry dates of the compound family, and the claims of WO2026198842A1, were not readable.
- The FDA drug-vs-biologic appeal (5 vs 12 years of US exclusivity) had no ruling yet.
