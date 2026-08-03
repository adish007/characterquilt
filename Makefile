.PHONY: demo test verify audit discrepancies

demo:
	PYTHONPATH=src python3 demo.py

audit:
	PYTHONPATH=src python3 aj_work/audit.py --list fixtures/target_accounts.json
	PYTHONPATH=src python3 aj_work/audit.py --list fixtures/second_list.json

discrepancies:
	PYTHONPATH=src python3 aj_work/discrepancies.py --list fixtures/target_accounts.json
	PYTHONPATH=src python3 aj_work/discrepancies.py --list fixtures/second_list.json

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v


verify:
	PYTHONPATH=src python3 demo.py --list fixtures/second_list.json
