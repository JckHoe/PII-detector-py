.PHONY: install-model install-trf-model run detect

install-model:
	uv run python -m spacy download en_core_web_trf

run: install-model
	uv run pii_cli.py --interactive

detect: install-model
	@if [ -z "$(INPUT)" ]; then echo "Usage: make detect INPUT='your text here'"; exit 1; fi
	@echo "$(INPUT)" | uv run pii_cli.py --quiet
