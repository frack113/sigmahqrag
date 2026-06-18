/**
 * Config Dashboard - Unified JavaScript module
 *
 * Combines functionality from system.html, backend.html, and llm.html
 * Provides a Config object with all methods accessible via onclick attributes.
 */

// ──────────────────────────────────────────────────────────────
// API Configuration
// ──────────────────────────────────────────────────────────────
var CONFIG = {
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
		status: "/api/v1/system/dashboard",
		create: "/api/v1/system/dashboard",
		clean: "/api/v1/system/dashboard/clean",
		reset: "/api/v1/system/dashboard/hard-reset",
	},
	logging: {
		get: "/api/v1/config/logging",
		save: "/api/v1/config/logging",
	},
	llm: {
		installed: "/api/v1/models/llm/installed",
		download: "/api/v1/models/llm/download",
		search: "/api/v1/models/llm/search",
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
};

// ──────────────────────────────────────────────────────────────
// State
// ──────────────────────────────────────────────────────────────
var _BACKEND_CONFIG = {};
var selectedLlmRepo = null;
var selectedEmbRepo = null;

try {
	var configDataEl = document.getElementById("backend-config-data");
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
	var k = 1024;
	var sizes = ["B", "KB", "MB", "GB"];
	var i = Math.floor(Math.log(bytes) / Math.log(k));
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
	var el = document.getElementById(groupId);
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
		fetch("/api/v1/system/dashboard")
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
			var adminData = results[0].data || {};
			var _llamaInfo = results[1] || {};
			var _qdrantInfo = results[2] || {};
			var duckDbStatus = results[3] || {};
			var _loggingData = results[4] || {};
			var llama = adminData.llama_cpp || {};
			var qdrant = adminData.qdrant || {};

			// Update llama status
			var llamaStatusCard = document.querySelector('[data-service="llama"]');
			if (llamaStatusCard) {
				llamaStatusCard.querySelector(".status-text").textContent =
					llama.status || "unknown";
				llamaStatusCard.className = `status-card ${getStatusCardClass(llama.status)}`;
			}

			// Update qdrant status
			var qdrantStatusCard = document.querySelector('[data-service="qdrant"]');
			if (qdrantStatusCard) {
				qdrantStatusCard.querySelector(".status-text").textContent =
					qdrant.status || "unknown";
				qdrantStatusCard.className = `status-card ${getStatusCardClass(qdrant.status)}`;
			}

			// Update duckdb status
			var duckdbStatusCard = document.querySelector('[data-service="duckdb"]');
			if (duckdbStatusCard) {
				var duckState = duckDbStatus.state || "healthy";
				duckdbStatusCard.querySelector(".status-text").textContent =
					duckState || "unknown";
				duckdbStatusCard.className =
					"status-card " +
					getStatusCardClass(duckState === "healthy" ? "active" : "inactive");
			}

			// Update logging status
			var loggingStatusCard = document.querySelector(
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
	var hw = cfg?.Hardware || {};
	var osSel = document.getElementById("os-select");
	var gpuSel = document.getElementById("gpu-select");
	if (osSel) osSel.value = hw.os || "windows";
	if (gpuSel) gpuSel.value = hw.gpu || "cpu";
}

function saveBackendConfig() {
	var statusEl = document.getElementById("config-status");
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
var renderDataDirs = (dirs) => {
	var readyCount = 0;
	var missingCount = 0;
	for (var i = 0; i < dirs.length; i++) {
		var d = dirs[i];
		if (d.is_healthy) readyCount++;
		else missingCount++;
	}

	var statusEl = document.getElementById("data-global-status");
	statusEl.className = "global-status";
	if (readyCount === dirs.length) statusEl.classList.add("ok");

	var dotClass =
		readyCount === dirs.length
			? "data-dot-ok"
			: missingCount > 0 && readyCount === 0
				? "data-dot-missing"
				: "data-dot-warn";

	var summaryClass =
		readyCount === dirs.length
			? "text-success"
			: missingCount > 0 && readyCount === 0
				? "text-danger"
				: "text-warning";

	var summaryLabel =
		readyCount === dirs.length
			? "READY"
			: missingCount > 0 && readyCount === 0
				? "ERROR"
				: "PARTIAL";

	var fixBtnHtml =
		readyCount === dirs.length
			? '<button class="btn btn-primary btn-sm" disabled>Fix</button>'
			: '<button class="btn btn-primary btn-sm" onclick="Config.createDataDirs()">Fix</button>';

	var listEl = document.getElementById("data-dirs-list");
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
		'  <button class="btn btn-danger btn-sm" onclick="Config.resetDataDirs()">Hard Reset</button>' +
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
			var listEl = document.getElementById("data-dirs-list");
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
			alert(`Error: ${e.message}`);
		});
}

