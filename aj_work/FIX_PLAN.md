# Fix plan — issues, solutions, and the numbers each one moves

Every number below was measured, not estimated. "Current" is what the repo does
today. "Expected" is what the same command should print once the fix lands.

**Revision 2.** Adds three defects found in review — two of them reproduced bugs
in code this plan previously proposed shipping (**A4**, **B4**) and one
undecided output policy (**C4**). Corrects the C2 and B2 figures, merges the
first two work steps, moves A3 from *unfixable* to *partly closed*, and reverses
the brand-kit decision in **C3**.

**Revision 3.** Settles **C4** — no company is blocked; a domain claimed by more
than one `company_id` is disqualified, and a leftover single-owner conflict is a
note rather than a blocker. Restates the `t-9f21` reconstruction after testing it
(**D3**): the numeric match is far weaker evidence than revision 2 claimed.

**Revision 4.** Adds **A5 — filtered read**, a distinct failure mode from A3 that
no loader in `sources.py` models and that the page shape shows is what actually
happened. Repoints the `t-9f21` narrative from A3 to A5.

**Revision 5.** Four corrections to this document's own proposals, all verified
against the fixtures: **C4**'s rule 1 stripped the only domain from 7 companies
and is rewritten as a preference; **A4**'s cursor rule was wrong in both
directions and is replaced; **B4** reached the company key but not provenance;
**D1** carried a stale brand-kit loophole from revision 2.

**State of the repo:** `src/identity.py` and `src/paging.py` are written, but
**nothing is wired into the product path**. `src/repair_lab.py`, `demo.py` and
`tests/test_visible.py` are untouched starter code, so `make demo` and
`make verify` still run the original broken planner end to end.

```bash
git diff 8f0f5c7 --stat -- src/ tests/ demo.py Makefile
#  Makefile        |  10 ++-
#  src/identity.py | 197 +++++++++++++++++++++++++++++++++
#  src/paging.py   | 119 +++++++++++++++++++
#  (repair_lab.py, demo.py, tests/ unchanged)
```

---

## Headline numbers

### List 1 — `fixtures/target_accounts.json` (223 rows on disk)

| Measure | Current | Expected | Why it changes |
|---|---:|---:|---|
| rows campaigned @ ps=10 | 214 | **209** | companies, not rows |
| rows campaigned @ ps=25 | 214 | **209** | " |
| rows campaigned @ ps=100 | 211 | **209** | " |
| deliverables @ ps=25 | 856 | **836** | 209 × 4 |
| deliverables @ ps=100 | 844 | **836** | " |
| distinct companies in plan | 204 | **209** | 203 identified + 6 unidentified |
| deliverables in requested kit | 820 | **836** | request now wins — **C3** |
| deliverables in legacy kit | 36 (silent) | **0**, 9 companies listed as exceptions | **C3** |
| page-size variance | **3 different answers** | **0 — invariant** | the core fix |
| completion | `complete: True` | **structured** — see **D2** | boolean replaced |

### List 2 — `fixtures/second_list.json` (115 rows on disk)

| Measure | Current | Expected | Why it changes |
|---|---:|---:|---|
| rows campaigned @ ps=10 | 103 | **99** | companies, not rows |
| rows campaigned @ ps=25 | 100 | **99** | " |
| rows campaigned @ ps=100 | 98 | **99** | ← was **below** the true count |
| deliverables @ ps=25 | 400 | **396** | 99 × 4 |
| distinct companies in plan | 98 | **99** | 97 identified + 2 unidentified |
| exceptions block | absent | **present and empty** | proves no special-casing |
| page-size variance | **3 different answers** | **0 — invariant** | the core fix |

> **Watch this number.** List 1 lands on **836**, exactly what trace `t-9f21`
> claimed. Same number, different composition: the trace got 209 *rows* × 4 after
> partial dedupe; we get 209 *companies* × 4. Not confirmation — see **D3**.

> **C4 is settled — nothing is blocked.** Every company receives an address, so
> list 1 stays at **836**. 195 companies resolve silently, **8 carry a domain
> note** (1 with competing sole-owned domains, 7 whose only domain is shared —
> already contested identities). Revision 2's "828 + 2 blocked" alternative is
> withdrawn; revision 3's "1 flagged" undercounted because its rule 1 was broken.

---

## Issue inventory — 20 issues in 6 groups

**P0** ships wrong creative to a real customer. **P1** makes a wrong answer
undetectable. **P2** correctness of the report.

