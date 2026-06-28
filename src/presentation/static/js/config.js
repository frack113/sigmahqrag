/**
 * Config Dashboard - Unified JavaScript module
 *
 * Combines functionality from system.html, backend.html, and llm.html
 * Provides a Config object with all methods accessible via onclick attributes.
 */

// ──────────────────────────────────────────────────────────────
// Global state: storage fix tracking
// ──────────────────────────────────────────────────────────────
let _dataDirsNeedFix = false;
let _duckDbNeedFix = false;

function _updateStorageLock() {
	const needsFix = _dataDirsNeedFix || _duckDbNeedFix;
	// Target the inner .config-dashboard that wraps the sections
	const container = document.querySelector(
		".config-dashboard > .config-dashboard",
	);
	if (container) {
		container.classList.toggle("storage-needs-fix", needsFix);
	}
}

// ──────────────────────────────────────────────────────────────
// API Configuration
// ──────────────────────────────────────────────────────────────
const CONFIG = {
	spec: {
		list: "/api/v1/spec/repos",
		add: "/api/v1/spec/repos",
		sync_all: "/api/v1/spec/repos/sync-all",
	},
	data: {
		list: "/api/v1/system/data-dirs",
		create: "/api/v1/system/data-dirs/fix",
		clean: "/api/v1/system/data-dirs/clean",
		reset: "/api/v1/system/data-dirs/hard-reset",
	},
	duckdb: {
		status: "/api/v1/system/duckdb",
		create: "/api/v1/system/duckdb",
		clean: "/api/v1/system/duckdb/clean",
		reset: "/api/v1/system/duckdb/hard-reset",
	},
	logging: {
		get: "/api/v1/config/logging",
		save: "/api/v1/config/logging",
	},
	llm: {
		installed: "/api/v1/models/llm/installed",
		search: "/api/v1/models/llm/search",
		files: "/api/v1/models/llm/files",
		download: "/api/v1/models/llm/download",
		delete: "/api/v1/models/llm",
		progress: "/api/v1/models/llm/progress",
	},
	embedding: {
		installed: "/api/v1/models/embedding/installed",
		search: "/api/v1/models/embeddings/search",
		download: "/api/v1/models/embedding/download",
		delete: "/api/v1/models/embedding",
		progress: "/api/v1/models/embedding/progress",
	},
	embeddingFast: {
		installed: "/api/v1/models/embedding-fast/installed",
		progress: "/api/v1/models/embedding-fast/progress",
	},
};

// ──────────────────────────────────────────────────────────────
// State
// ──────────────────────────────────────────────────────────────
let _BACKEND_CONFIG = {};
let selectedLlmRepo = null;
let selectedEmbRepo = null;

