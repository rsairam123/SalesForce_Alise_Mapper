document.addEventListener("DOMContentLoaded", loadUsers);

// Load all users and display them (each Salesforce name on a separate row)
async function loadUsers() {
    const res = await fetch("/users");
    const data = await res.json();
    const tbody = document.querySelector("#users_table tbody");
    tbody.innerHTML = "";

    let sno = 1;

    data.forEach(user => {
        user.salesforce_names.forEach(sfName => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${sno++}</td>
                <td>${user.user_name}</td>
                <td contenteditable="true" onblur="updateName('${user.id}', '${sfName}', this.innerText)">
                    ${sfName}
                </td>
                <td style="text-align:center;">
                    <button class="bx--btn bx--btn--sm bx--btn--secondary" onclick="updateUser('${user.id}')">Update</button>
                    <button class="bx--btn bx--btn--sm bx--btn--danger" onclick="deleteUser('${user.id}', '${sfName}')">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    });
}

// Add new Account Name or Salesforce Account Name
async function addUser() {
    const userName = document.getElementById("user_name").value.trim();
    const salesforceName = document.getElementById("salesforce_name").value.trim();

    if (!userName || !salesforceName) {
        showCarbonNotification("error", "Please enter both Account Name and Salesforce Account Name");
        return;
    }

    const resUsers = await fetch("/users");
    const users = await resUsers.json();

    const existingUser = users.find(u => u.user_name.toLowerCase() === userName.toLowerCase());

    if (existingUser) {
        if (existingUser.salesforce_names.includes(salesforceName)) {
            showCarbonNotification("warning", "This Salesforce Account Name already exists for this Account");
            return;
        } else {
            existingUser.salesforce_names.push(salesforceName);
            await fetch(`/users/${existingUser.id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_name: existingUser.user_name,
                    salesforce_names: existingUser.salesforce_names
                })
            });
            document.getElementById("salesforce_name").value = "";
            loadUsers();
            showCarbonNotification("success", "New Salesforce Account added successfully");
            return;
        }
    }

    // Create a completely new Account Name
    await fetch("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, salesforce_names: [salesforceName] })
    });

    document.getElementById("user_name").value = "";
    document.getElementById("salesforce_name").value = "";
    loadUsers();
    showCarbonNotification("success", "New Account added successfully");
}

// Update user (keeps existing Salesforce names)
async function updateUser(id) {
    const resUsers = await fetch("/users");
    const users = await resUsers.json();
    const user = users.find(u => u.id === id);

    if (!user) return;

    await fetch(`/users/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: user.user_name,
            salesforce_names: user.salesforce_names
        })
    });

    loadUsers();
}

// Delete Salesforce name or entire Account
async function deleteUser(id, sfNameToDelete) {
    if (!confirm("Are you sure you want to delete this entry?")) return;

    const resUsers = await fetch("/users");
    const users = await resUsers.json();
    const user = users.find(u => u.id === id);

    if (!user) return;

    if (user.salesforce_names.length === 1 && user.salesforce_names[0] === sfNameToDelete) {
        // Delete entire Account
        await fetch(`/users/${id}`, { method: "DELETE" });
    } else {
        // Delete only one Salesforce name
        const updatedNames = user.salesforce_names.filter(name => name !== sfNameToDelete);
        await fetch(`/users/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_name: user.user_name,
                salesforce_names: updatedNames
            })
        });
    }

    loadUsers();
    showCarbonNotification("success", "Entry deleted successfully");
}

// Update Salesforce name directly (inline edit)
async function updateName(id, oldName, newName) {
    newName = newName.trim();
    if (!newName) {
        showCarbonNotification("error", "Salesforce Name cannot be empty");
        loadUsers();
        return;
    }

    const resUsers = await fetch("/users");
    const users = await resUsers.json();
    const user = users.find(u => u.id === id);

    if (!user) return;

    // Prevent duplicates
    if (user.salesforce_names.includes(newName) && oldName !== newName) {
        showCarbonNotification("warning", "Duplicate Salesforce Name not allowed");
        loadUsers();
        return;
    }

    const updatedNames = user.salesforce_names.map(name => (name === oldName ? newName : name));

    await fetch(`/users/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: user.user_name,
            salesforce_names: updatedNames
        })
    });

    loadUsers();
}

// Show notifications styled like Carbon toasts
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
            <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
                 fill="currentColor" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
                <circle cx="10" cy="10" r="8"></circle>
            </svg>
            <div class="bx--inline-notification__text-wrapper">
                <p class="bx--inline-notification__title">${type.charAt(0).toUpperCase() + type.slice(1)}</p>
                <p class="bx--inline-notification__subtitle">${message}</p>
            </div>
        </div>
        <button class="bx--inline-notification__close-button" type="button" aria-label="close" title="close">
            <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
                 fill="currentColor" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M15 5L5 15M5 5l10 10"></path>
            </svg>
        </button>
    `;

    document.body.appendChild(container);

    // Close after 3 seconds or on click
    setTimeout(() => container.remove(), 3000);
    container.querySelector("button").onclick = () => container.remove();
}
