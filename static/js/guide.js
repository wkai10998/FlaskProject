(function () {
  const button = document.getElementById("toggle-complete");
  const label = document.getElementById("complete-label");
  const hint = document.getElementById("complete-hint");
  if (!button || !label || !hint) return;

  button.addEventListener("click", async function () {
    const api = button.dataset.api;
    if (!api) return;

    button.disabled = true;

    try {
      const response = await fetch(api, { method: "POST" });
      if (!response.ok) {
        throw new Error("request failed");
      }

      const payload = await response.json();
      const completed = Boolean(payload.completed);

      label.textContent = completed ? "已完成" : "标记为已完成";
      hint.textContent = "已完成步骤数：" + String(payload.completed_count || 0);

      button.classList.remove("bg-brand-600", "hover:bg-brand-700", "bg-emerald-600", "hover:bg-emerald-700");
      if (completed) {
        button.classList.add("bg-emerald-600", "hover:bg-emerald-700");
      } else {
        button.classList.add("bg-brand-600", "hover:bg-brand-700");
      }
    } catch (_error) {
      window.alert("状态更新失败，请稍后重试。");
    } finally {
      button.disabled = false;
    }
  });
})();
