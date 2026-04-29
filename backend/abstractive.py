import os
import re
from functools import lru_cache


MODEL_MAP = {
    "bart": "sshleifer/distilbart-cnn-12-6",
    "t5": "t5-small",
}


def generate_abstractive_summary(text, model_choice="bart", max_words=280):
    """Summarize long document text with a lazy-loaded HuggingFace model."""
    model_key = model_choice.lower()
    model_name = os.getenv("HF_SUMMARIZATION_MODEL", MODEL_MAP.get(model_key, MODEL_MAP["bart"]))
    summarizer = _load_summarizer(model_name)

    chunk_size = 430 if "t5" in model_name.lower() else 820
    chunks = chunk_by_words(text, chunk_size=chunk_size, overlap=80)
    if not chunks:
        return ""

    partial_summaries = []
    for chunk in chunks:
        input_text = f"summarize: {chunk}" if "t5" in model_name.lower() else chunk
        max_length = 160 if len(chunk.split()) > 350 else 100
        min_length = 35 if len(chunk.split()) > 120 else 15
        result = summarizer(
            input_text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
            truncation=True,
        )
        partial_summaries.append(result[0]["summary_text"].strip())

    combined = " ".join(partial_summaries)
    if len(combined.split()) <= max_words or len(partial_summaries) == 1:
        return combined

    second_pass_input = f"summarize: {combined}" if "t5" in model_name.lower() else combined
    final = summarizer(
        second_pass_input,
        max_length=min(220, max_words),
        min_length=60,
        do_sample=False,
        truncation=True,
    )
    return final[0]["summary_text"].strip()


def chunk_by_words(text, chunk_size=800, overlap=80):
    """Split text into overlapping word chunks that fit transformer limits."""
    words = re.findall(r"\S+", text)
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks


@lru_cache(maxsize=2)
def _load_summarizer(model_name):
    """Load and cache the HuggingFace summarization pipeline."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Transformers is required for abstractive summarization. Install requirements.txt first."
        ) from exc

    try:
        return pipeline("summarization", model=model_name, tokenizer=model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load HuggingFace model '{model_name}'. Check your internet/model cache and try again."
        ) from exc
