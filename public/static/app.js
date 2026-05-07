const chatInput = document.querySelector("#chat-input");
const chatSend = document.querySelector("#chat-send");
const chatForm = document.querySelector("#chat-form");
const chatBox = document.querySelector("#chat-box");
const chatState = document.querySelector("#chat-state");
const quickPrompts = document.querySelectorAll("[data-prompt]");

const sampleText = `Artificial intelligence tools are becoming part of everyday research, writing, and operations work. Teams use summarizers to reduce long documents into decisions, risks, and next steps. A useful summarizer should preserve the author's main argument, remove repeated detail, and make the result easy to scan. The strongest interfaces also show basic context, such as word counts and compression, so people can judge whether the output is complete enough for their task.`;

const form = document.querySelector("#summary-form");
const sourceText = document.querySelector("#source-text");
const sourceCount = document.querySelector("#source-count");
const sentenceCount = document.querySelector("#sentence-count");
const sentenceOutput = document.querySelector("#sentence-output");
const focusTerms = document.querySelector("#focus-terms");
const summarizeButton = document.querySelector("#summarize-button");
const sampleButton = document.querySelector("#sample-button");
const clearButton = document.querySelector("#clear-button");
const result = document.querySelector("#summary-result");
const summaryCount = document.querySelector("#summary-count");
const message = document.querySelector("#message");
const statusPill = document.querySelector("#status-pill");
const copyButton = document.querySelector("#copy-button");
const downloadButton = document.querySelector("#download-button");
const keyTerms = document.querySelector("#key-terms");
const fileInput = document.querySelector("#source-file");
const importFileButton = document.querySelector("#import-file-button");
const fileStatus = document.querySelector("#file-status");
const fileDropZone = document.querySelector("#file-drop-zone");

const cardCount = document.querySelector("#card-count");
const cardCountOutput = document.querySelector("#card-count-output");
const flashcardCount = document.querySelector("#flashcard-count");
const generateCardsButton = document.querySelector("#generate-cards-button");
const flashcard = document.querySelector("#flashcard");
const cardLabel = document.querySelector("#card-label");
const cardContent = document.querySelector("#card-content");
const cardHint = document.querySelector("#card-hint");
const prevCardButton = document.querySelector("#prev-card");
const nextCardButton = document.querySelector("#next-card");
const flipCardButton = document.querySelector("#flip-card");

const metrics = {
  sourceWords: document.querySelector("#metric-source-words"),
  summaryWords: document.querySelector("#metric-summary-words"),
  compression: document.querySelector("#metric-compression"),
  readingTime: document.querySelector("#metric-reading-time"),
};

let cards = [];
let activeCardIndex = 0;
let showingAnswer = false;
let pendingFile = null;

