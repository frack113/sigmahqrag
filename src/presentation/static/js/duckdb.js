let currentTable = null;
let currentOffset = 0;
let currentTotal = 0;
const PAGE_SIZE = 50;
let autoRefreshInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    loadTableList();
    loadTableListCount();
    startAutoRefresh();
});

let autoRefreshEnabled = true;

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        if (!autoRefreshEnabled) return;
        if (currentTable) {
            loadTableData();
        }
        loadTableList();
    }, 5000);
}

function toggleAutoRefresh() {
    autoRefreshEnabled = !autoRefreshEnabled;
    const btn = document.getElementById('auto-refresh-btn');
    if (btn) {
        btn.textContent = autoRefreshEnabled ? 'Auto-refresh: ON (5s)' : 'Auto-refresh: OFF';
    }
}

async function loadTableList() {
    const container = document.getElementById('table-list');
    if (!container) return;
    try {
        const res = await fetch('/api/v1/duckdb/tables');
        const data = await res.json();
        container.innerHTML = data.tables.map(t =>
            `<a href="#" data-table="${escAttr(t)}" ${currentTable === t ? 'class="active"' : ''}>${esc(t)}</a>`
        ).join('');
        container.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                selectTable(a.dataset.table);
            });
        });
    } catch {
        container.innerHTML = '<p class="sidebar-loading">Error loading tables</p>';
    }
}

async function loadTableListCount() {
    const summary = document.querySelector('.tables-summary');
    if (!summary) return;
    try {
        const res = await fetch('/api/v1/duckdb/tables');
        const data = await res.json();
        summary.textContent = `${data.tables.length} tables available: ${data.tables.join(', ')}`;
    } catch {
    }
}

function selectTable(tableName) {
    currentTable = tableName;
    currentOffset = 0;
    currentTotal = 0;
    document.querySelectorAll('#table-list a').forEach(a => a.classList.remove('active'));
    const link = document.querySelector(`#table-list a[data-table="${escAttr(tableName)}"]`);
    if (link) link.classList.add('active');
    loadTableData();
}

async function loadTableData() {
    const content = document.getElementById('duckdb-content');
    if (!content || !currentTable) return;

    content.innerHTML = '<p class="table-empty">Loading...</p>';

    try {
        const res = await fetch(`/api/v1/duckdb/tables/${encodeURIComponent(currentTable)}?limit=${PAGE_SIZE}&offset=${currentOffset}`);
        const data = await res.json();
        if (!res.ok) {
            content.innerHTML = `<p class="table-error">${esc(data.detail || res.statusText)}</p>`;
            return;
        }
        currentTotal = data.total;
        renderTable(data, content);
    } catch {
        content.innerHTML = '<p class="table-error">Failed to load table data</p>';
    }
}

function renderTable(data, container) {
    const rows = data.rows;
    if (rows.length === 0) {
        const prevDisabled = currentOffset === 0 ? 'disabled' : '';
        container.innerHTML = `<div class="table-controls">
            <h2>${esc(currentTable)}</h2>
            <div class="pagination">
                <button onclick="prevPage()" ${prevDisabled}>← Prev</button>
                <span>${data.total} row(s) total</span>
                <button disabled>Next →</button>
            </div>
        </div><p class="table-empty">No data</p>`;
        return;
    }

    const colNames = Object.keys(rows[0]);

    let html = `<div class="table-controls">
        <h2>${esc(currentTable)}</h2>
        <div class="pagination">
            <button onclick="prevPage()" ${currentOffset === 0 ? 'disabled' : ''}>← Prev</button>
            <span>rows ${currentOffset + 1}–${Math.min(currentOffset + rows.length, currentTotal)} of ${data.total}</span>
            <button onclick="nextPage()" ${currentOffset + rows.length >= currentTotal ? 'disabled' : ''}>Next →</button>
        </div>
    </div>`;

    html += '<div class="table-container"><table><thead><tr>';
    colNames.forEach(c => { html += `<th>${esc(c)}</th>`; });
    html += '</tr></thead><tbody>';

    rows.forEach(row => {
        html += '<tr>';
        colNames.forEach(c => {
            const val = row[c] !== null && row[c] !== undefined ? String(row[c]) : '';
            const isLong = val.length > 100;
            const cls = isLong ? 'expandable' : '';
            html += `<td class="${cls}" data-cell="${escAttr(val)}" title="${isLong ? 'Click to expand' : ''}">${esc(truncate(val, 100))}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;

    container.querySelectorAll('td.expandable').forEach(td => {
        td.addEventListener('click', () => showCellModal(td.dataset.cell));
    });
}

function prevPage() {
    if (currentOffset > 0) {
        currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
        loadTableData();
    }
}

function nextPage() {
    currentOffset += PAGE_SIZE;
    loadTableData();
}

function showCellModal(content) {
    const overlay = document.createElement('div');
    overlay.className = 'cell-modal-overlay';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    overlay.innerHTML = `<div class="cell-modal">
        <button class="modal-close">&times;</button>
        <pre>${esc(content)}</pre>
    </div>`;
    overlay.querySelector('.modal-close').addEventListener('click', () => overlay.remove());
    document.body.appendChild(overlay);
}

function esc(s) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return s.replace(/[&<>"']/g, c => map[c]);
}

function escAttr(s) {
    return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function truncate(s, max) {
    return s.length > max ? s.substring(0, max) + '…' : s;
}
