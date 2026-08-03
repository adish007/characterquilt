# Roadmap

## Step 1 — The contested rows

A small set of rows moves the count; the rest is unambiguous.

**List 1 — `target_accounts.json`, 223 rows**

| Class | Which | Why contested |
|---|---|---|
| Blank `company_id` (`null`) | `row-2401`…`row-2406` (6) | All key to `"None"`; merge when they share a page |
| Duplicate `company_id` | 13 groups, 14 extra rows | 5 straddle a page boundary at every page size: `kestrel-dynamics`, `harbor-group`, `ironwood-logistics`, `vantage-networks`, `tessellate-energy` |
| One id → two domains | `company-kestrel-robotics`, `company-copperline-energy` | One customer or two? Not resolvable here |
| One domain → two ids | `northwind-energy`, `sable-fitness`, `tessellate-capital` (`-emea` pairs), `copperline-group` | Domain is not identity; merging these is wrong |

223 − 14 duplicate rows = **209 companies**; the blank-id rows have 6 distinct names and domains, so each counts once.

**List 2 — `second_list.json`, 115 rows.** Blanks are `""`, not `null` (`srow-1114/1115`); 15 duplicate groups, 16 extra rows; no domain conflicts, no overrides. 115 − 16 = **99**.

Output: a script printing these classes for any list — the number derived, not asserted.

## Step 2 — Defects - fix these defects. 

For each defect, fully understand the issue and then we should know the rows that apply for that defect and then we fix the defect and should see the expected rows.

1. **The check is vacuous.** `evaluate_campaign_coverage` never reads `accounts`; an empty plan returns `True`. It echoes `complete`, which `build_campaign_plan` hardcodes.
2. **Dedup is per-page.** Page size changes the answer: 214 / 214 / 211 rows, all "complete".
3. **Blank ids collapse.** `str(None)` merges distinct companies; at `page_size=100` three vanish silently. Same bug via `""` in list 2.
4. **Rows override the request.** 9 rows force `brand-kit-2019-legacy` and `template-legacy-blast` — 36 deliverables off-brand, templates never reported.
5. **Paging never terminates safely.** All five `sources.py` shapes break it: duplicated reads, three infinite loops, one short read declared complete.
6. **Traceability is lost.** Collapsed rows vanish from `source_row_ids`; a deliverable can't be traced to every row behind it.
