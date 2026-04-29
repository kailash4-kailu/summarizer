import os
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, send_file
app = Flask(__name__)
CORS(app)

from backend.abstractive import generate_abstractive_summary
from backend.chatbot import answer_question, prepare_rag_index
from backend.document_loader import extract_documents
from backend.extractive import summarize_textrank, summarize_tfidf
from backend.flashcards import generate_flashcards_for_documents
from backend.flowchart import generate_flowchart
from backend.metrics import calculate_metrics
from backend.mindmap import generate_mindmap


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}


CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "32")) * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False

os.makedirs(UPLOAD_DIR, exist_ok=True)

# In production, move this to Redis or a database-backed session store.
DOCUMENT_SESSIONS = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/process")
def process_documents():
    """Handle multi-file upload, generate summary, metrics, and intelligent views."""
    started_at = time.perf_counter()

    files = request.files.getlist("documents")
    method = request.form.get("method", "textrank").strip().lower()

    if not files or all(not file.filename for file in files):
        return jsonify({"error": "Upload at least one PDF or text file."}), 400

    try:
        documents, upload_errors = extract_documents(
            files=files,
            upload_dir=app.config["UPLOAD_FOLDER"],
            allowed_extensions=ALLOWED_EXTENSIONS,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not read uploaded files: {exc}"}), 500

    if not documents:
        return jsonify({"error": "No readable text was found in the uploaded files.", "warnings": upload_errors}), 400

    combined_text = "\n\n".join(doc["text"] for doc in documents)

    try:
        summary = build_summary(combined_text, method)
    except RuntimeError as exc:
        return jsonify({"error": str(exc), "warnings": upload_errors}), 500

    processing_time = time.perf_counter() - started_at
    metrics = calculate_metrics(combined_text, summary, processing_time)
    flowchart_code = generate_flowchart(summary)
    mindmap = generate_mindmap(summary)
    flashcards = generate_flashcards_for_documents(documents, summary)
    rag_index = prepare_rag_index(combined_text, documents)

    session_id = str(uuid.uuid4())
    DOCUMENT_SESSIONS[session_id] = {
        "id": session_id,
        "documents": documents,
        "combined_text": combined_text,
        "summary": summary,
        "method": method,
        "metrics": metrics,
        "flowchart": flowchart_code,
        "mindmap": mindmap,
        "flashcards": flashcards,
        "rag_index": rag_index,
        "history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return jsonify(
        {
            "session_id": session_id,
            "method": method,
            "document_count": len(documents),
            "documents": [{"filename": doc["filename"], "word_count": doc["word_count"]} for doc in documents],
            "summary": summary,
            "metrics": metrics,
            "flowchart": flowchart_code,
            "mindmap": mindmap,
            "flashcards": flashcards,
            "warnings": upload_errors,
        }
    )


@app.post("/api/chat")
def chat():
    """Answer questions using only the uploaded document session as context."""
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id")
    message = (payload.get("message") or "").strip()

    if not session_id or session_id not in DOCUMENT_SESSIONS:
        return jsonify({"error": "Process documents before starting a chat."}), 400

    if not message:
        return jsonify({"error": "Enter a question."}), 400

    session = DOCUMENT_SESSIONS[session_id]
    response = answer_question(
        question=message,
        rag_index=session["rag_index"],
        history=session["history"],
    )

    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": response["answer"]})
    session["history"] = session["history"][-12:]

    return jsonify(response)


@app.get("/api/download-summary/<session_id>")
def download_summary(session_id):
    """Return the generated summary as a downloadable text file."""
    session = DOCUMENT_SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Summary session not found."}), 404

    output_path = os.path.join(UPLOAD_DIR, f"summary-{session_id}.txt")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(session["summary"])

    return send_file(
        output_path,
        as_attachment=True,
        download_name="multi-document-summary.txt",
        mimetype="text/plain",
    )


def build_summary(text, method):
    """Route the request to the requested summarization strategy."""
    if method == "tfidf":
        return summarize_tfidf(text)

    if method == "textrank":
        return summarize_textrank(text)

    if method in {"bart", "t5", "abstractive"}:
        model_choice = "bart" if method == "abstractive" else method
        return generate_abstractive_summary(text, model_choice=model_choice)

    raise RuntimeError("Choose a supported summarization method: TF-IDF, TextRank, BART, or T5.")


@app.errorhandler(413)
def file_too_large(_error):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({"error": f"Uploaded files are too large. Limit is {max_mb} MB."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