try {
	const configDataEl = document.getElementById("backend-config-data");
	if (configDataEl) {
		_BACKEND_CONFIG = JSON.parse(configDataEl.textContent);
	}
} catch (_e) {
	/* ignore parse errors */
}

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────
function escHtml(s) {
	if (s == null) return "";
	return String(s)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function formatBytes(bytes) {
	if (bytes === 0) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${Math.round((bytes / k ** i) * 100) / 100} ${sizes[i]}`;
}

function setStatusText(el, text, ok) {
	if (!el) return;
	el.textContent = text;
	el.className = `global-status${ok ? " ok" : " critical"}`;
}

// ──────────────────────────────────────────────────────────────
// Native <details> group helpers
// ──────────────────────────────────────────────────────────────
function scrollToAndOpen(groupId) {
	const el = document.getElementById(groupId);
	if (el) {
		el.scrollIntoView({ behavior: "smooth", block: "start" });
		if (!el.open) el.open = true;
	}
}

// ──────────────────────────────────────────────────────────────
// System Status (Hero Banner)
// ──────────────────────────────────────────────────────────────
function loadSystemStatus() {
	Promise.all([
		fetch("/api/v1/admin/status")
			.then((r) => r.json())
			.catch(() => ({ data: {} })),
		fetch("/api/v1/llamacpp/status")
			.then((r) => r.json())
			.catch(() => ({})),
		fetch("/api/v1/qdrant/status")
			.then((r) => r.json())
			.catch(() => ({})),
		fetch("/api/v1/system/duckdb")
			.then((r) =>
				r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
			)
			.catch(() => ({})),
		fetch("/api/v1/config/logging")
			.then((r) =>
				r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
			)
			.catch(() => ({})),
	])
		.then((results) => {
			const adminData = results[0].data || {};
			const _llamaInfo = results[1] || {};
			const _qdrantInfo = results[2] || {};
			const duckDbStatus = results[3] || {};
			const _loggingData = results[4] || {};
			const llama = adminData.llama_cpp || {};
			const qdrant = adminData.qdrant || {};

			// Update llama status
			const llamaStatusCard = document.querySelector('[data-service="llama"]');
			if (llamaStatusCard) {
				llamaStatusCard.querySelector(".status-text").textContent =
					llama.status || "unknown";
				llamaStatusCard.className = `status-card ${getStatusCardClass(llama.status)}`;
			}

			// Update qdrant status
			const qdrantStatusCard = document.querySelector(
				'[data-service="qdrant"]',
			);
			if (qdrantStatusCard) {
				qdrantStatusCard.querySelector(".status-text").textContent =
					qdrant.status || "unknown";
				qdrantStatusCard.className = `status-card ${getStatusCardClass(qdrant.status)}`;
			}

			// Update duckdb status
			const duckdbStatusCard = document.querySelector(
				'[data-service="duckdb"]',
			);
			if (duckdbStatusCard) {
				const duckState = duckDbStatus.state || "healthy";
				duckdbStatusCard.querySelector(".status-text").textContent =
					duckState || "unknown";
				duckdbStatusCard.className =
					"status-card " +
					getStatusCardClass(duckState === "healthy" ? "active" : "inactive");
			}

			// Update logging status
			const loggingStatusCard = document.querySelector(
				'[data-service="logging"]',
			);
			if (loggingStatusCard) {
				loggingStatusCard.querySelector(".status-text").textContent = "OK";
				loggingStatusCard.className = "status-card status-card-ok";
			}
		})
		.catch((err) => {
			console.error("Failed to load system status:", err);
		});
}

function getStatusCardClass(status) {
	if (status === "active" || status === "healthy" || status === "ready") {
		return "status-card-ok";
	} else if (
		status === "error" ||
		status === "missing" ||
		status === "dirty_tables"
	) {
		return "status-card-error";
	} else {
		return "status-card-warning";
	}
}

// ──────────────────────────────────────────────────────────────
// Configuration (OS / GPU)
// ──────────────────────────────────────────────────────────────
function applyBackendConfig(cfg) {
	const hw = cfg?.Hardware || {};
	const osSel = document.getElementById("os-select");
	const gpuSel = document.getElementById("gpu-select");
	if (osSel) osSel.value = hw.os || "windows";
	if (gpuSel) gpuSel.value = hw.gpu || "cpu";
}

function saveBackendConfig() {
	const statusEl = document.getElementById("config-status");
	statusEl.textContent = "Saving...";
	statusEl.className = "status-message";

	fetch("/api/v1/config", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			backend: {
				os: document.getElementById("os-select").value,
				gpu_type: document.getElementById("gpu-select").value,
			},
		}),
	})
		.then((r) => r.json())
		.then((data) => {
			statusEl.textContent =
				data.status === "success"
					? data.message || "Configuration saved"
					: data.error || "Save failed";
			statusEl.className = `status-message ${data.status === "success" ? "success" : "error"}`;
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
		});
}

// ──────────────────────────────────────────────────────────────
// Data directories
// ──────────────────────────────────────────────────────────────
const renderDataDirs = (dirs) => {
	let readyCount = 0;
	let missingCount = 0;
	for (let i = 0; i < dirs.length; i++) {
		const d = dirs[i];
		if (d.is_healthy) readyCount++;
		else missingCount++;
	}

	const statusEl = document.getElementById("data-global-status");
	statusEl.className = "global-status";
	if (readyCount === dirs.length) statusEl.classList.add("ok");

	const dotClass =
		readyCount === dirs.length
			? "data-dot-ok"
			: missingCount > 0 && readyCount === 0
				? "data-dot-missing"
				: "data-dot-warn";

	const summaryClass =
		readyCount === dirs.length
			? "text-success"
			: missingCount > 0 && readyCount === 0
				? "text-danger"
				: "text-warning";

	const summaryLabel =
		readyCount === dirs.length
			? "READY"
			: missingCount > 0 && readyCount === 0
				? "ERROR"
				: "PARTIAL";

	const needsFix = readyCount !== dirs.length;
	_dataDirsNeedFix = needsFix;
	_updateStorageLock();

	const fixBtnHtml = needsFix
		? '<button class="btn btn-primary btn-sm" onclick="Config.createDataDirs()">Fix</button>'
		: '<button class="btn btn-primary btn-sm" disabled>Fix</button>';

	const hardResetHtml = needsFix
		? '<button class="btn btn-danger btn-sm" disabled title="Apply Fix first">Hard Reset</button>'
		: '<button class="btn btn-danger btn-sm" onclick="Config.resetDataDirs()">Hard Reset</button>';

	const listEl = document.getElementById("data-dirs-list");
	listEl.innerHTML =
		'<div class="data-row">' +
		'  <span class="' +
		dotClass +
		' status-dot"></span>' +
		'  <span class="label">Data Folders (' +
		readyCount +
		"/" +
		dirs.length +
		" ready)</span>" +
		'  <span class="' +
		summaryClass +
		' data-status-label">' +
		summaryLabel +
		"</span>" +
		'  <span class="data-action-buttons">' +
		fixBtnHtml +
		'  <button class="btn btn-warning btn-sm" disabled>Clean</button>' +
		hardResetHtml +
		"  </span>" +
		"</div>";
};

function checkDataDirs() {
	fetch(CONFIG.data.list)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((dirs) => {
			renderDataDirs(dirs);
		})
		.catch((e) => {
			console.error(e);
			const listEl = document.getElementById("data-dirs-list");
			if (listEl)
				listEl.innerHTML =
					'<div class="data-row">' +
					'  <span class="label error-text">Error loading data: ' +
					escHtml(e.message) +
					"</span>" +
					"</div>";
		});
}

function createDataDirs() {
	fetch(CONFIG.data.create, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDataDirs();
		})
		.catch((e) => {
			showToast(`Error: ${e.message}`, "error");
		});
}

async function cleanDataDirs() {
	if (
		!(await showConfirm(
			"Clean all data directories? Non-official contents will be deleted.",
		))
	)
		return;
	try {
		const r = await fetch(CONFIG.data.clean, { method: "POST" });
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		checkDataDirs();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	}
}

async function resetDataDirs() {
	if (
		!(await showConfirm(
			"\u26a0\ufe0f HARD RESET \u2014 This will permanently delete ALL data in the data/ directory. Continue?",
		))
	)
		return;
	try {
		const r = await fetch(CONFIG.data.reset, { method: "POST" });
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		checkDataDirs();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	}
}

// ──────────────────────────────────────────────────────────────
// DuckDB
// ──────────────────────────────────────────────────────────────
function renderDuckDbStatus(status) {
	const el = document.getElementById("duckdb-status");
	if (!el) return;

	let dotClass, labelClass, summaryLabel;
	const st = status.state || "healthy";

	if (st === "healthy") {
		dotClass = "data-dot-ok";
		labelClass = "text-success";
		summaryLabel = "READY";
	} else if (st === "dirty_tables") {
		dotClass = "data-dot-warn";
		labelClass = "text-warning";
		summaryLabel = "DIRTY";
	} else if (st === "excess_tables") {
		dotClass = "data-dot-warn";
		labelClass = "text-warning";
		summaryLabel = "EXCESS";
	} else if (st === "missing") {
		dotClass = "data-dot-missing";
		labelClass = "text-danger";
		summaryLabel = "MISSING";
	} else {
		dotClass = "data-dot-missing";
		labelClass = "text-danger";
		summaryLabel = `UNKNOWN (${st})`;
	}

	const size =
		status.file_size > 0 ? ` (${formatBytes(status.file_size)})` : "";
	const needsFix = status.needs_fix;
	_duckDbNeedFix = needsFix;
	_updateStorageLock();
	const fixBtnHtml = needsFix
		? '<button class="btn btn-primary btn-sm" onclick="Config.createDuckDb()">Fix</button>'
		: '<button class="btn btn-primary btn-sm" disabled>Fix</button>';
	const cleanBtnHtml =
		status.needs_clean && !needsFix
			? '<button class="btn btn-warning btn-sm" onclick="Config.cleanDuckDb()">Clean</button>'
			: '<button class="btn btn-warning btn-sm" disabled>Clean</button>';
	const resetHtml = needsFix
		? '<button class="btn btn-danger btn-sm" disabled title="Apply Fix first">Hard Reset</button>'
		: '<button class="btn btn-danger btn-sm" onclick="Config.resetDuckDb()">Hard Reset</button>';

	el.innerHTML =
		'<div class="data-row">' +
		'  <span class="' +
		dotClass +
		' status-dot"></span>' +
		'  <span class="label">DuckDB' +
		size +
		"</span>" +
		'  <span class="' +
		labelClass +
		' data-status-label">' +
		summaryLabel +
		"</span>" +
		'  <span class="data-action-buttons">' +
		fixBtnHtml +
		" " +
		cleanBtnHtml +
		" " +
		resetHtml +
		"  </span>" +
		"</div>";
}

function checkDuckDbStatus() {
	fetch(CONFIG.duckdb.status)
		.then((r) => {
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			return r.text().then((t) => JSON.parse(t));
		})
		.then((status) => {
			renderDuckDbStatus(status);
		})
		.catch((e) => {
			console.error(e);
			const el = document.getElementById("duckdb-status");
			if (el)
				el.innerHTML =
					'<span class="label error-text">Error loading DuckDB: ' +
					escHtml(e.message) +
					"</span>";
		});
}

function createDuckDb() {
	fetch(CONFIG.duckdb.create, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDuckDbStatus();
		})
		.catch((e) => {
			showToast(`Error: ${e.message}`, "error");
		});
}

async function cleanDuckDb() {
	if (
		!(await showConfirm(
			"This will remove excess tables not in the schema. Continue?",
		))
	)
		return;
	try {
		const r = await fetch(CONFIG.duckdb.clean, { method: "POST" });
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		checkDuckDbStatus();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	}
}

async function resetDuckDb() {
	if (
		!(await showConfirm(
			"\u26a0\ufe0f HARD RESET \u2014 This will permanently delete the DuckDB database and create a fresh one. Continue?",
		))
	)
		return;
	try {
		const r = await fetch(CONFIG.duckdb.reset, { method: "POST" });
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		checkDuckDbStatus();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	}
}

// ──────────────────────────────────────────────────────────────
// Logging
// ──────────────────────────────────────────────────────────────
function renderLoggingConfig(data) {
	const levelSelect = document.getElementById("log-level-select");
	const maxSizeInput = document.getElementById("log-max-size-input");
	const maxFileInput = document.getElementById("log-max-file-input");
	const cleanToggle = document.getElementById("log-clean-at-startup");
	const _toggleLabel = document.getElementById("log-clean-toggle");

	setStatusText(
		document.getElementById("logging-status"),
		"Configuration loaded",
		true,
	);

	if (levelSelect) levelSelect.value = data.level || "INFO";
	if (maxSizeInput) maxSizeInput.value = data.log_max_size || "10M";
	if (maxFileInput) maxFileInput.value = data.log_max_file || 5;
	if (cleanToggle) {
		cleanToggle.checked = data.clean_at_startup || false;
		cleanToggle.onchange = () => {
			const lbl = document.getElementById("log-clean-label");
			if (lbl) lbl.textContent = cleanToggle.checked ? "Yes" : "No";
		};
	}
	const cleanLabel = document.getElementById("log-clean-label");
	if (cleanLabel) {
		cleanLabel.textContent = data.clean_at_startup ? "Yes" : "No";
	}
}

function checkLoggingConfig() {
	fetch(CONFIG.logging.get)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			if (data.status === "success") renderLoggingConfig(data.data);
			else
				setStatusText(
					document.getElementById("logging-status"),
					"Error loading logging config",
					false,
				);
		})
		.catch((e) => {
			console.error(e);
			setStatusText(
				document.getElementById("logging-status"),
				`Error loading logging: ${e.message}`,
				false,
			);
		});
}

function saveLoggingConfig() {
	const statusEl = document.getElementById("logging-config-status");
	const payload = {
		level: document.getElementById("log-level-select").value,
		log_max_size: document.getElementById("log-max-size-input").value,
		log_max_file: parseInt(
			document.getElementById("log-max-file-input").value,
			10,
		),
		clean_at_startup: document.getElementById("log-clean-at-startup").checked,
	};

	statusEl.textContent = "Saving...";
	statusEl.className = "status-message";

	fetch(CONFIG.logging.save, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	})
		.then((r) => r.json())
		.then((data) => {
			if (data.status === "success") {
				statusEl.textContent = data.message || "Logging configuration saved";
				statusEl.className = "status-message success";
			} else {
				statusEl.textContent = data.error || "Save failed";
				statusEl.className = "status-message error";
			}
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
		});
}

// ──────────────────────────────────────────────────────────────
// Backend Management (llama.cpp + Qdrant)
// ──────────────────────────────────────────────────────────────
function makeProgressBar(prefix) {
	return new ProgressBar({
		container: document.getElementById(`${prefix}-progress-container`),
		fill: document.getElementById(`${prefix}-progress-fill`),
		text: document.getElementById(`${prefix}-progress-text`),
	});
}

function loadBackendStatus() {
	Promise.all([
		fetch("/api/v1/admin/status")
			.then((r) => r.json())
			.catch(() => ({ data: {} })),
		fetch("/api/v1/llamacpp/status")
			.then((r) => r.json())
			.catch(() => ({})),
		fetch("/api/v1/qdrant/status")
			.then((r) => r.json())
			.catch(() => ({})),
		fetch("/api/v1/config")
			.then((r) =>
				r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
			)
			.catch(() => ({ data: {} })),
	])
		.then((results) => {
			const adminData = results[0].data || {};
			const llamaInfo = results[1] || {};
			const qdrantInfo = results[2] || {};
			const configData = results[3].data || {};
			const llama = adminData.llama_cpp || {};
			const qdrant = adminData.qdrant || {};

			function setStatus(containerId, statusText, statusClass) {
				const container = document.getElementById(containerId);
				const dot = container.querySelector(".status-dot");
				const textSpans = container.querySelectorAll("span:not(.status-dot)");
				if (dot)
					dot.className = `status-dot status-${statusClass || "unknown"}`;
				if (textSpans.length > 0)
					textSpans[textSpans.length - 1].textContent = statusText || "unknown";
			}

			setStatus(
				"llama-status",
				llama.status || "unknown",
				llama.status === "active"
					? "ok"
					: llama.status === "inactive"
						? "error"
						: "warning",
			);
			setStatus(
				"qdrant-status",
				qdrant.status || "unknown",
				qdrant.status === "active"
					? "ok"
					: qdrant.status === "inactive"
						? "error"
						: "warning",
			);

			const isLlamaExternal = llamaInfo.mode === "external";
			document.getElementById("llama-start-btn").disabled = isLlamaExternal;
			document.getElementById("llama-stop-btn").disabled = isLlamaExternal;
			document.getElementById("llama-download-btn").disabled = isLlamaExternal;

			const isQdrantExternal = qdrantInfo.mode === "external";
			const qdrantStartBtn = document.getElementById("qdrant-start-btn");
			const qdrantStopBtn = document.getElementById("qdrant-stop-btn");
			const qdrantDownloadBtn = document.getElementById("qdrant-download-btn");
			if (qdrantStartBtn) qdrantStartBtn.disabled = isQdrantExternal;
			if (qdrantStopBtn) qdrantStopBtn.disabled = isQdrantExternal;
			if (qdrantDownloadBtn) qdrantDownloadBtn.disabled = isQdrantExternal;

			const lv = (llamaInfo.current_version || "").replace(/^0$/, "");
			loadReleaseTags("llama-release-select", "llama.cpp", { value: lv });

			const qv = (qdrantInfo.current_version || "").replace(/^0$/, "");
			if (qv && qv !== "unknown" && qv !== "Not installed") {
				loadReleaseTags("qdrant-release-select", "qdrant", { value: qv });
			} else {
				loadReleaseTags("qdrant-release-select", "qdrant");
			}

			const uv = (qdrantInfo.webui_version || "").replace(/^0$/, "");
			if (uv && uv !== "unknown" && uv !== "Not installed") {
				loadReleaseTags("qdrant-ui-release-select", "qdrant-web-ui", {
					value: uv,
				});
			} else {
				loadReleaseTags("qdrant-ui-release-select", "qdrant-web-ui");
			}

			// Populate new backend service controls from config
			const services =
				configData.services ||
				configData.backend?.services ||
				_BACKEND_CONFIG.services ||
				{};
			const llamaSvc = services.llama || {};
			const qdrantSvc = services.qdrant || {};

			const llamaUrlInput = document.getElementById("llama-base-url");
			if (llamaUrlInput)
				llamaUrlInput.value = llamaSvc.base_url || "http://127.0.0.1:8080";

			const llamaManageSlider = document.getElementById(
				"llama-manage-internally",
			);
			if (llamaManageSlider)
				llamaManageSlider.checked = llamaSvc.manage_internally !== false;
			const llamaModeLabel = document.getElementById("llama-mode-label");
			if (llamaModeLabel)
				llamaModeLabel.textContent =
					llamaSvc.manage_internally !== false ? "Internal" : "External";
			updateServiceControls("llama", llamaSvc.manage_internally !== false);

			const llamaAutostartSlider = document.getElementById(
				"llama-autorun-at-startup",
			);
			if (llamaAutostartSlider)
				llamaAutostartSlider.checked = llamaSvc.autorun_at_startup !== false;
			const llamaAutostartLabel = document.getElementById(
				"llama-autostart-label",
			);
			if (llamaAutostartLabel)
				llamaAutostartLabel.textContent =
					llamaSvc.autorun_at_startup !== false ? "Yes" : "No";

			const qdrantUrlInput = document.getElementById("qdrant-base-url");
			if (qdrantUrlInput)
				qdrantUrlInput.value = qdrantSvc.base_url || "http://127.0.0.1:6333";

			const qdrantManageSlider = document.getElementById(
				"qdrant-manage-internally",
			);
			if (qdrantManageSlider)
				qdrantManageSlider.checked = qdrantSvc.manage_internally !== false;
			const qdrantModeLabel = document.getElementById("qdrant-mode-label");
			if (qdrantModeLabel)
				qdrantModeLabel.textContent =
					qdrantSvc.manage_internally !== false ? "Internal" : "External";
			updateServiceControls("qdrant", qdrantSvc.manage_internally !== false);

			const qdrantAutostartSlider = document.getElementById(
				"qdrant-autorun-at-startup",
			);
			if (qdrantAutostartSlider)
				qdrantAutostartSlider.checked = qdrantSvc.autorun_at_startup !== false;
			const qdrantAutostartLabel = document.getElementById(
				"qdrant-autostart-label",
			);
			if (qdrantAutostartLabel)
				qdrantAutostartLabel.textContent =
					qdrantSvc.autorun_at_startup !== false ? "Yes" : "No";

			// Build summary
			let _summaryHtml = "";
			_summaryHtml +=
				'<div class="data-row"><span class="status-dot ' +
				(llama.status === "active" ? "data-dot-ok" : "data-dot-warn") +
				'"></span><span class="label">llama.cpp</span><span>' +
				(llama.status || "unknown") +
				"</span></div>";
			_summaryHtml +=
				'<div class="data-row" style="margin-top: 4px;"><span class="status-dot ' +
				(qdrant.status === "active" ? "data-dot-ok" : "data-dot-warn") +
				'"></span><span class="label">Qdrant</span><span>' +
				(qdrant.status || "unknown") +
				"</span></div>";
		})
		.catch(() => {
			document.getElementById("llama-status").innerHTML =
				'<p class="error">Failed to load status</p>';
			document.getElementById("qdrant-status").innerHTML =
				'<p class="error">Failed to load status</p>';
		});
}

// ──────────────────────────────────────────────────────────────
// Backend Service Config Toggles
// ──────────────────────────────────────────────────────────────
function updateBackendServiceConfig(service, field, value) {
	const nested = {};
	nested[field] = value;
	const svc = {};
	svc[service] = nested;
	fetch("/api/v1/config", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			backend: { services: svc },
		}),
	})
		.then((r) => r.json())
		.then((data) => {
			if (data.status !== "success") {
				console.error(`Failed to update ${service}.${field}:`, data.error);
			}
		})
		.catch((err) => {
			console.error(`Error updating ${service}.${field}:`, err);
		});
}

function saveBackendServiceConfig(service) {
	const baseUrl = document.getElementById(`${service}-base-url`);
	const manage = document.getElementById(`${service}-manage-internally`);
	const autorun = document.getElementById(`${service}-autorun-at-startup`);
	const payload = {
		backend: {
			services: {},
		},
	};
	payload.backend.services[service] = {};
	if (baseUrl) payload.backend.services[service].base_url = baseUrl.value;
	if (manage)
		payload.backend.services[service].manage_internally = manage.checked;
	if (autorun)
		payload.backend.services[service].autorun_at_startup = autorun.checked;

	const statusEl = document.getElementById(`${service}-status-text`);
	if (statusEl) statusEl.textContent = "Saving...";

	fetch("/api/v1/config", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	})
		.then((r) => r.json())
		.then((data) => {
			if (statusEl) {
				statusEl.textContent =
					data.status === "success"
						? data.message || "Configuration saved"
						: data.error || "Save failed";
			}
		})
		.catch((err) => {
			if (statusEl) statusEl.textContent = `Error: ${err.message}`;
		});
}

function updateServiceControls(service, isInternal) {
	const startBtn = document.getElementById(`${service}-start-btn`);
	const stopBtn = document.getElementById(`${service}-stop-btn`);
	const downloadBtn = document.getElementById(`${service}-download-btn`);
	const releaseSelect = document.getElementById(`${service}-release-select`);
	const autostartSlider = document.getElementById(
		`${service}-autorun-at-startup`,
	);
	const autostartToggle = document.getElementById(
		`${service}-autostart-toggle`,
	);

	if (isInternal) {
		if (startBtn) startBtn.disabled = false;
		if (stopBtn) stopBtn.disabled = false;
		if (downloadBtn) downloadBtn.disabled = false;
		if (releaseSelect) releaseSelect.disabled = false;
		if (autostartSlider) autostartSlider.disabled = false;
		if (autostartToggle) autostartToggle.style.opacity = "1";
	} else {
		if (startBtn) startBtn.disabled = true;
		if (stopBtn) stopBtn.disabled = true;
		if (downloadBtn) downloadBtn.disabled = true;
		if (releaseSelect) releaseSelect.disabled = true;
		if (autostartSlider) {
			autostartSlider.disabled = true;
			autostartSlider.checked = false;
			updateBackendServiceConfig(service, "autorun_at_startup", false);
		}
		if (autostartToggle) autostartToggle.style.opacity = "0.5";
		const label = document.getElementById(`${service}-autostart-label`);
		if (label) label.textContent = "Off";
	}
}

function onLlamaModeChange() {
	const cb = document.getElementById("llama-manage-internally");
	const checked = cb.checked;
	updateBackendServiceConfig("llama", "manage_internally", checked);
	const label = document.getElementById("llama-mode-label");
	if (label) label.textContent = checked ? "Internal" : "External";
	updateServiceControls("llama", checked);
}

function onLlamaAutostartChange() {
	const cb = document.getElementById("llama-autorun-at-startup");
	const checked = cb.checked;
	updateBackendServiceConfig("llama", "autorun_at_startup", checked);
	const label = document.getElementById("llama-autostart-label");
	if (label) label.textContent = checked ? "Yes" : "No";
}

function onQdrantModeChange() {
	const cb = document.getElementById("qdrant-manage-internally");
	const checked = cb.checked;
	updateBackendServiceConfig("qdrant", "manage_internally", checked);
	const label = document.getElementById("qdrant-mode-label");
	if (label) label.textContent = checked ? "Internal" : "External";
	updateServiceControls("qdrant", checked);
}

function onQdrantAutostartChange() {
	const cb = document.getElementById("qdrant-autorun-at-startup");
	const checked = cb.checked;
	updateBackendServiceConfig("qdrant", "autorun_at_startup", checked);
	const label = document.getElementById("qdrant-autostart-label");
	if (label) label.textContent = checked ? "Yes" : "No";
}

function downloadLlama() {
	const btn = document.getElementById("llama-download-btn");
	if (btn?.disabled) return;
	if (btn) btn.disabled = true;
	const sel = document.getElementById("llama-release-select");
	const version = sel ? sel.value : "";
	const url =
		"/api/v1/llamacpp/download" +
		(version ? `?version=${encodeURIComponent(version)}` : "");
	const pb = makeProgressBar("llama");
	const statusEl = document.getElementById("llama-download-status");
	statusEl.textContent = "Starting download...";
	statusEl.className = "status-message";
	pb.show();
	fetch(url, { method: "POST" })
		.then((r) => r.json())
		.then((data) => {
			if (data.download_id) {
				statusEl.textContent = "Download started";
				statusEl.className = "status-message success";
				ProgressBar.pollDownload({
					endpoint: "/api/v1/llamacpp/status",
					downloadId: data.download_id,
					onUpdate: (pct, text) => {
						pb.setProgress(pct);
						pb.setText(text);
					},
					onComplete: () => {
						pb.hide();
						statusEl.textContent = "Download completed!";
						if (btn) btn.disabled = false;
						scanLocalVersions();
						loadBackendStatus();
					},
					onError: (msg) => {
						pb.hide();
						statusEl.textContent = `Download failed: ${msg}`;
						statusEl.className = "status-message error";
						if (btn) btn.disabled = false;
					},
				});
			} else {
				statusEl.textContent =
					data.message || data.error || "Download completed";
				statusEl.className = `status-message ${data.error ? "error" : "success"}`;
				pb.hide();
				if (btn) btn.disabled = false;
			}
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
			pb.hide();
			if (btn) btn.disabled = false;
		});
}

function downloadQdrantBinary() {
	const pb = makeProgressBar("qdrant");
	const statusEl = document.getElementById("qdrant-download-status");
	statusEl.textContent = "Starting download...";
	statusEl.className = "status-message";
	pb.show();
	const sel = document.getElementById("qdrant-release-select");
	const version = sel ? sel.value : "latest";
	fetch("/api/v1/qdrant", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			action: "download_update",
			payload: { action: "download_update", version: version, force: false },
		}),
	})
		.then((r) => r.json())
		.then((data) => {
			if (data.data?.download_id) {
				statusEl.textContent = "Download started";
				statusEl.className = "status-message success";
				ProgressBar.pollDownload({
					endpoint: "/api/v1/qdrant/status",
					downloadId: data.data.download_id,
					onUpdate: (pct, text) => {
						pb.setProgress(pct);
						pb.setText(text);
					},
					onComplete: () => {
						pb.hide();
						statusEl.textContent = "Download completed!";
						scanLocalVersions();
						loadBackendStatus();
					},
					onError: (msg) => {
						pb.hide();
						statusEl.textContent = `Download failed: ${msg}`;
						statusEl.className = "status-message error";
					},
				});
			} else {
				statusEl.textContent = data.message || data.error || "Download failed";
				statusEl.className = "status-message error";
				pb.hide();
				loadBackendStatus();
			}
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
			pb.hide();
		});
}

function downloadQdrantUI() {
	const pb = makeProgressBar("qdrant");
	const statusEl = document.getElementById("qdrant-download-status");
	statusEl.textContent = "Starting download...";
	statusEl.className = "status-message";
	pb.show();
	const sel = document.getElementById("qdrant-ui-release-select");
	const version = sel ? sel.value : "latest";
	fetch("/api/v1/qdrant", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			action: "download_update",
			payload: {
				action: "download_update",
				version: version,
				force: false,
				service: "qdrant-web-ui",
			},
		}),
	})
		.then((r) => r.json())
		.then((data) => {
			if (data.data?.download_id) {
				statusEl.textContent = "Download started";
				statusEl.className = "status-message success";
				ProgressBar.pollDownload({
					endpoint: "/api/v1/qdrant/status",
					downloadId: data.data.download_id,
					onUpdate: (pct, text) => {
						pb.setProgress(pct);
						pb.setText(text);
					},
					onComplete: () => {
						pb.hide();
						statusEl.textContent = "Web UI downloaded!";
						scanLocalVersions();
						loadBackendStatus();
					},
					onError: (msg) => {
						pb.hide();
						statusEl.textContent = `Download failed: ${msg}`;
						statusEl.className = "status-message error";
					},
				});
			} else {
				statusEl.textContent = data.message || data.error || "Download failed";
				statusEl.className = "status-message error";
				pb.hide();
				loadBackendStatus();
			}
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
			pb.hide();
		});
}

function startService(service) {
	fetch("/api/v1/orchestration/backend", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ action: "start", service: service }),
	})
		.then((r) => r.json())
		.then((data) => {
			const msg =
				data.data?.message || data.data?.error || data.error || "Started";
			showToast(msg, data.data?.error || data.error ? "error" : "success");
			loadBackendStatus();
		});
}

async function stopService(service) {
	if (!(await showConfirm(`Stop ${service}?`))) return;
	fetch("/api/v1/orchestration/backend", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ action: "stop", service: service }),
	})
		.then((r) => r.json())
		.then((data) => {
			const msg =
				data.data?.message || data.data?.error || data.error || "Stopped";
			showToast(msg, data.data?.error || data.error ? "error" : "success");
			loadBackendStatus();
		});
}

function openQdrantUI() {
	window.open("http://127.0.0.1:6333/dashboard", "_blank");
}

function loadReleaseTimestamps() {
	fetch("/api/v1/releases/status/timestamps")
		.then((r) => r.json())
		.then((data) => {
			const ts = data.timestamps || {};
			let latest = "";
			for (const key in ts) {
				if (ts[key] && (!latest || ts[key] > latest)) latest = ts[key];
			}
			const el = document.getElementById("releases-last-update");
			if (el) {
				if (latest) {
					const d = new Date(latest);
					el.textContent = `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
				} else {
					el.textContent = "Never";
				}
			}
		})
		.catch(() => {
			const el = document.getElementById("releases-last-update");
			if (el) el.textContent = "—";
		});
}

