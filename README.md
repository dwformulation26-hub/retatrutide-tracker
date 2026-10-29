# Retatrutide LAI Radar

Bilingual (EN/KR) competitor tracker for long-acting retatrutide: microspheres, lipid depots, in-situ gels, hydrogels
and implants dosed once a month or less often. Lilly's weekly retatrutide, oral drugs, generics and other triple-agonist
molecules are out of scope as competitors. Same format as the Presbyopia, Intranasal and Tirzepatide Radars, plus a page
on the patent holder.

1. **Competitors**: programme cards in stage lanes (in human testing → inactive), technology × stage table, Korea/Global
   and technology filters, target dosing interval, patents, and the trial registries checked.
2. **Patents**: long-acting retatrutide patent families and broader platform families that list retatrutide.
3. **Lilly timeline**: Lilly's own retatrutide patent families on one time axis (priority → 20-year expiry, with the
   possible extension dashed), and Lilly's milestones, done and planned.
4. **News**: dated events since Jan 2025.

`index.html` is one static file with all data built in - deploy it as-is. Internal use only.

## Files

| File | Role |
|---|---|
| `reta_data.json` | All ledes, cards, patents, Lilly patent families (`estate`), milestones (`plan`) and news |
| `template.html` | Page design and rendering code |
| `build.py` | `python build.py [--as-of YYYY-MM-DD]` validates the data and renders `index.html`; `--check` validates only |

## Updating

Edit `reta_data.json`, run `python build.py`, commit both the JSON and `index.html`.

- Card `lane`: `clinic` needs a registered trial; `animal` = published animal/PK data; `patent` = patent or announcement only;
  `stopped` = ceased or dormant.
- Every card, milestone and news item needs English and Korean text and a source URL. News is sorted newest first and
  dated by the article's own printed date.
- `estate[].kind` is `compound`, `use`, `formulation` or `process`. `expiry` is the 20-year date (Google Patents' estimate
  or filing + 20 years); `extMax` is the furthest a term extension could reach and stays an estimate until one is granted.
- `plan[].done` is `false` for anything after `asOf`; the build refuses a "done" milestone dated in the future.
- Ledes carry `{n}`, `{p}` and `{q}` placeholders for the card, patent and platform counts; reread them when facts change.

Initial research: 2026-10-29, from ClinicalTrials.gov, Espacenet, Google Patents (rate-limited part-way), Lilly's SEC
filings and releases, Camurus releases, Korean and US trade press. China CDE, Korea MFDS/CRIS, EU CTIS and jRCT could not
be read automatically and are shown as not checked. Open questions at first build:

- Whether the triple agonist in Lilly's 2025 Camurus licence is retatrutide (no compound named anywhere).
- Which drugs G2GBio's ADA 2026 poster tested beside retatrutide (CagriSema or semaglutide - outlets differ).
- Korean and Japanese expiry dates of the compound family, and the claims of WO2026198842A1, were not readable.
- The FDA drug-vs-biologic appeal (5 vs 12 years of US exclusivity) had no ruling yet.
