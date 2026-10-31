/**
 * Empório da Música — Storefront & Floating Chat Widget Client Script
 */

// Generate or retrieve persistent session ID
function getSessionId() {
  let sid = localStorage.getItem("emporio_session_id");
  if (!sid) {
    sid = "session_" + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("emporio_session_id", sid);
  }
  return sid;
}

const SESSION_ID = getSessionId();
let allProducts = [];
let currentCategory = "";

// Format Brazilian Real Currency
function formatCurrency(val) {
  return Number(val).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ==========================================
// Product Catalog Ingestion & Rendering
// ==========================================

async function loadProducts(categoryId = null) {
  const countEl = document.getElementById("product-count");
  const gridEl = document.getElementById("products-grid");

  try {
    countEl.textContent = "Carregando catálogo...";
    const url = categoryId ? `/api/products?category_id=${categoryId}` : "/api/products";
    const res = await fetch(url);
    if (!res.ok) throw new Error("Erro ao carregar produtos");
    allProducts = await res.json();

    renderProducts(allProducts);
    countEl.textContent = `${allProducts.length} instrumentos encontrados`;
  } catch (err) {
    console.error("Erro na busca de produtos:", err);
    countEl.textContent = "Falha ao carregar instrumentos.";
    gridEl.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #64748b; padding: 40px;">
      Não foi possível carregar os produtos. Verifique se o servidor está ativo.
    </div>`;
  }
}

function renderProducts(products) {
  const gridEl = document.getElementById("products-grid");
  gridEl.innerHTML = "";

  if (products.length === 0) {
    gridEl.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #64748b; padding: 40px;">
      Nenhum instrumento musical encontrado para esta seleção.
    </div>`;
    return;
  }

  products.forEach((prod) => {
    const card = document.createElement("article");
    card.className = "product-card";

    // Build specs pills
    const specs = prod.specs || {};
    let specsHtml = "";
    if (specs.top) specsHtml += `<span class="spec-pill">Tampo: ${specs.top}</span>`;
    if (specs.strings) specsHtml += `<span class="spec-pill">Cordas: ${specs.strings}</span>`;
    if (specs.color) specsHtml += `<span class="spec-pill">${specs.color}</span>`;

    // Pricing logic
    const hasDiscount = prod.discount_percent && prod.discount_percent > 0;
    const originalPriceHtml = hasDiscount
      ? `<div class="original-price">${formatCurrency(prod.base_price)}</div>`
      : "";

    // Stock tag
    const isLowStock = prod.stock_quantity <= 5;
    const stockHtml = isLowStock
      ? `<div class="stock-tag low">⚠️ Apenas ${prod.stock_quantity} unidades em estoque!</div>`
      : `<div class="stock-tag">✓ Em estoque (${prod.stock_quantity} unid.)</div>`;

    card.innerHTML = `
      <div>
        <span class="product-category-badge">${prod.category}</span>
        <h4>${prod.name}</h4>
        <p class="product-description">${prod.description || ""}</p>
        <div class="product-specs">${specsHtml}</div>
      </div>
      <div>
        <div class="product-pricing">
          ${originalPriceHtml}
          <div class="main-price">${formatCurrency(prod.effective_price)}</div>
          <div class="pix-highlight">⚡ ${formatCurrency(prod.pix_price)} à vista no PIX (5% OFF)</div>
          <div class="installment-info">ou até 12x de ${formatCurrency(prod.installment_12x)} sem juros</div>
          ${stockHtml}
        </div>
        <button class="btn-card-ask" data-name="${prod.name}">
          💬 Consultar no Chat
        </button>
      </div>
    `;

    gridEl.appendChild(card);
  });

  // Attach click listeners to "Consultar no Chat" buttons
  document.querySelectorAll(".btn-card-ask").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prodName = btn.getAttribute("data-name");
      openChatWithQuery(`Quanto custa o ${prodName} e quais as condições de entrega?`);
    });
  });
}

// Filter products locally by search keyword and category
function filterProducts() {
  const searchTerm = document.getElementById("catalog-search").value.toLowerCase().trim();
  const filtered = allProducts.filter((p) => {
    const matchesCategory = !currentCategory || p.category.toLowerCase() === currentCategory.toLowerCase();
    const matchesSearch =
      !searchTerm ||
      p.name.toLowerCase().includes(searchTerm) ||
      (p.description && p.description.toLowerCase().includes(searchTerm));
    return matchesCategory && matchesSearch;
  });

  renderProducts(filtered);
  document.getElementById("product-count").textContent = `${filtered.length} instrumentos encontrados`;
}


