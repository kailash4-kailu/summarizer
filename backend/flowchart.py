import re

from backend.extractive import split_sentences


def generate_flowchart(summary):
    """Convert summary sentences into Mermaid flowchart syntax."""
    sentences = split_sentences(summary)[:7]
    if not sentences:
        sentences = ["Uploaded documents", "Generated summary"]

    lines = ["flowchart TD", '  A["Uploaded Documents"]', '  B["Combined Text"]', '  C["Generated Summary"]']
    lines.extend(["  A --> B", "  B --> C"])

    previous = "C"
    for index, sentence in enumerate(sentences, start=1):
        node_id = f"S{index}"
        label = mermaid_label(sentence)
        lines.append(f'  {previous} --> {node_id}["{label}"]')
        previous = node_id

    return "\n".join(lines)


def mermaid_label(text, max_length=82):
    """Sanitize and shorten text for Mermaid node labels."""
    label = re.sub(r"[\[\]{}<>|`]", "", text)
    label = label.replace('"', "'")
    label = re.sub(r"\s+", " ", label).strip()
    if len(label) > max_length:
        label = label[: max_length - 3].rsplit(" ", 1)[0] + "..."
    return label
