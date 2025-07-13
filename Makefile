.PHONY: install-model install-trf-model run-local detect build-binary run-binary

install-model:
	uv run python -m spacy download en_core_web_trf

run-local:
	uv run pii_cli.py --interactive --local-model-path extracted_model/en_core_web_trf/en_core_web_trf-3.8.0

detect:
	@if [ -z "$(INPUT)" ]; then echo "Usage: make detect INPUT='your text here'"; exit 1; fi
	@echo "$(INPUT)" | uv run pii_cli.py --quiet --local-model-path extracted_model/en_core_web_trf/en_core_web_trf-3.8.0

build-binary:
	uv run python build_binary.py

run-binary:
	@echo "Running binary interactively..."
	@if [ -f "dist/pii-cli-darwin-arm64" ]; then \
		./dist/pii-cli-darwin-arm64 --interactive --local-model-path extracted_model/en_core_web_trf/en_core_web_trf-3.8.0; \
	elif [ -f "dist/pii-cli-darwin-amd64" ]; then \
		./dist/pii-cli-darwin-amd64 --interactive --local-model-path extracted_model/en_core_web_trf/en_core_web_trf-3.8.0; \
	elif [ -f "dist/pii-cli-linux-amd64" ]; then \
		./dist/pii-cli-linux-amd64 --interactive; \
	elif [ -f "dist/pii-cli-windows-amd64.exe" ]; then \
		./dist/pii-cli-windows-amd64.exe --interactive; \
	else \
		echo "No binary found. Run 'make build-binary' first."; \
		exit 1; \
	fi