// ==========================================
// Floating Chat Widget Controller
// ==========================================

const chatWindow = document.getElementById("chat-window");
const chatLauncher = document.getElementById("chat-launcher");
const chatCloseBtn = document.getElementById("chat-close-btn");
const chatResetBtn = document.getElementById("chat-reset-btn");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const typingIndicator = document.getElementById("typing-indicator");
const headerChatBtn = document.getElementById("header-chat-btn");

function toggleChat(show) {
  chatWindow.style.display = show ? "flex" : "none";
  if (show) {
    chatInput.focus();
  }
}

function openChatWithQuery(query) {
  toggleChat(true);
  chatInput.value = query;
  sendMessage(query);
}

// Format markdown helper
function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\\n/g, "\n")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

// Append a message to the chat feed
function appendMessage(text, isAgent = false) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${isAgent ? "agent-message" : "user-message"}`;
  msgDiv.innerHTML = `<div class="message-content">${formatMarkdown(text)}</div>`;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msgDiv;
}

// Send message to FastAPI endpoint with streaming & JSON fallback
async function sendMessage(messageText) {
  const text = messageText.trim();
  if (!text) return;

  chatInput.value = "";
  appendMessage(text, false);
  typingIndicator.style.display = "flex";
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: SESSION_ID,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`Erro na API: ${response.status}`);
    }

    const contentType = response.headers.get("content-type") || "";

    // If server returned regular JSON
    if (contentType.includes("application/json")) {
      const data = await response.json();
      typingIndicator.style.display = "none";
      appendMessage(data.response || "Sem resposta.", true);
      return;
    }

    // Process SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let agentMsgEl = null;
    let accumulatedText = "";
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Retain incomplete line

      for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) continue;

        // Support lines starting with "data:"
        if (line.startsWith("data:")) {
          const jsonStr = line.replace(/^(data:\s*)+/, "").trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);
            if (data.chunk) {
              typingIndicator.style.display = "none";
              accumulatedText += data.chunk;
              if (!agentMsgEl) {
                agentMsgEl = appendMessage(accumulatedText, true);
              } else {
                agentMsgEl.querySelector(".message-content").innerHTML = formatMarkdown(accumulatedText);
              }
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
          } catch (e) {
            // Incomplete JSON token - continue
          }
        }
      }
    }

    // Fallback if streaming ended without rendering text
    if (!agentMsgEl) {
      if (accumulatedText.trim()) {
        appendMessage(accumulatedText, true);
      } else {
        // Fallback fetch non-streamed
        const fbRes = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, session_id: SESSION_ID, stream: false }),
        });
        if (fbRes.ok) {
          const fbData = await fbRes.json();
          appendMessage(fbData.response, true);
        }
      }
    }
  } catch (err) {
    console.error("Chat error:", err);
    appendMessage("Desculpe, ocorreu uma instabilidade momentânea na conexão. Por favor, tente novamente.", true);
  } finally {
    typingIndicator.style.display = "none";
  }
}


// ==========================================
// Event Listeners Initialization
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  // Load products
  loadProducts();

  // Category filter pills
  const pills = document.querySelectorAll("#category-filters .pill");
  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category");
      filterProducts();
    });
  });

  // Search input live filtering
  document.getElementById("catalog-search").addEventListener("input", filterProducts);
  document.getElementById("search-btn").addEventListener("click", filterProducts);

  // Chat launcher events
  chatLauncher.addEventListener("click", () => toggleChat(true));
  headerChatBtn.addEventListener("click", () => toggleChat(true));
  chatCloseBtn.addEventListener("click", () => toggleChat(false));

  // Chat submit form
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(chatInput.value);
  });

  // Prompt chips
  document.querySelectorAll(".quick-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const msg = chip.getAttribute("data-msg");
      openChatWithQuery(msg);
    });
  });

  // Reset session
  chatResetBtn.addEventListener("click", async () => {
    if (confirm("Deseja reiniciar a conversa com o consultor?")) {
      await fetch("/api/session/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID }),
      });
      chatMessages.innerHTML = `
        <div class="message agent-message">
          <div class="message-content">
            Conversa reiniciada! Como posso te ajudar na escolha do seu próximo instrumento musical?
          </div>
        </div>
      `;
    }
  });
});
