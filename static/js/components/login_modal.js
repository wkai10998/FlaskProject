(function () {
  const modal = document.getElementById("login-modal");
  if (!modal) return;

  const tabButtons = Array.from(modal.querySelectorAll("[data-auth-tab]"));
  const tabPanels = Array.from(modal.querySelectorAll("[data-auth-panel]"));
  const openTriggers = Array.from(document.querySelectorAll("[data-open-login]"));
  const closeTriggers = Array.from(modal.querySelectorAll("[data-close-login]"));

  function setTab(tabName) {
    const targetTab = tabName === "register" ? "register" : "login";

    tabButtons.forEach(function (button) {
      const isActive = button.dataset.authTab === targetTab;
      button.classList.toggle("bg-amber-700", isActive);
      button.classList.toggle("text-white", isActive);
      button.classList.toggle("shadow-sm", isActive);
      button.classList.toggle("text-gray-500", !isActive);
    });

    tabPanels.forEach(function (panel) {
      panel.classList.toggle("hidden", panel.dataset.authPanel !== targetTab);
    });
  }

  function openModal(tabName) {
    setTab(tabName);
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.body.classList.add("overflow-hidden");
  }

  function closeModal() {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    document.body.classList.remove("overflow-hidden");
  }

  tabButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setTab(button.dataset.authTab);
    });
  });

  openTriggers.forEach(function (trigger) {
    trigger.addEventListener("click", function (event) {
      event.preventDefault();
      openModal(trigger.dataset.authTab || "login");
    });
  });

  closeTriggers.forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      closeModal();
    });
  });

  modal.addEventListener("click", function (event) {
    if (event.target === modal) {
      closeModal();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.classList.contains("hidden")) {
      closeModal();
    }
  });

  if (modal.dataset.autoOpen === "1") {
    openModal(modal.dataset.autoTab || "login");
  } else {
    setTab("login");
  }

  window.openLoginModal = openModal;

  // 密码可见性切换函数
  window.togglePasswordVisibility = function(button) {
    const input = button.previousElementSibling;
    const icon = button.querySelector('svg');
    if (input.type === 'password') {
      input.type = 'text';
      icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>';
    } else {
      input.type = 'password';
      icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>';
    }
  };
})();
