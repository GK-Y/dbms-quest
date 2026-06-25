PY := python3
CLI := scripts/sql50.py

.PHONY: help reset list next sources question run test schema hint solution progress clean

help:
	$(PY) $(CLI) --help

reset:
	$(PY) $(CLI) reset $(Q)

list:
	$(PY) $(CLI) list

next:
	$(PY) $(CLI) next

sources:
	$(PY) $(CLI) sources

question:
	$(PY) $(CLI) question $(Q)

run:
	$(PY) $(CLI) run $(Q)

test:
	$(PY) $(CLI) test $(Q)

schema:
	$(PY) $(CLI) schema $(Q)

hint:
	$(PY) $(CLI) hint $(Q)

solution:
	$(PY) $(CLI) solution $(Q)

progress:
	$(PY) $(CLI) progress

clean:
	$(PY) $(CLI) clean