| # | Issue | Severity | Status |
|---|---|---|---|
| A1 | Paging loop hangs on stalled/cycling/cursorless services | P1 | fixed in `paging.py`, **not wired** |
| A2 | Replayed pages double-count rows | P1 | fixed in `paging.py`, **not wired** |
| A3 | Short read claiming success is undetectable | P1 | **partly closable** — see below |
| **A4** | **Page fingerprinting discards legitimate duplicate pages** | **P0** | **reproduced bug in `paging.py`** |
| **A5** | **Filtered read — protocol-perfect read of an incomplete row set** | **P1** | **not modelled by any loader; what `t-9f21` actually shows** |
| B1 | Dedupe is per-page, so the count depends on page size | P0 | policy in `identity.py`, **not wired** |
| B2 | `str(None)` / `""` folds unrelated companies into one | P0 | policy in `identity.py`, **not wired** |
| B3 | Identity policy not applied in the product path | P0 | **not wired** |
| **B4** | **Blank-identity rows merge when uploaded ids collide** | **P0** | **reproduced bug in `identity.py`** |
| C1 | Deliverables keyed to rows, so duplicates get 4 assets each | P0 | not started |
| C2 | No traceability from deliverable back to uploaded rows | **P1** | not started — **co-requisite of step 1** |
| C3 | Row `saved_brand_kit_id` overrides the request | P0 | not started — **policy reversed** |
| **C4** | **No rule for which domain personalizes a conflicted company** | **P1** | **decided — see below** |
| D1 | Check never reconciles the plan against the upload | P1 | not started |
| D2 | Completion is a hardcoded boolean | P1 | not started |
| D3 | Check echoes the plan's own claim (circular) | P1 | not started |
| E1 | Contested records not surfaced for review | P2 | detectors exist, no report |
| E2 | No guard for conflicting attributes within one identity | **P1** | not started |
| F1 | `demo.py` reports rows, not companies | P2 | not started |
| F2 | `tests/test_visible.py` asserts the broken check passes | P1 | not started |

---

## Group A — reading the upload

### A1. Paging loop hangs on stalled, cycling, or cursorless services

`build_campaign_plan` follows `next_cursor` with no progress check and does
`int(None or "0")` when the cursor is absent — restarting at zero forever. This
is *"a rerun that never came back"*; trace `t-77b3` shows cursor `25` twice, then
`worker_timeout` at 90s.

**Current** (starter planner, list 1, ps=25):

```
StallingLoader                 RuntimeError: page budget exhausted
CyclingLoader                  RuntimeError: page budget exhausted
TruncatedWithoutCursorLoader   RuntimeError: page budget exhausted
```

**Solution.** Route reads through `paging.collect_rows` — already written,
**pending the A4 fix**.

**Expected** (list 1, ps=25):

| Loader | rows | complete | reason |
|---|---:|---|---|
| `StallingLoader` | 75 | **False** | cursor stopped advancing at `'50'` |
| `CyclingLoader` | 223 | **False** | cursor stopped advancing at `'50'` |
| `TruncatedWithoutCursorLoader` | 25 | **False** | more rows claimed, no cursor supplied |

`CyclingLoader` collects all 223 rows yet still reports `complete=False` —
correct conservatism.

---

### A2. Replayed pages double-count rows

**Current:** `ReplayingLoader` → `rows=428`, `complete=True`.

**Expected:** `rows=223, companies=209, complete=True` at every page size.

---

### A4. Page fingerprinting discards legitimate duplicate pages — **P0, NEW**

**Problem.** `paging.py:47` fingerprints a page by its serialised content and
drops any page whose fingerprint was seen before. Two *legitimate* pages with
identical row content are therefore treated as a replay and silently discarded.

**Reproduced:**

```
upload: 50 rows, second half byte-identical to first half
rows collected: 25 of 50   complete=True
reason: service reported the end of the list
```

**Half the upload lost, and the reader declared success.** This is the same
defect class as `SilentlyShortLoader` (A3) — except introduced by our own fix,
in code this plan previously proposed shipping unchanged.

The docstring reasons its way into the bug and contradicts itself:

> *"Deliberately not keyed on row ids: an upload is not guaranteed to give every
> row a unique one, and a replayed page is a property of the page."*

If row ids are not guaranteed unique, then two legitimate pages **can** be
byte-identical — which is exactly the failing case. Not triggered by either
fixture, so no existing test would catch it.

**Solution — revised; the obvious fix does not work.** Revision 2 proposed *"a
page is a replay only if the cursor did not advance."* Traced against the actual
loaders, that is wrong in **both** directions:

```
ReplayingLoader                     StallingLoader
sent  first     next  advanced?     sent  first     next  advanced?
None  row-1001  0     n/a           None  row-1001  25    n/a
0     row-1001  25    n/a           25    row-1023  50    n/a
25    row-1023  25    yes           50    row-1045  50    yes   <- NEW rows, cursor repeats
25    row-1023  50    NO            50    row-1045  50    NO
```

- **`ReplayingLoader`** — the first duplicate arrives at request 2 (`None` →
  `"0"`), where the sent cursor *did* change. The rule misses it and ingests 25
  extra rows. It only catches the later pairs.
- **`StallingLoader`** — at request 3 the rows are **new**, yet `next_cursor`
  equals the cursor just sent. Reading that as "replay, discard" **loses
  `rows[50:75]`.**

The rule conflates two distinct signals. Separate them:

| Signal | Meaning | Action |
|---|---|---|
| Same cursor repeatedly returns no new content and fails to advance beyond the allowed replay retry | **stall** — the service is not progressing | stop, `complete=False`. **Never** discard first-seen rows |
| Page content already held | **suspected replay** — not decidable alone | see below |

**Replay is not decidable from the protocol.** Content-matching catches every
replay but false-positives on legitimate duplicate pages (the bug above); cursor
rules avoid false positives but miss real replays. So:

- **With a declared row count** (A3/A5): dedupe iff doing so reconciles to the
  declared size. The count decides, not a heuristic.
- **Without one:** **keep the rows** — never lose data — and mark the result
  `verified_complete: unknown`, reporting both the raw and deduped totals.

