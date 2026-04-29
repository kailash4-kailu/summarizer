import re

from backend.extractive import extract_keywords, split_sentences


QUESTION_TEMPLATES = [
    "What is a key point about {keyword}?",
    "Why is {keyword} important in this document?",
    "What does the document say about {keyword}?",
    "How is {keyword} described?",
]


def generate_flashcards_for_documents(documents, summary, min_cards=5, max_cards=10):
    """Create per-document Q&A flashcards from source text and summary context."""
    all_cards = []
    summary_sentences = split_sentences(summary)

    for document in documents:
        sentences = split_sentences(document["text"])
        candidates = sentences if len(sentences) >= min_cards else sentences + summary_sentences
        keywords = extract_keywords(document["text"], limit=max_cards) or extract_keywords(summary, limit=max_cards)

        cards = []
        seen_answers = set()
        for index, sentence in enumerate(candidates):
            if len(cards) >= max_cards:
                break
            answer = compact_sentence(sentence)
            if not answer or answer.lower() in seen_answers:
                continue

            keyword = keywords[index % len(keywords)] if keywords else "the main topic"
            question = QUESTION_TEMPLATES[index % len(QUESTION_TEMPLATES)].format(keyword=keyword)
            cards.append(
                {
                    "question": question,
                    "answer": answer,
                    "source": document["filename"],
                }
            )
            seen_answers.add(answer.lower())

        while len(cards) < min_cards and summary_sentences:
            index = len(cards)
            sentence = summary_sentences[index % len(summary_sentences)]
            answer = compact_sentence(sentence)
            keyword = keywords[index % len(keywords)] if keywords else "the summary"
            cards.append(
                {
                    "question": f"What should you remember about {keyword}?",
                    "answer": answer,
                    "source": document["filename"],
                }
            )

        all_cards.extend(cards[:max_cards])

    return all_cards


def compact_sentence(sentence, limit=240):
    """Clean and shorten an answer for the back of a flashcard."""
    sentence = re.sub(r"\s+", " ", sentence).strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 3].rsplit(" ", 1)[0] + "..."
