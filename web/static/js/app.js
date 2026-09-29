/**
 * Confere Placa Web - Frontend Application Logic
 */

// Application State
const state = {
  user: null,
  activeFilter: "all",
  searchQuery: "",
  searchDebounceTimer: null,
  addTempPresetHours: 24,
  editTempPresetHours: 24,
  deleteTargetPlate: null,
  fontSize: localStorage.getItem("confere_placa_font_size") || "16",
};

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", () => {
  applyFontSize(state.fontSize);
  setupEventListeners();
  checkAuthAndInitialize();
});

function applyFontSize(size) {
  state.fontSize = String(size);
  document.documentElement.style.setProperty("--app-font-size", `${size}px`);
  localStorage.setItem("confere_placa_font_size", String(size));

  document.querySelectorAll(".font-size-option").forEach((opt) => {
    if (opt.dataset.size === String(size)) {
      opt.classList.add("active");
    } else {
      opt.classList.remove("active");
    }
  });
}

async function checkAuthAndInitialize() {
  try {
    const res = await apiFetch("/api/auth/me");
    if (res.ok && res.user) {
      setUser(res.user);
      initializeApp();
    } else {
      openLoginModal();
    }
  } catch (err) {
    openLoginModal();
  }
}

function initializeApp() {
  loadConfigStats();
  loadPlates();
  loadHistory();
  if (state.user && state.user.role === "admin") {
    loadUsers();
  }
}

