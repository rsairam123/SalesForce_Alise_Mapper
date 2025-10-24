document.addEventListener("DOMContentLoaded", loadUsers);

function addSfInput() {
    const container = document.getElementById("salesforce_names_container");
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Salesforce Name";
    input.className = "sf-input";
    container.appendChild(input);
}

async function loadUsers() {
    const res = await fetch("/users");
    const data = await res.json();
    const tbody = document.querySelector("#users_table tbody");
    tbody.innerHTML = "";

    data.forEach(user => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${user.sno}</td>
            <td>${user.user_name}</td>
            <td class="sf-names">${user.salesforce_names.map(name => 
                `<span class="sf-tag" contenteditable="true" onblur="updateName('${user.id}', this.innerText)">${name}</span>`
            ).join('')}</td>
            <td>
                <button class="update-btn" onclick="updateUser('${user.id}')">Update</button>
                <button class="delete-btn" onclick="deleteUser('${user.id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function addUser() {
    const userName = document.getElementById("user_name").value.trim();
    if (!userName) return alert("Enter user name");

    const sfInputs = document.querySelectorAll(".sf-input");
    const sfNames = [...sfInputs].map(i => i.value.trim()).filter(v => v);

    const res = await fetch("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, salesforce_names: sfNames })
    });

    if (res.ok) {
        document.getElementById("user_name").value = "";
        document.getElementById("salesforce_names_container").innerHTML = "";
        loadUsers();
    }
}

async function updateUser(id) {
    const row = event.target.closest("tr");
    const userName = row.children[1].innerText.trim();
    const sfNames = [...row.querySelectorAll(".sf-tag")].map(t => t.innerText.trim());

    await fetch(`/users/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, salesforce_names: sfNames })
    });
    loadUsers();
}

async function deleteUser(id) {
    if (!confirm("Are you sure you want to delete this user?")) return;
    await fetch(`/users/${id}`, { method: "DELETE" });
    loadUsers();
}

async function updateName(id, newName) {
    const row = event.target.closest("tr");
    const userName = row.children[1].innerText.trim();
    const sfNames = [...row.querySelectorAll(".sf-tag")].map(t => t.innerText.trim());

    await fetch(`/users/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, salesforce_names: sfNames })
    });
}