**Expected:** the 50-row identical-halves case returns `rows=50` — no loss.
`ReplayingLoader` with a declared size of 223 returns `rows=223, complete=True`;
**without** a declared size it returns `rows=428, verified_complete: unknown`,
reporting that 223 is the deduped alternative. That is a real cost of honesty
over guessing, and it is why A4's fix depends on A3/A5 landing.

---

### A3. A short read that claims success — **partly closable**

**Problem.** `SilentlyShortLoader` stops early and sets `truncated=False`. From
inside the loader interface that is indistinguishable from a genuine end.

**Current:**

| List | rows served | companies | complete | correct? |
|---|---:|---:|---|---|
| List 1 @ ps=25 | 125 of 223 | 116 | `True` | **no — 93 companies missing** |
| List 1 @ ps=100 | 200 of 223 | 191 | `True` | **no — 18 missing** |
| List 2 @ any ps | 115 of 115 | 99 | `True` | yes, by luck |

> **`make verify` is blind to A3.** `STOP_AFTER = 120` exceeds list 2's 115 rows,
> so the loader never truncates there. Second question — after the identity rule
> — where the held-out list proves nothing.

**Solution — closable for every path the harness exercises.** An earlier draft
called this unfixable "because no fixture provides an expected row count." That
was wrong. `demo.py` already reads the upload to construct the loader and holds
`len(accounts)`; it simply does not pass it. **An upload record declaring its own
size is independent of the paging service** — that is how a real upload works,
and it is not reading behind the interface, since the rows still arrive through
`load_page`.

1. Give `collect_rows` an optional `expected_row_count`. When supplied,
   reconcile and fail loudly on a shortfall.
2. Keep the claimed-vs-verified split regardless (see **D2**).

**Expected with the count supplied** (list 1, ps=25): `SilentlyShortLoader` →
`rows=125, complete=False, reason="expected 223 rows, service ended after 125"`.
Without a count: rows unchanged, reported as `verified_complete: unknown`.

**Residual limit:** a caller that genuinely has no declared size. Much narrower
than "undetectable."

> **A3 is not what happened to this customer.** It describes
> `SilentlyShortLoader`, a real shape in `sources.py` that must still be handled.
> The recorded incident is **A5** below — a different mechanism with the same
> remedy.

---

### A5. Filtered read — a protocol-perfect read of an incomplete row set — **P1, NEW**

**Problem.** The row set handed to pagination is already missing rows. Paging
then behaves *correctly* over it: clean cursor chain, natural partial final page,
honest `truncated: false`. Nothing in the protocol is violated, so **no amount of
hardening in `paging.py` can see it.**

**The page shape shows this, not A3, is what `t-9f21` records:**

```
trace t-9f21 (ps=25):        9 pages, final page 17 rows, truncated=False

SilentlyShortLoader / 223:   5 pages, final page 25 rows, truncated=False
filtered 217, read to end:   9 pages, final page 17 rows, truncated=False   <- exact match
unfiltered 223:              9 pages, final page 23 rows, truncated=False
```

A short read leaves a weak tell — a **full** final page beside `truncated: false`.
A filtered read ends on a **partial** page, which is the signature of reaching a
row set's natural end. The trace's `17` therefore **excludes** the short-read
model rather than merely disfavouring it, and A5 is strictly the harder bug: it
leaves no protocol-level trace at all.

**How a system produces this.** Every realistic mechanism puts a filter
*upstream* of pagination:

| Mechanism | Fits the observed cursors? |
|---|---|
| `INNER JOIN` where a `LEFT JOIN` was intended — rows whose identity resolution failed have no company record and are silently dropped | **yes** — most likely |
| A "resolved rows only" serving view (`WHERE company_id IS NOT NULL`) over a staging table that still holds all 223 | **yes** |
| Keyset pagination on a nullable column (`WHERE company_id > :cursor`) — SQL `NULL` comparisons are never true, so those rows are permanently unreachable | **no** — would emit company-id-shaped cursors, but the trace shows numeric offsets `"25"`, `"50"` |
| A partial index (`... WHERE company_id IS NOT NULL`) used to order the scan | agnostic |

The first two match the incident. The third is a genuine hazard but not an
explanation of *this* run.

**Why this is the worst version of the defect.** The loss is **not random — it is
correlated with difficulty.** The rows that vanished are precisely those whose
identity could not be resolved: the hardest cases, the ones most needing human
review. A system with this bug discards its own unresolved work and reports
success. The harder a row is, the more likely it disappears, and the cleaner the
run looks.

That also explains a detail of the customer's report. They found duplicates,
wrong-brand creative and ambiguous entries — every one visible *in what was
delivered*. They reported **no** missing companies, because absence is not
spot-checkable. Six companies never mentioned leave no trace in a sample of
twenty.

**Solution — the same as A3, for a different reason.** Reconcile the collected
row count against the upload's declared size. `223 ≠ 217` catches filtered and
short reads identically. What changes is **where to look** (upstream of
pagination, not at the paging service) and **what to test**.

**Test.** A `FilteringLoader` test double that drops rows **by predicate** rather
than by offset — no loader in `sources.py` models this. It belongs in `tests/`,
**not** in `sources.py`: that file documents shapes *"recorded during past
incidents"*, and adding a fabricated one misrepresents its provenance. TASK.md
sanctions the alternative directly — *"Your own checks may supply their own
implementation of that interface."*

