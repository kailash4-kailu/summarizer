# AI Summarizer

A Flask web app for summarizing pasted text or imported documents. It supports PDF, DOCX, TXT, MD, and RTF extraction, summary metrics, key terms, flashcards, and a document-grounded chatbot.

## Project Structure

```text
summarizer/
  app.py                 # Vercel Flask entrypoint
  wsgi.py                # Local WSGI entrypoint
  vercel.json            # Vercel function config
  requirements.txt
  backend/
    app.py               # Main Flask app and summarization logic
  templates/
    index.html
  static/
    app.js
    styles.css
  public/
    static/
      app.js
      styles.css         # Vercel-served static assets
```

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python wsgi.py
```

Open `http://127.0.0.1:5000`.


