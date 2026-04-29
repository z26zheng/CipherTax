# Contributing to CipherTax

Thank you for your interest in contributing to CipherTax! This project helps people safely use AI for tax filing by keeping their personal data private.

## How to Contribute

### Reporting Bugs
- Use the [Bug Report](https://github.com/z26zheng/CipherTax/issues/new?template=bug_report.md) template
- Include steps to reproduce, expected vs actual behavior
- Include your Python version and OS

### Suggesting Features
- Use the [Feature Request](https://github.com/z26zheng/CipherTax/issues/new?template=feature_request.md) template
- Explain the use case and why it would benefit users

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest`
5. Ensure all 152+ tests pass
6. Submit a pull request

### Development Setup

```bash
git clone https://github.com/z26zheng/CipherTax.git
cd CipherTax
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
pytest  # Verify everything works
```

### Code Style
- We use [Ruff](https://github.com/astral-sh/ruff) for linting
- Line length: 100 characters
- Run `ruff check src/` before submitting

### Areas That Need Help

| Area | Description | Difficulty |
|------|-------------|------------|
| **State tax support** | Add state tax calculations (start with CA, NY, TX) | Medium |
| **Tax year 2025** | Add 2025 brackets and limits to `tax/data/` | Easy |
| **Form recognizers** | Improve PII detection for specific form layouts | Medium |
| **Web UI** | Build a web interface (Flask/FastAPI) | Hard |
| **More test scenarios** | Additional tax calculation edge cases | Easy |
| **Documentation** | Improve docstrings and API docs | Easy |

### Testing

- All changes must include tests
- PII leak prevention tests are critical — never skip them
- Run the full suite: `pytest -v`
- For tax calculations, verify against known IRS examples

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Adding tests
- `refactor:` — Code restructuring

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
