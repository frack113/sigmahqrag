let currentSource = "system";
let eventSource = null;
let isTailMode = true;
let scrollLocked = true;
let allLines = [];
let allLinesLower = [];
let generation = 1;
let connecting = false;
let searchDebounce = null;
const MAX_LINES = 10000;

const LEVEL_CLASS = {
	ERROR: "error",
	CRITICAL: "error",
	WARNING: "warning",
	WARN: "warning",
	INFO: "info",
	DEBUG: "debug",
};

document.addEventListener("DOMContentLoaded", () => {
	const output = document.getElementById("logs-output");
	const linesInput = document.getElementById("log-lines");

	linesInput.addEventListener("change", () => {
		if (isTailMode) restartTail();
		else loadLogs();
	});

	document.querySelectorAll("#log-sources a").forEach((a) => {
		a.addEventListener("click", (e) => {
			e.preventDefault();
			selectSource(a.dataset.source);
		});
	});

	const searchInput = document.getElementById("log-search");
	searchInput.addEventListener("input", () => {
		if (searchDebounce) clearTimeout(searchDebounce);
		searchDebounce = setTimeout(renderFilteredLogs, 200);
	});

	output.addEventListener("scroll", () => {
		const atBottom =
			output.scrollHeight - output.scrollTop - output.clientHeight < 100;
		scrollLocked = atBottom;
	});

	startTail();
});

function trimLines() {
	if (allLines.length > MAX_LINES) {
		const excess = allLines.length - MAX_LINES;
		allLines = allLines.slice(excess);
		allLinesLower = allLinesLower.slice(excess);
	}
}

function selectSource(source) {
	currentSource = source;
	document.querySelectorAll("#log-sources a").forEach((a) => {
		a.classList.remove("active");
	});
	const link = document.querySelector(
		`#log-sources a[data-source="${escAttr(source)}"]`,
	);
	if (link) link.classList.add("active");
	document.querySelector("#logs-header h2").textContent =
		source === "system"
			? "System Logs"
			: source === "llamacpp"
				? "llama.cpp Logs"
				: "Qdrant Logs";
	restartTail();
}

function getLines() {
	const val = parseInt(document.getElementById("log-lines").value, 10);
	return Number.isFinite(val) && val > 0 ? val : 50;
}

function _toggleTail() {
	isTailMode = document.getElementById("tail-mode").checked;
	scrollLocked = true;
	const pauseBtn = document.getElementById("pause-btn");
	if (pauseBtn) pauseBtn.textContent = isTailMode ? "Pause" : "Resume";
	stopTail();
	allLines = [];
	allLinesLower = [];
	if (isTailMode) {
		startTail();
	} else {
		loadLogs();
	}
}

function stopTail() {
	if (eventSource) {
		const old = eventSource;
		eventSource = null;
		old.close();
	}
}

function startTail() {
	if (!isTailMode || connecting) return;
	connecting = true;
	stopTail();
	allLines = [];
	allLinesLower = [];
	const myGen = ++generation;
	const lines = getLines();
	const url = `/api/v1/logs/stream?source=${encodeURIComponent(currentSource)}&lines=${lines}`;
	eventSource = new EventSource(url);
	connecting = false;

	eventSource.addEventListener("log", (event) => {
		try {
			if (myGen !== generation) return;
			const data = JSON.parse(event.data);

			if (data.type === "init") {
				allLines = data.lines || [];
				allLinesLower = allLines.map((l) => l.toLowerCase());
				scrollLocked = true;
				trimLines();
			} else if (data.type === "update") {
				const newLines = data.lines || [];
				allLines.push(...newLines);
				allLinesLower.push(...newLines.map((l) => l.toLowerCase()));
				scrollLocked = true;
				trimLines();
			} else if (data.type === "error") {
				allLines = [`Error: ${data.message}`];
				allLinesLower = [allLines[0].toLowerCase()];
			}
			renderFilteredLogs();
		} catch (e) {
			console.error("SSE parse error:", e);
		}
	});

	eventSource.onerror = (errEvent) => {
		const dead = errEvent.target ? errEvent.target : eventSource;
		dead.close();
		if (eventSource === dead) eventSource = null;
		const output = document.getElementById("logs-output");
		if (output && output.querySelector(".logs-error") === null) {
			const el = document.createElement("div");
			el.className = "logs-error";
			el.textContent = "Connection lost, retrying in 3s...";
			output.prepend(el);
		}
		setTimeout(() => {
			const errEl = document.querySelector(".logs-error");
			if (errEl) errEl.remove();
			if (isTailMode) startTail();
		}, 3000);
	};
}