**Expected:** `FilteringLoader` dropping every blank-identity row from list 1
serves 217 rows with `service_claimed_complete=True`; with the declared size
supplied, `verified_complete=false, reason="expected 223 rows, collected 217"`.
Without a declared size it is **indistinguishable from a correct read** — which
is the point.

---

## Group B — deciding what one company is

### B1. Per-page dedupe makes the count depend on page size — **P0**

**Current:**

```
LIST1: ps=10 → 214    ps=25 → 214    ps=100 → 211
LIST2: ps=10 → 103    ps=25 → 100    ps=100 →  98
```

The bug runs in **both directions**:

```
LIST1 ps=100: 209 + 5 surviving duplicates − 3 companies deleted = 211
LIST2 ps=100:  99 + 0 surviving duplicates − 1 company  deleted =  98
```

**Solution.** Delete `_collapse_page`. Collect all rows, then group once via
`identity.build_inventory`. Grouping cannot see page boundaries because it runs
after the read.

**Expected:** `209 / 209 / 209` and `99 / 99 / 99`.

---

### B2. `str(None)` / `""` folds unrelated companies into one — **P0**

**Problem.** `str(row["company_id"])` turns `None` into `"None"`. List 2 has the
same bug with `""`.

**Current:** list 1 — 6 companies collapse to 1, **up to 5 lost; 3 lost at
ps=100** (the blank rows sit at indices 12, 37, 61, 98, 149, 202, so only four
share page 0 — losing all 5 needs the whole list on one page, ps ≥ 203). List 2
— 2 collapse to 1, 1 lost at ps=100.

Rows — list 1: `row-2401`…`row-2406`. List 2: `srow-1114`, `srow-1115`.

**Solution.** `identity.identity_of` — blank identity is *absence*, never a
shared value. Predicate is falsy-or-blank after stripping, so `None` and `""`
behave identically.

**Expected:** list 1 **6 unidentified companies, each flagged**; list 2 **2**.

> **Policy this makes explicit.** `836 = 209 × 4` means unidentified companies
> each receive four deliverables — we ship personalized creative for companies we
> cannot identify. Chosen over quarantine-and-withhold because dropping them
> repeats the original defect (six companies silently receiving nothing). Stated
> here so it reads as decided, not defaulted. Reversing it gives
> **203 × 4 = 812** deliverables + 6 withheld.

---

### B4. Blank-identity rows merge when uploaded ids collide — **P0, NEW**

**Problem.** `identity_of` returns `f"unidentified:{row_label(row, index)}"`, and
`row_label` prefers the row's own `id`. Two blank-identity rows sharing an
uploaded `id` therefore collide.

**Reproduced:**

```
two distinct companies, both blank identity, same row id
keys: ['unidentified:dup-1', 'unidentified:dup-1']
companies produced: 1  -> BUG: MERGED
```

This directly contradicts `identity.py`'s own rule 2 — *"It is never merged with
any other row"* — and `paging.py` elsewhere states row ids are not guaranteed
unique. Not triggered by either fixture (all ids unique in both).

**Solution — two halves; revision 4 shipped only the first.**

1. **Identity key.** Key on the occurrence index, unique by construction:
   `f"unidentified:{index}:{row_label(row, index)}"`.
2. **Provenance.** The index must reach `Company.row_labels` too. Revision 4
   fixed only the key, leaving:

   ```
   key='unidentified:dup-1'   row_labels=('dup-1', 'dup-1')
   ```

   Two companies, but a deliverable still cannot say which row it came from.
   **This also makes C2's conservation law unverifiable** — "every row appears
   in exactly one company" cannot be asserted when two rows are
   indistinguishable. Provenance entries must carry the occurrence, e.g.
   `("dup-1#0", "dup-1#1")`, and the row's own id must remain readable
   alongside it.

Separately, report duplicate uploaded ids as their own discrepancy class.

**Expected:** the case above yields **2 companies with distinguishable
provenance**; both fixtures unchanged at 209 and 99 (0 duplicate ids in either,
so the suffix never appears in their output).

---

### B3. Identity policy not applied in the product path — **P0**

**Solution.** `build_campaign_plan` becomes `collect_rows` → `build_inventory` →
deliverables per company.

**Expected:** list 1 → 203 + 6 = **209**; list 2 → 97 + 2 = **99**. No hardcoded
counts.

---

## Group C — building deliverables

### C1. Deliverables keyed to rows, so duplicates get 4 assets each — **P0**

A company named twice gets 8 assets and is billed twice — *"a couple of companies
came back twice."* In the reconstructed `t-9f21` run this hit **6 companies**:
`sable-works`, `kestrel-dynamics`, `harbor-group`, `ironwood-logistics`,
`vantage-networks`, `tessellate-energy`.

**Current:** list 1 856 @ ps=25; list 2 400.

**Expected:** list 1 **836** = 209 × 4; list 2 **396** = 99 × 4. Assert
`deliverables == 4 × companies`, and that each company has **exactly one of each
of the four asset types** — not merely four assets.

---

### C2. No traceability from a deliverable back to its uploaded rows — **P1**

**Corrected framing.** This is not primarily an existing defect — it is one that
**B1/B3 would introduce** if plural provenance did not ship in the same change.

