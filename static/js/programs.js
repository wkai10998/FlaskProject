(function () {
  const input = document.getElementById("program-search");
  const list = document.getElementById("program-list");
  if (!input || !list) return;

  const items = Array.from(list.querySelectorAll(".program-item"));

  input.addEventListener("input", function () {
    const keyword = input.value.trim().toLowerCase();

    items.forEach(function (item) {
      const name = (item.dataset.name || "").toLowerCase();
      const school = (item.dataset.school || "").toLowerCase();
      const focus = (item.dataset.focus || "").toLowerCase();

      const matched = !keyword || name.includes(keyword) || school.includes(keyword) || focus.includes(keyword);
      item.style.display = matched ? "block" : "none";
    });
  });
})();
