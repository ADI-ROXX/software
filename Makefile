.PHONY: all

# Default target: run streamlit
all:
	@streamlit run main.py

.PHONY: fmt

# fmt target: format code using isort and black
fmt:
	@isort .
	@black .

.PHONY: lint

## lint target: run pylint on all Python files in the project
lint:
	@echo "Running pylint on all Python files..."
	@find . -type f -name "*.py" -exec pylint {} +