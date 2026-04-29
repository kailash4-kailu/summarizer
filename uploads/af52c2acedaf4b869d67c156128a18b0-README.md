# Multi-Document AI Summarizer

A Flask web application that uploads multiple PDF/text documents, extracts and combines their text, produces extractive or abstractive summaries, calculates quality/efficiency metrics, and generates flowcharts, mind maps, flashcards, and a document-grounded chatbot.

## Folder Structure

```text
summarizer/
  app.py
  requirements.txt
  README.md
  backend/
    __init__.py
    abstractive.py
    chatbot.py
    document_loader.py
    extractive.py
    flashcards.py
    flowchart.py
    metrics.py
    mindmap.py
  templates/
    index.html
  static/
    app.js
    styles.css
  uploads/
    .gitkeep
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Optional Configuration

```bash
set OPENAI_API_KEY=your_key
set OPENAI_MODEL=gpt-4o-mini
set HF_SUMMARIZATION_MODEL=sshleifer/distilbart-cnn-12-6
set MAX_UPLOAD_MB=32
```

Abstractive summarization uses HuggingFace Transformers and downloads the selected model on first use if it is not already cached. The chatbot always retrieves from uploaded content first; without `OPENAI_API_KEY`, it uses a local extractive answer generator.