function restartTail() {
	if (isTailMode) {
		startTail();
	} else {
		loadLogs();
	}
}

function renderFilteredLogs() {
	const output = document.getElementById("logs-output");
	const searchTerm = document.getElementById("log-search").value.toLowerCase();
	const statsEl = document.getElementById("log-stats");
	const count = getLines();

	const startIdx = allLines.length > count ? allLines.length - count : 0;
	const displayedLines = allLines.slice(startIdx);
	const displayedLower = allLinesLower.slice(startIdx);

	const searchIdx = displayedLower.findIndex((l) => l.includes(searchTerm));
	const filtered =
		searchTerm && searchIdx >= 0
			? displayedLines.filter((_, i) => displayedLower[i].includes(searchTerm))
			: displayedLines;

	const html = filtered.map((line) => colorizeLine(line)).join("\n");

	output.innerHTML = html || "No logs found";

	if (scrollLocked && isTailMode && !searchTerm) {
		requestAnimationFrame(() => {
			output.scrollTop = output.scrollHeight;
		});
	}

	if (statsEl) {
		let text = `${filtered.length} lines`;
		if (allLines.length !== displayedLines.length)
			text += ` / ${allLines.length} total`;
		if (searchTerm) text += " (filtered)";
		statsEl.textContent = text;
	}
}

function colorizeLine(line) {
	const escaped = line
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
	const m = escaped.match(
		/^\d{4}-\d{2}-\d{2}.*?(ERROR|CRITICAL|WARNING|WARN|DEBUG|INFO)/,
	);
	if (m) {
		const cls = LEVEL_CLASS[m[1]] || m[1].toLowerCase();
		return `<span class="log-level-${cls}">${escaped}</span>`;
	}
	return `<span class="log-line">${escaped}</span>`;
}

async function loadLogs() {
	stopTail();
	const lines = getLines();
	const params = new URLSearchParams({ source: currentSource, lines: lines });

	try {
		const response = await fetch(`/api/v1/logs?${params}`);
		if (!response.ok) {
			throw new Error(`Server returned ${response.status}`);
		}
		const data = await response.json();
		allLines = data.logs.map((l) => l.text);
		allLinesLower = allLines.map((l) => l.toLowerCase());
		scrollLocked = true;
		renderFilteredLogs();
	} catch (error) {
		console.error("Failed to load logs:", error);
		const output = document.getElementById("logs-output");
		output.innerHTML = `<div class="logs-error">Failed to load logs: ${error.message}</div>`;
	}
}

async function _clearLogs() {
	if (!confirm(`Clear all logs for ${currentSource}?`)) return;
	try {
		const response = await fetch(
			`/api/v1/logs?source=${encodeURIComponent(currentSource)}`,
			{ method: "DELETE" },
		);
		const data = await response.json();
		if (data.success) {
			allLines = [];
			allLinesLower = [];
			document.getElementById("logs-output").innerHTML = "";
			const statsEl = document.getElementById("log-stats");
			if (statsEl) statsEl.textContent = "Logs cleared";
		} else {
			console.error("Failed to clear logs:", data.message);
		}
	} catch (error) {
		console.error("Failed to clear logs:", error);
	}
}

async function _togglePause() {
	const btn = document.getElementById("pause-btn");
	if (isTailMode) {
		stopTail();
		scrollLocked = false;
		btn.textContent = "Resume";
		btn.classList.remove("btn-secondary");
		btn.classList.add("btn-primary");
		isTailMode = false;
	} else {
		isTailMode = true;
		scrollLocked = true;
		btn.textContent = "Pause";
		btn.classList.remove("btn-primary");
		btn.classList.add("btn-secondary");
		startTail();
	}
	document.getElementById("tail-mode").checked = isTailMode;
}

function escAttr(s) {
	return String(s)
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}
