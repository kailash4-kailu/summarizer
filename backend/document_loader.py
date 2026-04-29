import os
import re
import uuid

from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    """Check whether an upload has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def extract_documents(files, upload_dir, allowed_extensions):
    """Validate, store, and extract plain text from uploaded PDF/text files."""
    documents = []
    errors = []

    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue

        original_name = secure_filename(file_storage.filename)
        if not allowed_file(original_name, allowed_extensions):
            errors.append(f"{original_name}: unsupported file type.")
            continue

        extension = original_name.rsplit(".", 1)[1].lower()
        stored_name = f"{uuid.uuid4().hex}-{original_name}"
        stored_path = os.path.join(upload_dir, stored_name)
        file_storage.save(stored_path)

        try:
            if extension == "pdf":
                text = extract_pdf_text(stored_path)
            else:
                text = extract_text_file(stored_path)
        except Exception as exc:
            errors.append(f"{original_name}: {exc}")
            continue

        cleaned = clean_text(text)
        if not cleaned:
            errors.append(f"{original_name}: no readable text found.")
            continue

        documents.append(
            {
                "filename": original_name,
                "stored_path": stored_path,
                "text": cleaned,
                "word_count": len(cleaned.split()),
            }
        )

    return documents, errors


def extract_pdf_text(path):
    """Read text from every page of a PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise RuntimeError("PyPDF2 is required to read PDF files.") from exc

    reader = PdfReader(path)
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return "\n".join(page_text)


def extract_text_file(path):
    """Read a UTF-8 text file with a Latin-1 fallback for older documents."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as handle:
            return handle.read()


def clean_text(text):
    """Normalize whitespace while preserving sentence boundaries."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
