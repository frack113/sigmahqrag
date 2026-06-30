function _showToast(message, type) {
	if (!type) type = "info";
	const container = document.getElementById("toast-container");
	if (!container) return;
	const toast = document.createElement("div");
	toast.className = `toast ${type}`;
	toast.textContent = message;
	container.appendChild(toast);
	setTimeout(() => {
		toast.remove();
	}, 3000);
}

function _esc(s) {
	if (s == null) return "";
	var m = {
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		'"': "&quot;",
		"'": "&#39;",
	};
	return String(s).replace(/[&<>"']/g, (c) => m[c]);
}

function _escAttr(s) {
	if (s == null) return "";
	var m = {
		"&": "\x26amp;",
		'"': "\x26quot;",
		"'": "\x26#39;",
		"<": "\x26lt;",
		">": "\x26gt;",
	};
	return String(s).replace(/[&"'<>]/g, (c) => m[c]);
}
