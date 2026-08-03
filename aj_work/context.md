# Context: what happened, and how we know

Consolidated findings for the campaign audit. This is the shared reference for
what the evidence supports, what is inference, and what stays open.

Companion documents:

- `discrepencies/step1_discrepancies.md` — row-level inventory of both lists.
- `claude_discrepancies.md` — inspection findings and scanner output.

This file does not repeat those tables. It covers the **runtime** story: what
the recorded runs actually did, why the shipped check agreed with them, and
which numbers can be trusted.

---

## 1. The three numbers, and their units

Three different numbers circulate in the starter, in two different units. They
are not alternatives to each other.

| Number | Unit | Meaning |
|---:|---|---|
| 223 | rows | rows actually present in `fixtures/target_accounts.json` |
| 217 | rows | what the README claims, and what the service actually served |
| 209 | companies | logical companies under our identity rule |
| 205 | companies | the alternative if the 4 contested identity relationships were merged |

Terminology note: **4 contested identity relationships, involving 8 company IDs**,
drive the 209-versus-205 decision. Both IDs in each pair are contested — the
upload establishes neither as canonical — so the count falls by 4 whichever side
a merge absorbs. Separately, **5 contested companies** need human review: the four
a merge would most likely absorb, plus `company-kestrel-robotics`, whose two
domains are unresolved but whose count is not in doubt. 4, 8 and 5 answer
different questions and are not in conflict; say which you mean when quoting one.
Canonical definitions and the full table live in
`discrepencies/step1_discrepancies.md`, "Canonical wording for the contested
records."

The `223 → 217` gap is explained exactly by the row-id blocks:

```
id block 1xxx: 217 rows  range row-1001..row-1217
id block 2xxx:   6 rows  range row-2401..row-2406
```

Every `1xxx` row carries a `company_id`; no `2xxx` row does. The `2xxx` block is
precisely the six null-identity rows. They are scattered through the file
(positions 12, 37, 61, 98, 149, 202), not appended, so this is not a case of
someone forgetting to update a count after adding rows to the end.

The ladder from rows to companies:

```
223  rows in the file
     ├─ 217  rows carrying a company_id   ──► 203 distinct companies
     │                                         (14 rows are repeat mentions:
     │                                          12 pairs + 1 triple)
     └─   6  rows carrying none           ──►   6 distinct companies
                                                (unique domains, zero collisions)

     203 + 6 = 209 logical companies
     209 − 4 = 205 if the 4 contested identity relationships were merged
```

**Takeaway: no number quoted anywhere in the starter is trustworthy without
deriving it yourself.** The README says 217, the trace claims 209, the demo
prints 214 rows campaigned and 204 distinct company ids, and none of them
answer "how many companies did the customer ask for."

---

## 2. Reconstruction of the recorded runs

`fixtures/failure-traces.jsonl` holds **three separate runs** interleaved across
10 events.

### t-9f21 — the run that reported success

The log records three `tool_result` events: 25 + 25 + 17 = 67 rows. Yet it
claims `source_row_count: 209`. You cannot get 209 companies out of 67 rows, so
the log must be **elided** — it records the first two pages and the last, not
the six in between.

That makes the final page's `row_count: 17` a fingerprint of the total:

```
all 223 rows -> 9 pages, last page row_count=23
only 217     -> 9 pages, last page row_count=17    <-- trace says 17
```

Running the starter's planner over just the 217 `1xxx` rows reproduces the
trace exactly:

```
all 223 rows          -> source_row_count=214, deliverables=856
only 1xxx (217 rows)  -> source_row_count=209, deliverables=836
trace t-9f21 claimed  -> source_row_count=209, deliverable_count=836
```

Three independent numbers — last-page count, row count, deliverable count — all
match on the 217-row hypothesis and none match on 223. **This is a confirmed
reconstruction, not a guess.**

What that run actually shipped:

| | |
|---|---|
| companies never served at all | **6** (the null-`company_id` rows) |
| companies shipped **twice** | **6** — sable-works, kestrel-dynamics, harbor-group, ironwood-logistics, vantage-networks, tessellate-energy |
| deliverables in the **wrong brand kit** | **36** in `brand-kit-2019-legacy` vs 800 in the requested Meridian 2026 |
| what the shipped check said | `passed: true` |

The six doubled companies are exactly those whose duplicate rows straddled a
page boundary at `page_size=25` and so escaped the per-page dedupe. The eight
duplicate groups that happened to land inside one page were collapsed. **Which
companies get double-billed is a function of page size and nothing else.**

### t-77b3 — the rerun that never came back

```
row_count 25, next_cursor "25", truncated true
row_count 25, next_cursor "25", truncated true      <-- same cursor
worker_timeout, elapsed 90s, "No terminal campaign result was recorded."
```

The cursor does not advance. `build_campaign_plan` follows `next_cursor` with no
progress check, so it spins until the worker is killed. This is `StallingLoader`
from `src/sources.py`; running that loader through the planner reproduces the
hang (`RuntimeError: page budget exhausted`). It maps directly onto the
customer's *"I also kicked off a rerun that never came back."*

