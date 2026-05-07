from collections import Counter
from io import BytesIO
import math
import os
import re
import xml.etree.ElementTree as ET
import zipfile

from flask import Flask, jsonify, render_template, request

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "public", "static")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=STATIC_DIR,
)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

STOP_WORDS = {
    "the", "is", "and", "to", "of", "in", "a", "for", "on", "with", "as",
    "by", "an", "be", "are", "this", "that", "it", "from", "at", "or",
    "was", "were", "will", "would", "can", "could", "should", "has", "have",
    "had", "their", "there", "they", "them", "into", "about", "than", "then",
    "also", "such", "which", "when", "where", "while", "because", "using",
    "help", "helps", "helped", "important", "main", "most", "people", "team",
    "teams", "tool", "tools", "text", "source", "current", "ready", "what",
    "why", "how", "does", "did", "tell", "give", "make", "made",
    "becoming", "part", "everyday", "work",
    "research", "writing", "operations", "reduce", "reduces", "preserve",
    "remove", "show", "shows", "judge", "useful", "strongest", "basic",
    "complete", "enough", "result", "easy", "scan",
    "author",
}

QUESTION_REPLACEMENTS = {
    "abt": "about",
    "wht": "what",
    "whats": "what is",
    "u": "you",
    "ur": "your",
}

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def normalize_text(text):
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text):
    cleaned = normalize_text(text).replace("\n", " ")
    sentences = [
        sentence.strip(" -")
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
        if sentence.strip(" -")
    ]

    if len(sentences) <= 1 and len(cleaned.split()) > 45:
        sentences = [
            chunk.strip(" -")
            for chunk in re.split(r"\s{2,}|[;:]\s+", cleaned)
            if chunk.strip(" -")
        ]

    return sentences


def tokenize(text):
    return re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower())


def extract_keywords(text, limit=8):
    filtered = [
        word for word in tokenize(text)
        if word not in STOP_WORDS and len(word) > 3
    ]
    return [word for word, _ in Counter(filtered).most_common(limit)]


def extract_display_terms(text, limit=6):
    display_stop_words = STOP_WORDS - {"main"}
    chunks = re.split(r"[.!?;,\n]+", text)
    all_words = tokenize(text)
    words = [
        word for word in all_words
        if word not in display_stop_words and len(word) > 3
    ]
    phrase_counts = Counter()
    for chunk in chunks:
        tokens = tokenize(chunk)
        size = 2
        for index in range(len(tokens) - size + 1):
            gram = tokens[index:index + size]
            if any(word in display_stop_words or len(word) <= 3 for word in gram):
                continue
            phrase = " ".join(gram)
            phrase_counts[phrase] += 1

    terms = []
    for phrase, _ in phrase_counts.most_common(limit):
        if any(phrase in existing or existing in phrase for existing in terms):
            continue
        terms.append(phrase)
        if len(terms) >= limit:
            return terms

    for word, _ in Counter(words).most_common(limit):
        if word not in terms:
            terms.append(word)
        if len(terms) >= limit:
            break
    return terms


def sentence_score(sentence, keywords):
    normalized = sentence.lower()
    keyword_hits = sum(
        1 for keyword in keywords
        if re.search(rf"\b{re.escape(keyword)}\b", normalized)
    )
    length = len(sentence.split())
    length_score = 1 if 8 <= length <= 34 else 0.45
    return keyword_hits * 2 + length_score


def choose_summary_count(sentence_count, requested):
    if sentence_count <= 2:
        return sentence_count

    requested = max(1, min(int(requested), 10))
    natural_count = max(2, math.ceil(sentence_count * 0.6))
    return min(requested, natural_count, sentence_count)


def rank_sentences(sentences, focus=""):
    keywords = extract_keywords(f"{focus} {' '.join(sentences)}", limit=14)

    if TfidfVectorizer is None or cosine_similarity is None or len(sentences) < 2:
        return [
            (index, sentence_score(sentence, keywords))
            for index, sentence in enumerate(sentences)
        ]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=4000,
        )
        matrix = vectorizer.fit_transform(sentences)
        centrality = cosine_similarity(matrix).sum(axis=1)
    except Exception:
        centrality = [0] * len(sentences)

    ranked = []
    focus_terms = extract_keywords(focus, limit=10)
    for index, sentence in enumerate(sentences):
        position_boost = 0.7 if index == 0 else 0.15
        if index == len(sentences) - 1:
            position_boost += 0.2
        focus_boost = sentence_score(sentence, focus_terms) if focus_terms else 0
        quality_score = sentence_score(sentence, keywords)
        ranked.append((index, float(centrality[index]) + quality_score + focus_boost + position_boost))

    return ranked


