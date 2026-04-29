import re
from collections import Counter


def calculate_metrics(source_text, summary, processing_time):
    """Calculate compression and source-overlap ROUGE metrics for the summary."""
    source_words = tokenize(source_text)
    summary_words = tokenize(summary)
    source_count = len(source_words)
    summary_count = len(summary_words)

    ratio = round(summary_count / source_count, 4) if source_count else 0.0
    reduction = round((1.0 - ratio) * 100, 2) if source_count else 0.0

    return {
        "source_words": source_count,
        "summary_words": summary_count,
        "compression_ratio": ratio,
        "reduction_percent": reduction,
        "processing_time_seconds": round(processing_time, 2),
        "rouge": {
            "rouge_1": rouge_n(source_words, summary_words, 1),
            "rouge_2": rouge_n(source_words, summary_words, 2),
            "rouge_l": rouge_l(source_words, summary_words),
        },
    }


def tokenize(text):
    """Normalize text into lowercase word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def rouge_n(reference_tokens, candidate_tokens, n):
    """Compute ROUGE-N precision, recall, and F1 scores."""
    reference = ngrams(reference_tokens, n)
    candidate = ngrams(candidate_tokens, n)
    if not reference or not candidate:
        return score_payload(0, 0, 0)

    overlap = sum((reference & candidate).values())
    precision = overlap / sum(candidate.values())
    recall = overlap / sum(reference.values())
    f1 = harmonic_mean(precision, recall)
    return score_payload(precision, recall, f1)


def rouge_l(reference_tokens, candidate_tokens):
    """Compute ROUGE-L using longest common subsequence F1."""
    if not reference_tokens or not candidate_tokens:
        return score_payload(0, 0, 0)

    lcs = longest_common_subsequence_length(reference_tokens, candidate_tokens)
    precision = lcs / len(candidate_tokens)
    recall = lcs / len(reference_tokens)
    f1 = harmonic_mean(precision, recall)
    return score_payload(precision, recall, f1)


def ngrams(tokens, n):
    """Return n-gram counts for a token sequence."""
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1))


def longest_common_subsequence_length(left, right):
    """Calculate LCS length with a memory-efficient dynamic program."""
    previous = [0] * (len(right) + 1)
    for left_token in left:
        current = [0]
        for index, right_token in enumerate(right, start=1):
            if left_token == right_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def harmonic_mean(precision, recall):
    """Return F1 from precision and recall."""
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_payload(precision, recall, f1):
    """Round metric values for API responses."""
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
