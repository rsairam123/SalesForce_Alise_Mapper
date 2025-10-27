document.addEventListener("DOMContentLoaded", async () => {
    await loadUsers();
    setupComboBox();
  });
  
  /* -------------------------
     Load & render functions
     ------------------------- */
  async function loadUsers() {
    const res = await fetch("/users");
    const data = await res.json();
    const tbody = document.querySelector("#users_table tbody");
    tbody.innerHTML = "";
  
    data.forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="account-name-cell">${escapeHtml(row.user_name || '')}</td>
        <td class="sf-name-cell" contenteditable="true" onblur="updateName('${row.id}', this.innerText)">
          ${escapeHtml(row.salesforce_name || '')}
        </td>
        <td>
          <div class="action-buttons">
            <button class="bx--btn bx--btn--sm bx--btn--secondary" onclick="updateUser('${row.id}')">Update</button>
            <button class="bx--btn bx--btn--sm bx--btn--danger" onclick="deleteUser('${row.id}')">Delete</button>
          </div>
        </td>`;
      tbody.appendChild(tr);
    });
  
    // update combobox options
    updateComboOptions(data.map(u => u.user_name));
  }
  
  /* -------------------------
     ComboBox logic (smooth)
     ------------------------- */
  function setupComboBox() {
    const combo = document.getElementById("accountComboBox");
    const input = document.getElementById("accountInput");
    const menu = document.getElementById("comboMenu");
    const toggleBtn = combo.querySelector(".bx--list-box__menu-icon");
  
    // toggle dropdown on button click
    toggleBtn.addEventListener("click", () => {
      const hidden = menu.getAttribute("aria-hidden") === "true";
      menu.setAttribute("aria-hidden", hidden ? "false" : "true");
    });
  
    // filter items on input
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      const items = Array.from(menu.children);
      let anyVisible = false;
      items.forEach(li => {
        const match = li.textContent.toLowerCase().includes(q);
        li.style.display = match ? "block" : "none";
        if (match) anyVisible = true;
      });
      menu.setAttribute("aria-hidden", !anyVisible);
    });
  
    // close dropdown when clicked outside
    document.addEventListener("click", (e) => {
      if (!combo.contains(e.target)) {
        menu.setAttribute("aria-hidden", "true");
      }
    });
  }
  
  function updateComboOptions(names) {
    const menu = document.getElementById("comboMenu");
    const input = document.getElementById("accountInput");
    menu.innerHTML = "";
    // remove duplicates & keep order
    [...new Set(names)].forEach(name => {
      const li = document.createElement("li");
      li.className = "bx--list-box__menu-item";
      li.textContent = name;
      li.addEventListener("click", () => {
        input.value = name;
        menu.setAttribute("aria-hidden", "true");
      });
      menu.appendChild(li);
    });
  }
  
  /* -------------------------
     CRUD operations
     ------------------------- */
  async function addUser() {
    const input = document.getElementById("accountInput");
    const userName = input.value.trim();
    const salesforceName = document.getElementById("salesforce_name").value.trim();
  
    if (!userName || !salesforceName) {
      showCarbonNotification("error", "Please enter both Account Name and Salesforce Account Name");
      return;
    }
  
    await fetch("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_name: userName, salesforce_name: salesforceName })
    });
  
    document.getElementById("salesforce_name").value = "";
    input.value = "";
    await loadUsers();
    showCarbonNotification("success", "Account Name saved");
  }
  
  async function updateUser(id) {
    const res = await fetch("/users");
    const users = await res.json();
    const row = users.find(u => u.id === id);
    if (!row) return;
    await fetch(`/users/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_name: row.user_name,
        salesforce_name: row.salesforce_name
      })
    });
    showCarbonNotification("success", "Account updated");
  }
  
  async function deleteUser(id) {
    if (!confirm("Are you sure you want to delete this mapping?")) return;
    await fetch(`/users/${id}`, { method: "DELETE" });
    await loadUsers();
    showCarbonNotification("success", "Account deleted successfully");
  }
  
  async function updateName(id, newName) {
    newName = (newName || '').trim();
    if (!newName) {
      showCarbonNotification("error", "Salesforce Name cannot be empty");
      await loadUsers();
      return;
    }
    const res = await fetch("/users");
    const users = await res.json();
    const row = users.find(u => u.id === id);
    if (!row) return;
    await fetch(`/users/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_name: row.user_name, salesforce_name: newName })
    });
    await loadUsers();
  }
  
  /* -------------------------
     Notifications
     ------------------------- */
  function showCarbonNotification(type, message) {
    const existing = document.querySelector(".bx--inline-notification");
    if (existing) existing.remove();
    const container = document.createElement("div");
    container.className = `bx--inline-notification bx--inline-notification--${type}`;
    container.setAttribute("role", "alert");
    container.style.position = "fixed";
    container.style.top = "20px";
    container.style.right = "20px";
    container.style.zIndex = "9999";
    container.innerHTML = `
      <div class="bx--inline-notification__details">
        <div class="bx--inline-notification__text-wrapper">
          <p class="bx--inline-notification__title">${type.charAt(0).toUpperCase() + type.slice(1)}</p>
          <p class="bx--inline-notification__subtitle">${message}</p>
        </div>
      </div>
      <button class="bx--inline-notification__close-button" type="button">×</button>
    `;
    document.body.appendChild(container);
    setTimeout(() => container.remove(), 3000);
    container.querySelector("button").onclick = () => container.remove();
  }
  
  /* -------------------------
     Small helpers
     ------------------------- */
  function escapeHtml(text) {
    if (!text && text !== 0) return "";
    return String(text).replace(/[&<>"']/g, function (m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
  }
  function escapeJs(text) {
    return ('' + text).replace(/'/g, "\\'");
  }
  
