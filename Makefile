.PHONY: install-model install-trf-model run detect

install-model:
	uv run python -m spacy download en_core_web_trf

run:
	uv run pii_cli.py --interactive --local-model-path /Users/juster/Project/playground/pii_detector/extracted_model/en_core_web_trf/en_core_web_trf-3.8.0

detect: install-model
	@if [ -z "$(INPUT)" ]; then echo "Usage: make detect INPUT='your text here'"; exit 1; fi
	@echo "$(INPUT)" | uv run pii_cli.py --quiet
