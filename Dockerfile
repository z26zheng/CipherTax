FROM python:3.12-slim

RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir -e . && python -m spacy download en_core_web_sm

COPY examples/ examples/
COPY tests/ tests/

ENTRYPOINT ["ciphertax"]
CMD ["--help"]