def summarize_extractive(text, num_sentences=3, focus=""):
    sentences = split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) == 1:
        return sentences[0]

    target_count = choose_summary_count(len(sentences), num_sentences)
    ranked = sorted(rank_sentences(sentences, focus), key=lambda item: item[1], reverse=True)
    selected_indexes = sorted(index for index, _ in ranked[:target_count])
    return " ".join(sentences[index] for index in selected_indexes)


def keyword_hit_count(sentence, keywords):
    normalized = sentence.lower()
    return sum(
        1 for keyword in keywords
        if re.search(rf"\b{re.escape(keyword)}\b", normalized)
    )


def build_flashcards(text, count=6):
    sentences = split_sentences(text)
    ranked = sorted(rank_sentences(sentences), key=lambda item: item[1], reverse=True)

    cards = []
    used_answers = set()
    for index, _ in ranked:
        answer = sentences[index].strip()
        if len(answer.split()) < 7 or answer.lower() in used_answers:
            continue

        terms = extract_keywords(answer, limit=3)
        topic = terms[0] if terms else "this idea"
        cards.append({
            "question": f"What does the text say about {topic}?",
            "answer": answer,
            "hint": f"Connect {topic} to the author's point.",
        })
        used_answers.add(answer.lower())

        if len(cards) >= count:
            break

    if not cards and text.strip():
        cards.append({
            "question": "What is the main idea of this text?",
            "answer": summarize_extractive(text, 1),
            "hint": "Look for the central claim.",
        })

    return cards


def normalize_question(message):
    words = re.findall(r"\b[a-zA-Z0-9']+\b", message.lower())
    cleaned = [QUESTION_REPLACEMENTS.get(word, word) for word in words]
    return " ".join(cleaned)


def is_about_question(question):
    about_terms = (
        "about", "main point", "main idea", "main points", "overview",
        "what is this", "what is it", "what it all", "gist", "topic",
    )
    return any(term in question for term in about_terms)


def rank_for_question(question, context, limit=3):
    sentences = split_sentences(context)
    if not sentences:
        return []

    if TfidfVectorizer is not None and cosine_similarity is not None:
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=4000,
            )
            matrix = vectorizer.fit_transform(sentences + [question])
            scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
            ranked = sorted(
                enumerate(scores),
                key=lambda item: item[1],
                reverse=True,
            )
            matches = [sentences[index] for index, score in ranked if score > 0.03]
            if matches:
                return matches[:limit]
        except Exception:
            pass

    keywords = extract_keywords(question, limit=10)
    if not keywords:
        return []

    ranked = sorted(
        sentences,
        key=lambda sentence: (
            keyword_hit_count(sentence, keywords),
            sentence_score(sentence, keywords),
        ),
        reverse=True,
    )
    return [
        sentence for sentence in ranked
        if keyword_hit_count(sentence, keywords) > 0
    ][:limit]


def build_about_reply(context):
    summary = summarize_extractive(context, 3)
    points = split_sentences(summary)
    if not points:
        return "I need source text before I can explain what it is about."

    lines = [f"Main idea: {points[0]}"]
    if len(points) > 1:
        lines.append("")
        lines.append("Key points:")
        lines.extend(f"- {point}" for point in points[1:4])

    return "\n".join(lines)


def build_simple_explanation(context):
    summary = summarize_extractive(context, 2)
    if not summary:
        return "I need source text before I can explain it."
    return f"In simple terms: {summary}"


def build_chat_reply(message, context=""):
    question = normalize_question(message)
    context = normalize_text(context)

    if any(greeting in question.split() for greeting in ("hello", "hi", "hey")):
        return "Hi. Add text or import a file, then ask me about the actual content."

    if not context:
        return "Add source text or import a PDF/DOCX first, then I can answer from it."

    if "quiz" in question or "flashcard" in question or "study" in question:
        card = build_flashcards(context, 1)[0]
        return f"Quiz: {card['question']}\nHint: {card['hint']}"

    if is_about_question(question):
        return build_about_reply(context)

    if "explain" in question or "simple" in question or "hardest" in question:
        return build_simple_explanation(context)

    if "summary" in question or "summarize" in question or "shorten" in question:
        return summarize_extractive(context, 3)

    matches = rank_for_question(question, context, limit=3)
    if matches:
        return "From the text:\n" + "\n".join(f"- {match}" for match in matches)

    fallback = summarize_extractive(context, 2)
    return f"I do not see a direct answer in the text. Closest useful context:\n{fallback}"


