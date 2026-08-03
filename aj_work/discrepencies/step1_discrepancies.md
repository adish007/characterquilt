# Step 1 data discrepancies

This is a direct inventory of the discrepancies in
`fixtures/target_accounts.json` and `fixtures/second_list.json`. The row IDs
below are the uploaded row IDs, not generated company IDs.

## Counting rule used for the notes

- A nonblank `company_id` is treated as the strongest available identity key.
- Repeated rows with the same nonblank `company_id` are grouped together, but
  every contributing row must remain traceable.
- A row with a blank `company_id` is **not** grouped with other blank rows. A
  blank value is missing identity information, not a shared identity.
- A shared domain is recorded as a conflict, not used automatically to merge
  two different nonblank company IDs.
- If one company ID has two domains, the company count can remain one only if
  company ID is declared authoritative. The conflicting domain still needs to
  be surfaced because it is not safe to silently choose personalization data.

Under that rule, list 1 has 209 logical company records and list 2 has 99.
Those counts are policy-dependent conclusions, not facts contained explicitly
in the JSON.

### Canonical wording for the contested records

Two different numbers describe the contested rows in list 1, and they answer
different questions. These are the agreed terms; use them verbatim in
`new_discrepancies.md`, `context.md` and `DECISIONS.md` so 4 and 5 never read as
a contradiction.

**4 contested identity relationships, involving 8 company IDs** — these drive the
209-versus-205 decision. Each is one domain carrying two nonblank company IDs.
Both IDs in a pair are contested; neither is established as the canonical one by
anything in the upload:

| Domain | Company ID A | Company ID B |
|---|---|---|
| `northwind-energy.example` | `company-northwind-energy` (`row-1020`) | `company-northwind-energy-emea` (`row-1213`) |
| `sable-fitness.example` | `company-sable-fitness` (`row-1047`) | `company-sable-fitness-emea` (`row-1214`) |
| `tessellate-capital.example` | `company-tessellate-capital` (`row-1076`) | `company-tessellate-capital-emea` (`row-1215`) |
| `copperline-group.example` | `company-copperline-group` (`row-1093`, `row-1206`) | `company-copperline-energy` (`row-1100`, `row-1217`) |

Merging all four relationships gives 205. Not merging gives 209. **The count
drops by 4 regardless of which side of each pair survives** — which side is
absorbed is a policy choice, not a fact in the data. Earlier drafts of this note
listed only the `-emea`/Energy side as "at risk," which silently assumed the
other side was canonical. That assumption is not supported by the upload.

Row order is the only asymmetry available, and it does not point the same way in
all four cases:

- Three of the four contested relationships were created by a **later-added
  record**: `company-northwind-energy-emea`, `company-sable-fitness-emea` and
  `company-tessellate-capital-emea` exist only at `row-1213`–`row-1215`.
- The fourth is different. `company-copperline-energy` is a **base-block
  company** at `row-1100` with its own domain. A later row, `row-1217`, places
  that same company ID on `copperline-group.example`. Here a later *row* pulls a
  pre-existing *company* into the conflict — not a later company appearing.

**5 contested companies** — the records a human must review before the campaign
is trusted. Four of the eight IDs above are the ones a merge would absorb under
the most likely reading (the three `-emea` records plus `company-copperline-energy`),
and in addition:

| Company | Why contested | Changes the count? |
|---|---|---|
| `company-kestrel-robotics` | one ID, two domains (`kestrel-robotics.example`, `kestrel-group.example`) | **no** |

`company-kestrel-robotics` stays one company under our rule, so it never moves
the total — but which domain personalizes its creative is unresolved, and
picking the first row encountered makes that an ordering accident. It is a
correctness problem in the output, not a counting problem.

`company-copperline-energy` appears in both classes: it carries two domains
*and* one of those domains belongs to another company ID. It is counted once.

So: **the count is 209, the merge alternative is 205, 4 relationships across 8
company IDs drive that gap, and 5 companies need review.** When quoting a single
figure, say which of the three you mean — relationships (4), IDs involved (8), or
companies needing review (5).

## List 1: `target_accounts.json`

### Summary