**Current** (starter, `source_row_ids` holds one row per company):

```
list1 ps=25   referenced=214 of 223 -> unreferenced=9
list1 ps=100  referenced=211 of 223 -> unreferenced=12
list2 ps=25   referenced=100 of 115 -> unreferenced=15
list2 ps=100  referenced= 98 of 115 -> unreferenced=17
```

Today **9** rows lose provenance on list 1. After correct grouping that becomes
**14** — unless `source_row_ids` goes plural in the same commit. Note the current
figures are page-size dependent (9 vs 12), which is B1 leaking into provenance.

**Solution.** Carry `source_row_ids` (plural) per deliverable, from
`Company.row_labels`. **Ship with step 1, not after it.**

**Expected:** every uploaded row appears in exactly one company — **223 of 223**
and **115 of 115**. Assert as a conservation law: no row invented, none dropped,
at every page size.

---

### C3. Row `saved_brand_kit_id` overrides the request — **P0, policy reversed**

**Problem.** `_make_deliverables` lets a row displace the requested Brand Kit
with no signal anywhere — *"some of the creative is not in the brand we picked."*

**Current:** list 1 — 36 deliverables in `brand-kit-2019-legacy` (9 rows × 4),
reported nowhere. Those 9 rows are **9 distinct companies**, so 36 survives
per-company grouping rather than shrinking.

**Reversed decision.** Revision 1 kept the override and merely disclosed it. That
was wrong. The customer's complaint is that *the creative is in the wrong brand*,
not that they were not told — a disclosed violation is still a violation, and a
run that knowingly ships against the explicit request must not report success.

