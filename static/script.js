let currentSort = { column: "account", ascending: true };
let cachedUsers = [];

// -----------------------------
// On Page Load
// -----------------------------
document.addEventListener("DOMContentLoaded", async () => {
  await loadUsers();
  setupComboBox();
});

// -----------------------------
// Load & Render Functions
// -----------------------------
async function loadUsers(preserveSort = true) {
  const res = await fetch("/users");
  const data = await res.json();
  cachedUsers = data;

  const tbody = document.querySelector("#users_table tbody");
  tbody.innerHTML = "";

  // Apply sorting if table is already sorted
  let sortedData = [...data];
  if (preserveSort && currentSort.column === "account") {
    sortedData.sort((a, b) => {
      const aText = (a.user_name || "").toLowerCase();
      const bText = (b.user_name || "").toLowerCase();
      return currentSort.ascending
        ? aText.localeCompare(bText)
        : bText.localeCompare(aText);
    });
  }

  sortedData.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="account-name-cell">${escapeHtml(row.user_name || "")}</td>
      <td class="sf-name-cell" contenteditable="true" onblur="updateName('${row.id}', this.innerText)">
        ${escapeHtml(row.salesforce_name || "")}
      </td>
      <td>
        <div class="action-buttons">
          <button class="bx--btn bx--btn--sm bx--btn--secondary" onclick="updateUser('${row.id}')">Update</button>
          <button class="bx--btn bx--btn--sm bx--btn--danger" onclick="deleteUser('${row.id}')">Delete</button>
        </div>
      </td>`;
    tbody.appendChild(tr);
  });

  updateComboOptions(data.map((u) => u.user_name));
}

// -----------------------------
// ComboBox Logic
// -----------------------------
function setupComboBox() {
  const combo = document.getElementById("accountComboBox");
  const input = document.getElementById("accountInput");
  const menu = document.getElementById("comboMenu");
  const toggleBtn = combo.querySelector(".bx--list-box__menu-icon");

  toggleBtn.addEventListener("click", () => {
    const hidden = menu.getAttribute("aria-hidden") === "true";
    menu.setAttribute("aria-hidden", hidden ? "false" : "true");
  });

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    const items = Array.from(menu.children);
    let anyVisible = false;
    items.forEach((li) => {
      const match = li.textContent.toLowerCase().includes(q);
      li.style.display = match ? "block" : "none";
      if (match) anyVisible = true;
    });
    menu.setAttribute("aria-hidden", !anyVisible);
  });

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
  [...new Set(names)].forEach((name) => {
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

// -----------------------------
// CRUD Operations
// -----------------------------
async function addUser() {
  const input = document.getElementById("accountInput");
  const userName = input.value.trim();
  const salesforceName = document
    .getElementById("salesforce_name")
    .value.trim();

  if (!userName || !salesforceName) {
    showCarbonNotification(
      "error",
      "Please enter both Account Name and Salesforce Account Name"
    );
    return;
  }

  // Check for duplicate Salesforce Name
  const duplicate = cachedUsers.find(
    (u) =>
      u.salesforce_name &&
      u.salesforce_name.toLowerCase() === salesforceName.toLowerCase()
  );
  if (duplicate) {
    showCarbonNotification(
      "error",
      "Alias (Salesforce) Account Name already exists"
    );
    return;
  }

  await fetch("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_name: userName,
      salesforce_name: salesforceName,
    }),
  });

  document.getElementById("salesforce_name").value = "";
  input.value = "";
  await loadUsers(true); // Preserve sorting
  showCarbonNotification("success", "Account Name saved");
}

async function updateUser(id) {
  const res = await fetch("/users");
  const users = await res.json();
  const row = users.find((u) => u.id === id);
  if (!row) return;

  // Ensure unique alias before update
  const duplicate = users.find(
    (u) =>
      u.id !== id &&
      u.salesforce_name &&
      u.salesforce_name.toLowerCase() === row.salesforce_name.toLowerCase()
  );
  if (duplicate) {
    showCarbonNotification(
      "error",
      "Alias (Salesforce) Account Name already exists"
    );
    await loadUsers(true);
    return;
  }

  await fetch(`/users/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_name: row.user_name,
      salesforce_name: row.salesforce_name,
    }),
  });
  await loadUsers(true);
  showCarbonNotification("success", "Account updated");
}

async function deleteUser(id) {
  if (!confirm("Are you sure you want to delete this mapping?")) return;
  await fetch(`/users/${id}`, { method: "DELETE" });
  await loadUsers(true);
  showCarbonNotification("success", "Account deleted successfully");
}

async function updateName(id, newName) {
  newName = (newName || "").trim();
  if (!newName) {
    showCarbonNotification("error", "Salesforce Name cannot be empty");
    await loadUsers(true);
    return;
  }

  const res = await fetch("/users");
  const users = await res.json();

  // Prevent duplicate alias names
  const duplicate = users.find(
    (u) =>
      u.id !== id &&
      u.salesforce_name &&
      u.salesforce_name.toLowerCase() === newName.toLowerCase()
  );
  if (duplicate) {
    showCarbonNotification(
      "error",
      "Alias (Salesforce) Account Name already exists"
    );
    await loadUsers(true);
    return;
  }

  const row = users.find((u) => u.id === id);
  if (!row) return;

  await fetch(`/users/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_name: row.user_name,
      salesforce_name: newName,
    }),
  });

  await loadUsers(true);
}

// -----------------------------
// Notifications
// -----------------------------
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
        <p class="bx--inline-notification__title">${
          type.charAt(0).toUpperCase() + type.slice(1)
        }</p>
        <p class="bx--inline-notification__subtitle">${message}</p>
      </div>
    </div>
    <button class="bx--inline-notification__close-button" type="button">×</button>
  `;
  document.body.appendChild(container);
  setTimeout(() => container.remove(), 3500);
  container.querySelector("button").onclick = () => container.remove();
}

// -----------------------------
// Helpers
// -----------------------------
function escapeHtml(text) {
  if (!text && text !== 0) return "";
  return String(text).replace(/[&<>"']/g, (m) => {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[m];
  });
}
function escapeJs(text) {
  return ("" + text).replace(/'/g, "\\'");
}