function loadReleasesTable() {
	fetch("/api/v1/releases/all-releases")
		.then((r) => r.json())
		.then((data) => {
			const tableEl = document.getElementById("releases-table");
			if (!tableEl) return;

			const releases = data.releases || [];
			const versions = data.installed_versions || {};

			if (releases.length === 0 && Object.keys(versions).length === 0) {
				tableEl.innerHTML =
					'<p style="font-style:italic;color:var(--text-card-body);"><i>undef</i></p>';
				return;
			}

			let html =
				'<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">';
			html +=
				'<thead><tr style="border-bottom:1px solid var(--layout-card-border);">' +
				'<th style="padding:8px;text-align:left;">Service</th>' +
				'<th style="padding:8px;text-align:left;">Latest Tag</th>' +
				'<th style="padding:8px;text-align:left;">Installed Version</th>' +
				'<th style="padding:8px;text-align:left;">Last Scanned</th>' +
				'<th style="padding:8px;text-align:left;">Published At</th>' +
				'<th style="padding:8px;text-align:left;">Fetched At</th>' +
				"</tr></thead>";
			html += "<tbody>";

			// Define known services in desired order
			const knownServices = ["llama.cpp", "qdrant", "qdrant-web-ui"];

			for (let si = 0; si < knownServices.length; si++) {
				const svc = knownServices[si];
				let release = null;
				for (let ri = 0; ri < releases.length; ri++) {
					if (releases[ri].service === svc) {
						release = releases[ri];
						break;
					}
				}
				const installed = versions[svc] || null;

				html +=
					'<tr style="border-bottom:1px solid var(--layout-card-border);">' +
					'<td style="padding:8px;">' +
					svc +
					"</td>" +
					'<td style="padding:8px;">' +
					(release ? release.last_tag_name || "—" : "—") +
					"</td>" +
					'<td style="padding:8px;">' +
					(installed ? installed.version : "—") +
					"</td>" +
					'<td style="padding:8px;">' +
					(installed
						? installed.scanned_at
							? new Date(installed.scanned_at).toLocaleString()
							: "—"
						: "—") +
					"</td>" +
					'<td style="padding:8px;">' +
					(release ? release.published_at || "—" : "—") +
					"</td>" +
					'<td style="padding:8px;">' +
					(release ? release.fetched_at || "—" : "—") +
					"</td>" +
					"</tr>";
			}

			// Add any extra releases not in knownServices
			for (let ri = 0; ri < releases.length; ri++) {
				const r = releases[ri];
				if (knownServices.indexOf(r.service) === -1) {
					const extInstalled = versions[r.service] || null;
					html +=
						'<tr style="border-bottom:1px solid var(--layout-card-border);">' +
						'<td style="padding:8px;">' +
						(r.service || "—") +
						"</td>" +
						'<td style="padding:8px;">' +
						(r.last_tag_name || "—") +
						"</td>" +
						'<td style="padding:8px;">' +
						(extInstalled ? extInstalled.version : "—") +
						"</td>" +
						'<td style="padding:8px;">' +
						(extInstalled
							? extInstalled.scanned_at
								? new Date(extInstalled.scanned_at).toLocaleString()
								: "—"
							: "—") +
						"</td>" +
						'<td style="padding:8px;">' +
						(r.published_at || "—") +
						"</td>" +
						'<td style="padding:8px;">' +
						(r.fetched_at || "—") +
						"</td>" +
						"</tr>";
				}
			}

			html += "</tbody></table></div>";

			tableEl.innerHTML = html;
		})
		.catch((_err) => {
			const tableEl = document.getElementById("releases-table");
			if (tableEl)
				tableEl.innerHTML = '<p class="error">Failed to load releases</p>';
		});
}