**The request wins.** `brand_kit_id` and `template_id` from the request apply to
every deliverable unless the request itself authorises row-level overrides. The
override is not deleted — it is **recorded and reported** ("9 rows requested a
different kit; the request took precedence; review if intentional"), so the
mechanism survives for a customer who wants it, but it never silently beats an
explicit instruction.

Note the three remedies floated in review are not parallel: **once the request
wins there is no violation left to block or mark incomplete.** Blocking is only
needed if row-overrides-win is retained.

**Expected:**

| | Current | Expected |
|---|---:|---|
| List 1 deliverables in requested kit | 820 | **836 (all)** |
| List 1 deliverables in legacy kit | 36, silent | **0** |
| List 1 override rows reported | 0 | **9** (`row-1014`, `1082`, `1084`, `1123`, `1140`, `1163`, `1176`, `1195`, `1213`) |
| List 1 companies affected | — | **9** |
| List 2 exceptions block | absent | **present and empty** |

---

### C4. No rule for which domain personalizes a conflicted company — **P1, DECIDED**

**Problem.** Two companies carry two domains each. `company_id` settles that each
is **one company** — the count is 209 either way, and this is *not* part of the
209-vs-205 decision. But a landing page needs exactly one URL, so a choice
cannot be avoided; it can only be made well or badly.

```
company-kestrel-robotics   row-1066  Kestrel Robotics   logistics  kestrel-robotics.example
                           row-1216  Kestrel Robotics   logistics  kestrel-group.example

company-copperline-energy  row-1100  Copperline Energy  software   copperline-energy.example
                           row-1217  Copperline Energy  software   copperline-group.example
```

Same id, same name, same segment in both pairs — **only the domain differs.**

**The two cases are not equivalent, and the difference is mechanical:**

```
kestrel-robotics.example    claimed by ['company-kestrel-robotics']
kestrel-group.example       claimed by ['company-kestrel-robotics']      <- sole owner

copperline-energy.example   claimed by ['company-copperline-energy']
copperline-group.example    claimed by ['company-copperline-energy',
                                         'company-copperline-group']     <- two owners
```

Both of Kestrel's candidates are **its own** domains. Picking wrong points the
landing page at another page of the same company's web presence — untidy, not
harmful. Copperline's second domain is **another company's primary domain**.
Picking wrong there ships Copperline Group's website on Copperline Energy's
landing page — the wrong company entirely.

**Policy — corrected. Revision 3's rule 1 was a disqualification and broke 7
companies.** Written as *"disqualify any domain claimed by more than one
`company_id`"*, it stripped the **only** domain from every company on a shared
domain — while rule 4 said never block, leaving the policy self-contradictory on
real data:

```
applying the old rule 1 to every identified company:
  zero candidates : 7
      company-northwind-energy         domains=['northwind-energy.example']
      company-northwind-energy-emea    domains=['northwind-energy.example']
      company-sable-fitness            domains=['sable-fitness.example']
      company-sable-fitness-emea       domains=['sable-fitness.example']
      company-tessellate-capital       domains=['tessellate-capital.example']
      company-tessellate-capital-emea  domains=['tessellate-capital.example']
      company-copperline-group         domains=['copperline-group.example']
  one candidate   : 195
  several         : 1  ['company-kestrel-robotics']
```

Those seven include **both sides of every EMEA pair** — the companies kept
separate precisely *because* they legitimately share a web presence. A shared
domain must be **less preferred**, never disqualified.

**Corrected policy, applied in order:**

1. **Prefer domains owned solely by this `company_id`.**
2. **Exactly one such → use it, no flag.** The conflict resolved itself.
3. **Several such → first occurrence in service order, and flag.**
   First-occurrence is deterministic and page-size independent because collected
   row order is service order.
4. **None such → use the shared domain, and flag.** It is the only address on
   file; withholding it would delete a company for a data-quality problem.
5. **Never block.** Every company gets an address; conflicts are notes.

**Applied to the fixtures:**

| Rule | Companies | Outcome |
|---|---:|---|
| 2 — one sole-owned domain | **195** | resolved silently |
| 3 — several sole-owned (`kestrel-robotics`) | **1** | `kestrel-robotics.example` (`row-1066`), flagged |
| 4 — none sole-owned (3 EMEA pairs + `copperline-group`) | **7** | shared domain used, flagged |
| — | **203 identified** + 6 unidentified = **209** | every company has a domain |

`company-copperline-energy` falls under rule 2: it holds
`copperline-energy.example` (sole-owned) alongside the shared
`copperline-group.example`, so the preference resolves it silently — the outcome
revision 3 wanted, now reached without stripping anyone.

**Expected:** list 1 **836 deliverables, 0 blocked, 8 companies carrying a domain
note** (1 from rule 3, 7 from rule 4 — the latter already appear in E1's
contested-identity report, so they are not new problems). List 2 **396, 0
blocked, 0 flagged**.

**Why not simply ignore domain conflicts.** "Same id, same name, same segment —
so it doesn't matter" is correct for the Kestrel pair, but it is *not* a safe
general rule: the dangerous version of this defect matches on all three of those
fields too. Copperline is the proof — identical name and segment, and still the
wrong company's URL. **Rule 1 is what separates them**, so the guard stays even
though it fires on only one row pair here.

Two things a reviewer may push on, both deliberate: whether the multi-claim
disqualifier is a principled rule or a convenient one, and whether
first-occurrence is defensible given this plan criticises ordering accidents
elsewhere. The answer to the second is that it applies only *after* rule 1 has
removed every case where the choice could ship another company's asset — what
remains is a choice among a company's own domains, where order is a tiebreak
rather than a correctness decision.

---

## Group D — the check

### D1. The check never reconciles the plan against the upload — **P1**

**Problem.** `evaluate_campaign_coverage` asks only whether rows *already in the
plan* have 4 assets. **A plan containing one row passes.**

**Current:** returns `True` on both lists, and returned `True` on the historical
run that shipped 6 duplicates and dropped 6 companies.

**Solution — the full completion contract.** Revision 1 listed four conditions;
that was too loose. A run is complete only if **all** of these hold, each failing
separately with its own message:

1. **Coverage** — every company derived from the upload has deliverables.
2. **Asset exclusivity** — exactly one of each of the four required asset types
   per company. Not "four assets" — four *landing pages* must fail.
3. **No orphans or extras** — every deliverable maps to a company in the
   inventory; no deliverable exists for a company that is not there.
4. **No duplicates** — no repeated `(company, asset_type)` pair.
5. **Correct attribution** — each deliverable's company and rows match the
   inventory entry it claims.
6. **Traceability** — every uploaded row appears in exactly one company's
   provenance; none invented, none dropped.
7. **Request conformity** — every deliverable carries the requested brand kit and
   template. **Unconditional.** Revision 2 allowed "…or appears in the declared
   exceptions block," which made sense only while C3 preserved row overrides.
   Revision 3 made the request win, so a non-conforming deliverable is a failure
   with no escape hatch — **a reported violation is still a violation.**
8. **Exceptions block accuracy** — the block lists exactly the rows whose saved
   values were overridden by the request, no more and no fewer. It is a record
   of what was suppressed, never a licence to ship a different kit.
9. **Determinism** — page size does not change the answer.
10. **Honesty** — the read completed, or the result says it did not and why.

**Expected:** passes on both lists with a stated basis — e.g. `209 companies from
223 rows, 836 deliverables, 0 exceptions, read complete (verified against
declared size 223)` — and fails when any single condition breaks.

---

### D2. Completion is a hardcoded boolean — **P1**

**Problem.** `repair_lab.py:124` sets `"complete": True` unconditionally. And a
boolean cannot carry the qualification A3 requires: any downstream caller reading
`complete=True (unverified)` sees only `True`.

**Solution.** Replace the boolean with structured fields:

```
service_claimed_complete : bool          # what the loader reported
verified_complete        : true | false | unknown
completion_reason        : str
```

`unknown` is the honest state when no expected row count was supplied. The
headline must never print a bare "complete."

**Expected:**

| Loader (list 1, ps=25) | claimed | verified | reason |
|---|---|---|---|
| `TargetAccountTool` | True | **true** | 223 rows, matches declared size |
| `ReplayingLoader` | True | **true** | 223 rows after replay removal |
| `StallingLoader` | False | **false** | cursor stopped advancing at `'50'` |
| `CyclingLoader` | False | **false** | cursor stopped advancing at `'50'` |
| `TruncatedWithoutCursorLoader` | False | **false** | more rows claimed, no cursor |
| `SilentlyShortLoader` | True | **false** | expected 223, service ended after 125 |
| `SilentlyShortLoader` *(no count given)* | True | **unknown** | completion unverified |

---

### D3. The check echoes the plan's own claim — **P1**

The check reads `plan["complete"]` — the plan grading itself. This is why
`t-9f21` shows `passed: true` beside a wrong answer, and why **a matching number
is not evidence**:

```
claimed 209 = 203 companies served once + 6 surviving duplicate rows
  true  209 = 203 companies served once + 6 companies never served
```

Six extra shipments and six missing companies cancelled exactly.

> **Status of that reconstruction — restated after testing it.** Revision 2
> claimed "three-way numeric corroboration." That was wrong on both counts, and
> the check that showed it is 15 lines:
>
> ```
> 836 = 209 x 4                -> derived from 209, not independent evidence
> last page 17 -> 217 rows     -> 217 mod 25 = 17; ANY 217-row set gives 17
> random 6-row drops           -> 1418/3000 produce 209  (47.3%)
> outcomes: 209:1418  208:919  210:566  211:88  212:9
> ```
>
> **209 is the single most likely outcome of dropping *any* 6 rows**, so the
> numeric match is near-worthless evidence for *which* six. What survives:
>
> | Claim | Support | Strength |
> |---|---|---|
> | The log is elided (3 of 9 pages recorded) | 67 rows cannot yield 209 companies | **entailed** |
> | The service served **217** rows | last page = 17 at ps=25 | **strong** |
> | The six missing were the blank-`company_id` rows | id-block structure + README's independent "217" | **moderate, structural — not numeric** |
> | The read was **filtered**, not **truncated** | final page 17 (partial) excludes the short-read shape — see **A5** | **strong** |
>
> The alternative that cannot be excluded: the six rows were added to the fixture
> *after* the run. That requires a re-export interleaving them rather than
> appending, but the evidence here does not rule it out. **Both readings are
> indistinguishable to any reader that does not reconcile against the upload** —
> which is the actual point.
>
> Nothing downstream changes: the fix is to reconcile against what you were asked
> to load either way. But the write-up must not lean on the 209 match, and
> `context.md`'s "confirmed reconstruction, not a guess" needs the same
> correction.

**Solution.** The check recomputes from the upload through the loader interface
and never reads a self-reported field.

**Expected:** agreement between check and plan becomes meaningful. **Test
directly:** hand the check a plan whose `complete` is `True` but which is missing
a company, and require failure.

---

## Group E — the report

### E1. Contested records are not surfaced — P2

| Report line | List 1 | List 2 |
|---|---:|---:|
| logical companies | 209 | 99 |
| unidentified companies | 6 | 2 |
| companies named more than once | 13 | 15 |
| extra rows absorbed | 14 | 16 |
| contested identity relationships | 4 (8 IDs) | **0** |
| one identity, several domains | 2 | **0** |
| rows overriding the request | 9 | **0** |
| rows a human must review | 47 | 33 |

**This table is the answer to "why the two lists do not produce the same shape of
answer."** List 1 needs a contested section; list 2's is legitimately empty.

---

### E2. No guard for conflicting attributes within one identity — **P1**

Raised from P2: a conflicting personalization domain produces **incorrect
creative**, not merely an incomplete report — the same severity as C4, which it
feeds.

**Current,** measured across all 28 duplicate groups:

```
segment conflicts : 0 of 13 (list 1), 0 of 15 (list 2)
domain  conflicts : 2 of 13 (list 1), 0 of 15 (list 2)
name    variants  : cosmetic only (Inc suffix, ALL-CAPS)
```

**Solution.** Generalise the domain check to any attribute, reporting per-field
disagreement within one identity.

**Expected:** list 1 **2 conflicts**, list 2 **0**. Segment reports zero on both
— and that is the point: **a guard silent on both fixtures cannot have been
fitted to them.** Log it as deliberately empty so silence is not read as omission.

---

## Group F — harness

### F1. `demo.py` reports rows, not companies — P2

Report companies, deliverables, structured completion, exceptions, and the
contested summary across all three page sizes.

### F2. `tests/test_visible.py` asserts the broken check passes — **P1**

The visible test asserts `evaluate_campaign_coverage` returns `True` on the
starter plan. **It will fail once D1 lands, correctly.** Replace it; do not
weaken the check to keep it green.

**Tests to add** — all written against the interface, no hardcoded counts, no
fixture special-casing:

*Invariants*
1. Page-size invariance — same company count at ps 1, 7, 10, 25, 100, 1000.
2. Blank identity never merges — parameterised over `None`, `""`, `"  "`.
3. Shared domain never merges — two IDs on one domain stay two companies.
4. Conservation — every uploaded row in exactly one company.
5. Deliverable arity — exactly one of each of the four asset types.

*Paging*
6. All five shapes × both lists = 10 cases; assert the **reason**, not just the
   boolean.
7. **Two legitimate pages with identical content** — no rows lost (guards **A4**).
8. Short read with `expected_row_count` supplied → `verified_complete: false`
   (guards **A3**).
8a. **`FilteringLoader`** — a test double dropping rows **by predicate**, not by
    offset. Serves a protocol-perfect read of an incomplete set: clean cursor
    chain, partial final page, `truncated=False`. With a declared size →
    `verified_complete: false`; without one → **indistinguishable from a correct
    read**, asserted explicitly so the limit is recorded rather than assumed
    (guards **A5**). Lives in `tests/`, not `sources.py`.

*Adversarial — the check must reject a doctored plan*
9. A company missing from an otherwise valid plan.
10. A company with doubled deliverables.
11. An orphan deliverable for a company not in the inventory.
12. A deliverable attributed to the wrong company.
13. A deliverable carrying a brand kit the request did not authorise.
14. **Two blank-identity rows sharing an uploaded id** → 2 companies (guards
    **B4**); duplicate ids reported.

*Domain selection (guards **C4**)*
15. A company holding one sole-owned and one shared domain **prefers the
    sole-owned one** — synthetic, so it does not depend on Copperline.
16. A company with **two sole-owned domains** ships 4 deliverables, uses the
    first occurrence, is **flagged not blocked**, and picks the same domain at
    every page size.
17. **Zero sole-owned domains** — a company whose only domain is shared still
    ships 4 deliverables using that domain, flagged. **Assert no company anywhere
    ends with an empty domain**, which is the invariant revision 3 violated for 7
    companies.

*Request conformity (guards **D1.7**)*
18. **No deliverable carries a non-requested brand kit or template**, even when
    its source row named one and the exceptions block reports it.

**Expected:** `make test` green on tests that fail if any fix regresses. Test
count 1 → roughly 19–21.

---

## Order of work

1. **A4 + B4** — fix the two reproduced bugs **before wiring anything in**.
   Shipping A4 as-is would introduce silent data loss.
2. **B1 + B2 + B3 + A1 + A2 + C2** — one step. Grouping after the full read
   *requires* the full read, so identity and paging land together, and plural
   provenance must ship with them or C2 regresses from 9 rows to 14.
   *Moves 214/214/211 → 209/209/209 and 103/100/98 → 99/99/99.*
3. **C1 + C4** — deliverables per company; apply the conflicted-domain policy.
   *856 → 836, 400 → 396. Nothing blocked; 8 companies carry a domain note on
   list 1.*
4. **C3** — request wins; overrides recorded as exceptions. *36 → 0 legacy.*
5. **D1 + D2 + D3** — full completion contract, structured completion,
   independent reconciliation.
6. **F2** — replace the visible test with the 14 above.
7. **E1 + E2 + F1** — report and demo output.
8. **A3** — wire `expected_row_count` through `demo.py`; document the residual.

Steps 1–3 change the customer's answer. Steps 5–6 make it provable.

---

## Cause vs symptom

| Fix | Removes a cause | Hides a symptom |
|---|---|---|
| B1 — group after the full read | ✔ | |
| B2 — blank identity never merges | ✔ | |
| B4 — occurrence-keyed blank identity | ✔ | |
| A1/A2 — defensive paging | ✔ | |
| A4 — cursor-aware replay detection | ✔ | |
| C1 — deliverables per company | ✔ | |
| C2 — plural provenance | ✔ | |
| C3 — request wins | ✔ | |
| D1/D2/D3 — independent reconciliation | ✔ | |
| A3 — reconcile against declared size | ✔ (where a count exists) | |
| A5 — reconcile against declared size | ✔ (where a count exists) — the *only* defence; nothing in the protocol reveals it | |
| C4 — disqualify multi-claimed domains | ✔ | |

Nothing here is a symptom-hider. C3 changed category in this revision: disclosing
the override removed only the *silence*; making the request win removes the
cause.

---

## Out of scope, and why

- **`t-4c08`** — `image_search` timeout marked `retryable: true`, plus a 310ms
  template-cache cold start. Neither matches any line of the customer's report.
- **The README's "217"** — accurate for the `row-1xxx` block, misleading as a
  total. Leaving it is the clearest artifact of the anchoring problem.
- **Resolving the 4 contested relationships** — a customer decision. We report
  209 and flag. Merging gives 205.
- **The segment taxonomy** (`financial services` vs `real_estate`) — real
  inconsistency, no tie to the complaint.

---

## Known limits after all fixes land

1. **A3's and A5's residual** — a caller with no declared upload size still
   cannot verify completion. For **A5 this is the whole defence**: a filtered read
   leaves no protocol-level trace, so without a declared count it is not merely
   hard to detect, it is *indistinguishable from success*. **`make verify` cannot
   exercise A3 at all**: `SilentlyShortLoader` never truncates on list 2's 115
   rows.
2. **List 2 cannot validate the identity policy.** It returns 99 whether we
   report 209-and-flag or merge-to-205. It proves we did not hardcode; it does
   not prove the rule is right.
3. **Blank-identity fallback is untested by the data.** Current policy gives each
   blank row its own company. Domain-fallback would merge blank rows sharing a
   domain — no two do in either fixture, so both rules agree and the choice is
   unexercised.
4. **A4 and B4 were found by inspection, not by any test** — and neither fixture
   triggers them. Both are guarded by synthetic tests (7 and 14). There is no
   reason to think inspection found the last such case.
5. **C4's multi-claim disqualifier fires on exactly one row pair here.** It
   resolves `company-copperline-energy` and never triggers on list 2. Its value
   is that it separates a harmless conflict from one that would ship another
   company's URL — but with a single live example, it is a rule argued from
   principle, not one demonstrated across varied data.
6. **First-occurrence domain selection assumes service order is meaningful.**
   It is deterministic and page-size independent, but if a service returned rows
   in an arbitrary order the tiebreak would be arbitrary too. Acceptable only
   because rule 1 has already removed every case where the choice could be
   harmful.
5. **Two hand-built fixtures are a weak held-out set.** The stronger
   generalisation argument is `sources.py`: a check surviving all five paging
   pathologies holds for reasons unrelated to either file.