| Discrepancy type | Groups/rows | Effect or risk |
|---|---:|---|
| Missing company ID (`null`) | 6 rows | A string conversion makes all six look like the same ID, even though names and domains differ. |
| Repeated nonblank company ID | 13 groups, 27 rows | There are 14 extra source rows after grouping; `company-sable-works` occurs three times. |
| Same company ID, conflicting domain | 2 groups | Identity count may remain one per ID, but the correct domain is unresolved. |
| Same domain, different company IDs | 4 domains | Domain cannot safely be used as a global identity key. |
| Saved settings conflict with request | 9 rows | These rows select the legacy Brand Kit and template instead of the request settings. |
| Duplicate uploaded row ID | 0 | All 223 `id` values are unique. |

Important overlap: `row-1217` participates in both a same-ID/two-domain
conflict and the `copperline-group.example` same-domain/two-ID conflict. These
are two observations about one row, not two extra companies.

### A. Missing identity: null `company_id`

| Row | Company name | Domain | Segment | Type/note |
|---|---|---|---|---|
| `row-2401` | Halverson Freight | `halverson-freight.example` | logistics | Missing company ID; distinct name and domain |
| `row-2402` | Pell & Sons Ironworks | `pellsons.example` | manufacturing | Missing company ID; distinct name and domain |
| `row-2403` | Cobalt Ridge Dental | `cobaltridge.example` | healthcare | Missing company ID; distinct name and domain |
| `row-2404` | Northgate Tutoring | `northgate-tutoring.example` | education | Missing company ID; distinct name and domain |
| `row-2405` | Riverbend Cold Storage | `riverbend-cold.example` | logistics | Missing company ID; distinct name and domain |
| `row-2406` | Aster Point Realty | `asterpoint.example` | real_estate | Missing company ID; distinct name and domain |

Notes:

- There is no evidence that these six rows are the same company.
- Treating `null` as the string `"None"` creates a false shared identity.
- With the counting rule above, all six remain separate unresolved companies.

### B. Repeated nonblank company IDs

| Company ID | Source rows | Data difference | Discrepancy type |
|---|---|---|---|
| `company-alder-health` | `row-1017`, `row-1201` | `Alder Health` / `ALDER HEALTH` | Name capitalization variant |
| `company-bright-foods` | `row-1095`, `row-1207` | `Bright Foods` / `BRIGHT FOODS` | Name capitalization variant |
| `company-copperline-energy` | `row-1100`, `row-1217` | `copperline-energy.example` / `copperline-group.example` | **Conflicting domain** |
| `company-copperline-group` | `row-1093`, `row-1206` | `Copperline Group` / `Copperline Group Inc` | Legal-suffix name variant |
| `company-harbor-group` | `row-1107`, `row-1209` | `Harbor Group` / `Harbor Group Inc` | Legal-suffix name variant; rows are far apart |
| `company-ironwood-logistics` | `row-1117`, `row-1210` | `Ironwood Logistics` / `IRONWOOD LOGISTICS` | Name capitalization variant; rows are far apart |
| `company-ironwood-partners` | `row-1029`, `row-1202` | `Ironwood Partners` / `Ironwood Partners Inc` | Legal-suffix name variant |
| `company-kestrel-dynamics` | `row-1097`, `row-1208` | `Kestrel Dynamics` / `Kestrel Dynamics Inc` | Legal-suffix name variant; rows are far apart |
| `company-kestrel-robotics` | `row-1066`, `row-1216` | `kestrel-robotics.example` / `kestrel-group.example` | **Conflicting domain** |
| `company-sable-works` | `row-1092`, `row-1204`, `row-1205` | `Sable Works` / `SABLE WORKS` / `SABLE WORKS Inc` | Capitalization and legal-suffix variants; three source rows |
| `company-tessellate-energy` | `row-1167`, `row-1212` | `Tessellate Energy` / `Tessellate Energy Inc` | Legal-suffix name variant; rows are far apart |
| `company-vantage-capital` | `row-1042`, `row-1203` | `Vantage Capital` / `Vantage Capital Inc` | Legal-suffix name variant |
| `company-vantage-networks` | `row-1127`, `row-1211` | `Vantage Networks` / `Vantage Networks Inc` | Legal-suffix name variant; rows are far apart |

The five far-apart groups are split across pages at page sizes 10, 25, and
100: `company-kestrel-dynamics`, `company-harbor-group`,
`company-ironwood-logistics`, `company-vantage-networks`, and
`company-tessellate-energy`. This is why per-page grouping leaves those five
companies duplicated at all three demonstrated page sizes.