def extract_pdf_text(file_bytes):
    if PdfReader is None:
        raise ValueError("PDF support is unavailable because PyPDF2 is not installed.")

    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return normalize_text("\n\n".join(pages))


def docx_paragraph_text(paragraph):
    chunks = []
    for child in paragraph.iter():
        if child.tag == f"{{{WORD_NAMESPACE['w']}}}t" and child.text:
            chunks.append(child.text)
        elif child.tag == f"{{{WORD_NAMESPACE['w']}}}tab":
            chunks.append(" ")
        elif child.tag == f"{{{WORD_NAMESPACE['w']}}}br":
            chunks.append("\n")
    return "".join(chunks).strip()


def extract_docx_text(file_bytes):
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as document:
            xml_parts = ["word/document.xml", "word/footnotes.xml", "word/endnotes.xml"]
            paragraphs = []
            for part_name in xml_parts:
                if part_name not in document.namelist():
                    continue
                root = ET.fromstring(document.read(part_name))
                for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
                    text = docx_paragraph_text(paragraph)
                    if text:
                        paragraphs.append(text)
    except zipfile.BadZipFile as error:
        raise ValueError("This Word file is not a valid .docx document.") from error

    return normalize_text("\n\n".join(paragraphs))


def extract_plain_text(file_bytes):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return normalize_text(file_bytes.decode(encoding))
        except UnicodeDecodeError:
            continue
    return ""


def extract_text_from_upload(uploaded_file):
    filename = uploaded_file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    file_bytes = uploaded_file.read()

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    if extension == ".pdf":
        text = extract_pdf_text(file_bytes)
    elif extension == ".docx":
        text = extract_docx_text(file_bytes)
    elif extension in {".txt", ".md", ".rtf"}:
        text = extract_plain_text(file_bytes)
    elif extension == ".doc":
        raise ValueError("Old .doc files are not supported. Please save it as .docx and upload again.")
    else:
        raise ValueError("Upload a PDF, DOCX, TXT, MD, or RTF file.")

    if not text:
        raise ValueError("No readable text was found in this file.")

    return filename, text


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Backend updated successfully",
    })


@app.route("/extract-file", methods=["POST"])
def extract_file():
    try:
        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return jsonify({"error": "No file provided"}), 400

        filename, text = extract_text_from_upload(uploaded_file)
        return jsonify({
            "filename": filename,
            "text": text,
            "word_count": len(text.split()),
        })
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Could not read file: {error}"}), 500


@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json() or {}

        if "text" not in data:
            return jsonify({"error": "No text provided"}), 400

        text = normalize_text(data.get("text", ""))
        if not text:
            return jsonify({"error": "No text provided"}), 400

        num_sentences = max(1, min(int(data.get("sentences", 3)), 10))
        focus = data.get("focus", "").strip()
        summary = summarize_extractive(text, num_sentences, focus)

        if not summary:
            summary = text[:250]

        source_words = len(text.split())
        summary_words = len(summary.split())
        compression = int((summary_words / source_words) * 100) if source_words else 0
        reading_time = max(1, round(summary_words / 200))

        return jsonify({
            "summary": summary,
            "stats": {
                "source_words": source_words,
                "summary_words": summary_words,
                "compression_percent": compression,
                "reading_time_minutes": reading_time,
            },
            "key_terms": extract_display_terms(text, limit=6),
        })

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/flashcards", methods=["POST"])
def flashcards():
    data = request.get_json() or {}
    text = normalize_text(data.get("text", ""))
    count = max(3, min(int(data.get("count", 6)), 12))

    if not text:
        return jsonify({"error": "No text provided"}), 400

    return jsonify({"cards": build_flashcards(text, count)})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    context = data.get("context", "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    return jsonify({"reply": build_chat_reply(message, context)})


if __name__ == "__main__":
    app.run(debug=True)