function cleanDataDirs() {
	if (
		!confirm(
			"Clean all data directories? Non-official contents will be deleted.",
		)
	)
		return;
	fetch(CONFIG.data.clean, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDataDirs();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

function resetDataDirs() {
	if (
		!confirm(
			"\u26a0\ufe0f HARD RESET \u2014 This will permanently delete ALL data in the data/ directory. Continue?",
		)
	)
		return;
	fetch(CONFIG.data.reset, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDataDirs();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

// ──────────────────────────────────────────────────────────────
// DuckDB
// ──────────────────────────────────────────────────────────────
function renderDuckDbStatus(status) {
	var el = document.getElementById("duckdb-status");
	if (!el) return;

	var dotClass, labelClass, summaryLabel;
	var st = status.state || "healthy";

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

	var size = status.file_size > 0 ? ` (${formatBytes(status.file_size)})` : "";
	var fixBtnHtml = status.needs_fix
		? '<button class="btn btn-primary btn-sm" onclick="Config.createDuckDb()">Fix</button>'
		: '<button class="btn btn-primary btn-sm" disabled>Fix</button>';
	var cleanBtnHtml = status.needs_clean
		? '<button class="btn btn-warning btn-sm" onclick="Config.cleanDuckDb()">Clean</button>'
		: '<button class="btn btn-warning btn-sm" disabled>Clean</button>';

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
		'<button class="btn btn-danger btn-sm" onclick="Config.resetDuckDb()">Hard Reset</button>' +
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
			var el = document.getElementById("duckdb-status");
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
			alert(`Error: ${e.message}`);
		});
}

function cleanDuckDb() {
	if (!confirm("This will remove excess tables not in the schema. Continue?"))
		return;
	fetch(CONFIG.duckdb.clean, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDuckDbStatus();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

function resetDuckDb() {
	if (
		!confirm(
			"\u26a0\ufe0f HARD RESET \u2014 This will permanently delete the DuckDB database and create a fresh one. Continue?",
		)
	)
		return;
	fetch(CONFIG.duckdb.reset, { method: "POST" })
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			checkDuckDbStatus();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

// ──────────────────────────────────────────────────────────────
// Logging
// ──────────────────────────────────────────────────────────────
function renderLoggingConfig(data) {
	var levelSelect = document.getElementById("log-level-select");
	var maxSizeInput = document.getElementById("log-max-size-input");
	var maxFileInput = document.getElementById("log-max-file-input");
	var cleanToggle = document.getElementById("log-clean-at-startup");
	var _toggleLabel = document.getElementById("log-clean-toggle");

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
			var lbl = document.getElementById("log-clean-label");
			if (lbl) lbl.textContent = cleanToggle.checked ? "Yes" : "No";
		};
	}
	var cleanLabel = document.getElementById("log-clean-label");
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
	var statusEl = document.getElementById("logging-config-status");
	var payload = {
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
			var adminData = results[0].data || {};
			var llamaInfo = results[1] || {};
			var qdrantInfo = results[2] || {};
			var configData = results[3].data || {};
			var llama = adminData.llama_cpp || {};
			var qdrant = adminData.qdrant || {};

			function setStatus(containerId, statusText, statusClass) {
				var container = document.getElementById(containerId);
				var dot = container.querySelector(".status-dot");
				var textSpans = container.querySelectorAll("span:not(.status-dot)");
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

			var isLlamaExternal = llamaInfo.mode === "external";
			document.getElementById("llama-start-btn").disabled = isLlamaExternal;
			document.getElementById("llama-stop-btn").disabled = isLlamaExternal;
			document.getElementById("llama-download-btn").disabled = isLlamaExternal;

			var isQdrantExternal = qdrantInfo.mode === "external";
			var qdrantStartBtn = document.getElementById("qdrant-start-btn");
			var qdrantStopBtn = document.getElementById("qdrant-stop-btn");
			var qdrantDownloadBtn = document.getElementById("qdrant-download-btn");
			if (qdrantStartBtn) qdrantStartBtn.disabled = isQdrantExternal;
			if (qdrantStopBtn) qdrantStopBtn.disabled = isQdrantExternal;
			if (qdrantDownloadBtn) qdrantDownloadBtn.disabled = isQdrantExternal;

			var lv = (llamaInfo.current_version || "").replace(/^0$/, "");
			loadReleaseTags("llama-release-select", "llama.cpp", { value: lv });

			var qv = (qdrantInfo.current_version || "").replace(/^0$/, "");
			if (qv && qv !== "unknown" && qv !== "Not installed") {
				loadReleaseTags("qdrant-release-select", "qdrant", { value: qv });
			} else {
				loadReleaseTags("qdrant-release-select", "qdrant");
			}

			var uv = (qdrantInfo.webui_version || "").replace(/^0$/, "");
			if (uv && uv !== "unknown" && uv !== "Not installed") {
				loadReleaseTags("qdrant-ui-release-select", "qdrant-web-ui", {
					value: uv,
				});
			} else {
				loadReleaseTags("qdrant-ui-release-select", "qdrant-web-ui");
			}

			// Populate new backend service controls from config
			var services =
				configData.services ||
				configData.backend?.services ||
				_BACKEND_CONFIG.services ||
				{};
			var llamaSvc = services.llama || {};
			var qdrantSvc = services.qdrant || {};

			var llamaUrlInput = document.getElementById("llama-base-url");
			if (llamaUrlInput)
				llamaUrlInput.value = llamaSvc.base_url || "http://127.0.0.1:8080";

			var llamaManageSlider = document.getElementById(
				"llama-manage-internally",
			);
			if (llamaManageSlider)
				llamaManageSlider.checked = llamaSvc.manage_internally !== false;
			var llamaModeLabel = document.getElementById("llama-mode-label");
			if (llamaModeLabel)
				llamaModeLabel.textContent =
					llamaSvc.manage_internally !== false ? "Internal" : "External";
			updateServiceControls("llama", llamaSvc.manage_internally !== false);

			var llamaAutostartSlider = document.getElementById(
				"llama-autorun-at-startup",
			);
			if (llamaAutostartSlider)
				llamaAutostartSlider.checked = llamaSvc.autorun_at_startup !== false;
			var llamaAutostartLabel = document.getElementById(
				"llama-autostart-label",
			);
			if (llamaAutostartLabel)
				llamaAutostartLabel.textContent =
					llamaSvc.autorun_at_startup !== false ? "Yes" : "No";

			var qdrantUrlInput = document.getElementById("qdrant-base-url");
			if (qdrantUrlInput)
				qdrantUrlInput.value = qdrantSvc.base_url || "http://127.0.0.1:6333";

			var qdrantManageSlider = document.getElementById(
				"qdrant-manage-internally",
			);
			if (qdrantManageSlider)
				qdrantManageSlider.checked = qdrantSvc.manage_internally !== false;
			var qdrantModeLabel = document.getElementById("qdrant-mode-label");
			if (qdrantModeLabel)
				qdrantModeLabel.textContent =
					qdrantSvc.manage_internally !== false ? "Internal" : "External";
			updateServiceControls("qdrant", qdrantSvc.manage_internally !== false);

			var qdrantAutostartSlider = document.getElementById(
				"qdrant-autorun-at-startup",
			);
			if (qdrantAutostartSlider)
				qdrantAutostartSlider.checked = qdrantSvc.autorun_at_startup !== false;
			var qdrantAutostartLabel = document.getElementById(
				"qdrant-autostart-label",
			);
			if (qdrantAutostartLabel)
				qdrantAutostartLabel.textContent =
					qdrantSvc.autorun_at_startup !== false ? "Yes" : "No";

			// Build summary
			var _summaryHtml = "";
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
	var nested = {};
	nested[field] = value;
	var svc = {};
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
	var baseUrl = document.getElementById(`${service}-base-url`);
	var manage = document.getElementById(`${service}-manage-internally`);
	var autorun = document.getElementById(`${service}-autorun-at-startup`);
	var payload = {
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

	var statusEl = document.getElementById(`${service}-status-text`);
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
	var startBtn = document.getElementById(`${service}-start-btn`);
	var stopBtn = document.getElementById(`${service}-stop-btn`);
	var downloadBtn = document.getElementById(`${service}-download-btn`);
	var releaseSelect = document.getElementById(`${service}-release-select`);
	var autostartSlider = document.getElementById(
		`${service}-autorun-at-startup`,
	);
	var autostartToggle = document.getElementById(`${service}-autostart-toggle`);

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
		var label = document.getElementById(`${service}-autostart-label`);
		if (label) label.textContent = "Off";
	}
}

function onLlamaModeChange() {
	var cb = document.getElementById("llama-manage-internally");
	var checked = cb.checked;
	updateBackendServiceConfig("llama", "manage_internally", checked);
	var label = document.getElementById("llama-mode-label");
	if (label) label.textContent = checked ? "Internal" : "External";
	updateServiceControls("llama", checked);
}

function onLlamaAutostartChange() {
	var cb = document.getElementById("llama-autorun-at-startup");
	var checked = cb.checked;
	updateBackendServiceConfig("llama", "autorun_at_startup", checked);
	var label = document.getElementById("llama-autostart-label");
	if (label) label.textContent = checked ? "Yes" : "No";
}

function onQdrantModeChange() {
	var cb = document.getElementById("qdrant-manage-internally");
	var checked = cb.checked;
	updateBackendServiceConfig("qdrant", "manage_internally", checked);
	var label = document.getElementById("qdrant-mode-label");
	if (label) label.textContent = checked ? "Internal" : "External";
	updateServiceControls("qdrant", checked);
}

function onQdrantAutostartChange() {
	var cb = document.getElementById("qdrant-autorun-at-startup");
	var checked = cb.checked;
	updateBackendServiceConfig("qdrant", "autorun_at_startup", checked);
	var label = document.getElementById("qdrant-autostart-label");
	if (label) label.textContent = checked ? "Yes" : "No";
}

function downloadLlama() {
	var btn = document.getElementById("llama-download-btn");
	if (btn?.disabled) return;
	if (btn) btn.disabled = true;
	var sel = document.getElementById("llama-release-select");
	var version = sel ? sel.value : "";
	var url =
		"/api/v1/llamacpp/download" +
		(version ? `?version=${encodeURIComponent(version)}` : "");
	var pb = makeProgressBar("llama");
	var statusEl = document.getElementById("llama-download-status");
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
	var pb = makeProgressBar("qdrant");
	var statusEl = document.getElementById("qdrant-download-status");
	statusEl.textContent = "Starting download...";
	statusEl.className = "status-message";
	pb.show();
	var sel = document.getElementById("qdrant-release-select");
	var version = sel ? sel.value : "latest";
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
	var pb = makeProgressBar("qdrant");
	var statusEl = document.getElementById("qdrant-download-status");
	statusEl.textContent = "Starting download...";
	statusEl.className = "status-message";
	pb.show();
	var sel = document.getElementById("qdrant-ui-release-select");
	var version = sel ? sel.value : "latest";
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
	fetch("/api/v1/admin/backend", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ action: "start", service: service }),
	})
		.then((r) => r.json())
		.then((data) => {
			alert(data.message || data.error || "Started");
			loadBackendStatus();
		});
}

function stopService(service) {
	if (!confirm(`Stop ${service}?`)) return;
	fetch("/api/v1/admin/backend", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ action: "stop", service: service }),
	})
		.then((r) => r.json())
		.then((data) => {
			alert(data.message || data.error || "Stopped");
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
			var ts = data.timestamps || {};
			var latest = "";
			for (var key in ts) {
				if (ts[key] && (!latest || ts[key] > latest)) latest = ts[key];
			}
			var el = document.getElementById("releases-last-update");
			if (el) {
				if (latest) {
					var d = new Date(latest);
					el.textContent = `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
				} else {
					el.textContent = "Never";
				}
			}
		})
		.catch(() => {
			var el = document.getElementById("releases-last-update");
			if (el) el.textContent = "—";
		});
}

function loadReleasesTable() {
	fetch("/api/v1/releases/all-releases")
		.then((r) => r.json())
		.then((data) => {
			var tableEl = document.getElementById("releases-table");
			if (!tableEl) return;

			var releases = data.releases || [];
			var versions = data.installed_versions || {};

			if (releases.length === 0 && Object.keys(versions).length === 0) {
				tableEl.innerHTML =
					'<p style="font-style:italic;color:var(--text-card-body);"><i>undef</i></p>';
				return;
			}

			var html =
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
			var knownServices = ["llama.cpp", "qdrant", "qdrant-web-ui"];

			for (var si = 0; si < knownServices.length; si++) {
				var svc = knownServices[si];
				var release = null;
				for (var ri = 0; ri < releases.length; ri++) {
					if (releases[ri].service === svc) {
						release = releases[ri];
						break;
					}
				}
				var installed = versions[svc] || null;

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
			for (var ri = 0; ri < releases.length; ri++) {
				var r = releases[ri];
				if (knownServices.indexOf(r.service) === -1) {
					var extInstalled = versions[r.service] || null;
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
			var tableEl = document.getElementById("releases-table");
			if (tableEl)
				tableEl.innerHTML = '<p class="error">Failed to load releases</p>';
		});
}

function refreshReleases() {
	var statusEl = document.getElementById("releases-refresh-status");
	if (statusEl) {
		statusEl.textContent = "Refreshing...";
		statusEl.className = "status-message";
	}
	fetch("/api/v1/releases/refresh", { method: "POST" })
		.then((r) => r.json())
		.then((data) => {
			if (data.errors) {
				var msgs = Object.values(data.errors);
				var rateLimited = msgs.some((m) => m.indexOf("rate limit") !== -1);
				if (rateLimited) {
					alert(
						"GitHub API rate limit reached. Please wait a few minutes and try again.",
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
			alert("Failed to refresh releases. Check your connection.");
			if (statusEl) {
				statusEl.textContent = "Failed";
				statusEl.className = "status-message error";
			}
		});
}

function scanLocalVersions() {
	var statusEl = document.getElementById("releases-refresh-status");
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
	var listEl = document.getElementById("llm-models-list");
	var statusEl = document.getElementById("llm-global-status");
	var textEl = document.getElementById("llm-global-text");
	var btnDownload = document.getElementById("btn-download-llm");
	var btnDelete = document.getElementById("btn-delete-llm");

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

	var html = '<table class="model-table"><tbody>';
	for (var i = 0; i < models.length; i++) {
		var m = models[i];
		html += "<tr>";
		html +=
			'<td class="model-name" onclick="Config.selectLlmModel(\'' +
			escHtml(m.repo_id) +
			"')\">" +
			escHtml(m.repo_id) +
			"</td>";
		html += `<td>${m.files ? `${m.files.length} file(s)` : ""}</td>`;
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
			var statusEl = document.getElementById("llm-global-status");
			var textEl = document.getElementById("llm-global-text");
			statusEl.className = "global-status critical";
			textEl.textContent = "Error loading LLM models";
		});
}

function selectLlmModel(repoId) {
	selectedLlmRepo = repoId;
	var listEl = document.getElementById("llm-models-list");
	var rows = listEl.querySelectorAll(".model-name");
	for (var i = 0; i < rows.length; i++) {
		rows[i].style.fontWeight = "normal";
		rows[i].style.color = "#007bff";
	}
	if (rows.length > 0) {
		for (var j = 0; j < rows.length; j++) {
			if (rows[j].textContent === repoId) {
				rows[j].style.fontWeight = "bold";
				rows[j].style.color = "#0056b3";
				break;
			}
		}
	}
}

function searchLlmModel() {
	var query = document.getElementById("llm-search-input").value.trim();
	if (!query) return;

	fetch(`${CONFIG.llm.search}?q=${encodeURIComponent(query)}&limit=10`)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then((data) => {
			var resultsEl = document.getElementById("llm-search-results");
			if (!data.models || data.models.length === 0) {
				resultsEl.innerHTML = '<p class="info-text">No results found.</p>';
				return;
			}

			var html = "";
			for (var i = 0; i < data.models.length; i++) {
				var m = data.models[i];
				html += '<div class="search-item">';
				html += `<span class="result-name">${escHtml(m.repo_id)}</span>`;
				html +=
					'<button class="btn btn-primary btn-sm" onclick="Config.downloadLlmModelDirect(\'' +
					escHtml(m.repo_id) +
					"')\">Download</button>";
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

function downloadLlmModel() {
	if (!selectedLlmRepo) return;
	fetch(
		`${CONFIG.llm.download}?repo_id=${encodeURIComponent(selectedLlmRepo)}`,
		{ method: "POST" },
	)
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			var btn = document.getElementById("btn-download-llm");
			var progressBtn = document.getElementById("btn-download-llm");
			progressBtn.textContent = "Downloading...";
			progressBtn.disabled = true;

			var checkProgress = setInterval(() => {
				fetch(
					CONFIG.llm.progress +
						"?repo_id=" +
						encodeURIComponent(selectedLlmRepo),
				)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === "completed") {
							clearInterval(checkProgress);
							btn.textContent = "Download";
							btn.disabled = false;
							checkLlmModels();
						} else if (data.status?.startsWith("error")) {
							clearInterval(checkProgress);
							btn.textContent = "Download";
							btn.disabled = false;
							alert(`Download failed: ${data.status}`);
						}
					})
					.catch(() => {});
			}, 1000);
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

function downloadLlmModelDirect(repoId) {
	selectedLlmRepo = repoId;
	downloadLlmModel();
}

function deleteLlmModel() {
	if (!selectedLlmRepo) return;
	if (!confirm(`Delete model ${selectedLlmRepo}?`)) return;

	fetch(`${CONFIG.llm.delete}/${encodeURIComponent(selectedLlmRepo)}`, {
		method: "DELETE",
	})
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			selectedLlmRepo = null;
			checkLlmModels();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

// ──────────────────────────────────────────────────────────────
// Embedding Management
// ──────────────────────────────────────────────────────────────
function renderEmbModels(models) {
	var listEl = document.getElementById("emb-models-list");
	var statusEl = document.getElementById("emb-global-status");
	var textEl = document.getElementById("emb-global-text");
	var btnDownload = document.getElementById("btn-download-emb");
	var btnDelete = document.getElementById("btn-delete-emb");

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

	var html = '<table class="model-table"><tbody>';
	for (var i = 0; i < models.length; i++) {
		var m = models[i];
		var repoId = Object.keys(m)[0];
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
		selectedEmbRepo = Object.keys(models[0]);
		selectedEmbRepo = selectedEmbRepo[0];
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
			var statusEl = document.getElementById("emb-global-status");
			var textEl = document.getElementById("emb-global-text");
			statusEl.className = "global-status critical";
			textEl.textContent = "Error loading embedding models";
		});
}

function selectEmbModel(repoId) {
	selectedEmbRepo = repoId;
	var listEl = document.getElementById("emb-models-list");
	var rows = listEl.querySelectorAll(".model-name");
	for (var i = 0; i < rows.length; i++) {
		rows[i].style.fontWeight = "normal";
		rows[i].style.color = "#007bff";
	}
	if (rows.length > 0) {
		for (var j = 0; j < rows.length; j++) {
			if (rows[j].textContent === repoId) {
				rows[j].style.fontWeight = "bold";
				rows[j].style.color = "#0056b3";
				break;
			}
		}
	}
}

function searchEmbModel() {
	var query = document.getElementById("emb-search-input").value.trim();
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
			var resultsEl = document.getElementById("emb-search-results");
			if (!data.models || data.models.length === 0) {
				resultsEl.innerHTML = '<p class="info-text">No results found.</p>';
				return;
			}

			var html = "";
			for (var i = 0; i < data.models.length; i++) {
				var m = data.models[i];
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

function downloadEmbModel() {
	if (!selectedEmbRepo) return;
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
			var btn = document.getElementById("btn-download-emb");
			btn.textContent = "Downloading...";
			btn.disabled = true;

			var checkProgress = setInterval(() => {
				fetch(
					CONFIG.embedding.progress +
						"?repo_id=" +
						encodeURIComponent(selectedEmbRepo),
				)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === "completed") {
							clearInterval(checkProgress);
							btn.textContent = "Download";
							btn.disabled = false;
							checkEmbModels();
						} else if (data.status?.startsWith("error")) {
							clearInterval(checkProgress);
							btn.textContent = "Download";
							btn.disabled = false;
							alert(`Download failed: ${data.status}`);
						}
					})
					.catch(() => {});
			}, 1000);
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

function downloadEmbModelDirect(repoId) {
	selectedEmbRepo = repoId;
	downloadEmbModel();
}

function checkDimensionStatus() {
	fetch("/api/v1/models/embeddings/dimension-status")
		.then((r) => r.json())
		.then((data) => {
			var banner = document.getElementById("emb-dim-banner");
			if (!banner) return;
			if (data.mismatch) {
				document.getElementById("emb-model-dim").textContent =
					data.model_dimension || "unknown";
				document.getElementById("emb-coll-dim").textContent =
					data.collection_dimension || "unknown";
				banner.style.display = "block";
			} else {
				banner.style.display = "none";
			}
		})
		.catch(() => {
			var banner = document.getElementById("emb-dim-banner");
			if (banner) banner.style.display = "none";
		});
}

function recreateAndReindex() {
	if (
		!confirm(
			"Recreate Qdrant collection(s) and reindex all documents? This will delete existing vectors.",
		)
	)
		return;
	var btn = document.querySelector("#emb-dim-banner .btn");
	if (btn) {
		btn.textContent = "Recreating...";
		btn.disabled = true;
	}
	var statusEl =
		document.getElementById("emb-download-status") ||
		document.getElementById("qdrant-download-status");
	if (statusEl) {
		statusEl.textContent = "Reindexing...";
		statusEl.className = "status-message";
	}

	fetch("/api/v1/models/embeddings/dimension-status")
		.then((r) => r.json())
		.then((data) => {
			var collections = data.mismatched_collections || ["sigma_docs"];
			var chain = Promise.resolve();
			collections.forEach((name) => {
				chain = chain.then(() =>
					fetch("/api/v1/qdrant", {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							action: "reindex",
							payload: { action: "reindex", collection_name: name },
						}),
					}).then((r) => r.json()),
				);
			});
			return chain;
		})
		.then(() => {
			checkDimensionStatus();
			if (statusEl) {
				statusEl.textContent = "Reindex completed";
				statusEl.className = "status-message success";
			}
		})
		.catch((e) => {
			alert(`Reindex failed: ${e.message || "Unknown error"}`);
			if (statusEl) {
				statusEl.textContent = "Reindex failed";
				statusEl.className = "status-message error";
			}
		})
		.finally(() => {
			if (btn) {
				btn.textContent = "Recreate collection & Reindex";
				btn.disabled = false;
			}
		});
}

function deleteEmbModel() {
	if (!selectedEmbRepo) return;
	if (!confirm(`Delete model ${selectedEmbRepo}?`)) return;

	fetch(`${CONFIG.embedding.delete}/${encodeURIComponent(selectedEmbRepo)}`, {
		method: "DELETE",
	})
		.then((r) =>
			r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
		)
		.then(() => {
			selectedEmbRepo = null;
			checkEmbModels();
		})
		.catch((e) => {
			alert(`Error: ${e.message}`);
		});
}

// ──────────────────────────────────────────────────────────────
// Specifications
// ──────────────────────────────────────────────────────────────
function renderSpecsStatus(repos, defaultOrg, defaultName) {
	var statusEl = document.getElementById("specs-status");
	var listEl = document.getElementById("specs-repos-list");

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

	var found = false;
	var foundRepo = null;
	for (var i = 0; i < repos.length; i++) {
		if (repos[i].org === defaultOrg && repos[i].name === defaultName) {
			found = true;
			foundRepo = repos[i];
			break;
		}
	}

	if (found) {
		setStatusText(statusEl, "Default repository configured", true);
		var statusClass =
			foundRepo.repo_status === "error" ? "text-danger" : "text-success";
		var statusLabel =
			foundRepo.repo_status === "error"
				? "ERROR"
				: foundRepo.repo_status === "cloning" ||
						foundRepo.repo_status === "syncing"
					? "SYNCING"
					: "READY";
		var dotClass =
			foundRepo.repo_status === "error"
				? "data-dot-missing"
				: foundRepo.repo_status === "cloning" ||
						foundRepo.repo_status === "syncing"
					? "data-dot-warn"
					: "data-dot-ok";
		var fixBtnHtml =
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
	var statusEl = document.getElementById("specs-status");
	setStatusText(statusEl, "Loading specifications...", true);

	var defaultOrg = _BACKEND_CONFIG.Hardware ? "sigmahq" : "sigmahq";
	var defaultName = _BACKEND_CONFIG.Hardware
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
			var listEl = document.getElementById("specs-repos-list");
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

function fixSpecRepo() {
	var defaultUrl = "https://github.com/sigmahq/sigma-specification";
	var defaultBranch = "main";

	if (
		!confirm(
			"Clone the default SigmaHQ specification repository (" +
				defaultUrl +
				")?",
		)
	)
		return;

	var statusEl = document.getElementById("specs-config-status");
	statusEl.textContent = "Cloning repository...";
	statusEl.className = "status-message";

	fetch(CONFIG.spec.add, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ url: defaultUrl, branch: defaultBranch }),
	})
		.then((r) => r.json())
		.then((data) => {
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
		})
		.catch((err) => {
			statusEl.textContent = `Error: ${err.message}`;
			statusEl.className = "status-message error";
		});
}

// ──────────────────────────────────────────────────────────────
// Config Object (accessible via onclick=)
// ──────────────────────────────────────────────────────────────
var _Config = {
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
	downloadLlmModel: downloadLlmModel,
	downloadLlmModelDirect: downloadLlmModelDirect,
	deleteLlmModel: deleteLlmModel,

	// Embedding
	selectEmbModel: selectEmbModel,
	searchEmbModel: searchEmbModel,
	downloadEmbModel: downloadEmbModel,
	downloadEmbModelDirect: downloadEmbModelDirect,
	deleteEmbModel: deleteEmbModel,

	// Scroll helpers
	scrollToAndOpen: scrollToAndOpen,

	// Status
	loadSystemStatus: loadSystemStatus,
};

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
	checkDimensionStatus();
	loadSystemStatus();

	// Bind form submit
	var form = document.getElementById("config-form");
	if (form)
		form.addEventListener("submit", (e) => {
			e.preventDefault();
			saveBackendConfig();
		});

	// Update Qdrant Web UI link when Base URL changes
	var qdrantUrlInput = document.getElementById("qdrant-base-url");
	var qdrantWebLink = document.getElementById("qdrant-webui-link");
	if (qdrantUrlInput && qdrantWebLink) {
		function updateQdrantWebLink() {
			var base = qdrantUrlInput.value.replace(/\/+$/, "");
			qdrantWebLink.href = base
				? `${base}/dashboard`
				: "http://127.0.0.1:6333/dashboard";
		}
		qdrantUrlInput.addEventListener("change", updateQdrantWebLink);
		qdrantUrlInput.addEventListener("input", updateQdrantWebLink);
	}

	// Setup sidebar nav clicks
	var navLinks = document.querySelectorAll(".config-nav-link");
	navLinks.forEach((link) => {
		link.addEventListener("click", function (_e) {
			navLinks.forEach((l) => {
				l.classList.remove("active");
			});
			this.classList.add("active");
		});
	});
});