### C. Same nonblank company ID, conflicting domains

| Company ID | Row and domain 1 | Row and domain 2 | Note |
|---|---|---|---|
| `company-kestrel-robotics` | `row-1066`: `kestrel-robotics.example` | `row-1216`: `kestrel-group.example` | Company ID and other fields agree, but the personalization domain does not. |
| `company-copperline-energy` | `row-1100`: `copperline-energy.example` | `row-1217`: `copperline-group.example` | The second domain is also used by a different company ID and segment. |

These are not ordinary duplicate rows. Silently retaining whichever row is
encountered first makes the chosen domain an ordering accident.

### D. Same domain, different nonblank company IDs

| Domain | Rows and company IDs | Note |
|---|---|---|
| `northwind-energy.example` | `row-1020`: `company-northwind-energy`; `row-1213`: `company-northwind-energy-emea` | Base and EMEA identities share a domain. |
| `sable-fitness.example` | `row-1047`: `company-sable-fitness`; `row-1214`: `company-sable-fitness-emea` | Base and EMEA identities share a domain. |
| `tessellate-capital.example` | `row-1076`: `company-tessellate-capital`; `row-1215`: `company-tessellate-capital-emea` | Base and EMEA identities share a domain. |
| `copperline-group.example` | `row-1093` and `row-1206`: `company-copperline-group`; `row-1217`: `company-copperline-energy` | Different IDs, names, and segments share the domain; also overlaps a conflicting-domain group. |

These rows show why domain alone is not a safe company identity key. They may
represent divisions or regional records that intentionally share a site.

### E. Row-level settings that conflict with the request

The request selects `brand-kit-meridian-2026` and `template-abm-q3`. Each row
below instead contains `brand-kit-2019-legacy` and
`template-legacy-blast`.

| Row | Company ID | Company name | Discrepancy type |
|---|---|---|---|
| `row-1014` | `company-kestrel-supply` | Kestrel Supply | Brand Kit and template override |
| `row-1082` | `company-halcyon-group` | Halcyon Group | Brand Kit and template override |
| `row-1084` | `company-marrow-media` | Marrow Media | Brand Kit and template override |
| `row-1123` | `company-foundry-partners` | Foundry Partners | Brand Kit and template override |
| `row-1140` | `company-cedar-partners` | Cedar Partners | Brand Kit and template override |
| `row-1163` | `company-pinnacle-systems` | Pinnacle Systems | Brand Kit and template override |
| `row-1176` | `company-cedar-labs` | Cedar Labs | Brand Kit and template override |
| `row-1195` | `company-sable-dynamics` | Sable Dynamics | Brand Kit and template override |
| `row-1213` | `company-northwind-energy-emea` | Northwind Energy EMEA | Brand Kit and template override; also shares a domain with another ID |

This discrepancy is not part of the identity count, but it is part of the
uploaded-data audit and affects 36 deliverables if four assets are created for
each row.

### F. List 1 count reconciliation

- 223 uploaded rows.
- 217 rows have a nonblank company ID.
- The 13 repeated nonblank-ID groups contain 14 extra source rows, leaving 203
  distinct nonblank company IDs.
- The six null-ID rows are retained separately because their missing IDs do
  not establish a shared identity.
- Result under the stated rule: **203 + 6 = 209 logical company records**.
- Two of the 203 nonblank records have unresolved domain conflicts and should
  be reported as conflicted rather than silently treated as clean.

## List 2: `second_list.json`

### Summary

| Discrepancy type | Groups/rows | Effect or risk |
|---|---:|---|
| Missing company ID (empty string) | 2 rows | Both rows collapse if `""` is treated as a real shared identity. |
| Repeated nonblank company ID | 15 groups, 31 rows | There are 16 extra source rows; `company-straddle-works` occurs three times. |
| Same company ID, conflicting domain | 0 | Repeated IDs have consistent domains and segments. |
| Same domain, different company IDs | 0 | No cross-ID domain conflicts were found. |
| Saved settings conflict with request | 0 | No saved Brand Kit or template fields are present. |
| Duplicate uploaded row ID | 0 | All 115 `id` values are unique. |

### A. Missing identity: empty-string `company_id`