function countWords(text) {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

function formatWordCount(count) {
  return `${count.toLocaleString()} ${count === 1 ? "word" : "words"}`;
}

function setStatus(text, tone = "neutral") {
  statusPill.textContent = text;
  statusPill.dataset.tone = tone;
}

function setMessage(text, tone = "neutral") {
  message.textContent = text;
  message.dataset.tone = tone;
}

function setFileStatus(text, tone = "neutral") {
  fileStatus.textContent = text;
  fileStatus.dataset.tone = tone;
}

function updateInputCount() {
  sourceCount.textContent = formatWordCount(countWords(sourceText.value));
}

function updateSentenceOutput() {
  sentenceOutput.textContent = sentenceCount.value;
}

function updateCardCountOutput() {
  cardCountOutput.textContent = cardCount.value;
}

function setLoading(isLoading) {
  summarizeButton.disabled = isLoading;
  summarizeButton.textContent = isLoading ? "Summarizing..." : "Summarize";
  if (isLoading) {
    setStatus("Working", "working");
  }
}

function setCardsLoading(isLoading) {
  generateCardsButton.disabled = isLoading;
  generateCardsButton.textContent = isLoading ? "Generating..." : "Generate cards";
}

function setChatLoading(isLoading) {
  chatSend.disabled = isLoading;
  chatInput.disabled = isLoading;
  chatState.textContent = isLoading ? "Thinking" : "Context aware";
}

function setImportLoading(isLoading) {
  importFileButton.disabled = isLoading || !pendingFile;
  importFileButton.textContent = isLoading ? "Importing..." : "Import";
}

function setResult(summary, stats = {}, terms = []) {
  result.textContent = summary || "Summary appears here.";
  result.classList.toggle("empty", !summary);
  summaryCount.textContent = formatWordCount(countWords(summary || ""));
  copyButton.disabled = !summary;
  downloadButton.disabled = !summary;
  renderMetrics(stats);
  renderKeyTerms(terms);
}

function renderMetrics(stats) {
  metrics.sourceWords.textContent = (stats.source_words || 0).toLocaleString();
  metrics.summaryWords.textContent = (stats.summary_words || 0).toLocaleString();
  metrics.compression.textContent = `${stats.compression_percent || 0}%`;
  metrics.readingTime.textContent = `${stats.reading_time_minutes || 0} min`;
}

function renderKeyTerms(terms) {
  keyTerms.replaceChildren();
  terms.forEach((term) => {
    const chip = document.createElement("span");
    chip.textContent = term;
    keyTerms.appendChild(chip);
  });
}

function getSummaryText() {
  if (result.classList.contains("empty")) {
    return "";
  }
  return result.textContent.trim();
}

function getContextText() {
  return [sourceText.value.trim(), getSummaryText()].filter(Boolean).join("\n\n");
}

async function summarize(event) {
  event.preventDefault();
  const text = sourceText.value.trim();

  if (!text) {
    setMessage("Add source text first.", "error");
    setStatus("Needs text", "error");
    sourceText.focus();
    return;
  }

  setLoading(true);
  setMessage("");

  try {
    const response = await fetch("/summarize", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        sentences: sentenceCount.value,
        focus: focusTerms.value,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to summarize text.");
    }

    setResult(data.summary, data.stats, data.key_terms || []);
    setMessage("Summary ready.", "success");
    setStatus("Complete", "success");
  } catch (error) {
    setMessage(error.message, "error");
    setStatus("Error", "error");
  } finally {
    setLoading(false);
  }
}

async function copySummary() {
  const text = getSummaryText();
  if (!text) {
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const fallback = document.createElement("textarea");
    fallback.value = text;
    document.body.appendChild(fallback);
    fallback.select();
    document.execCommand("copy");
    fallback.remove();
  }

  setMessage("Copied.", "success");
}

function downloadSummary() {
  const text = getSummaryText();
  if (!text) {
    return;
  }

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "summary.txt";
  link.click();
  URL.revokeObjectURL(url);
}

function clearWorkspace() {
  sourceText.value = "";
  focusTerms.value = "";
  fileInput.value = "";
  pendingFile = null;
  cards = [];
  activeCardIndex = 0;
  showingAnswer = false;
  setResult("", {}, []);
  renderFlashcard();
  chatBox.replaceChildren();
  addChatMessage("ai", "Add text or import a file, then ask me about the actual content.");
  setMessage("");
  setFileStatus("No file selected");
  setStatus("Ready");
  setImportLoading(false);
  updateInputCount();
  sourceText.focus();
}

function selectFile(file) {
  if (!file) {
    return;
  }

  pendingFile = file;
  importFileButton.disabled = false;
  setFileStatus(file.name);
}

async function importFile(file = pendingFile) {
  if (!file) {
    return;
  }

  pendingFile = file;
  const payload = new FormData();
  payload.append("file", file);

  setImportLoading(true);
  setFileStatus("Reading file", "working");
  setStatus("Importing", "working");
  setMessage("");

  try {
    const response = await fetch("/extract-file", {
      method: "POST",
      body: payload,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not import file.");
    }

    sourceText.value = data.text;
    cards = [];
    activeCardIndex = 0;
    showingAnswer = false;
    setResult("", {}, []);
    renderFlashcard();
    chatBox.replaceChildren();
    addChatMessage("ai", "File imported. Ask me what it is about, or summarize it first.");
    updateInputCount();
    setFileStatus(`${data.filename} imported`, "success");
    setMessage(`Imported ${data.word_count.toLocaleString()} words.`, "success");
    setStatus("Ready", "success");
  } catch (error) {
    setFileStatus(error.message, "error");
    setMessage(error.message, "error");
    setStatus("Error", "error");
  } finally {
    setImportLoading(false);
  }
}

async function generateFlashcards() {
  const text = getContextText();
  if (!text) {
    setMessage("Add source text before generating cards.", "error");
    setStatus("Needs text", "error");
    sourceText.focus();
    return;
  }

  setCardsLoading(true);
  setMessage("");

  try {
    const response = await fetch("/flashcards", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        count: cardCount.value,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to generate flashcards.");
    }

    cards = data.cards || [];
    activeCardIndex = 0;
    showingAnswer = false;
    renderFlashcard();
    setMessage("Flashcards ready.", "success");
    setStatus("Study ready", "success");
  } catch (error) {
    setMessage(error.message, "error");
    setStatus("Error", "error");
  } finally {
    setCardsLoading(false);
  }
}

function renderFlashcard() {
  const hasCards = cards.length > 0;
  flashcard.classList.toggle("empty", !hasCards);
  flashcardCount.textContent = `${cards.length} ${cards.length === 1 ? "card" : "cards"}`;
  prevCardButton.disabled = !hasCards || cards.length === 1;
  nextCardButton.disabled = !hasCards || cards.length === 1;
  flipCardButton.disabled = !hasCards;
  flipCardButton.textContent = showingAnswer ? "Show question" : "Show answer";

  if (!hasCards) {
    cardLabel.textContent = "Question";
    cardContent.textContent = "Generate flashcards from your source text.";
    cardHint.textContent = "";
    return;
  }

  const card = cards[activeCardIndex];
  cardLabel.textContent = showingAnswer
    ? `Answer ${activeCardIndex + 1} of ${cards.length}`
    : `Question ${activeCardIndex + 1} of ${cards.length}`;
  cardContent.textContent = showingAnswer ? card.answer : card.question;
  cardHint.textContent = showingAnswer ? "" : card.hint;
}

function moveCard(direction) {
  if (!cards.length) {
    return;
  }

  activeCardIndex = (activeCardIndex + direction + cards.length) % cards.length;
  showingAnswer = false;
  renderFlashcard();
}

function flipCard() {
  if (!cards.length) {
    return;
  }

  showingAnswer = !showingAnswer;
  renderFlashcard();
}

function addChatMessage(author, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-message ${author}`;

  const label = document.createElement("strong");
  label.textContent = author === "user" ? "You" : "AI";

  const content = document.createElement("p");
  content.textContent = text;

  bubble.append(label, content);
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage(event) {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) {
    return;
  }

  addChatMessage("user", text);
  chatInput.value = "";
  setChatLoading(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        context: getContextText(),
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Error connecting to server.");
    }

    addChatMessage("ai", data.reply);
  } catch (error) {
    addChatMessage("ai", error.message);
  } finally {
    setChatLoading(false);
    chatInput.focus();
  }
}

sourceText.addEventListener("input", updateInputCount);
fileInput.addEventListener("change", () => {
  selectFile(fileInput.files[0]);
});
importFileButton.addEventListener("click", importFile);
fileDropZone.addEventListener("dragenter", (event) => {
  event.preventDefault();
  fileDropZone.classList.add("drag-over");
});
fileDropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
});
fileDropZone.addEventListener("dragleave", (event) => {
  if (!fileDropZone.contains(event.relatedTarget)) {
    fileDropZone.classList.remove("drag-over");
  }
});
fileDropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  fileDropZone.classList.remove("drag-over");
  const file = event.dataTransfer.files[0];
  selectFile(file);
  importFile(file);
});
sentenceCount.addEventListener("input", updateSentenceOutput);
cardCount.addEventListener("input", updateCardCountOutput);
form.addEventListener("submit", summarize);
copyButton.addEventListener("click", copySummary);
downloadButton.addEventListener("click", downloadSummary);
clearButton.addEventListener("click", clearWorkspace);
generateCardsButton.addEventListener("click", generateFlashcards);
prevCardButton.addEventListener("click", () => moveCard(-1));
nextCardButton.addEventListener("click", () => moveCard(1));
flipCardButton.addEventListener("click", flipCard);
flashcard.addEventListener("click", flipCard);
flashcard.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    flipCard();
  }
});

sampleButton.addEventListener("click", () => {
  sourceText.value = sampleText;
  updateInputCount();
  setMessage("");
  sourceText.focus();
});

chatForm.addEventListener("submit", sendMessage);
quickPrompts.forEach((button) => {
  button.addEventListener("click", () => {
    chatInput.value = button.dataset.prompt;
    chatInput.focus();
  });
});

updateInputCount();
updateSentenceOutput();
updateCardCountOutput();
renderFlashcard();
addChatMessage("ai", "Add text or import a file, then ask me about the actual content.");