// ==================== AUTH & SESSION ====================
function setUser(user) {
  state.user = user;
  const nameEl = document.getElementById("user-name-display");
  const roleEl = document.getElementById("user-role-badge");
  const avatarEl = document.getElementById("user-avatar-initial");

  if (nameEl) nameEl.textContent = user.name || user.username;
  if (avatarEl) avatarEl.textContent = (user.name || user.username).charAt(0).toUpperCase();
  if (roleEl) {
    roleEl.textContent = user.role.toUpperCase();
    if (user.role === "admin") {
      roleEl.classList.add("admin");
    } else {
      roleEl.classList.remove("admin");
    }
  }

  // Adjust role visibility
  const adminElements = document.querySelectorAll(".admin-only");
  adminElements.forEach((el) => {
    if (user.role === "admin") {
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  });
}

function openLoginModal() {
  const modal = document.getElementById("modal-login");
  const alertBox = document.getElementById("login-alert");
  if (alertBox) alertBox.classList.add("hidden");
  if (modal) {
    if (!modal.open) modal.showModal();
    document.getElementById("login-username")?.focus();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");
  const alertBox = document.getElementById("login-alert");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      if (alertBox) {
        alertBox.textContent = data.detail || "Erro ao realizar login.";
        alertBox.classList.remove("hidden");
      }
      return;
    }

    closeModal("modal-login");
    setUser(data.user);
    initializeApp();
    showAlert(`Bem-vindo, ${data.user.name || data.user.username}!`, "success");
  } catch (err) {
    if (alertBox) {
      alertBox.textContent = "Falha na conexão com o servidor.";
      alertBox.classList.remove("hidden");
    }
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (e) {}
  state.user = null;
  openLoginModal();
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll(".nav-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.tab;
      document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(targetId)?.classList.add("active");

      // Auto-focus on search tab
      if (targetId === "tab-search") {
        document.getElementById("search-input")?.focus();
        loadPlates();
      } else if (targetId === "tab-config") {
        loadConfigStats();
      } else if (targetId === "tab-users") {
        loadUsers();
      }
    });
  });

  // Search Input & Debounce
  const searchInput = document.getElementById("search-input");
  const btnClear = document.getElementById("btn-search-clear");

  searchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    if (state.searchQuery.trim().length > 0) {
      btnClear.classList.remove("hidden");
    } else {
      btnClear.classList.add("hidden");
    }

    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(() => {
      loadPlates();
    }, 300);
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      clearTimeout(state.searchDebounceTimer);
      loadPlates();
    }
  });

  btnClear.addEventListener("click", () => {
    searchInput.value = "";
    state.searchQuery = "";
    btnClear.classList.add("hidden");
    searchInput.focus();
    loadPlates();
  });

  document.getElementById("chk-ignore-case")?.addEventListener("change", () => {
    loadPlates();
  });

  document.getElementById("btn-refresh-search")?.addEventListener("click", () => {
    loadPlates();
    loadConfigStats();
  });

  // Filter Chips
  document.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.activeFilter = chip.dataset.filter;
      loadPlates();
    });
  });

  // History Clear
  document.getElementById("btn-clear-history")?.addEventListener("click", async () => {
    if (confirm("Deseja realmente limpar todo o histórico recente de buscas?")) {
      await apiFetch("/api/plates/history", { method: "DELETE" });
      loadHistory();
    }
  });

  // Add Plate Form
  const formAdd = document.getElementById("form-add-plate");
  const addStatusSelect = document.getElementById("add-status");
  const addPlacaInput = document.getElementById("add-placa");

  addPlacaInput?.addEventListener("input", (e) => {
    e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  });

  addStatusSelect?.addEventListener("change", (e) => {
    const tempBox = document.getElementById("add-temp-box");
    if (e.target.value === "autorizado_temp") {
      tempBox.classList.remove("hidden");
    } else {
      tempBox.classList.add("hidden");
    }
  });

  document.querySelectorAll(".btn-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-preset").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.addTempPresetHours = parseInt(btn.dataset.hours, 10);
      document.getElementById("add-expires-at").value = "";
    });
  });

  formAdd?.addEventListener("submit", handleAddPlate);
  document.getElementById("btn-add-clear")?.addEventListener("click", () => {
    formAdd.reset();
    document.getElementById("add-temp-box")?.classList.add("hidden");
  });

  // Edit Plate Form
  const editStatusSelect = document.getElementById("edit-status");
  editStatusSelect?.addEventListener("change", (e) => {
    const tempBox = document.getElementById("edit-temp-box");
    if (e.target.value === "autorizado_temp") {
      tempBox.classList.remove("hidden");
    } else {
      tempBox.classList.add("hidden");
    }
  });

  document.querySelectorAll(".btn-preset-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-preset-edit").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const hours = parseInt(btn.dataset.hours, 10);
      state.editTempPresetHours = hours;
      // Pre-fill datetime-local with now + hours
      const targetDate = new Date(Date.now() + hours * 3600 * 1000);
      document.getElementById("edit-expires-at").value = formatForDateTimeInput(targetDate);
    });
  });

  document.getElementById("form-edit-plate")?.addEventListener("submit", handleEditPlate);

  // Delete Plate Confirmation
  document.getElementById("btn-confirm-delete")?.addEventListener("click", handleDeletePlateConfirm);

  // User Management
  document.getElementById("btn-open-new-user-modal")?.addEventListener("click", () => {
    openUserModal();
  });
  document.getElementById("form-user")?.addEventListener("submit", handleSaveUser);

  // Change Password
  document.getElementById("btn-change-password")?.addEventListener("click", () => {
    document.getElementById("form-change-password").reset();
    document.getElementById("change-pwd-alert").classList.add("hidden");
    openModal("modal-change-password");
  });
  document.getElementById("form-change-password")?.addEventListener("submit", handleChangePassword);

  // CSV Configuration Forms
  document.getElementById("form-csv-path")?.addEventListener("submit", handleSetCsvPath);
  document.getElementById("form-csv-upload")?.addEventListener("submit", handleUploadCsv);

  // Font Size Accessibility Controls
  document.querySelectorAll(".font-size-option").forEach((opt) => {
    opt.addEventListener("click", () => {
      applyFontSize(opt.dataset.size);
    });
  });

  document.getElementById("btn-reset-font-size")?.addEventListener("click", () => {
    applyFontSize("16");
    showAlert("Tamanho da fonte restaurado para 16px (padrão).", "success");
  });

  // Login & Logout
  document.getElementById("form-login")?.addEventListener("submit", handleLogin);
  document.getElementById("btn-logout")?.addEventListener("click", handleLogout);
}

