(function () {
  const input = document.getElementById("program-search");
  const collegeFilter = document.getElementById("program-college-filter");
  const list = document.getElementById("program-list");
  const clearBtn = document.getElementById("program-search-clear");
  const searchBtn = document.getElementById("program-search-btn");
  if (!input || !list || !collegeFilter) return;

  const items = Array.from(list.querySelectorAll(".program-item"));

  function applyFilters() {
    const keyword = input.value.trim().toLowerCase();
    const selectedCollege = collegeFilter.value;

    items.forEach(function (item) {
      const name = (item.dataset.name || "").toLowerCase();
      const nameZh = (item.dataset.nameZh || "").toLowerCase();
      const nameEn = (item.dataset.nameEn || "").toLowerCase();
      const school = (item.dataset.school || "").toLowerCase();
      const college = item.dataset.college || "";
      const focus = (item.dataset.focus || "").toLowerCase();

      const keywordMatched =
        !keyword ||
        name.includes(keyword) ||
        nameZh.includes(keyword) ||
        nameEn.includes(keyword) ||
        school.includes(keyword) ||
        focus.includes(keyword);
      const collegeMatched = selectedCollege === "全部" || college === selectedCollege;
      const matched = keywordMatched && collegeMatched;

      item.style.display = matched ? "" : "none";
    });
  }

  // 清除按钮逻辑
  if (clearBtn) {
    function toggleClearBtn() {
      clearBtn.style.display = input.value ? "flex" : "none";
    }
    input.addEventListener("input", toggleClearBtn);
    toggleClearBtn();
    clearBtn.addEventListener("click", function () {
      input.value = "";
      input.focus();
      applyFilters();
      toggleClearBtn();
    });
  }

  // 搜索按钮逻辑
  if (searchBtn) {
    searchBtn.addEventListener("click", function () {
      applyFilters();
      input.focus();
    });
  }

  input.addEventListener("input", applyFilters);
  collegeFilter.addEventListener("change", applyFilters);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      applyFilters();
    }
  });
  applyFilters();
})();