function refreshReleases() {
	const statusEl = document.getElementById("releases-refresh-status");
	if (statusEl) {
		statusEl.textContent = "Refreshing...";
		statusEl.className = "status-message";
	}
	fetch("/api/v1/releases/refresh", { method: "POST" })
		.then((r) => r.json())
		.then((data) => {
			if (data.errors) {
				const msgs = Object.values(data.errors);
				const rateLimited = msgs.some((m) => m.indexOf("rate limit") !== -1);
				if (rateLimited) {
					showToast(
						"GitHub API rate limit reached. Please wait a few minutes and try again.",
						"error",
					);
				}
			}
			loadBackendStatus();
			loadReleaseTimestamps();
			loadReleasesTable();
			if (statusEl) {
				statusEl.textContent = "Done";
				statusEl.className = "status-message success";
			}
		})
		.catch(() => {
			showToast("Failed to refresh releases. Check your connection.", "error");
			if (statusEl) {
				statusEl.textContent = "Failed";
				statusEl.className = "status-message error";
			}
		});
}

function scanLocalVersions() {
	const statusEl = document.getElementById("releases-refresh-status");
	if (statusEl) {
		statusEl.textContent = "Scanning local versions...";
		statusEl.className = "status-message";
	}
	fetch("/api/v1/releases/scan-versions", { method: "POST" })
		.then((r) => r.json())
		.then((data) => {
			if (data.status === "success") {
				loadReleasesTable();
				if (statusEl) {
					statusEl.textContent = "Versions scanned successfully";
					statusEl.className = "status-message success";
				}
			} else {
				if (statusEl) {
					statusEl.textContent = `Scan failed: ${data.error || "Unknown error"}`;
					statusEl.className = "status-message error";
				}
			}
		})
		.catch((err) => {
			if (statusEl) {
				statusEl.textContent = `Scan failed: ${err.message}`;
				statusEl.className = "status-message error";
			}
		});
}