| Row | Company name | Domain | Segment | Type/note |
|---|---|---|---|---|
| `srow-1114` | Unresolved Import A | `unresolved-a.example` | retail | Missing company ID; distinct name and domain |
| `srow-1115` | Unresolved Import B | `unresolved-b.example` | energy | Missing company ID; distinct name and domain |

The empty string has the same meaning problem as `null` in list 1. It is an
absence of identity, not evidence that the two rows describe one company.

### B. Repeated nonblank company IDs

| Company ID | Source rows | Data difference | Discrepancy type |
|---|---|---|---|
| `company-windrow` | `srow-1004`, `srow-1005` | `Windrow` / `Windrow Inc` | Legal-suffix name variant |
| `company-sable` | `srow-1012`, `srow-1013` | `Sable` / `Sable Inc` | Legal-suffix name variant |
| `company-bramble` | `srow-1020`, `srow-1021` | `Bramble` / `Bramble Inc` | Legal-suffix name variant |
| `company-straddle-works` | `srow-1111`, `srow-1112`, `srow-1113` | All other identity fields match | Three repeated source rows; deliberately separated in list order |
| `company-kestrel2` | `srow-1028`, `srow-1029` | `Kestrel 2` / `Kestrel 2 Inc` | Legal-suffix name variant |
| `company-pinnacle2` | `srow-1036`, `srow-1037` | `Pinnacle 2` / `Pinnacle 2 Inc` | Legal-suffix name variant |
| `company-wrenfield2` | `srow-1044`, `srow-1045` | `Wrenfield 2` / `Wrenfield 2 Inc` | Legal-suffix name variant |
| `company-fennel2` | `srow-1052`, `srow-1053` | `Fennel 2` / `Fennel 2 Inc` | Legal-suffix name variant |
| `company-talbot3` | `srow-1060`, `srow-1061` | `Talbot 3` / `Talbot 3 Inc` | Legal-suffix name variant |
| `company-thistle3` | `srow-1068`, `srow-1069` | `Thistle 3` / `Thistle 3 Inc` | Legal-suffix name variant |
| `company-cinder3` | `srow-1076`, `srow-1077` | `Cinder 3` / `Cinder 3 Inc` | Legal-suffix name variant |
| `company-ambit4` | `srow-1084`, `srow-1085` | `Ambit 4` / `Ambit 4 Inc` | Legal-suffix name variant |
| `company-quill4` | `srow-1092`, `srow-1093` | `Quill 4` / `Quill 4 Inc` | Legal-suffix name variant |
| `company-yarrow4` | `srow-1100`, `srow-1101` | `Yarrow 4` / `Yarrow 4 Inc` | Legal-suffix name variant |
| `company-garnet4` | `srow-1108`, `srow-1109` | `Garnet 4` / `Garnet 4 Inc` | Legal-suffix name variant |

Page-shape notes:

- At page size 10, the Bramble, Kestrel 2, and Cinder 3 pairs cross page
  boundaries. The third Straddle Works row is also on a later page. Four
  duplicate source rows therefore survive per-page grouping, producing 103
  campaigned rows instead of 99.
- At page size 25, only the third Straddle Works row is separated from its
  first two rows, producing 100 instead of 99.
- At page size 100, all repeated nonblank IDs are grouped, but the two blank-ID
  rows are on the same page and incorrectly collapse, producing 98 instead of
  99.

### C. List 2 count reconciliation

- 115 uploaded rows.
- 113 rows have a nonblank company ID.
- The 15 repeated nonblank-ID groups contain 16 extra source rows, leaving 97
  distinct nonblank company IDs.
- The two empty-ID rows are retained separately.
- Result under the stated rule: **97 + 2 = 99 logical company records**.

## Classification notes

- **Name variants** are evidence supporting a duplicate interpretation when
  the nonblank company ID, domain, and segment agree. They should not cause the
  source rows to disappear from provenance.
- **Domain conflicts within one company ID** are data-quality conflicts, not
  harmless duplicates. The identity rule can determine the count, but it
  cannot determine which domain is correct.
- **Shared domains across company IDs** are relationship signals, not proof of
  identity. Automatically merging them would combine records that the source
  assigned different IDs.
- **Missing IDs** require an explicit fallback policy. Grouping all missing
  values together is never justified by the missing value itself.
- **Request-setting overrides** do not change the company count, but they are
  discrepancies between uploaded row metadata and the customer's explicit
  campaign request.
