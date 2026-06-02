let scope = "core";

const coreBtn = document.getElementById("coreBtn");
const fullBtn = document.getElementById("fullBtn");
const form = document.getElementById("askForm");
const question = document.getElementById("question");
const directAnswer = document.getElementById("directAnswer");
const modeNote = document.getElementById("modeNote");
const supportingPoints = document.getElementById("supportingPoints");
const caveats = document.getElementById("caveats");
const citationCount = document.getElementById("citationCount");
const citations = document.getElementById("citations");
const entries = document.getElementById("entries");
const entryDetail = document.getElementById("entryDetail");
const evidence = document.getElementById("evidence");

coreBtn.addEventListener("click", () => setScope("core"));
fullBtn.addEventListener("click", () => setScope("full"));

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    question.value = button.dataset.example;
    question.focus();
  });
});

function setScope(nextScope) {
  scope = nextScope;
  coreBtn.classList.toggle("active", scope === "core");
  fullBtn.classList.toggle("active", scope === "full");
  modeNote.textContent =
    scope === "core"
      ? "核心规则模式会优先给出可落桌的规则裁定。"
      : "全量模式会扩大到拓展资料，更适合百科探索。";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  setLoading();

  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: text, scope }),
  });

  if (!response.ok) {
    directAnswer.textContent = "请求失败，请检查后端服务。";
    return;
  }

  renderAnswer(await response.json());
});

function setLoading() {
  directAnswer.textContent = "正在检索规则证据...";
  supportingPoints.innerHTML = "";
  caveats.innerHTML = "";
  citations.innerHTML = '<div class="empty">检索中。</div>';
  entries.innerHTML = '<div class="empty">检索中。</div>';
  evidence.innerHTML = "";
  entryDetail.textContent = "选择一个来源或百科条目查看完整信息。";
  citationCount.textContent = "检索中";
}

function renderAnswer(data) {
  directAnswer.textContent = data.direct_answer || data.answer;
  renderList(supportingPoints, data.supporting_points || []);
  renderList(caveats, data.caveats || []);
  citationCount.textContent = `${data.citations.length} 个来源`;
  renderCitations(data.citations);
  renderEntries(data.related_entries);
  renderEvidence(data.evidence);
}

function renderList(container, items) {
  container.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderCitations(items) {
  citations.classList.toggle("empty", items.length === 0);
  citations.innerHTML = items.length
    ? items
        .map(
          (item, index) => `
          <article class="citation">
            <button class="link-card" type="button" data-entry-id="${escapeHtml(item.document_id)}">
              <div class="title">[${index + 1}] ${escapeHtml(item.label)}</div>
              <div class="meta">${escapeHtml(item.source_id)} · ${escapeHtml(item.passages.length)} 条支撑片段</div>
              <div class="passages">
                ${item.passages.map((passage) => `<div class="passage">${escapeHtml(passage.display_text)}</div>`).join("")}
              </div>
            </button>
          </article>
        `
        )
        .join("")
    : "没有可展示引用。";
}

function renderEntries(items) {
  entries.classList.toggle("empty", items.length === 0);
  entries.innerHTML = items.length
    ? items
        .map(
          (item) => `
          <article class="entry">
            <button class="link-card" type="button" data-entry-id="${escapeHtml(item.id)}">
              <div class="title">${escapeHtml(item.title_zh)}</div>
              <div class="meta">${escapeHtml(item.category)} / ${escapeHtml(item.source_id)} / ${escapeHtml(item.knowledge_domain)}</div>
              <div class="snippet">${escapeHtml(item.summary_text || "")}</div>
            </button>
          </article>
        `
        )
        .join("")
    : "没有相关条目。";
}

document.addEventListener("click", async (event) => {
  const card = event.target.closest("[data-entry-id]");
  if (!card) return;
  const id = card.dataset.entryId;
  entryDetail.textContent = "正在打开条目...";
  const response = await fetch(`/api/entries/${encodeURIComponent(id)}`);
  if (!response.ok) {
    entryDetail.textContent = "条目加载失败。";
    return;
  }
  renderEntryDetail(await response.json());
});

function renderEntryDetail(item) {
  entryDetail.classList.remove("empty");
  entryDetail.innerHTML = `
    <h3>${escapeHtml(item.title_zh)}</h3>
    <div class="meta">${escapeHtml(item.title_en || "")} · ${escapeHtml(item.citation)}</div>
    <div class="meta">${escapeHtml(item.category)} / ${escapeHtml(item.source_id)} / ${escapeHtml(item.knowledge_domain)}</div>
    <pre>${escapeHtml(item.body_text || item.summary_text || "")}</pre>
  `;
}

function renderEvidence(items) {
  evidence.innerHTML = items
    .map(
      (item) => `
      <article class="evidence">
        <div class="title">${escapeHtml(item.title)} · ${escapeHtml(item.chunk_type)}</div>
        <div class="meta">${escapeHtml(item.source)} / ${escapeHtml(item.chunk_level)} / ${escapeHtml(item.title_path.join(" / "))}</div>
        <div class="score-grid">
          <span>final ${item.score.final}</span>
          <span>dense ${item.score.dense}</span>
          <span>lexical ${item.score.lexical}</span>
          <span>alias ${item.score.alias}</span>
          <span>title ${item.score.title}</span>
          <span>structure ${item.score.structure}</span>
        </div>
        <div class="snippet">${escapeHtml(item.display_text)}</div>
        <div class="meta">${escapeHtml(item.score.reasons.join("；"))}</div>
      </article>
    `
    )
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
