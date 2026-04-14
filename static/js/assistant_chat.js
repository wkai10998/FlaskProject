(function () {
  const shell = document.querySelector("[data-assistant-shell]");
  const emptyState = document.querySelector("[data-assistant-empty-state]");
  const form = document.getElementById("assistant-chat-form");
  const input = document.getElementById("assistant-chat-input");
  const sendButton = document.getElementById("assistant-chat-send");
  const chatLog = document.getElementById("assistant-chat-log");
  const statusNode = document.getElementById("assistant-chat-status");
  const chips = Array.from(document.querySelectorAll("[data-question-chip]"));

  if (!shell || !form || !input || !sendButton || !chatLog || !statusNode) return;

  const endpoint = form.dataset.endpoint || "/assistant/message";
  const initialMessage = chatLog.dataset.initialMessage || "";
  let pending = false;
  let phaseTimer = null;
  let hasActivatedChat = shell.dataset.assistantStage === "chat";
  let hasRenderedGreeting = false;

  function safeLink(href) {
    if (typeof href !== "string") return "#";
    if (href.startsWith("/")) return href;
    return "#";
  }

  function activateChatMode() {
    if (hasActivatedChat) return;
    hasActivatedChat = true;
    shell.dataset.assistantStage = "chat";
    if (emptyState) {
      emptyState.setAttribute("aria-hidden", "true");
    }
  }

  function setStatus(text) {
    statusNode.textContent = text;
  }

  function setPending(isPending) {
    pending = isPending;
    input.disabled = isPending;
    sendButton.disabled = isPending;
    sendButton.classList.toggle("opacity-70", isPending);
    sendButton.classList.toggle("cursor-not-allowed", isPending);
  }

  function resizeInput() {
    input.style.height = "0px";
    input.style.height = Math.min(input.scrollHeight, 192) + "px";
  }

  function scrollToBottom() {
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function renderSources(parent, sources) {
    if (!Array.isArray(sources) || sources.length === 0) return;

    const title = document.createElement("p");
    title.className = "tocu-chat-bubble__meta-title";
    title.textContent = "引用来源";
    parent.appendChild(title);

    const list = document.createElement("ul");
    list.className = "tocu-chat-bubble__sources";

    sources.slice(0, 3).forEach((item) => {
      const source = item && typeof item.source === "string" ? item.source : "来源";
      const link = item && typeof item.link === "string" ? item.link : "#";

      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = safeLink(link);
      a.textContent = source;
      li.appendChild(a);
      list.appendChild(li);
    });

    parent.appendChild(list);
  }

  function appendMessage(role, text, meta) {
    const row = document.createElement("article");
    row.className = role === "user" ? "tocu-chat-message tocu-chat-message--user" : "tocu-chat-message tocu-chat-message--assistant";

    const bubble = document.createElement("div");
    if (role === "user") {
      bubble.className = "tocu-chat-bubble tocu-chat-bubble--user";
    } else {
      bubble.className = "tocu-chat-bubble tocu-chat-bubble--assistant";
    }

    const textNode = document.createElement("p");
    textNode.className = "tocu-chat-bubble__text";
    textNode.textContent = text;
    bubble.appendChild(textNode);

    if (role === "assistant" && meta && Array.isArray(meta.sources)) {
      renderSources(bubble, meta.sources);
    }

    if (role === "assistant" && meta && typeof meta.elapsedMs === "number") {
      const timing = document.createElement("p");
      timing.className = "tocu-chat-bubble__timing";
      timing.textContent = "响应耗时 " + (meta.elapsedMs / 1000).toFixed(2) + "s";
      bubble.appendChild(timing);
    }

    row.appendChild(bubble);
    chatLog.appendChild(row);
    scrollToBottom();
  }

  function ensureGreeting() {
    if (hasRenderedGreeting || !initialMessage) return;
    appendMessage("assistant", initialMessage);
    hasRenderedGreeting = true;
  }

  async function submitQuestion(question) {
    const normalized = (question || "").trim();
    if (pending || normalized.length < 2) {
      if (normalized.length > 0 && normalized.length < 2) {
        setStatus("问题太短，请至少输入 2 个字。");
      }
      return;
    }

    activateChatMode();
    ensureGreeting();
    appendMessage("user", normalized);
    input.value = "";
    resizeInput();
    setPending(true);
    setStatus("正在检索资料...");
    phaseTimer = window.setTimeout(function () {
      setStatus("正在生成回答...");
    }, 450);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: normalized }),
      });
      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error((data && data.error) || "当前服务繁忙，请稍后重试。");
      }

      appendMessage("assistant", data.answer || "暂未获得回答。", {
        sources: data.sources || [],
        elapsedMs: Number(data.elapsed_ms) || 0,
      });
      setStatus("已完成，你可以继续追问。");
    } catch (error) {
      appendMessage("assistant", "本次回答暂时失败：" + (error.message || "请稍后重试。"), {
        sources: [],
      });
      setStatus("本次请求未完成，请重试或换个问法。");
    } finally {
      if (phaseTimer !== null) {
        window.clearTimeout(phaseTimer);
        phaseTimer = null;
      }
      setPending(false);
      input.focus();
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    void submitQuestion(input.value);
  });

  input.addEventListener("input", function () {
    resizeInput();
  });

  input.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    void submitQuestion(input.value);
  });

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      const preset = chip.dataset.questionChip || "";
      input.value = preset;
      input.focus();
      void submitQuestion(preset);
    });
  });

  resizeInput();
  input.focus();
})();
