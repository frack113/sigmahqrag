window.Dashboard = (() => {
	const PAGE_SIZE = 50;
	let currentTable = null;
	let currentOffset = 0;
	let currentTotal = 0;

	document.addEventListener("DOMContentLoaded", () => {
		loadSidebar();
		showHome();
	});

	// ── API ──

	const API = {
		tables: () => fetch("/api/v1/dashboard/tables").then((r) => r.json()),
		table: (name, offset) =>
			fetch(
				`/api/v1/dashboard/tables/${encodeURIComponent(name)}?limit=${PAGE_SIZE}&offset=${offset}`,
			).then((r) => {
				if (!r.ok) return r.json().then((d) => Promise.reject(d));
				return r.json();
			}),
		dashboard: () => fetch("/api/v1/dashboard").then((r) => r.json()),
		action: (action) => {
			const url =
				action === "fix"
					? "/api/v1/system/dashboard"
					: action === "clean"
						? "/api/v1/system/dashboard/clean"
						: "/api/v1/system/dashboard/hard-reset";
			return fetch(url, { method: "POST" }).then((r) => r.json());
		},
	};

	// ── Sidebar ──

	async function loadSidebar() {
		const el = byId("table-list");
		if (!el) return;
		try {
			const data = await API.tables();
			el.innerHTML = data.tables
				.map((t) => `<a href="#" data-table="${escAttr(t)}">${esc(t)}</a>`)
				.join("");
			el.querySelectorAll("a").forEach((a) => {
				a.addEventListener("click", (e) => {
					e.preventDefault();
					selectTable(a.dataset.table);
				});
			});
		} catch {
			el.innerHTML = '<p class="sidebar-loading">Error loading tables</p>';
		}
	}

	function selectTable(name) {
		currentTable = name;
		currentOffset = 0;
		currentTotal = 0;
		activeSidebar(null);
		const link = document.querySelector(
			`#table-list a[data-table="${escAttr(name)}"]`,
		);
		if (link) link.classList.add("active");
		loadTable();
	}

	function showHome() {
		currentTable = null;
		activeSidebar("sidebar-home");
		loadDashboard();
	}

	function activeSidebar(id) {
		document.getElementById("sidebar-home")?.classList.remove("active");
		document.querySelectorAll("#table-list a").forEach((el) => {
			el.classList.remove("active");
		});
		if (id) document.getElementById(id)?.classList.add("active");
	}

	// ── Dashboard ──

	async function loadDashboard() {
		const container = byId("duckdb-content");
		if (!container) return;
		container.innerHTML = loadingHTML();

		try {
			const data = await API.dashboard();
			container.innerHTML = buildDashboard(data);
			wireDashboardEvents();
		} catch {
			container.innerHTML = errorHTML("Failed to load dashboard");
		}
	}

	function buildDashboard(data) {
		const { health, tables, config, workers, recent_errors } = data;
		return `
      <div class="config-dashboard">
        <div class="config-hero-banner">
          <div class="hero-content">
            <h1>Database Dashboard</h1>
            <p>Metadata store — config, documents, workers, errors</p>
          </div>
          <div class="hero-actions">
            <button class="btn btn-secondary btn-sm" id="refresh-dash-btn">↻ Refresh</button>
          </div>
        </div>
        ${sectionHealth(health)}
        ${sectionTables(tables)}
        ${sectionConfig(config)}
        ${sectionWorkers(workers)}
        ${sectionErrors(recent_errors)}
      </div>`;
	}

	function sectionHealth(h) {
		const dotClass = h.is_healthy
			? "status-ok"
			: h.state === "missing"
				? "status-error"
				: "status-warning";
		const stateLabel = h.is_healthy
			? "Healthy"
			: h.state === "missing"
				? "Missing — database file not found"
				: h.state === "dirty_tables"
					? "Missing tables"
					: "Excess tables";
		const missing = h.tables_missing ?? [];
		const excess = h.tables_excess ?? [];

		return section(
			"Health",
			true,
			`
      <div class="card">
        <div class="card-header"><h2>Database Status</h2></div>
        <div class="card-body">
          <div class="global-status">
            <span class="status-dot ${dotClass}"></span>
            <span>${esc(stateLabel)}</span>
          </div>
          <div class="config-row"><strong>File size:</strong> <span>${h.file_size > 0 ? fmtBytes(h.file_size) : "—"}</span></div>
          <div class="config-row"><strong>Path:</strong> <span style="font-family:monospace;font-size:var(--text-sm)">${esc(h.relative)}</span></div>
          ${missing.length ? `<div class="config-row"><strong>Missing tables:</strong> <span class="error-text">${esc(missing.join(", "))}</span></div>` : ""}
          ${excess.length ? `<div class="config-row"><strong>Excess tables:</strong> <span style="color:var(--color-warning)">${esc(excess.join(", "))}</span></div>` : ""}
          <div class="form-actions" style="margin-top:12px">
            ${missing.length ? '<button class="btn btn-primary btn-sm dash-action" data-action="fix">Fix missing tables</button>' : ""}
            ${excess.length ? '<button class="btn btn-secondary btn-sm dash-action" data-action="clean">Drop excess tables</button>' : ""}
            <button class="btn btn-danger btn-sm dash-action" data-action="reset">Hard reset</button>
          </div>
          <div id="dash-action-status" class="status-message" style="margin-top:8px"></div>
        </div>
      </div>`,
		);
	}

	function sectionTables(tables) {
		const rows = tables
			.map(
				(t) =>
					`<tr><td>${esc(t.name)}</td><td class="num">${t.row_count.toLocaleString()}</td></tr>`,
			)
			.join("");
		return section(
			"Tables",
			true,
			`
      <div class="card" style="grid-column:1/-1">
        <div class="card-header"><h2>Table row counts</h2></div>
        <div class="card-body">
          ${
						tables.length
							? `<table><thead><tr><th>Table</th><th class="num">Rows</th></tr></thead><tbody>${rows}</tbody></table>`
							: '<p class="table-empty">No tables found.</p>'
					}
        </div>
      </div>`,
		);
	}

	function sectionConfig(config) {
		const keys = Object.keys(config);
		const rows = keys
			.map(
				(k) =>
					`<tr><td>${esc(k)}</td><td>${esc(fmtConfigVal(config[k]))}</td></tr>`,
			)
			.join("");
		return section(
			"Config",
			true,
			`
      <div class="card" style="grid-column:1/-1">
        <div class="card-header"><h2>Stored configuration</h2></div>
        <div class="card-body">
          ${
						keys.length
							? `<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>${rows}</tbody></table>`
							: '<p class="table-empty">No config values stored.</p>'
					}
        </div>
      </div>`,
		);
	}

	function sectionWorkers(workers) {
		const rows = workers
			.map((w) => {
				const dotClass =
					w.status === "running"
						? "status-ok"
						: w.status === "error"
							? "status-error"
							: "";
				return `<tr>
        <td>${esc(w.worker_type)}</td>
        <td><span class="status-dot ${dotClass}"></span> ${esc(w.status)}</td>
        <td class="num">${w.progress_percent != null ? `${Math.round(w.progress_percent)}%` : "—"}</td>
        <td>${esc(w.current_task_id || "—")}</td>
        <td>${esc(w.last_heartbeat || "—")}</td>
      </tr>`;
			})
			.join("");
		return section(
			"Workers",
			true,
			`
      <div class="card" style="grid-column:1/-1">
        <div class="card-header"><h2>Worker states</h2></div>
        <div class="card-body">
          ${
						workers.length
							? `<table><thead><tr><th>Worker</th><th>Status</th><th class="num">Progress</th><th>Task</th><th>Last heartbeat</th></tr></thead><tbody>${rows}</tbody></table>`
							: '<p class="table-empty">No worker states.</p>'
					}
        </div>
      </div>`,
		);
	}

	function sectionErrors(errors) {
		const rows = errors
			.map((e) => {
				const url = truncStr(e.normalized_url || e.original_url || "—", 60);
				const msg = truncStr(e.error_message || "", 80);
				return `<tr>
        <td title="${escAttr(e.original_url || "")}">${esc(url)}</td>
        <td>${esc(e.error_code || "")}</td>
        <td>${esc(msg)}</td>
        <td>${esc(e.org || "—")}</td>
      </tr>`;
			})
			.join("");
		return section(
			"Recent Errors",
			true,
			`
      <div class="card" style="grid-column:1/-1">
        <div class="card-header"><h2>Doc errors (last 10)</h2></div>
        <div class="card-body">
          ${
						errors.length
							? `<table><thead><tr><th>URL</th><th>Code</th><th>Message</th><th>Org</th></tr></thead><tbody>${rows}</tbody></table>`
							: '<p class="table-empty">No errors recorded.</p>'
					}
        </div>
      </div>`,
		);
	}

	function section(title, open, inner) {
		return `<details class="config-group" ${open ? "open" : ""}>
      <summary class="config-group-summary">${esc(title)}</summary>
      <div class="config-cards">${inner}</div>
    </details>`;
	}

	function wireDashboardEvents() {
		byId("refresh-dash-btn")?.addEventListener("click", loadDashboard);
		document.querySelectorAll(".dash-action").forEach((btn) => {
			btn.addEventListener("click", () => dbAction(btn.dataset.action));
		});
	}

	async function dbAction(action) {
		const statusEl = byId("dash-action-status");
		if (!statusEl) return;
		statusEl.textContent = "Processing…";
		statusEl.className = "status-message";
		try {
			const data = await API.action(action);
			statusEl.textContent = data.message || data.status || "Done";
			statusEl.className = "status-message";
			statusEl.style.color = "var(--color-success)";
			setTimeout(loadDashboard, 1000);
		} catch {
			statusEl.textContent = "Action failed";
			statusEl.className = "status-message error-text";
		}
	}

	// ── Table browsing ──

	async function loadTable() {
		const container = byId("duckdb-content");
		if (!container || !currentTable) return;
		container.innerHTML = loadingHTML();

		try {
			const data = await API.table(currentTable, currentOffset);
			currentTotal = data.total;
			container.innerHTML = buildTableUI(data);
			wireTableEvents(container);
		} catch (err) {
			const msg = err?.detail || err?.message || "Failed to load table data";
			container.innerHTML = errorHTML(esc(msg));
		}
	}

	function buildTableUI(data) {
		const { rows } = data;
		const isFirst = currentOffset === 0;
		const isLast = currentOffset + rows.length >= currentTotal;

		let html = paginationBar(isFirst, isLast);

		if (rows.length === 0) {
			html += '<p class="table-empty">No data</p>';
			return html;
		}

		const cols = Object.keys(rows[0]);
		html += '<div class="table-container"><table><thead><tr>';
		cols.forEach((c) => {
			html += `<th>${esc(c)}</th>`;
		});
		html += "</tr></thead><tbody>";

		rows.forEach((row) => {
			html += "<tr>";
			cols.forEach((c) => {
				const val = row[c] != null ? String(row[c]) : "";
				const isLong = val.length > 100;
				html += `<td class="${isLong ? "expandable" : ""}" data-cell="${escAttr(val)}" title="${isLong ? "Click to expand" : ""}">${esc(truncStr(val, 100))}</td>`;
			});
			html += "</tr>";
		});

		html += "</tbody></table></div>";
		return html;
	}

	function paginationBar(isFirst, isLast) {
		const prevDisabled = isFirst ? "disabled" : "";
		const nextDisabled = isLast ? "disabled" : "";
		return `<div class="table-controls">
      <h2>${esc(currentTable)}</h2>
      <div class="pagination">
        <button class="btn btn-sm btn-secondary" id="prev-btn" ${prevDisabled}>← Prev</button>
        <span>${currentTotal} row(s) total</span>
        <button class="btn btn-sm btn-secondary" id="next-btn" ${nextDisabled}>Next →</button>
        <button class="btn btn-sm btn-secondary" id="refresh-table-btn">↻ Refresh</button>
      </div>
    </div>`;
	}

	function wireTableEvents(container) {
		byId("prev-btn")?.addEventListener("click", () => {
			currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
			loadTable();
		});
		byId("next-btn")?.addEventListener("click", () => {
			currentOffset += PAGE_SIZE;
			loadTable();
		});
		byId("refresh-table-btn")?.addEventListener("click", loadTable);
		container.querySelectorAll("td.expandable").forEach((td) => {
			td.addEventListener("click", () => showCellModal(td.dataset.cell));
		});
	}

	// ── Helpers ──

	function loadingHTML() {
		return '<p class="table-empty" style="padding:24px">Loading…</p>';
	}

	function errorHTML(msg) {
		return `<p class="table-error">${msg}</p>`;
	}

	function showCellModal(content) {
		const existing = document.querySelector(".modal-overlay");
		if (existing) existing.remove();

		const overlay = document.createElement("div");
		overlay.className = "modal-overlay";
		overlay.addEventListener("click", (e) => {
			if (e.target === overlay) overlay.remove();
		});
		overlay.innerHTML = `<div class="modal-content modal-wide">
      <button class="btn btn-ghost modal-close">&times;</button>
      <pre>${esc(content)}</pre>
    </div>`;
		overlay
			.querySelector(".modal-close")
			?.addEventListener("click", () => overlay.remove());
		document.body.appendChild(overlay);
	}

	function fmtBytes(bytes) {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / 1048576).toFixed(1)} MB`;
	}

	function fmtConfigVal(v) {
		if (v == null) return "—";
		if (typeof v === "object") return JSON.stringify(v);
		return String(v);
	}

	function esc(s) {
		if (s == null) return "";
		return String(s)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	function escAttr(s) {
		if (s == null) return "";
		return String(s)
			.replace(/&/g, "&amp;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;");
	}

	function truncStr(s, n) {
		if (s == null) return "";
		return s.length > n ? `${s.substring(0, n)}…` : s;
	}

	function byId(id) {
		return document.getElementById(id);
	}

	// Public API for onclick handlers in template
	return { showHome, selectTable };
})();