// ──────────────────────────────────────────────────────────────
// LLM Management
// ──────────────────────────────────────────────────────────────
function renderLlmModels(models) {
	const listEl = document.getElementById("llm-models-list");
	const statusEl = document.getElementById("llm-global-status");
	const textEl = document.getElementById("llm-global-text");
	const btnDownload = document.getElementById("btn-download-llm");
	const btnDelete = document.getElementById("btn-delete-llm");

	statusEl.className = "global-status";

	if (!models || models.length === 0) {
		statusEl.classList.add("warn");
		textEl.textContent = "No LLM models installed";
		btnDownload.style.display = "inline-block";
		btnDelete.style.display = "none";
		listEl.innerHTML =
			'<p class="info-text info-text-with-margin">Search and download a model to get started.</p>';
		return;
	}

	statusEl.classList.add("ok");
	textEl.textContent = `${models.length} model(s) installed`;
	btnDownload.style.display = "none";
	btnDelete.style.display = "inline-block";

	let html = '<table class="model-table"><tbody>';
	for (let i = 0; i < models.length; i++) {
		const m = models[i];
		html += "<tr>";
		html +=
			'<td class="model-name" onclick="Config.selectLlmModel(\'' +
			escHtml(m.repo_id) +
			"')\">" +
			escHtml(m.repo_id) +
			"</td>";
		const filesHtml = m.files
			? m.files
					.map((f) => {
						const sizeGb = (f.size / (1024 * 1024 * 1024)).toFixed(1);
						return `${escHtml(f.filename)} (${sizeGb} GB)`;
					})
					.join("<br>")
			: "";
		html += `<td>${filesHtml}</td>`;
		html += "</tr>";
	}
	html += "</tbody></table>";
	listEl.innerHTML = html;
	selectedLlmRepo = models[0].repo_id;
}

