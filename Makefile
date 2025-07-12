.PHONY: install-model run

install-model:
	uv run python -m spacy download en_core_web_sm

run: install-model
	uv run pii_cli.py --interactive