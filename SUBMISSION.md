# Submission

- Transcript (file or link): Had three agents:
  - `CharacterQuilt1.txt` — main Claude Code session (the bulk of the work)
  - `CharacterQuilt2.txt` — second Claude session
  - `CharacterQuilt3Codex.txt` — Codex session

  All three are raw exports in the repo root, not tidied up.

- `make demo` output:
                                    page_size=10    page_size=25   page_size=100
  companies                                  209             209             209
  deliverables                               836             836             836
  uploaded rows read                         223             223             223
  service claimed complete                  True            True            True
  verified complete                         true            true            true

  the count is                  invariant at 209 companies
  read                          : service reported the end of the list; matches declared size 223

  deliverables by brand kit:
    brand-kit-meridian-2026               836

  rows whose saved selections the request overrode: 9
  companies whose domain needed a choice: 8

  check returned                : True
  check said                    : 209 companies from 223 rows, 836 deliverables, 9 exceptions,
                                  read verified against declared size 223

- `make test` output:
  Ran 26 tests in 0.173s
  OK

- `make verify` output:
                                    page_size=10    page_size=25   page_size=100
  companies                                   99              99              99
  deliverables                               396             396             396
  uploaded rows read                         115             115             115

  contested identity relationships                 0
  one identity, several domains                    0
  rows overriding the request                      0

  check said                    : 99 companies from 115 rows, 396 deliverables, 0 exceptions,
                                  read verified against declared size 115

- The one thing you found yourself rather than took from the agent:

Figured out very early on that there were very different numbers that we were getting. In the readme.md I saw 217 and then 223 in the actual file. Then claude also gave me 209 and 205. So I found this discrepency and ask claude about it and it was one of the bugs that claude was able to look deeper into and solve.

- The claim in this submission you are least sure of, and how you checked it:

That 209 is right rather than 205. I checked it by seeing what would the list look like if we keyed on domain instead of company_id and it gives 207. It deleted 4 companies that share a domain and split two companies that have two domains each. So I didn't think this was correct.

- Anything a reviewer should know before opening the repository:

aj_work/ is my working notes, not part of the deliverable. FIX_PLAN.md there has the full
  issue list with before and after numbers for each one. The six commits A through F are
  one per group of fixes and each commit message has the numbers it moved.