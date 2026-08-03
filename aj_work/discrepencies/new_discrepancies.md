# Discrepancies in the two uploaded lists

Two parts, in this order:

- **Part 1** — what I found by inspecting the data and the surrounding files. Some
  of it I later encoded into the scanner; some of it cannot be encoded because it
  is an inference about provenance rather than a property of a row.
- **Part 2** — the verbatim output of `aj_work/discrepancies.py` for both lists.

Where Part 1 says *now automated*, the scanner emits it because I added the check
after finding the thing by hand. Where it says *not automated*, the scanner has
nothing to say and the judgement is mine.

---

## Part 1 — Found by inspection

### 1. The README's "217 rows" is not stale. It is the original upload. *(not automated)*

`README.md` says the list is 217 rows. The file holds 223. Row ids fall into
exactly two contiguous blocks:

```
1001-1217   217 rows
2401-2406     6 rows
```

The second block is *precisely* the six rows with `company_id: null`. So this
upload is two batches, and the six rows the README does not know about are the
batch whose identity resolution failed.

This matters for the count. It is evidence that the six blank-id rows are six
real companies that arrived without ids, not one company or corrupt data. A
reader who assumes the README is simply out of date loses that.

The block detection is automated; reading it against the README is not.

### 2. List 1's contamination sits in one contiguous sub-range. *(not automated)*

Inside block 1, the trouble is not scattered:

| id range | rows | what they are |
|---|---|---|
| `1001-1200` | 200 | internally unique company IDs and domains; 8 request overrides |
| `1201-1212` | 12 | duplicate re-imports (`Inc` / ALL-CAPS name variants) |
| `1213-1215` | 3 | `-emea` subsidiaries carrying the parent's domain |
| `1216-1217` | 2 | duplicates carrying a *different* domain |
| `2401-2406` | 6 | unresolved identity |

200 + 12 + 3 + 2 + 6 = 223. Every row that makes **the count** arguable lives
above `row-1200`.

That is a claim about the count only. The `1001-1200` block is **internally**
unique — 200 rows, 200 distinct company IDs, 200 distinct domains, no blanks —
but "internally" is doing real work in that sentence, and two things qualify it:

- **Later rows introduce duplicates and conflicts that reach back into this
  range.** 14 of the 200 share a domain with a row above `row-1200`, including
  `row-1020`, `row-1047`, `row-1076` and `row-1093`, which become one side of the
  four contested identity relationships. The block is clean read alone, not clean
  read against the rest of the file.
- **It contains 8 of the 9 request overrides** (`row-1014`, `row-1082`,
  `row-1084`, `row-1123`, `row-1140`, `row-1163`, `row-1176`, `row-1195`); only
  `row-1213` sits above the boundary. These do not change how many companies
  there are, which is why they leave the block story intact — but they are the
  direct cause of the customer's "creative is not in the brand we picked."

So the base upload is internally consistent on identity, not defect-free.

### 3. The starter is wrong in *both* directions, not just "duplicates survive". *(not automated)*

I had assumed per-page dedup only ever over-counts. It does not. On list 2:

```
page_size=10    103 rows   (+4 over the true 99)
page_size=25    100 rows   (+1)
page_size=100    98 rows   (-1)   <-- below the true count
```

At `page_size=100` the two blank-id rows land on the same page and merge, so a
real company is **deleted**. Same code, same file, over-counts at one page size
and under-counts at another.

### 4. `company-copperline-energy` is contested twice over. *(partly automated)*

The scanner flags it under two separate classes, but not the interaction:

- it carries two domains — `copperline-energy.example` and `copperline-group.example`
- its second domain is *also* `company-copperline-group`'s own domain

So either `row-1217` is mislabelled, or these are one customer under two ids. The
upload cannot settle it. This is the sharpest instance of the customer's "entries
I cannot tell apart well enough to say whether they are one customer or two."

### 5. The `-emea` rows are the trap that punishes a domain-based fix. *(now automated, class 4)*

`northwind-energy`, `sable-fitness` and `tessellate-capital` each appear twice:
once as themselves, once as `-emea`, sharing the parent's domain. Any fix that
treats domain as identity silently deletes three real accounts.