// ==================== PLATES SEARCH & RENDER ====================
async function loadPlates() {
  const query = state.searchQuery.trim();
  const ignoreCase = document.getElementById("chk-ignore-case")?.checked ?? true;
  let authorizedOnly = false;
  let tempFilter = null;

  switch (state.activeFilter) {
    case "authorized":
      authorizedOnly = true;
      break;
    case "temp_all":
      tempFilter = "all";
      break;
    case "temp_active":
      tempFilter = "active";
      break;
    case "temp_expired":
      tempFilter = "expired";
      break;
  }

  const params = new URLSearchParams();
  if (query) params.set("q", query);
  params.set("ignore_case", ignoreCase);
  if (authorizedOnly) params.set("authorized_only", "true");
  if (tempFilter) params.set("temp_filter", tempFilter);

  try {
    const res = await apiFetch(`/api/plates?${params.toString()}`);
    if (res.ok) {
      renderPlates(res.results);
      document.getElementById("results-count").textContent = `${res.count} placa(s) encontrada(s)`;
      if (query) {
        loadHistory();
      }
    }
  } catch (err) {
    console.error("Erro ao carregar placas:", err);
  }
}

function renderPlates(plates) {
  const tbody = document.getElementById("plates-table-body");
  if (!tbody) return;

  if (!plates || plates.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state">
          <div class="empty-message">
            <span class="empty-icon">🚗</span>
            <p>Nenhuma placa encontrada com os critérios informados.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  const isAdmin = state.user && state.user.role === "admin";
  tbody.innerHTML = plates
    .map((p) => {
      const statusBadge = renderStatusBadge(p);
      const expiryCell = renderExpiryCell(p);
      const vehicleDesc = [p.modelo, p.cor].filter(Boolean).join(" • ");
      const vehicleCell = vehicleDesc
        ? `<span style="font-weight: 600; color: var(--text-primary);">${escapeHtml(vehicleDesc)}</span>`
        : `<span class="text-muted">—</span>`;

      const actionsCell = isAdmin
        ? `
          <td style="text-align: center;">
            <div class="row-actions">
              <button class="btn-icon" title="Editar placa" onclick="openEditModal('${p.placa}')">✏️</button>
              <button class="btn-icon btn-icon-danger" title="Excluir placa" onclick="openDeleteModal('${p.placa}')">🗑️</button>
            </div>
          </td>
        `
        : "";

      return `
        <tr>
          <td><span class="plate-cell">${escapeHtml(p.placa)}</span></td>
          <td>${vehicleCell}</td>
          <td>${escapeHtml(p.detalhes || "—")}</td>
          <td>${statusBadge}</td>
          <td>${expiryCell}</td>
          ${actionsCell}
        </tr>
      `;
    })
    .join("");
}

function renderStatusBadge(p) {
  if (p.status === "autorizado_temp") {
    if (p.expired) {
      return `<span class="status-badge status-temp-expired">⚠️ Temp - Expirado</span>`;
    } else {
      return `<span class="status-badge status-temp-active">⏱️ Temp - Ativo</span>`;
    }
  }

  switch (p.status) {
    case "autorizado":
      return `<span class="status-badge status-authorized">🟢 Autorizado</span>`;
    case "autorizado_patio":
      return `<span class="status-badge status-authorized">🟢 Pátio</span>`;
    case "para recepção":
      return `<span class="status-badge status-info">🔵 Recepção</span>`;
    case "para entrega":
      return `<span class="status-badge status-info">📦 Entrega</span>`;
    case "não autorizado":
    default:
      return `<span class="status-badge status-unauthorized">🔴 Não Autorizado</span>`;
  }
}

function renderExpiryCell(p) {
  if (p.status !== "autorizado_temp") {
    return `<span class="text-muted">—</span>`;
  }

  const timeClass = p.expired ? "expired" : "active";
  return `
    <div class="expiry-info">
      <span class="expiry-time ${timeClass}">${escapeHtml(p.time_remaining || "")}</span>
      <span class="expiry-date">Até ${escapeHtml(p.expires_display || "")}</span>
    </div>
  `;
}

// ==================== SEARCH HISTORY ====================
async function loadHistory() {
  try {
    const res = await apiFetch("/api/plates/history");
    const listEl = document.getElementById("history-list");
    if (!listEl) return;

    if (!res.ok || !res.history || res.history.length === 0) {
      listEl.innerHTML = `<li class="history-empty">Nenhuma busca recente.</li>`;
      return;
    }

    listEl.innerHTML = res.history
      .map(
        (h) => `
        <li class="history-item" onclick="applyHistoryQuery('${h.query}')">
          <span class="history-query">${escapeHtml(h.query)}</span>
          <span class="history-time">${escapeHtml(h.time)}</span>
        </li>
      `
      )
      .join("");
  } catch (err) {
    console.error("Erro ao carregar histórico:", err);
  }
}

function applyHistoryQuery(query) {
  const input = document.getElementById("search-input");
  if (input) {
    input.value = query;
    state.searchQuery = query;
    document.getElementById("btn-search-clear")?.classList.remove("hidden");
    loadPlates();
  }
}

// ==================== ADD / EDIT / DELETE PLATES ====================
async function handleAddPlate(e) {
  e.preventDefault();
  const placa = document.getElementById("add-placa").value.trim();
  const modelo = document.getElementById("add-modelo")?.value.trim() || "";
  const cor = document.getElementById("add-cor")?.value.trim() || "";
  const detalhes = document.getElementById("add-detalhes").value.trim();
  const status = document.getElementById("add-status").value;
  const exactExpires = document.getElementById("add-expires-at").value.trim();

  const payload = {
    placa,
    detalhes,
    status,
    modelo,
    cor,
  };

  if (status === "autorizado_temp") {
    if (exactExpires) {
      payload.expires_at = exactExpires.replace("T", " ");
    } else {
      payload.duration_hours = state.addTempPresetHours;
    }
  }

  try {
    const res = await apiFetch("/api/plates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      showAlert(`Placa ${res.plate.placa} cadastrada com sucesso!`, "success");
      document.getElementById("form-add-plate").reset();
      document.getElementById("add-temp-box").classList.add("hidden");
      loadConfigStats();
      // Switch back to search tab and view newly added plate
      document.querySelector('[data-tab="tab-search"]')?.click();
      applyHistoryQuery(placa);
    } else {
      showAlert(res.detail || "Erro ao cadastrar placa.", "danger");
    }
  } catch (err) {
    showAlert("Falha na comunicação com o servidor.", "danger");
  }
}

async function openEditModal(placa) {
  try {
    const res = await apiFetch(`/api/plates/${placa}`);
    if (!res.ok || !res.plate) {
      showAlert("Placa não encontrada.", "danger");
      return;
    }
    const p = res.plate;
    document.getElementById("edit-placa-val").value = p.placa;
    document.getElementById("edit-placa-title").textContent = p.placa;
    document.getElementById("edit-modelo").value = p.modelo || "";
    document.getElementById("edit-cor").value = p.cor || "";
    document.getElementById("edit-detalhes").value = p.detalhes || "";
    document.getElementById("edit-status").value = p.status;

    const tempBox = document.getElementById("edit-temp-box");
    if (p.status === "autorizado_temp") {
      tempBox.classList.remove("hidden");
      if (p.expires_at) {
        const dt = new Date(p.expires_at);
        if (!isNaN(dt.getTime())) {
          document.getElementById("edit-expires-at").value = formatForDateTimeInput(dt);
        }
      }
    } else {
      tempBox.classList.add("hidden");
      document.getElementById("edit-expires-at").value = "";
    }

    openModal("modal-edit-plate");
  } catch (err) {
    showAlert("Erro ao abrir modal de edição.", "danger");
  }
}

async function handleEditPlate(e) {
  e.preventDefault();
  const placa = document.getElementById("edit-placa-val").value;
  const modelo = document.getElementById("edit-modelo")?.value.trim() || "";
  const cor = document.getElementById("edit-cor")?.value.trim() || "";
  const detalhes = document.getElementById("edit-detalhes").value.trim();
  const status = document.getElementById("edit-status").value;
  const exactExpires = document.getElementById("edit-expires-at").value.trim();

  const payload = {
    detalhes,
    status,
    modelo,
    cor,
  };

  if (status === "autorizado_temp") {
    if (exactExpires) {
      payload.expires_at = exactExpires.replace("T", " ");
    } else {
      payload.duration_hours = state.editTempPresetHours;
    }
  }

  try {
    const res = await apiFetch(`/api/plates/${placa}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-edit-plate");
      showAlert(`Placa ${placa} atualizada com sucesso!`, "success");
      loadPlates();
      loadConfigStats();
    } else {
      showAlert(res.detail || "Erro ao atualizar placa.", "danger");
    }
  } catch (err) {
    showAlert("Falha na comunicação com o servidor.", "danger");
  }
}

function openDeleteModal(placa) {
  state.deleteTargetPlate = placa;
  document.getElementById("delete-placa-name").textContent = placa;
  openModal("modal-delete-confirm");
}

async function handleDeletePlateConfirm() {
  const placa = state.deleteTargetPlate;
  if (!placa) return;

  try {
    const res = await apiFetch(`/api/plates/${placa}`, { method: "DELETE" });
    closeModal("modal-delete-confirm");
    if (res.ok) {
      showAlert(`Placa ${placa} excluída com sucesso!`, "success");
      loadPlates();
      loadConfigStats();
    } else {
      showAlert(res.detail || "Erro ao excluir placa.", "danger");
    }
  } catch (err) {
    closeModal("modal-delete-confirm");
    showAlert("Falha na comunicação com o servidor.", "danger");
  }
}

// ==================== CONFIG & CSV ====================
async function loadConfigStats() {
  try {
    const res = await apiFetch("/api/config");
    if (res.ok && res.stats) {
      const s = res.stats;
      document.getElementById("stat-total").textContent = s.total;
      document.getElementById("stat-authorized").textContent = s.authorized;
      document.getElementById("stat-temp-active").textContent = s.temp_active;
      document.getElementById("stat-temp-expired").textContent = s.temp_expired;

      const csvLabel = document.getElementById("csv-name-label");
      if (csvLabel) csvLabel.textContent = s.csv_name || "Nenhum arquivo";

      const cfgInput = document.getElementById("cfg-csv-path");
      if (cfgInput) cfgInput.value = s.csv_path || "";
    }
  } catch (err) {
    console.error("Erro ao carregar estatísticas:", err);
  }
}

async function handleSetCsvPath(e) {
  e.preventDefault();
  const path = document.getElementById("cfg-csv-path").value.trim();
  try {
    const res = await apiFetch("/api/config/csv-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    if (res.ok) {
      showAlert(res.message, "success");
      loadConfigStats();
      loadPlates();
    } else {
      showAlert(res.detail || "Erro ao alterar arquivo CSV.", "danger");
    }
  } catch (err) {
    showAlert("Falha ao comunicar com servidor.", "danger");
  }
}

async function handleUploadCsv(e) {
  e.preventDefault();
  const fileInput = document.getElementById("cfg-csv-file");
  if (!fileInput.files || fileInput.files.length === 0) {
    showAlert("Selecione um arquivo .csv.", "danger");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/api/config/upload-csv", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (res.ok) {
      showAlert(data.message, "success");
      fileInput.value = "";
      loadConfigStats();
      loadPlates();
    } else {
      showAlert(data.detail || "Falha no upload do CSV.", "danger");
    }
  } catch (err) {
    showAlert("Erro de rede durante o upload.", "danger");
  }
}

// ==================== USERS MANAGEMENT ====================
async function loadUsers() {
  try {
    const res = await apiFetch("/api/auth/users");
    const tbody = document.getElementById("users-table-body");
    if (!tbody) return;

    if (!res.ok || !res.users || res.users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Nenhum usuário cadastrado.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.users
      .map(
        (u) => `
        <tr>
          <td><strong>${escapeHtml(u.username)}</strong></td>
          <td>${escapeHtml(u.name || "—")}</td>
          <td>
            <span class="user-role ${u.role === "admin" ? "admin" : ""}">
              ${u.role.toUpperCase()}
            </span>
          </td>
          <td>${escapeHtml(u.created_at ? u.created_at.substring(0, 10) : "—")}</td>
          <td style="text-align: center;">
            <div class="row-actions">
              <button class="btn-icon" title="Editar usuário" onclick="editUser('${u.username}', '${escapeHtml(u.name)}', '${u.role}')">✏️</button>
              ${
                u.username !== state.user?.username
                  ? `<button class="btn-icon btn-icon-danger" title="Excluir usuário" onclick="deleteUser('${u.username}')">🗑️</button>`
                  : ""
              }
            </div>
          </td>
        </tr>
      `
      )
      .join("");
  } catch (err) {
    console.error("Erro ao carregar usuários:", err);
  }
}

function openUserModal(username = "", name = "", role = "operador") {
  const isEdit = !!username;
  document.getElementById("modal-user-title").textContent = isEdit ? `✏️ Editar Usuário: ${username}` : "👤 Novo Usuário";
  const userAlert = document.getElementById("user-modal-alert");
  if (userAlert) userAlert.classList.add("hidden");

  const uInput = document.getElementById("user-input-username");
  uInput.value = username;
  uInput.readOnly = isEdit;

  document.getElementById("user-input-name").value = name;
  document.getElementById("user-input-role").value = role;

  const pwdInput = document.getElementById("user-input-password");
  pwdInput.value = "";
  pwdInput.required = !isEdit;

  const pwdLabel = document.getElementById("user-password-label");
  const pwdHint = document.getElementById("user-password-hint");
  if (isEdit) {
    pwdLabel.textContent = "Nova Senha (opcional)";
    pwdHint.textContent = "Deixe em branco para manter a senha atual.";
  } else {
    pwdLabel.textContent = "Senha *";
    pwdHint.textContent = "Mínimo de 4 caracteres.";
  }

  openModal("modal-user");
}

window.editUser = function (username, name, role) {
  openUserModal(username, name, role);
};

window.deleteUser = async function (username) {
  if (confirm(`Deseja realmente excluir o usuário '${username}'?`)) {
    try {
      const res = await apiFetch(`/api/auth/users/${username}`, { method: "DELETE" });
      if (res.ok) {
        showAlert(`Usuário '${username}' excluído.`, "success");
        loadUsers();
      } else {
        showAlert(res.detail || "Erro ao excluir usuário.", "danger");
      }
    } catch (err) {
      showAlert("Falha ao comunicar com o servidor.", "danger");
    }
  }
};

async function handleSaveUser(e) {
  e.preventDefault();
  const username = document.getElementById("user-input-username").value.trim();
  const name = document.getElementById("user-input-name").value.trim();
  const role = document.getElementById("user-input-role").value;
  const password = document.getElementById("user-input-password").value;

  const payload = { username, name, role };
  if (password) payload.password = password;

  try {
    const res = await apiFetch("/api/auth/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-user");
      showAlert(res.message, "success");
      loadUsers();
    } else {
      const alertBox = document.getElementById("user-modal-alert");
      if (alertBox) {
        alertBox.textContent = res.detail || "Erro ao salvar usuário.";
        alertBox.classList.remove("hidden");
      }
    }
  } catch (err) {
    showAlert("Falha ao comunicar com o servidor.", "danger");
  }
}

// ==================== CHANGE PASSWORD ====================
async function handleChangePassword(e) {
  e.preventDefault();
  const oldPassword = document.getElementById("pwd-old").value;
  const newPassword = document.getElementById("pwd-new").value;
  const confirmPassword = document.getElementById("pwd-confirm").value;
  const alertBox = document.getElementById("change-pwd-alert");

  if (newPassword !== confirmPassword) {
    alertBox.textContent = "A nova senha e a confirmação não coincidem.";
    alertBox.classList.remove("hidden");
    return;
  }

  try {
    const res = await apiFetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    });

    if (res.ok) {
      closeModal("modal-change-password");
      showAlert("Senha alterada com sucesso!", "success");
    } else {
      alertBox.textContent = res.detail || "Erro ao alterar senha.";
      alertBox.classList.remove("hidden");
    }
  } catch (err) {
    alertBox.textContent = "Falha ao comunicar com o servidor.";
    alertBox.classList.remove("hidden");
  }
}

// ==================== HELPERS ====================
async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    openLoginModal();
    throw new Error("Não autenticado");
  }
  const data = await res.json();
  if (!res.ok) {
    data.ok = false;
  }
  return data;
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m && !m.open) m.showModal();
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m && m.open) m.close();
}

function showAlert(message, type = "success") {
  const alertEl = document.getElementById("global-alert");
  const msgEl = document.getElementById("global-alert-msg");
  if (!alertEl || !msgEl) return;

  alertEl.className = `alert alert-${type}`;
  msgEl.textContent = message;
  alertEl.classList.remove("hidden");

  setTimeout(() => {
    alertEl.classList.add("hidden");
  }, 4000);
}

function closeAlert() {
  document.getElementById("global-alert")?.classList.add("hidden");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatForDateTimeInput(date) {
  const pad = (n) => String(n).padStart(2, "0");
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const h = pad(date.getHours());
  const min = pad(date.getMinutes());
  return `${y}-${m}-${d}T${h}:${min}`;
}
