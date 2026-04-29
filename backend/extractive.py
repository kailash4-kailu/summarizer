import math
import re
from collections import Counter


def split_sentences(text):
    """Split text into sentences without requiring external tokenizer data."""
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    if not text:
        return []

    blocks = re.split(r"\n{1,}|\s+[•*-]\s+", text)
    sentences = []
    for block in blocks:
        normalized = re.sub(r"\s+", " ", block).strip()
        if not normalized:
            continue
        sentences.extend(re.split(r"(?<=[.!?])\s+(?=[A-Z0-9`])", normalized))

    return [sentence.strip(" -`") for sentence in sentences if len(sentence.split()) >= 4]


def summarize_tfidf(text, max_sentences=8):
    """Generate an extractive summary by ranking sentences with TF-IDF scores."""
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for TF-IDF summarization.") from exc

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(sentences)
    scores = matrix.sum(axis=1).A1
    top_indexes = sorted(scores.argsort()[-max_sentences:])
    return " ".join(sentences[index] for index in top_indexes)


def summarize_textrank(text, max_sentences=8):
    """Generate an extractive summary with TextRank over sentence similarities."""
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for TextRank summarization.") from exc

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(sentences)
    similarity = cosine_similarity(matrix)

    scores = _pagerank(similarity)
    top_indexes = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:max_sentences]
    ordered_indexes = sorted(top_indexes)
    return " ".join(sentences[index] for index in ordered_indexes)


def extract_keywords(text, limit=12):
    """Extract top keywords with TF-IDF, falling back to term frequency."""
    sentences = split_sentences(text)
    if not sentences:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=60)
        matrix = vectorizer.fit_transform(sentences)
        scores = matrix.sum(axis=0).A1
        names = vectorizer.get_feature_names_out()
        ranked = sorted(zip(names, scores), key=lambda item: item[1], reverse=True)
        return [keyword.title() for keyword, _score in ranked[:limit]]
    except Exception:
        words = re.findall(r"[A-Za-z][A-Za-z-]{3,}", text.lower())
        stopwords = {
            "about",
            "after",
            "also",
            "because",
            "been",
            "between",
            "from",
            "have",
            "into",
            "that",
            "their",
            "there",
            "these",
            "this",
            "were",
            "with",
            "would",
        }
        counts = Counter(word for word in words if word not in stopwords)
        return [word.title() for word, _count in counts.most_common(limit)]


def _pagerank(similarity_matrix, damping=0.85, max_iter=80, tolerance=1.0e-6):
    """Compute PageRank scores for a weighted sentence-similarity graph."""
    size = similarity_matrix.shape[0]
    ranks = [1.0 / size] * size

    weights = []
    for row_index in range(size):
        row = similarity_matrix[row_index].copy()
        row[row_index] = 0
        total = row.sum()
        if math.isclose(total, 0.0):
            weights.append([1.0 / size] * size)
        else:
            weights.append((row / total).tolist())

    for _ in range(max_iter):
        new_ranks = [(1.0 - damping) / size] * size
        for source_index in range(size):
            for target_index in range(size):
                new_ranks[target_index] += damping * ranks[source_index] * weights[source_index][target_index]

        delta = sum(abs(new_ranks[index] - ranks[index]) for index in range(size))
        ranks = new_ranks
        if delta < tolerance:
            break

    return ranks