`make verify` will not catch this: list 2 has zero domain collisions. A
domain-keyed fix passes `verify` and is wrong on the customer's actual list.

### 6. List 2's identical triple was written by different code. *(now automated, classes 3 and 6)*

`srow-1111/1112/1113` are the only rows in either file whose JSON keys are
ordered `company_id … id` instead of `id … company_id`, and they are also the
only byte-identical rows (ignoring `id`) in either file. Different serializer,
same insertion event.

### 7. The two files are independent uploads. *(not automated)*

Zero shared row ids, zero shared `company_id`, zero shared domains. There is no
cross-list identity question, so nothing needs to dedup across uploads.

### 8. The reader cannot detect a short read that claims success. *(not automated — a gap, not a finding)*

Of the five paging shapes in `src/sources.py`, `src/paging.py` now handles four
honestly. `SilentlyShortLoader` still gets through: it returns 125 of 223 rows
with `truncated=False`, and the audit reports **116 companies** with no warning.

From inside the loader interface a short read that declares success is
indistinguishable from a real ending. Detecting it needs an independent expected
row count from the upload record. Until that exists, the number is unguarded.

### 9. Two things I checked and rejected

- **`Kestrel 2` vs `company-kestrel2`** — my first name-vs-id check flagged 83
  rows in list 2. It was my own slug heuristic mishandling the space before a
  digit, not a defect. Dropped.
- **`t-4c08` in the traces** — `image_search` timeout and a template-cache cold
  start. Neither matches any line in the customer's report. Left alone, per
  TASK.md's "don't repair behavior you can't tie to the customer's complaint."

I also had to fix a bug in my own scanner: the first "out of file order" check
compared each row against a running maximum and reported 205 rows. The corrected
adjacent-pair check reports 17.

### 10. Why the two lists do not produce the same shape of answer

List 1's mess is **appended** — a re-import batch plus an unresolved batch,
carrying genuine identity conflicts and 9 rows that override the request. Its
answer cannot be a bare integer: it is *209, of which 6 unidentified and 5
contested*.

Stated precisely: **four contested identity relationships, involving eight
company IDs, drive the 209-versus-205 decision.** Each relationship is one domain
carrying two company IDs, and both IDs in a pair are contested — the upload does
not establish either as canonical, so the count falls by 4 whichever side a merge
absorbs. Four records would be absorbed under the most likely reading: the three
`-emea` records added at `row-1213`–`row-1215`, plus `company-copperline-energy`.
`company-kestrel-robotics` additionally needs domain resolution without affecting
the count.

Note the fourth relationship works differently from the other three. The `-emea`
records are later-added companies. `company-copperline-energy` is not: it is a
base-block company at `row-1100`, pulled onto another company's domain by the
later `row-1217`. A later row, not a later company.

That is why 4, 8 and 5 all appear, and they are not in conflict — 4
relationships, 8 IDs involved, 5 companies needing a human. Definitions and the
full table are in `step1_discrepancies.md`, "Canonical wording for the contested
records."

List 2's mess is **inline** — no separate batches, no domain conflicts, no
overrides. Its only exotic case is three byte-identical rows. Its answer is a
clean **99**.

---

## Part 2 — Found by the scanner

Verbatim output of `aj_work/discrepancies.py`. Regenerate with `make discrepancies`.

### List 1 — `fixtures/target_accounts.json`

