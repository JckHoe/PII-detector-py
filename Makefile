.PHONY: install-model run-local build-binary run-binary

MODEL_PATH := $(shell pwd)/extracted_model/en_core_web_trf/en_core_web_trf-3.8.0

install-model:
	curl -L -o en_core_web_trf-3.8.0-py3-none-any.whl https://github.com/explosion/spacy-models/releases/download/en_core_web_trf-3.8.0/en_core_web_trf-3.8.0-py3-none-any.whl
	unzip -o en_core_web_trf-3.8.0-py3-none-any.whl -d extracted_model

run-server:
	uv run pii_server.py --local-model-path $(MODEL_PATH)

run-local:
	uv run pii_cli.py --local-model-path $(MODEL_PATH)

build-binary:
	uv run python build_binary.py

run-binary: install-model
	@echo "Running binary interactively..."
	@if [ -f "dist/pii-cli-darwin-arm64" ]; then \
		./dist/pii-cli-darwin-arm64 --local-model-path $(MODEL_PATH); \
	elif [ -f "dist/pii-cli-darwin-amd64" ]; then \
		./dist/pii-cli-darwin-amd64 --local-model-path $(MODEL_PATH); \
	elif [ -f "dist/pii-cli-linux-amd64" ]; then \
		./dist/pii-cli-linux-amd64 --local-model-path $(MODEL_PATH); \
	elif [ -f "dist/pii-cli-windows-amd64.exe" ]; then \
		./dist/pii-cli-windows-amd64.exe --local-model-path $(MODEL_PATH); \
	else \
		echo "No binary found. Run 'make build-binary' first."; \
		exit 1; \
	fi
