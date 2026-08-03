# Decisions

Short notes are fine. Fill this in before you submit.

- Time actually spent:
    ~2hours 25 minutes

- How many logical companies this upload represents, and why that number and
  not a neighbouring one: 
    209 for list 1 and 99 for list 2. Company_id is used as the identifier. If it isn't there then each company becomes its own company. And then different emeas also become different companies. 205 would have been the nieghboring number and four domains carry two different company_ids each (three emea subsidiaries and copperline-energy/copperline-group). Merging on domain gives 205. I did not merge.

- What changed between your roadmap and what you shipped:
    Roadmap had 6 defects as I went though we found way more, almost 20 so we fixed all of those.

- What you had the coding agent do, and where you overrode it:
    I had my coding agent find diffferent problems and then figure them out. I guided by first identifying the discrepencies and having it make a list. I then looked at the list and also had my agents look at it. I then created a plan to fix everything and then had multiple agents review the plan and then started making the changes. I also had the agent verify its own work with tests to make sure that it did everythign correctly.

- What your change guarantees, and what it only makes more likely:
    - Count does not depend on page size and won't change because of that.
    - Every row is traceable to exactly one company and no rows are made up or dropped
    - Every company has a brand kit with the proper template
    - Short reads can't be reported as completed when the size is defined
    Made more likely
    - I made the number 209 come everytime, so now it is the right answer more often 
    - If the size is not given the result says unknown.
    - If one company_id has two domains we still count it as one company, but we flag which domain we used because that's the one the landing page gets built against.


- What you fixed at the cause, and what you only stopped from showing:
  Fixed at the cause:
  - Grouping now happens after the full read, so page size can't reach the answer.
  - Blank companies are handeled properly
  - Duplicate rows get grouped into one company instead of each getting their own set of assets. No row is dropped, every one still traces to the company it landed in.
  - We get the correct brand kit which is there for the campaign not the one saved to the row
  Only stopped from showing:
  - The filtered read. The run we're looking at paged perfectly, it was just handed a short row set. We catch it by reconciling against the declared size, but the real cause is upstream of paging
  - The contested domains if all other information is the same. we just use the first one. We do flag the company for a human though.

- For at least one defect: the command that demonstrated it, pasted with its
  output, before your fix and after:
      The defect: the same upload gave three different answers depending on page size,
      and the check called all of them complete.

      Before, PYTHONPATH=src python3 demo.py at commit 8f0f5c7:

                                        page_size=10    page_size=25   page_size=100
      rows campaigned                            214             214             211
      deliverables                               856             856             844
      distinct company_id in plan                204             204             204
      complete flag                             True            True            True

      deliverables by brand kit (page_size=25):
        brand-kit-2019-legacy                36
        brand-kit-meridian-2026             820

      shipped check returned        : True
      shipped check said            : all 214 campaigned rows have the requested asset types

      After, make demo:

                                        page_size=10    page_size=25   page_size=100
      companies                                  209             209             209
      deliverables                               836             836             836
      uploaded rows read                         223             223             223
      service claimed complete                  True            True            True
      verified complete                         true            true            true

      the count is                  invariant at 209 companies

      deliverables by brand kit:
        brand-kit-meridian-2026               836

      check returned                : True
      check said                    : 209 companies from 223 rows, 836 deliverables,
                                      9 exceptions, read verified against declared size 223

  Deliverables went from 856 to 836. The 36 in the wrong brand kit went to 0 and the 9 rows that asked for it are listed as exceptions instead. 


- What you chose not to fix:
      Merging different contested identities. The emea ones we flag, however we do count them in the 209 as the default state, but they are flagged.
      Trace t-4c08. An image_search timeout marked retryable. Seemed like a red herring.
 

- What you are still unsure about, including anything that came up during the
  session and stayed open:

  - Why the service served 217 and not 223. Don't really know which six rows were missing between the readme and the file. The trace shows 217 as well but there are 223.
  - Whether 209 or 205 is right.


- The number your check reports for each list, and why the two lists don't produce
  the same shape of answer:
    209 for target_accounts.json and 99 for second_list.json.

    They don't produce the same shape because list 1 has contested records and list 2
    has none. So list one has contested pairs where the four domain names are different and 9 rows whos brand kit is overwritten. So that changes the shape of both the lists.