function checkLlmModels() {
	fetch(CONFIG.llm.installed)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			renderLlmModels(data.models);
		})
		.catch((e) => {
			console.error(e);
			const statusEl = document.getElementById("llm-global-status");
			const textEl = document.getElementById("llm-global-text");
			statusEl.className = "global-status critical";
			textEl.textContent = "Error loading LLM models";
		});
}

function selectLlmModel(repoId) {
	selectedLlmRepo = repoId;
	const listEl = document.getElementById("llm-models-list");
	const rows = listEl.querySelectorAll(".model-name");
	for (let i = 0; i < rows.length; i++) {
		rows[i].style.fontWeight = "normal";
		rows[i].style.color = "#007bff";
	}
	if (rows.length > 0) {
		for (let j = 0; j < rows.length; j++) {
			if (rows[j].textContent === repoId) {
				rows[j].style.fontWeight = "bold";
				rows[j].style.color = "#0056b3";
				break;
			}
		}
	}
}

function _setLlmBusy(busy) {
	const dl = document.getElementById("btn-download-llm");
	const del = document.getElementById("btn-delete-llm");
	if (dl) {
		dl.disabled = busy;
		dl.textContent = busy ? "Downloading..." : "Download";
	}
	if (del) del.disabled = busy;
}

function downloadLlmModel(filename) {
	if (!selectedLlmRepo) return;
	_setLlmBusy(true);
	let url = `${CONFIG.llm.download}?repo_id=${encodeURIComponent(selectedLlmRepo)}`;
	if (filename) {
		url += `&filename=${encodeURIComponent(filename)}`;
	}
	fetch(url, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			const checkProgress = setInterval(() => {
				fetch(
					CONFIG.llm.progress +
						"?repo_id=" +
						encodeURIComponent(selectedLlmRepo),
				)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === "completed") {
							clearInterval(checkProgress);
							_setLlmBusy(false);
							checkLlmModels();
						} else if (data.status?.startsWith("error")) {
							clearInterval(checkProgress);
							_setLlmBusy(false);
							showToast(`Download failed: ${data.status}`, "error");
						}
					})
					.catch(() => {});
			}, 1000);
		})
		.catch((e) => {
			_setLlmBusy(false);
			showToast(`Error: ${e.message}`, "error");
		});
}

function downloadLlmModelDirect(repoId, filename) {
	selectedLlmRepo = repoId;
	downloadLlmModel(filename);
}

async function deleteLlmModel() {
	if (!selectedLlmRepo) return;
	if (!(await showConfirm(`Delete model ${selectedLlmRepo}?`))) return;
	_setLlmBusy(true);
	try {
		const r = await fetch(
			`${CONFIG.llm.delete}/${encodeURIComponent(selectedLlmRepo)}`,
			{
				method: "DELETE",
			},
		);
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		selectedLlmRepo = null;
		checkLlmModels();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	} finally {
		_setLlmBusy(false);
	}
}

// ──────────────────────────────────────────────────────────────
// Embedding Management
// ──────────────────────────────────────────────────────────────
function renderEmbModels(models) {
	const listEl = document.getElementById("emb-models-list");
	const statusEl = document.getElementById("emb-global-status");
	const textEl = document.getElementById("emb-global-text");
	const btnDownload = document.getElementById("btn-download-emb");
	const btnDelete = document.getElementById("btn-delete-emb");

	statusEl.className = "global-status";

	if (!models || models.length === 0) {
		statusEl.classList.add("warn");
		textEl.textContent = "No embedding models installed";
		btnDownload.style.display = "inline-block";
		btnDelete.style.display = "none";
		listEl.innerHTML =
			'<p class="info-text">Search and download a model to get started.</p>';
		return;
	}

	statusEl.classList.add("ok");
	textEl.textContent = `${models.length} model(s) installed`;
	btnDownload.style.display = "none";
	btnDelete.style.display = "inline-block";

	let html = '<table class="model-table"><tbody>';
	for (let i = 0; i < models.length; i++) {
		const m = models[i];
		const repoId = m.repo_id;
		html += "<tr>";
		html +=
			'<td class="model-name" onclick="Config.selectEmbModel(\'' +
			escHtml(repoId) +
			"')\">" +
			escHtml(repoId) +
			"</td>";
		html += "</tr>";
	}
	html += "</tbody></table>";
	listEl.innerHTML = html;
	if (models.length > 0) {
		selectedEmbRepo = models[0].repo_id;
	}
}

function checkEmbModels() {
	fetch(CONFIG.embedding.installed)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			renderEmbModels(data.models);
		})
		.catch((e) => {
			console.error(e);
			const statusEl = document.getElementById("emb-global-status");
			const textEl = document.getElementById("emb-global-text");
			statusEl.className = "global-status critical";
			textEl.textContent = "Error loading embedding models";
		});
}

function selectEmbModel(repoId) {
	selectedEmbRepo = repoId;
	const listEl = document.getElementById("emb-models-list");
	const rows = listEl.querySelectorAll(".model-name");
	for (let i = 0; i < rows.length; i++) {
		rows[i].style.fontWeight = "normal";
		rows[i].style.color = "#007bff";
	}
	if (rows.length > 0) {
		for (let j = 0; j < rows.length; j++) {
			if (rows[j].textContent === repoId) {
				rows[j].style.fontWeight = "bold";
				rows[j].style.color = "#0056b3";
				break;
			}
		}
	}
}

function searchEmbModel() {
	const query = document.getElementById("emb-search-input").value.trim();
	if (!query) return;

	fetch(
		CONFIG.embedding.search +
			"?query=" +
			encodeURIComponent(query) +
			"&limit=10",
	)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			const resultsEl = document.getElementById("emb-search-results");
			if (!data.models || data.models.length === 0) {
				resultsEl.innerHTML = '<p class="info-text">No results found.</p>';
				return;
			}

			let html = "";
			for (let i = 0; i < data.models.length; i++) {
				const m = data.models[i];
				html += '<div class="search-item">';
				html += `<span class="result-name">${escHtml(m.repo_id)}</span>`;
				html +=
					'<button class="btn btn-primary btn-sm" onclick="Config.downloadEmbModelDirect(\'' +
					escHtml(m.repo_id) +
					"')\">Download</button>";
				html += "</div>";
			}
			resultsEl.innerHTML = html;
		})
		.catch((e) => {
			console.error(e);
			document.getElementById("emb-search-results").innerHTML =
				'<p class="error-text">Search error.</p>';
		});
}

function searchLlmModel() {
	const query = document.getElementById("llm-search-input").value.trim();
	if (!query) return;

	fetch(`${CONFIG.llm.search}?query=${encodeURIComponent(query)}&limit=10`)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			const resultsEl = document.getElementById("llm-search-results");
			if (!data.models || data.models.length === 0) {
				resultsEl.innerHTML = '<p class="info-text">No results found.</p>';
				return;
			}

			let html = "";
			for (let i = 0; i < data.models.length; i++) {
				const m = data.models[i];
				const safeId = escHtml(m.repo_id);
				html += '<div class="search-item">';
				html += `<span class="result-name">${safeId}</span>`;
				html +=
					'<button class="btn btn-primary btn-sm" onclick="Config.showLlmFiles(\'' +
					safeId +
					"')\">Download</button>";
				html += `<div id="llm-files-${i}" class="file-picker" style="display:none;margin-top:8px;"></div>`;
				html += "</div>";
			}
			resultsEl.innerHTML = html;
		})
		.catch((e) => {
			console.error(e);
			document.getElementById("llm-search-results").innerHTML =
				'<p class="error-text">Search error.</p>';
		});
}

function showLlmFiles(repoId) {
	const idx = Array.from(document.querySelectorAll(".search-item")).findIndex(
		(el) => el.querySelector(".result-name")?.textContent === repoId,
	);
	if (idx < 0) return;
	const picker = document.getElementById(`llm-files-${idx}`);
	if (!picker) return;

	if (picker.style.display === "block") {
		picker.style.display = "none";
		return;
	}

	picker.innerHTML = '<p class="info-text">Loading files...</p>';
	picker.style.display = "block";

	fetch(`${CONFIG.llm.files}?repo_id=${encodeURIComponent(repoId)}`)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			if (!data.files || data.files.length === 0) {
				picker.innerHTML = '<p class="info-text">No GGUF files found.</p>';
				return;
			}

			let html =
				'<div class="llm-file-list" style="display:flex;flex-direction:column;gap:2px;">';
			for (const f of data.files) {
				const size = formatBytes(f.size);
				const safeFile = escHtml(f.filename);
				html +=
					'<div class="llm-file-item" style="display:flex;align-items:center;gap:8px;padding:4px 8px;border:1px solid var(--border-color);border-radius:4px;">';
				html +=
					'<span style="flex:1;font-size:var(--text-sm);color:var(--text-body);">' +
					safeFile +
					"</span>";
				html +=
					'<span style="font-size:var(--text-sm);color:var(--text-card-label);white-space:nowrap;">' +
					size +
					"</span>";
				html +=
					'<button class="btn btn-primary btn-sm" style="white-space:nowrap;" onclick="Config._downloadLlmFile(\'' +
					escHtml(repoId) +
					"', '" +
					safeFile +
					"', this)\">Download</button>";
				html += "</div>";
			}
			html += "</div>";
			picker.innerHTML = html;
		})
		.catch(() => {
			picker.innerHTML = '<p class="error-text">Failed to load files.</p>';
		});
}

