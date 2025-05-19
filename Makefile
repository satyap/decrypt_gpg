# Makefile for Python project

# Virtual Environment Settings
VENV_DIR = ~/venv/decrypt_gpg
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

all: | install lint tests

# Install dependencies into virtual environment
install: $(VENV_DIR)/bin/activate
	$(PIP) install .

$(VENV_DIR)/bin/activate:
	python3 -m venv $(VENV_DIR)
	$(PIP) install -U pip setuptools wheel
	$(PIP) install .

# Install testing dependencies
install-test: $(VENV_DIR)/bin/activate
	$(PIP) install .[testing]

# Run black code formatter
black: $(VENV_DIR)/bin/activate
	$(PYTHON) -m black --check --diff . || (echo 'Run "make black-fix" to fix' && false)

black-fix: $(VENV_DIR)/bin/activate
	$(PYTHON) -m black .

# Run mypy for static type checking
mypy: $(VENV_DIR)/bin/activate
	$(PYTHON) -m mypy src tests

# Run tests with pytest and coverage
test: $(VENV_DIR)/bin/activate
	$(PYTHON) -m pytest
	@echo You should run: make coverage

# Run coverage with pytest
coverage: $(VENV_DIR)/bin/activate
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report

# Build the package
build: $(VENV_DIR)/bin/activate
	$(PIP) install .[build]
	$(PYTHON) -m build

# Clean up build artifacts
clean:
	rm -rf dist build $(VENV_DIR)

lint: black mypy
tests: lint coverage

.PHONY: install install-test black mypy test coverage build clean cli lint test