```
list                : fixtures/target_accounts.json
rows read           : 223  (complete=True)
logical companies   : 209
discrepancy classes : 12 populated, 54 findings

-- blank identity (6) --
   row-2401     Halverson Freight          halverson-freight.example  (company_id=None)
   row-2402     Pell & Sons Ironworks      pellsons.example  (company_id=None)
   row-2403     Cobalt Ridge Dental        cobaltridge.example  (company_id=None)
   row-2404     Northgate Tutoring         northgate-tutoring.example  (company_id=None)
   row-2405     Riverbend Cold Storage     riverbend-cold.example  (company_id=None)
   row-2406     Aster Point Realty         asterpoint.example  (company_id=None)

-- repeated identity (13) --
   company-alder-health             2 rows  row-1017, row-1201   Alder Health | ALDER HEALTH
   company-bright-foods             2 rows  row-1095, row-1207   Bright Foods | BRIGHT FOODS
   company-copperline-energy        2 rows  row-1100, row-1217   Copperline Energy
   company-copperline-group         2 rows  row-1093, row-1206   Copperline Group | Copperline Group Inc
   company-harbor-group             2 rows  row-1107, row-1209   Harbor Group | Harbor Group Inc
   company-ironwood-logistics       2 rows  row-1117, row-1210   Ironwood Logistics | IRONWOOD LOGISTICS
   company-ironwood-partners        2 rows  row-1029, row-1202   Ironwood Partners | Ironwood Partners Inc
   company-kestrel-dynamics         2 rows  row-1097, row-1208   Kestrel Dynamics | Kestrel Dynamics Inc
   company-kestrel-robotics         2 rows  row-1066, row-1216   Kestrel Robotics
   company-sable-works              3 rows  row-1092, row-1204, row-1205   Sable Works | SABLE WORKS | SABLE WORKS Inc
   company-tessellate-energy        2 rows  row-1167, row-1212   Tessellate Energy | Tessellate Energy Inc
   company-vantage-capital          2 rows  row-1042, row-1203   Vantage Capital | Vantage Capital Inc
   company-vantage-networks         2 rows  row-1127, row-1211   Vantage Networks | Vantage Networks Inc

-- one identity, several domains (2) --
   company-kestrel-robotics         kestrel-robotics.example, kestrel-group.example   rows row-1066, row-1216
   company-copperline-energy        copperline-energy.example, copperline-group.example   rows row-1100, row-1217

-- one domain, several identities (4) --
   copperline-group.example         company-copperline-energy, company-copperline-group
   northwind-energy.example         company-northwind-energy, company-northwind-energy-emea
   sable-fitness.example            company-sable-fitness, company-sable-fitness-emea
   tessellate-capital.example       company-tessellate-capital, company-tessellate-capital-emea

-- row overrides the request (9) --
   row-1014     Kestrel Supply             saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1213     Northwind Energy EMEA      saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1082     Halcyon Group              saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1084     Marrow Media               saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1123     Foundry Partners           saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1140     Cedar Partners             saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1163     Pinnacle Systems           saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1176     Cedar Labs                 saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast
   row-1195     Sable Dynamics             saved_brand_kit_id=brand-kit-2019-legacy, saved_template_id=template-legacy-blast

-- conflicting fields within one identity (2) --
   company-kestrel-robotics         domain: ['kestrel-group.example', 'kestrel-robotics.example']   rows row-1066, row-1216
   company-copperline-energy        domain: ['copperline-energy.example', 'copperline-group.example']   rows row-1100, row-1217

-- name differs only by case or suffix (11) --
   company-alder-health             Alder Health | ALDER HEALTH
   company-ironwood-partners        Ironwood Partners | Ironwood Partners Inc
   company-vantage-capital          Vantage Capital | Vantage Capital Inc
   company-sable-works              Sable Works | SABLE WORKS | SABLE WORKS Inc
   company-copperline-group         Copperline Group | Copperline Group Inc
   company-bright-foods             Bright Foods | BRIGHT FOODS
   company-kestrel-dynamics         Kestrel Dynamics | Kestrel Dynamics Inc
   company-harbor-group             Harbor Group | Harbor Group Inc
   company-ironwood-logistics       Ironwood Logistics | IRONWOOD LOGISTICS
   company-vantage-networks         Vantage Networks | Vantage Networks Inc
   company-tessellate-energy        Tessellate Energy | Tessellate Energy Inc

-- row id blocks (import batches) (2) --
   1001-1217  (217 rows)
   2401-2406  (6 rows)

-- rows written out of id order (1) --
   17 rows: row-2401, row-1201, row-1213, row-1202, row-2402, row-1203, row-1214, row-2403, row-1216, row-1215, row-2404, row-1205, row-1206, row-1207, row-1217, row-2405, row-2406

-- rows carry different fields (2) --
   214x  ['company_id', 'company_name', 'domain', 'id', 'segment']
   9x  ['company_id', 'company_name', 'domain', 'id', 'saved_brand_kit_id', 'saved_template_id', 'segment']

-- mixed segment taxonomy (1) --
   space-separated ['financial services'] alongside underscore ['real_estate']

-- value hygiene (1) --
   ALL-CAPS company_name on 4 rows: row-1201, row-1204, row-1207, row-1210

-- nothing found (2) --
   rows identical except id
   same fields, different key order
```