### t-4c08 — the decoy

An `image_search` timeout marked `retryable: true`, and a `template_cache` cold
start that rebuilt itself in 310ms. Both self-healing; neither touches counts,
identity, or brand kits. It is also the one run with **no terminal event** — no
output, no evaluation — so its outcome is unknown.

Read as deliberately planted noise. TASK.md warns *"Don't repair behavior you
can't tie to the customer's complaint."* This is the thing not to fix. It
belongs in `DECISIONS.md` under what we chose to leave alone.

---

## 3. The 209 is right by accident

This is the central trap and the reason the customer's instinct beat the check.

The run claimed 209. We independently calculate 209 logical companies. Same
number, completely different composition:

```
claimed 209 = 203 companies served once  +  6 duplicate rows that survived
  true  209 = 203 companies served once  +  6 companies never served at all
```

The six extra shipments and the six missing companies **cancel out exactly**. So
the headline number looks defensible, the shipped check agrees, and the customer
is still right — they are paying for six duplicates while six of their targets
received nothing.

**Consequence for the design: a count can never be the completeness test.** Any
check that compares totals passes this run. Only a check that matches each
deliverable back to a specific uploaded row catches it.

---

## 4. Why the shipped check could not have caught this

`evaluate_campaign_coverage` asks only: do the rows *that made it into the plan*
have four assets each?

- It never compares the plan against the upload, so a plan containing one row
  passes.
- It echoes `plan["complete"]`, which `build_campaign_plan` hardcodes to `True`
  (`src/repair_lab.py:124`).
- It reports a count of rows it was itself handed, which is why its message
  ("all 209 campaigned rows...") reads as corroboration when it is circular.

It cannot fail for the reason the customer cares about.

---

## 5. Defects, and which are cause vs symptom

| # | Defect | Location | Cause or symptom |
|---|---|---|---|
| 1 | Check never reconciles against the upload | `evaluate_campaign_coverage` | **cause** |
| 2 | `complete` hardcoded `True` | `repair_lab.py:124` | **cause** |
| 3 | Dedupe is per-page, so results depend on page size | `_collapse_page` | **cause** |
| 4 | `str(None)` / `str("")` collapses all null-identity rows into one | `_collapse_page` | **cause** |
| 5 | Row-level `saved_brand_kit_id` silently overrides the request | `_make_deliverables` | **cause** (of silence) |
| 6 | Paging loop trusts `truncated`, no progress check, `int(None or "0")` restarts at 0 | `build_campaign_plan` | **cause** |
| 7 | Six companies missing from output | — | symptom of 4 and 6 |
| 8 | Six companies double-billed | — | symptom of 3 |

---

## 6. Every paging shape in `sources.py` breaks the planner

All five loaders run through `build_campaign_plan` over list 1:

```
ReplayingLoader                rows=428  complete=True   # every row duplicated
StallingLoader                 RuntimeError: page budget exhausted
CyclingLoader                  RuntimeError: page budget exhausted
SilentlyShortLoader            rows=116  complete=True   # 107 rows never read
TruncatedWithoutCursorLoader   RuntimeError: page budget exhausted
```

Two of these return `complete=True` on a wrong answer; three hang. Note that for
`SilentlyShortLoader` and `TruncatedWithoutCursorLoader` **the correct outcome is
not a number** — TASK.md requires being "honest about the ones where the correct
answer is that the list cannot be read completely."

The full matrix is 2 lists × 5 loaders = 10 combinations, and passing all ten
does not mean returning ten numbers.

---

## 7. Why there are two lists

They are **two independent uploads**, not the same data fetched differently.
Zero overlap on every identity field:

```
id             list1= 223 list2= 115 overlap=  0
company_id     list1= 204 list2=  98 overlap=  0
company_name   list1= 221 list2= 113 overlap=  0
domain         list1= 207 list2=  99 overlap=  0
```

Shared *vocabulary* only (`kestrel`, `sable`, `vantage`, `works`) attached to
different companies. The "same data, read differently" axis is `sources.py`; the
two files are a different axis entirely.

Structural differences — each one a way to pass list 1 and be wrong:

| | list 1 | list 2 |
|---|---|---|
| missing-id sentinel | `None` | `""` |
| row id prefix | `row-` | `srow-` |
| `saved_brand_kit_id` rows | 9 | **0** |
| same-domain / different-id groups | 4 | **0** |
| name variants | UPPERCASE, `+Inc`, identical | `+Inc`, identical only |
| dup groups straddling a page (size 25) | 5 of 13 | **1 of 15** |
| logical companies | 209 | 99 |

Specific traps:

- **The sentinel flips.** `if company_id is None` passes list 1 and silently
  re-collapses list 2's two `Unresolved Import` rows.
- **List 2 has no brand-kit overrides**, so the exception report must be correct
  when empty.
- **List 2 has no contested identity relationships**, so it returns 99 whether we report
  209-and-flag or merge-to-205. **List 2 cannot validate the identity choice** —
  it can only prove we did not hardcode it.
