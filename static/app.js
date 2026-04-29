const state = {
  sessionId: null,
  lastMindmap: null,
};

const uploadForm = document.querySelector("#uploadForm");
const documentsInput = document.querySelector("#documents");
const fileList = document.querySelector("#fileList");
const errorBox = document.querySelector("#errorBox");
const summaryText = document.querySelector("#summaryText");
const metricsGrid = document.querySelector("#metricsGrid");
const loadingOverlay = document.querySelector("#loadingOverlay");
const downloadSummary = document.querySelector("#downloadSummary");
const flowchartVisual = document.querySelector("#flowchartVisual");
const flowchartCode = document.querySelector("#flowchartCode");
const flashcardsGrid = document.querySelector("#flashcardsGrid");
const chatMessages = document.querySelector("#chatMessages");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");

if (window.mermaid) {
  mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "loose" });
}

documentsInput.addEventListener("change", () => {
  const files = Array.from(documentsInput.files);
  fileList.innerHTML = files.map((file) => `<div class="file-chip">${escapeHtml(file.name)}</div>`).join("");
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const formData = new FormData(uploadForm);
  if (!documentsInput.files.length) {
    showError("Upload at least one PDF or text file.");
    return;
  }

  setLoading(true);
  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Document processing failed.");
    }
    renderResults(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.tab}`).classList.add("active");
    if (button.dataset.tab === "mindmap" && state.lastMindmap) {
      renderMindmap(state.lastMindmap);
    }
  });
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const message = chatInput.value.trim();
  if (!message) return;
  if (!state.sessionId) {
    showError("Process documents before starting a chat.");
    return;
  }

  addChatBubble(message, "user");
  chatInput.value = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, message }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Chat request failed.");
    }
    const sourceLine = data.sources?.length ? `\n\nSources: ${data.sources.join(", ")}` : "";
    addChatBubble(`${data.answer}${sourceLine}`, "assistant");
  } catch (error) {
    showError(error.message);
  }
});

function renderResults(data) {
  state.sessionId = data.session_id;
  state.lastMindmap = data.mindmap;

  summaryText.classList.remove("empty-state");
  summaryText.textContent = data.summary || "No summary generated.";
  renderMetrics(data.metrics);
  renderFlowchart(data.flowchart);
  renderMindmap(data.mindmap);
  renderFlashcards(data.flashcards || []);
  resetChat();

  downloadSummary.href = `/api/download-summary/${data.session_id}`;
  downloadSummary.classList.remove("disabled");
  downloadSummary.removeAttribute("aria-disabled");

  if (data.warnings?.length) {
    showError(data.warnings.join(" "));
  }
}

function renderMetrics(metrics) {
  const rouge = metrics.rouge || {};
  const cards = [
    ["Compression", `${Math.round((metrics.compression_ratio || 0) * 100)}%`],
    ["Reduction", `${metrics.reduction_percent || 0}%`],
    ["Processing", `${metrics.processing_time_seconds || 0}s`],
    ["Source Words", `${metrics.source_words || 0}`],
    ["ROUGE-1 F1", formatMetric(rouge.rouge_1?.f1)],
    ["ROUGE-2 F1", formatMetric(rouge.rouge_2?.f1)],
    ["ROUGE-L F1", formatMetric(rouge.rouge_l?.f1)],
    ["Summary Words", `${metrics.summary_words || 0}`],
  ];

  metricsGrid.innerHTML = cards
    .map(([label, value]) => `<article class="metric-card"><span>${label}</span><strong>${value}</strong></article>`)
    .join("");
}

async function renderFlowchart(code) {
  flowchartCode.textContent = code || "";
  flowchartVisual.innerHTML = "";

  if (!window.mermaid || !code) {
    flowchartVisual.textContent = "Flowchart renderer is unavailable.";
    return;
  }

  try {
    const graphId = `flowchart-${Date.now()}`;
    const { svg } = await mermaid.render(graphId, code);
    flowchartVisual.innerHTML = svg;
  } catch (error) {
    flowchartVisual.textContent = "Could not render Mermaid flowchart. The code is shown below.";
  }
}

function renderMindmap(data) {
  const container = document.querySelector("#mindmapVisual");
  container.innerHTML = "";
  if (!window.d3 || !data) {
    container.textContent = "Mind map renderer is unavailable.";
    return;
  }

  const width = Math.max(container.clientWidth || 900, 900);
  const height = 460;
  const root = d3.hierarchy(data);
  const tree = d3.tree().size([height - 70, width - 240]);
  tree(root);

  const svg = d3
    .select(container)
    .append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("role", "img");

  const group = svg.append("g").attr("transform", "translate(120,35)");

  group
    .selectAll("path")
    .data(root.links())
    .join("path")
    .attr("fill", "none")
    .attr("stroke", "#b8c8c3")
    .attr("stroke-width", 1.5)
    .attr(
      "d",
      d3
        .linkHorizontal()
        .x((node) => node.y)
        .y((node) => node.x),
    );

  const node = group
    .selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("transform", (item) => `translate(${item.y},${item.x})`);

  node.append("circle").attr("r", 6).attr("fill", (item) => (item.depth === 0 ? "#0f766e" : "#27548a"));

  node
    .append("text")
    .attr("dy", "0.32em")
    .attr("x", (item) => (item.children ? -12 : 12))
    .attr("text-anchor", (item) => (item.children ? "end" : "start"))
    .attr("font-size", 13)
    .attr("font-weight", (item) => (item.depth <= 1 ? 800 : 500))
    .attr("fill", "#17201c")
    .text((item) => item.data.name);
}

function renderFlashcards(cards) {
  if (!cards.length) {
    flashcardsGrid.innerHTML = `<div class="empty-state">No flashcards generated.</div>`;
    return;
  }

  flashcardsGrid.innerHTML = cards
    .map(
      (card, index) => `
        <article class="flashcard" tabindex="0" data-card="${index}">
          <div class="flashcard-inner">
            <div class="flashcard-face flashcard-front">
              <strong>${escapeHtml(card.question)}</strong>
              <span class="flashcard-source">${escapeHtml(card.source)}</span>
            </div>
            <div class="flashcard-face flashcard-back">
              <span>${escapeHtml(card.answer)}</span>
              <span class="flashcard-source">${escapeHtml(card.source)}</span>
            </div>
          </div>
        </article>
      `,
    )
    .join("");

  document.querySelectorAll(".flashcard").forEach((card) => {
    card.addEventListener("click", () => card.classList.toggle("flipped"));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        card.classList.toggle("flipped");
      }
    });
  });
}

function resetChat() {
  chatMessages.innerHTML = "";
  addChatBubble("Documents are ready. Ask a question grounded in the uploaded content.", "assistant");
}

function addChatBubble(message, role) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = message;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMetric(value) {
  if (typeof value !== "number") return "0.00";
  return value.toFixed(2);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.add("visible");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.remove("visible");
}

function setLoading(isLoading) {
  loadingOverlay.classList.toggle("visible", isLoading);
  loadingOverlay.setAttribute("aria-hidden", String(!isLoading));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