function _downloadLlmFile(repoId, filename, btn) {
	btn.disabled = true;
	btn.textContent = "Starting...";
	selectedLlmRepo = repoId;

	const progressUrl = `${CONFIG.llm.progress}?repo_id=${encodeURIComponent(repoId)}`;

	fetch(
		CONFIG.llm.download +
			"?repo_id=" +
			encodeURIComponent(repoId) +
			"&filename=" +
			encodeURIComponent(filename),
		{ method: "POST" },
	)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			btn.textContent = "Downloading...";
			let pollCount = 0;
			const checkProgress = setInterval(() => {
				pollCount++;
				if (pollCount > 600) {
					clearInterval(checkProgress);
					btn.textContent = "Download";
					btn.disabled = false;
					showToast("Download progress timed out — check server logs", "error");
					return;
				}
				fetch(progressUrl)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === "completed") {
							clearInterval(checkProgress);
							btn.textContent = "Done";
							btn.className = "btn btn-success btn-sm";
							showToast(`Downloaded ${filename}`, "success");
							checkLlmModels();
						} else if (data.status?.startsWith("error")) {
							clearInterval(checkProgress);
							btn.textContent = "Failed";
							btn.className = "btn btn-danger btn-sm";
							showToast(`Download failed: ${data.status}`, "error");
						}
					})
					.catch(() => {
						btn.textContent = "Download";
						btn.disabled = false;
						clearInterval(checkProgress);
						showToast("Progress check failed — see server logs", "error");
					});
			}, 1000);
		})
		.catch((e) => {
			btn.disabled = false;
			btn.textContent = "Download";
			showToast(`Error: ${e.message}`, "error");
		});
}

function _setEmbBusy(busy) {
	const dl = document.getElementById("btn-download-emb");
	const del = document.getElementById("btn-delete-emb");
	if (dl) {
		dl.disabled = busy;
		dl.textContent = busy ? "Downloading..." : "Download";
	}
	if (del) del.disabled = busy;
}

function downloadEmbModel() {
	if (!selectedEmbRepo) return;
	_setEmbBusy(true);
	fetch(
		CONFIG.embedding.download +
			"?repo_id=" +
			encodeURIComponent(selectedEmbRepo),
		{ method: "POST" },
	)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			const checkProgress = setInterval(() => {
				fetch(
					CONFIG.embedding.progress +
						"?repo_id=" +
						encodeURIComponent(selectedEmbRepo),
				)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === "completed") {
							clearInterval(checkProgress);
							_setEmbBusy(false);
							checkEmbModels();
						} else if (data.status?.startsWith("error")) {
							clearInterval(checkProgress);
							_setEmbBusy(false);
							showToast(`Download failed: ${data.status}`, "error");
						}
					})
					.catch(() => {});
			}, 1000);
		})
		.catch((e) => {
			_setEmbBusy(false);
			showToast(`Error: ${e.message}`, "error");
		});
}

function downloadEmbModelDirect(repoId) {
	selectedEmbRepo = repoId;
	downloadEmbModel();
}

function checkDimensionStatus() {
	const banner = document.getElementById("emb-dim-banner");
	if (banner) banner.style.display = "none";
}

async function recreateAndReindex() {
	if (
		!(await showConfirm(
			"Recreate Qdrant collection(s) and reindex all documents? This will delete existing vectors.",
		))
	)
		return;
	const btn = document.querySelector("#emb-dim-banner .btn");
	if (btn) {
		btn.textContent = "Recreating...";
		btn.disabled = true;
	}
	const statusEl =
		document.getElementById("emb-download-status") ||
		document.getElementById("qdrant-download-status");
	if (statusEl) {
		statusEl.textContent = "Reindexing...";
		statusEl.className = "status-message";
	}

	const collections = ["sigma_docs"];
	try {
		for (const name of collections) {
			const r = await fetch("/api/v1/qdrant", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					action: "reindex",
					payload: { action: "reindex", collection_name: name },
				}),
			});
			await r.json();
		}
		checkDimensionStatus();
		if (statusEl) {
			statusEl.textContent = "Reindex completed";
			statusEl.className = "status-message success";
		}
	} catch (e) {
		showToast(`Reindex failed: ${e.message || "Unknown error"}`, "error");
		if (statusEl) {
			statusEl.textContent = "Reindex failed";
			statusEl.className = "status-message error";
		}
	} finally {
		if (btn) {
			btn.textContent = "Recreate collection & Reindex";
			btn.disabled = false;
		}
	}
}

async function deleteEmbModel() {
	if (!selectedEmbRepo) return;
	if (!(await showConfirm(`Delete model ${selectedEmbRepo}?`))) return;
	_setEmbBusy(true);
	try {
		const r = await fetch(
			`${CONFIG.embedding.delete}/${encodeURIComponent(selectedEmbRepo)}`,
			{
				method: "DELETE",
			},
		);
		if (!r.ok) throw new Error(`HTTP ${r.status}`);
		selectedEmbRepo = null;
		checkEmbModels();
	} catch (e) {
		showToast(`Error: ${e.message}`, "error");
	} finally {
		_setEmbBusy(false);
	}
}

function renderFastModels(models) {
	const listEl = document.getElementById("fast-models-list");
	const statusEl = document.getElementById("fast-global-status");
	const textEl = document.getElementById("fast-global-text");

	statusEl.className = "global-status";

	if (!models || models.length === 0) {
		statusEl.classList.add("warn");
		textEl.textContent = "No fastembed models installed";
		listEl.innerHTML = '<p class="info-text">No sparse models found in embedding_fast.</p>';
		return;
	}

	statusEl.classList.add("ok");
	textEl.textContent = `${models.length} model(s) installed`;

	let html = '<table class="model-table"><tbody>';
	for (let i = 0; i < models.length; i++) {
		const m = models[i];
		html += "<tr>";
		html += '<td class="model-name">' + escHtml(m.repo_id) + "</td>";
		html += "</tr>";
	}
	html += "</tbody></table>";
	listEl.innerHTML = html;
}

function checkFastModels() {
	fetch(CONFIG.embeddingFast.installed)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			renderFastModels(data.models);
		})
		.catch((e) => {
			console.error(e);
			const statusEl = document.getElementById("fast-global-status");
			const textEl = document.getElementById("fast-global-text");
			statusEl.className = "global-status critical";
			textEl.textContent = "Error loading fastembed models";
		});
}


