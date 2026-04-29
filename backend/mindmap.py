from backend.extractive import extract_keywords, split_sentences


def generate_mindmap(summary):
    """Build a hierarchical mind map from the summary."""
    sentences = split_sentences(summary)
    keywords = extract_keywords(summary, limit=9)
    root_label = summarize_label(sentences[0] if sentences else "Document Summary", 64)

    if not keywords:
        keywords = ["Main Idea", "Key Details", "Conclusion"]

    children = []
    for index, keyword in enumerate(keywords[:6]):
        related = [sentence for sentence in sentences if keyword.split()[0].lower() in sentence.lower()]
        if not related and sentences:
            related = [sentences[index % len(sentences)]]

        children.append(
            {
                "name": keyword,
                "children": [
                    {"name": summarize_label(sentence, 86)}
                    for sentence in related[:2]
                ],
            }
        )

    return {"name": root_label, "children": children}


def summarize_label(text, limit):
    """Shorten a label while keeping it readable in the visual tree."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rsplit(" ", 1)[0] + "..."
