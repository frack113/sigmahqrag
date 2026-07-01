let currentPrompts = [];

function escapeHtml(str) {
	const div = document.createElement("div");
	div.textContent = str;
	return div.innerHTML;
}

async function loadPrompts() {
	try {
		const res = await fetch("/api/v1/admin/prompts");
		if (!res.ok) throw new Error("Failed to load prompts");
		const promptsRes = await res.json();

		currentPrompts = promptsRes;

		const tbody = document.getElementById("prompts-table-body");
		tbody.innerHTML = "";

		if (promptsRes.length === 0) {
			tbody.innerHTML =
				'<tr><td colspan="3" class="text-center text-muted">No prompts found</td></tr>';
		} else {
			promptsRes.forEach((p) => {
				const tr = document.createElement("tr");
				tr.innerHTML = `
                    <td><strong>${escapeHtml(p.name)}</strong></td>
                    <td class="text-muted">${escapeHtml(p.description || "")}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-primary" onclick="editPrompt('${escapeHtml(p.id)}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deletePrompt('${escapeHtml(p.id)}', '${escapeHtml(p.name)}')">Delete</button>
                    </td>
                `;
				tbody.appendChild(tr);
			});
		}
	} catch (err) {
		console.error("Error loading prompts:", err);
		showStatus("Failed to load prompts", "error");
	}
}

async function syncFromFiles() {
	showStatus("Syncing prompts from files...", "info");
	try {
		const res = await fetch("/api/v1/admin/prompts/sync", {
			method: "POST",
		});
		const data = await res.json();
		if (res.ok) {
			showStatus(data.message || "Sync complete", "success");
			await loadPrompts();
		} else {
			showStatus(data.error || "Sync failed", "error");
		}
	} catch (err) {
		showStatus("Network error: " + err.message, "error");
	}
}

async function refreshList() {
	showStatus("Refreshing...", "info");
	await loadPrompts();
	showStatus("", "");
}

function toggleFormInputs(disabled) {
	const fields = ["prompt-name", "prompt-description", "prompt-content-input"];
	fields.forEach((id) => {
		const el = document.getElementById(id);
		if (el) el.disabled = disabled;
	});
	document.getElementById("btn-cancel").disabled = disabled;
	document.getElementById("btn-save").disabled = disabled;
}

function generateUUID() {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0;
		const v = c === "x" ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}

function resetForm() {
	const fields = [
		"prompt-id",
		"prompt-name",
		"prompt-description",
		"prompt-content-input",
	];
	fields.forEach((id) => {
		const el = document.getElementById(id);
		if (el) el.value = "";
	});

	document.getElementById("edit-form-title").textContent = "Create New Prompt";
	document.getElementById("save-status").textContent = "";
	document.getElementById("save-status").className = "status-message";
	toggleFormInputs(true);
}

function EnableEditForm() {
	resetForm();
	const newId = generateUUID();
	document.getElementById("prompt-id").value = newId;
	document.getElementById("prompt-name").disabled = false;
	document.getElementById("prompt-description").disabled = false;
	document.getElementById("prompt-content-input").disabled = false;
	document.getElementById("btn-cancel").disabled = false;
	document.getElementById("btn-save").disabled = false;
	document.getElementById("edit-form-title").textContent = "Create New Prompt";
}

async function editPrompt(id) {
	try {
		const res = await fetch(`/api/v1/admin/prompts/${encodeURIComponent(id)}`);
		const data = await res.json();

		if (!res.ok || data.error)
			throw new Error(data.error || "Failed to load prompt");

		document.getElementById("prompt-id").value = data.id;
		document.getElementById("prompt-name").value = data.name;
		document.getElementById("prompt-description").value =
			data.description || "";
		document.getElementById("prompt-content-input").value = data.content || "";
		document.getElementById("edit-form-title").textContent = "Edit Prompt";
		document.getElementById("save-status").textContent = "";
		document.getElementById("save-status").className = "status-message";
		toggleFormInputs(false);
	} catch (err) {
		console.error("Error loading prompt:", err);
		showStatus("Error: " + err.message, "error");
	}
}

async function savePrompt() {
	const id = document.getElementById("prompt-id").value;
	const valName = document.getElementById("prompt-name").value.trim();
	const valDesc = document.getElementById("prompt-description").value.trim();
	const valContent = document.getElementById("prompt-content-input").value;

	if (!valName) {
		showStatus("Name is required", "error");
		return;
	}

	if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(valName)) {
		showStatus("Name must be in kebab-case (e.g., my-prompt)", "error");
		return;
	}

	const isNewPrompt = !currentPrompts.some((p) => p.id === id);
	const url = isNewPrompt
		? "/api/v1/admin/prompts"
		: `/api/v1/admin/prompts/${id}`;
	const method = isNewPrompt ? "POST" : "PUT";
	const body = JSON.stringify({
		name: valName,
		description: valDesc,
		content: valContent,
	});

	const saveBtn = document.getElementById("btn-save");
	saveBtn.disabled = true;

	try {
		const res = await fetch(url, {
			method: method,
			headers: { "Content-Type": "application/json" },
			body: body,
		});
		const data = await res.json();

		if (res.ok) {
			showStatus(data.message || "Saved!", "success");
			resetForm();
			await loadPrompts();
		} else {
			showStatus(data.error || "Error saving prompt", "error");
		}
	} catch (err) {
		console.error("Error saving prompt:", err);
		showStatus("Network error: " + err.message, "error");
	} finally {
		saveBtn.disabled = false;
	}
}

async function deletePrompt(id, name) {
	if (
		!(await showConfirm(
			`Delete prompt "${name}"?\n\nThis action cannot be undone.`,
		))
	)
		return;
	try {
		const res = await fetch(`/api/v1/admin/prompts/${encodeURIComponent(id)}`, {
			method: "DELETE",
		});
		const data = await res.json();
		if (res.ok) {
			showStatus("Prompt deleted", "success");
			await loadPrompts();
		} else {
			showStatus("Error deleting prompt", "error");
		}
	} catch (err) {
		console.error("Error deleting prompt:", err);
		showStatus("Network error: " + err.message, "error");
	}
}

function showStatus(msg, type) {
	const el = document.getElementById("save-status");
	el.textContent = msg;
	el.className = "status-message " + (type || "");
}

document.addEventListener("DOMContentLoaded", loadPrompts);