### List 2 — `fixtures/second_list.json`

```
list                : fixtures/second_list.json
rows read           : 115  (complete=True)
logical companies   : 99
discrepancy classes : 6 populated, 35 findings

-- blank identity (2) --
   srow-1114    Unresolved Import A        unresolved-a.example  (company_id='')
   srow-1115    Unresolved Import B        unresolved-b.example  (company_id='')

-- repeated identity (15) --
   company-ambit4                   2 rows  srow-1084, srow-1085   Ambit 4 | Ambit 4 Inc
   company-bramble                  2 rows  srow-1020, srow-1021   Bramble | Bramble Inc
   company-cinder3                  2 rows  srow-1076, srow-1077   Cinder 3 | Cinder 3 Inc
   company-fennel2                  2 rows  srow-1052, srow-1053   Fennel 2 | Fennel 2 Inc
   company-garnet4                  2 rows  srow-1108, srow-1109   Garnet 4 | Garnet 4 Inc
   company-kestrel2                 2 rows  srow-1028, srow-1029   Kestrel 2 | Kestrel 2 Inc
   company-pinnacle2                2 rows  srow-1036, srow-1037   Pinnacle 2 | Pinnacle 2 Inc
   company-quill4                   2 rows  srow-1092, srow-1093   Quill 4 | Quill 4 Inc
   company-sable                    2 rows  srow-1012, srow-1013   Sable | Sable Inc
   company-straddle-works           3 rows  srow-1111, srow-1112, srow-1113   Straddle Works
   company-talbot3                  2 rows  srow-1060, srow-1061   Talbot 3 | Talbot 3 Inc
   company-thistle3                 2 rows  srow-1068, srow-1069   Thistle 3 | Thistle 3 Inc
   company-windrow                  2 rows  srow-1004, srow-1005   Windrow | Windrow Inc
   company-wrenfield2               2 rows  srow-1044, srow-1045   Wrenfield 2 | Wrenfield 2 Inc
   company-yarrow4                  2 rows  srow-1100, srow-1101   Yarrow 4 | Yarrow 4 Inc

-- rows identical except id (1) --
   srow-1111, srow-1112, srow-1113   Straddle Works

-- name differs only by case or suffix (14) --
   company-windrow                  Windrow | Windrow Inc
   company-sable                    Sable | Sable Inc
   company-bramble                  Bramble | Bramble Inc
   company-kestrel2                 Kestrel 2 | Kestrel 2 Inc
   company-pinnacle2                Pinnacle 2 | Pinnacle 2 Inc
   company-wrenfield2               Wrenfield 2 | Wrenfield 2 Inc
   company-fennel2                  Fennel 2 | Fennel 2 Inc
   company-talbot3                  Talbot 3 | Talbot 3 Inc
   company-thistle3                 Thistle 3 | Thistle 3 Inc
   company-cinder3                  Cinder 3 | Cinder 3 Inc
   company-ambit4                   Ambit 4 | Ambit 4 Inc
   company-quill4                   Quill 4 | Quill 4 Inc
   company-yarrow4                  Yarrow 4 | Yarrow 4 Inc
   company-garnet4                  Garnet 4 | Garnet 4 Inc

-- rows written out of id order (1) --
   4 rows: srow-1112, srow-1113, srow-1114, srow-1115

-- same fields, different key order (2) --
   112x  ['id', 'company_id', 'company_name', 'domain', 'segment']
   3x  ['company_id', 'company_name', 'domain', 'segment', 'id']

-- nothing found (8) --
   one identity, several domains
   one domain, several identities
   row overrides the request
   conflicting fields within one identity
   row id blocks (import batches)
   rows carry different fields
   mixed segment taxonomy
   value hygiene
```
