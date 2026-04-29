.PHONY: install test lint demo clean publish docker

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"
	. .venv/bin/activate && python -m spacy download en_core_web_sm

test:
	. .venv/bin/activate && pytest -v

lint:
	. .venv/bin/activate && ruff check src/

demo:
	. .venv/bin/activate && python examples/demo_tax_filing.py

samples:
	. .venv/bin/activate && python examples/generate_samples.py

clean:
	rm -rf .venv build dist *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

publish:
	. .venv/bin/activate && python -m build && twine upload dist/*

docker:
	docker build -t ciphertax .
