.PHONY: install test analyze
install:
	python -m pip install -e '.[quality,agentic]'
test:
	python -m pytest -q
analyze:
	intra-ai analyze data/input --output outputs
