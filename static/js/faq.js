(function () {
  const input = document.getElementById("faq-search");
  const list = document.getElementById("faq-list");
  if (!input || !list) return;

  const items = Array.from(list.querySelectorAll(".faq-item"));

  input.addEventListener("input", function () {
    const keyword = input.value.trim().toLowerCase();

    items.forEach(function (item) {
      const question = (item.dataset.question || "").toLowerCase();
      const answer = (item.dataset.answer || "").toLowerCase();
      const category = (item.dataset.category || "").toLowerCase();

      const matched = !keyword || question.includes(keyword) || answer.includes(keyword) || category.includes(keyword);
      item.style.display = matched ? "block" : "none";
    });
  });
})();
