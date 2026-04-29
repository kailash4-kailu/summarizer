import os
import re


def prepare_rag_index(combined_text, documents, chunk_size=180, overlap=45):
    """Build a lightweight TF-IDF retrieval index for uploaded documents."""
    chunks = []
    for document in documents:
        words = re.findall(r"\S+", document["text"])
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(
                {
                    "text": " ".join(words[start:end]),
                    "source": document["filename"],
                }
            )
            if end == len(words):
                break
            start = max(end - overlap, start + 1)

    if not chunks:
        chunks = [{"text": combined_text, "source": "uploaded documents"}]

    vectorizer = None
    matrix = None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([chunk["text"] for chunk in chunks])
    except Exception:
        pass

    return {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "matrix": matrix,
    }


def answer_question(question, rag_index, history=None, top_k=4):
    """Answer a question from retrieved document chunks with OpenAI or local fallback."""
    history = history or []
    retrieved = retrieve_chunks(question, rag_index, top_k=top_k)
    context = "\n\n".join(f"[{item['source']}] {item['text']}" for item in retrieved)

    if os.getenv("OPENAI_API_KEY"):
        openai_answer = try_openai_answer(question, context, history)
        if openai_answer:
            return {"answer": openai_answer, "sources": sorted({item["source"] for item in retrieved})}

    return {
        "answer": local_supported_answer(question, retrieved),
        "sources": sorted({item["source"] for item in retrieved}),
    }


def retrieve_chunks(question, rag_index, top_k=4):
    """Return the most relevant chunks for a user question."""
    chunks = rag_index["chunks"]
    vectorizer = rag_index.get("vectorizer")
    matrix = rag_index.get("matrix")

    if vectorizer is not None and matrix is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            query_vector = vectorizer.transform([question])
            scores = cosine_similarity(query_vector, matrix).flatten()
            top_indexes = scores.argsort()[-top_k:][::-1]
            return [chunks[index] for index in top_indexes if scores[index] > 0][:top_k] or chunks[:top_k]
        except Exception:
            pass

    question_terms = set(tokenize(question))
    scored = []
    for chunk in chunks:
        terms = set(tokenize(chunk["text"]))
        scored.append((len(question_terms & terms), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:top_k]]


def try_openai_answer(question, context, history):
    """Use OpenAI when configured, while constraining answers to uploaded context."""
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI()
    compact_history = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-6:]
        if item.get("role") in {"user", "assistant"}
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "You answer only from the supplied uploaded-document context. "
                "If the answer is not supported by that context, say that the uploaded documents do not contain enough information."
            ),
        },
        *compact_history,
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.1,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def local_supported_answer(question, retrieved):
    """Create a deterministic answer from the most relevant retrieved sentences."""
    question_terms = set(tokenize(question))
    scored_sentences = []

    for item in retrieved:
        for sentence in re.split(r"(?<=[.!?])\s+", item["text"]):
            sentence_terms = set(tokenize(sentence))
            score = len(question_terms & sentence_terms)
            if score:
                scored_sentences.append((score, sentence.strip(), item["source"]))

    if not scored_sentences:
        return "I could not find enough support for that answer in the uploaded documents."

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    chosen = []
    seen = set()
    for _score, sentence, source in scored_sentences:
        normalized = sentence.lower()
        if normalized in seen or len(sentence.split()) < 5:
            continue
        chosen.append(f"{sentence} ({source})")
        seen.add(normalized)
        if len(chosen) == 3:
            break

    return " ".join(chosen) if chosen else "I could not find enough support for that answer in the uploaded documents."


def tokenize(text):
    """Tokenize text for retrieval overlap scoring."""
    return re.findall(r"[a-z0-9]+", text.lower())