// ──────────────────────────────────────────────────────────────
function renderSpecsStatus(repos, defaultOrg, defaultName) {
	const statusEl = document.getElementById("specs-status");
	const listEl = document.getElementById("specs-repos-list");

	if (!repos || repos.length === 0) {
		setStatusText(statusEl, "Default repository missing", false);
		listEl.innerHTML =
			'<div class="data-row">' +
			'  <span class="status-dot data-dot-missing"></span>' +
			'  <span class="label">' +
			escHtml(defaultOrg) +
			"/" +
			escHtml(defaultName) +
			"</span>" +
			'  <span class="text-danger">NOT FOUND</span>' +
			'  <span class="data-action-buttons">' +
			'  <button class="btn btn-primary btn-sm" onclick="Config.fixSpecRepo()">Fix</button>' +
			"  </span>" +
			"</div>";
		return;
	}

	let found = false;
	let foundRepo = null;
	for (let i = 0; i < repos.length; i++) {
		if (repos[i].org === defaultOrg && repos[i].name === defaultName) {
			found = true;
			foundRepo = repos[i];
			break;
		}
	}

	if (found) {
		setStatusText(statusEl, "Default repository configured", true);
		const statusClass =
			foundRepo.repo_status === "error" ? "text-danger" : "text-success";
		const statusLabel =
			foundRepo.repo_status === "error"
				? "ERROR"
				: foundRepo.repo_status === "cloning" ||
						foundRepo.repo_status === "syncing"
					? "SYNCING"
					: "READY";
		const dotClass =
			foundRepo.repo_status === "error"
				? "data-dot-missing"
				: foundRepo.repo_status === "cloning" ||
						foundRepo.repo_status === "syncing"
					? "data-dot-warn"
					: "data-dot-ok";
		const fixBtnHtml =
			foundRepo.repo_status === "error"
				? '<button class="btn btn-primary btn-sm" onclick="Config.fixSpecRepo()">Fix</button>'
				: '<button class="btn btn-primary btn-sm" disabled>Fix</button>';
		listEl.innerHTML =
			'<div class="data-row">' +
			'  <span class="' +
			dotClass +
			' status-dot"></span>' +
			'  <span class="label">' +
			escHtml(defaultOrg) +
			"/" +
			escHtml(defaultName) +
			"</span>" +
			'  <span class="' +
			statusClass +
			' data-status-label">' +
			statusLabel +
			"</span>" +
			'  <span class="data-action-buttons">' +
			fixBtnHtml +
			"  </span>" +
			"</div>";
		if (foundRepo.last_synced) {
			listEl.innerHTML +=
				'<p class="info-text" style="margin:4px 0 0 20px;font-size:12px;">Last sync: ' +
				escHtml(String(foundRepo.last_synced)) +
				"</p>";
		}
		return;
	}

	setStatusText(statusEl, "Default repository missing", false);
	listEl.innerHTML =
		'<div class="data-row">' +
		'  <span class="status-dot data-dot-missing"></span>' +
		'  <span class="label">' +
		escHtml(defaultOrg) +
		"/" +
		escHtml(defaultName) +
		"</span>" +
		'  <span class="text-danger">NOT FOUND</span>' +
		'  <span class="data-action-buttons">' +
		'  <button class="btn btn-primary btn-sm" onclick="Config.fixSpecRepo()">Fix</button>' +
		"  </span>" +
		"</div>";
}

function loadSpecs() {
	const statusEl = document.getElementById("specs-status");
	setStatusText(statusEl, "Loading specifications...", true);

	const defaultOrg = _BACKEND_CONFIG.Hardware ? "sigmahq" : "sigmahq";
	const defaultName = _BACKEND_CONFIG.Hardware
		? "sigma-specification"
		: "sigma-specification";

	fetch(CONFIG.spec.list)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((repos) => {
			renderSpecsStatus(repos, defaultOrg, defaultName);
		})
		.catch((e) => {
			console.error(e);
			setStatusText(statusEl, `Error loading specs: ${e.message}`, false);
			const listEl = document.getElementById("specs-repos-list");
			if (listEl) {
				listEl.innerHTML =
					'<div class="data-row">' +
					'  <span class="status-dot data-dot-missing"></span>' +
					'  <span class="label">' +
					defaultOrg +
					"/" +
					defaultName +
					"</span>" +
					'  <span class="text-danger">ERROR</span>' +
					'  <span class="data-action-buttons">' +
					'  <button class="btn btn-primary btn-sm" onclick="Config.fixSpecRepo()">Fix</button>' +
					"  </span>" +
					"</div>";
			}
		});
}

async function fixSpecRepo() {
	const defaultUrl = "https://github.com/sigmahq/sigma-specification";
	const defaultBranch = "main";

	if (
		!(await showConfirm(
			"Clone the default SigmaHQ specification repository (" +
				defaultUrl +
				")?",
		))
	)
		return;

	const statusEl = document.getElementById("specs-config-status");
	statusEl.textContent = "Cloning repository...";
	statusEl.className = "status-message";

	try {
		const r = await fetch(CONFIG.spec.add, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ url: defaultUrl, branch: defaultBranch }),
		});
		const data = await r.json();
		if (data.success) {
			statusEl.textContent = data.message || "Repository cloning started";
			statusEl.className = "status-message success";
			setTimeout(() => {
				loadSpecs();
			}, 2000);
		} else {
			statusEl.textContent = data.error || "Clone failed";
			statusEl.className = "status-message error";
		}
	} catch (err) {
		statusEl.textContent = `Error: ${err.message}`;
		statusEl.className = "status-message error";
	}
}

// ──────────────────────────────────────────────────────────────
// Config Object (accessible via onclick=)
// ──────────────────────────────────────────────────────────────
const _Config = {
	// System
	saveBackendConfig: saveBackendConfig,
	createDataDirs: createDataDirs,
	cleanDataDirs: cleanDataDirs,
	resetDataDirs: resetDataDirs,
	createDuckDb: createDuckDb,
	cleanDuckDb: cleanDuckDb,
	resetDuckDb: resetDuckDb,
	saveLoggingConfig: saveLoggingConfig,
	loadLoggingConfig: checkLoggingConfig,

	// Specs
	loadSpecs: loadSpecs,
	fixSpecRepo: fixSpecRepo,

	// Backend
	loadBackendStatus: loadBackendStatus,
	saveBackendServiceConfig: saveBackendServiceConfig,
	downloadLlama: downloadLlama,
	downloadQdrantBinary: downloadQdrantBinary,
	downloadQdrantUI: downloadQdrantUI,
	startService: startService,
	stopService: stopService,
	openQdrantUI: openQdrantUI,
	refreshReleases: refreshReleases,
	scanLocalVersions: scanLocalVersions,
	onLlamaModeChange: onLlamaModeChange,
	onLlamaAutostartChange: onLlamaAutostartChange,
	onQdrantModeChange: onQdrantModeChange,
	onQdrantAutostartChange: onQdrantAutostartChange,

	// Embedding dimension
	checkDimensionStatus: checkDimensionStatus,
	recreateAndReindex: recreateAndReindex,

	// LLM
	selectLlmModel: selectLlmModel,
	searchLlmModel: searchLlmModel,
	showLlmFiles: showLlmFiles,
	_downloadLlmFile: _downloadLlmFile,
	downloadLlmModel: downloadLlmModel,
	downloadLlmModelDirect: downloadLlmModelDirect,
	deleteLlmModel: deleteLlmModel,

	// Embedding
	selectEmbModel: selectEmbModel,
	searchEmbModel: searchEmbModel,
	downloadEmbModel: downloadEmbModel,
	downloadEmbModelDirect: downloadEmbModelDirect,
	deleteEmbModel: deleteEmbModel,

	// FastEmbed
	checkFastModels: checkFastModels,

	// Scroll helpers
	scrollToAndOpen: scrollToAndOpen,

	// Status
	loadSystemStatus: loadSystemStatus,
};
window.Config = _Config;

// Expose for backward compatibility with inline onclick=
window._cfg = {
	createDataDirs: createDataDirs,
	cleanDataDirs: cleanDataDirs,
	resetDataDirs: resetDataDirs,
	createDuckDb: createDuckDb,
	cleanDuckDb: cleanDuckDb,
	resetDuckDb: resetDuckDb,
};

// ──────────────────────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
	// Apply backend config
	applyBackendConfig(_BACKEND_CONFIG);

	// Load all data
	checkDataDirs();
	checkDuckDbStatus();
	checkLoggingConfig();
	loadSpecs();
	loadBackendStatus();
	loadReleaseTimestamps();
	loadReleasesTable();
	checkLlmModels();
	checkEmbModels();
	checkFastModels();
	checkDimensionStatus();
	loadSystemStatus();

	// Bind form submit
	const form = document.getElementById("config-form");
	if (form)
		form.addEventListener("submit", (e) => {
			e.preventDefault();
			saveBackendConfig();
		});

	// Update Qdrant Web UI link when Base URL changes
	const qdrantUrlInput = document.getElementById("qdrant-base-url");
	const qdrantWebLink = document.getElementById("qdrant-webui-link");
	if (qdrantUrlInput && qdrantWebLink) {
		function updateQdrantWebLink() {
			const base = qdrantUrlInput.value.replace(/\/+$/, "");
			qdrantWebLink.href = base
				? `${base}/dashboard`
				: "http://127.0.0.1:6333/dashboard";
		}
		qdrantUrlInput.addEventListener("change", updateQdrantWebLink);
		qdrantUrlInput.addEventListener("input", updateQdrantWebLink);
	}

	// Setup sidebar nav clicks
	const navLinks = document.querySelectorAll(".config-nav-link");
	navLinks.forEach((link) => {
		link.addEventListener("click", function (_e) {
			navLinks.forEach((l) => {
				l.classList.remove("active");
			});
			this.classList.add("active");
		});
	});
});