- **The page-boundary distribution is inverted** (5-of-13 vs 1-of-15), so
  per-page dedupe looks far less broken on list 2. Had only list 2 shipped, the
  page-size bug would be easy to miss.
- **Name normalization** built against list 2 alone never learns case folding.

**Why the two lists do not produce the same shape of answer:** list 1 requires an
"contested — needs a human" section that list 2's report legitimately leaves
empty. A check that emits one clean number for both is hiding something.

---

## 8. Mapping to the customer's complaint

Every line of `fixtures/customer_report.txt` is accounted for:

| complaint | finding |
|---|---|
| "a couple of companies came back twice" | 6, page-size dependent |
| "creative is not in the brand we picked" | 36 deliverables in `brand-kit-2019-legacy` |
| "entries I cannot tell apart" | 4 contested identity relationships across 8 company IDs; 5 companies need review |
| "a rerun that never came back" | t-77b3, stalled cursor, 90s timeout |
| "I don't believe the number" | correct — 209 is right for the wrong reasons |

The six never-served companies are the most serious defect, and the customer
could not have known about them.

---

## 9. Proposed definition of "complete"

Precise enough for a check to enforce:

> Every logical company in the upload has exactly 4 deliverables, each traceable
> to a specific uploaded row; the count is independent of page size; the read is
> provably exhaustive, or the run declares itself incomplete and says why; and
> every deliverable uses the requested brand kit or is explicitly listed as an
> exception.

Four separable obligations: **coverage**, **traceability**, **determinism**,
**honesty about the read**.

---

## 10. Open questions and things left uncertain

- **Why the service served 217 and not 223.** The reconstruction proves the
  service *delivered* 217 rows; it does not prove why. Whether upstream dropped
  the unresolvable rows before serving them, or the fixture represents a later
  state of the upload, cannot be determined from what is here. It does not
  change the fix — a reader must reconcile against what it was asked to load —
  but it should be flagged as open, not asserted as a cause.
- **The 4 contested identity relationships (209 vs 205).** Current position:
  report 209 and flag them rather than deciding for the customer. Silently
  merging a regional subsidiary is the same class of error as silently dropping
  one. This is a policy choice, not a fact in the data — and note that the
  choice is doubly open: whether to merge at all, and if so which of the two
  company IDs in each pair survives. The upload establishes neither as
  canonical.
- **The 2 same-ID / conflicting-domain groups** (`company-kestrel-robotics`,
  `company-copperline-energy`, per `step1_discrepancies.md`). The company count
  can stay at one per ID, but which domain is correct is unresolved, and picking
  the first row encountered makes personalization an ordering accident.
  `company-copperline-energy` is already inside the group of 4;
  `company-kestrel-robotics` is the 5th contested company and affects output
  correctness without affecting the count.
- **Whether `saved_brand_kit_id` is a bug or a feature.** The customer says the
  creative was not in the brand they picked. Leaning toward *surfacing as an
  exception rather than removing the mechanism* — but silent override is wrong
  either way.
- **The README's "217".** Currently unmodified. It is the clearest artifact of
  the anchoring problem, so it may be worth showing a reviewer rather than
  quietly correcting.
- **Generalization.** Two hand-built lists are a weak held-out set. Passing both
  shows we did not fit to one file; it does not show the fix survives a real
  upload. The stronger argument rests on `sources.py` — a check that survives all
  five paging pathologies holds for reasons unrelated to either fixture.

---

## 11. Commands that produced these findings

```bash
# baseline, both lists
make demo
make verify

# page-size drift (list 1): 214 / 214 / 211 rows campaigned
PYTHONPATH=src python3 demo.py

# all five paging shapes against the planner
PYTHONPATH=src python3 -c "
import json, signal
from repair_lab import build_campaign_plan
import sources
a = json.load(open('fixtures/target_accounts.json'))
signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError('hung')))
for cls in sources.ALL_SOURCES:
    signal.alarm(10)
    try:
        p = build_campaign_plan(cls(a), brand_kit_id='bk', template_id='tp', page_size=25)
        print(f'{cls.__name__:32} rows={len(p[\"source_row_ids\"]):6} complete={p[\"complete\"]}')
    except Exception as e:
        print(f'{cls.__name__:32} RAISED {type(e).__name__}: {e}')
    finally:
        signal.alarm(0)
"

# trace reconstruction: 217-row hypothesis reproduces 209 / 836 exactly
PYTHONPATH=src python3 -c "
import json
from repair_lab import TargetAccountTool, build_campaign_plan
a = json.load(open('fixtures/target_accounts.json'))
only1 = [r for r in a if r['id'].startswith('row-1')]
for name, rows in (('all 223 rows', a), ('only 1xxx (217 rows)', only1)):
    p = build_campaign_plan(TargetAccountTool(rows), brand_kit_id='x', template_id='y', page_size=25)
    print(f'{name:22} -> rows={len(p[\"source_row_ids\"])}, deliverables={len(p[\"deliverables\"])}')
"
```
