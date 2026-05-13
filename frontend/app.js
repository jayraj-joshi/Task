/* ═══════════════════════════════════════
   ChunkSmith PageIndexer – App Logic
   ═══════════════════════════════════════ */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "https://task-q35t.onrender.com";

// ── DOM refs ──
const docList      = document.getElementById("doc-list");
const docEmpty     = document.getElementById("doc-empty");
const hero         = document.getElementById("hero");
const chatArea     = document.getElementById("chat-area");
const chatDocName  = document.getElementById("chat-doc-name");
const chatDocId    = document.getElementById("chat-doc-id");
const chatMessages = document.getElementById("chat-messages");
const queryForm    = document.getElementById("query-form");
const queryInput   = document.getElementById("query-input");
const sendBtn      = document.getElementById("send-btn");
const uploadArea   = document.getElementById("upload-area");
const pdfUpload    = document.getElementById("pdf-upload");
const uploadProg   = document.getElementById("upload-progress");
const progressFill = document.getElementById("progress-fill");
const progressLbl  = document.getElementById("progress-label");

let activeDocId = null;

// ══════════════════
//  Toast
// ══════════════════
function toast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ══════════════════
//  Fetch Documents
// ══════════════════
async function fetchDocuments() {
  try {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    const docs = await res.json();
    renderDocList(docs);
  } catch (err) {
    console.error(err);
    // Silently fail on initial load – API might not be running yet
  }
}

function renderDocList(docs) {
  docList.innerHTML = "";
  if (!docs.length) {
    docEmpty.classList.remove("hidden");
    return;
  }
  docEmpty.classList.add("hidden");

  docs.forEach((doc) => {
    const li = document.createElement("li");
    li.className = "doc-item" + (doc.id === activeDocId ? " active" : "");
    li.dataset.id = doc.id;

    const date = new Date(doc.created_at);
    const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

    li.innerHTML = `
      <span class="doc-item-icon">📄</span>
      <span class="doc-item-name">${escapeHtml(doc.filename)}</span>
      <span class="doc-item-date">${dateStr}</span>
    `;
    li.addEventListener("click", () => selectDocument(doc));
    docList.appendChild(li);
  });
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ══════════════════
//  Select Document
// ══════════════════
function selectDocument(doc) {
  activeDocId = doc.id;

  // Update sidebar active state
  document.querySelectorAll(".doc-item").forEach((el) => {
    el.classList.toggle("active", Number(el.dataset.id) === doc.id);
  });

  // Switch to chat view
  hero.classList.add("hidden");
  chatArea.classList.remove("hidden");
  chatDocName.textContent = doc.filename;
  chatDocId.textContent = `ID: ${doc.id}`;
  chatMessages.innerHTML = "";

  // Welcome message
  addMessage("assistant", `Document **${doc.filename}** is loaded. Ask me anything about it!`);
  queryInput.focus();
}

// ══════════════════
//  Upload
// ══════════════════
uploadArea.addEventListener("dragover", (e) => { e.preventDefault(); uploadArea.classList.add("drag-over"); });
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith(".pdf")) handleUpload(file);
  else toast("Please drop a PDF file", "error");
});

pdfUpload.addEventListener("change", () => {
  if (pdfUpload.files[0]) handleUpload(pdfUpload.files[0]);
});

async function handleUpload(file) {
  uploadProg.classList.remove("hidden");
  progressLbl.textContent = "Processing… this may take a minute";
  progressFill.style.animation = "";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/process`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }
    const data = await res.json();
    toast(data.message);
    await fetchDocuments();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    uploadProg.classList.add("hidden");
    pdfUpload.value = "";
  }
}

// ══════════════════
//  Query / Chat
// ══════════════════
queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = queryInput.value.trim();
  if (!query || !activeDocId) return;

  addMessage("user", query);
  queryInput.value = "";
  sendBtn.disabled = true;

  // Thinking indicator
  const thinkingEl = addThinking();

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: activeDocId, query }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Query failed");
    }
    const data = await res.json();
    thinkingEl.remove();
    addMessage("assistant", data.answer, data.selected_nodes);
  } catch (err) {
    thinkingEl.remove();
    addMessage("assistant", `⚠️ ${err.message}`);
  } finally {
    sendBtn.disabled = false;
    queryInput.focus();
  }
});

// ══════════════════
//  Message Helpers
// ══════════════════
function addMessage(role, text, nodes) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  let html = `<div class="message-bubble">${formatText(text)}</div>`;

  if (nodes && nodes.length) {
    html += `<div class="node-tags">${nodes.map((n) => `<span class="node-tag">${escapeHtml(n)}</span>`).join("")}</div>`;
  }

  wrapper.innerHTML = html;
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrapper;
}

function addThinking() {
  const el = document.createElement("div");
  el.className = "message assistant";
  el.innerHTML = `<div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div>&nbsp;Thinking…</div>`;
  chatMessages.appendChild(el);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return el;
}

function formatText(text) {
  // Minimal markdown-like formatting
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

// ══════════════════
//  Init
// ══════════════════
fetchDocuments();
