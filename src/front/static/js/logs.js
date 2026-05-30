let currentSource = 'system';
let eventSource = null;
let isTailMode = true;
let scrollLocked = true;
let allLines = [];

document.addEventListener('DOMContentLoaded', () => {
    const output = document.getElementById('logs-output');
    const linesInput = document.getElementById('log-lines');

    linesInput.addEventListener('change', () => {
        if (!isTailMode) loadLogs();
    });

    document.querySelectorAll('#log-sources a').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            selectSource(a.dataset.source);
        });
    });

    // Search input - filter displayed lines
    const searchInput = document.getElementById('log-search');
    searchInput.addEventListener('input', () => {
        renderFilteredLogs();
    });

    // Scroll lock - unlock when user scrolls up
    output.addEventListener('scroll', () => {
        const atBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 100;
        scrollLocked = atBottom;
    });

    startTail();
});

function selectSource(source) {
    currentSource = source;
    document.querySelectorAll('#log-sources a').forEach(a => a.classList.remove('active'));
    const link = document.querySelector(`#log-sources a[data-source="${escAttr(source)}"]`);
    if (link) link.classList.add('active');
    document.querySelector('#logs-header h2').textContent =
        source === 'system' ? 'System Logs' :
        source === 'llamacpp' ? 'llama.cpp Logs' : 'Qdrant Logs';
    restartTail();
}

function getLines() {
    return parseInt(document.getElementById('log-lines').value) || 50;
}

function toggleTail() {
    isTailMode = document.getElementById('tail-mode').checked;
    scrollLocked = true;
    if (isTailMode) {
        startTail();
    } else {
        stopTail();
        loadLogs();
    }
}

function stopTail() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

function startTail() {
    if (!isTailMode) return;
    stopTail();
    allLines = [];
    const lines = getLines();
    const url = `/api/v1/logs/stream?source=${encodeURIComponent(currentSource)}&lines=${lines}`;
    eventSource = new EventSource(url);

    let totalSeen = 0;
    eventSource.addEventListener('log', (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'init') {
                allLines = data.lines || [];
                totalSeen = allLines.length;
                scrollLocked = true;
            } else if (data.type === 'update') {
                const newLines = data.lines || [];
                const newTotal = data.line_count || 0;
                // File was truncated/rotated — reset buffer
                if (newTotal < totalSeen) {
                    allLines = newLines;
                    totalSeen = newTotal;
                } else {
                    const countToAdd = newTotal - totalSeen;
                    allLines.push(...newLines.slice(-countToAdd));
                    totalSeen = newTotal;
                }
                scrollLocked = true;
            } else if (data.type === 'error') {
                allLines = [`Error: ${data.message}`];
                totalSeen = 0;
            }
            renderFilteredLogs();
        } catch (e) {
            console.error('SSE parse error:', e);
        }
    });

    eventSource.onerror = () => {
        console.error('SSE connection error, retrying in 3s...');
        eventSource.close();
        eventSource = null;
        setTimeout(() => { if (isTailMode) startTail(); }, 3000);
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
    const output = document.getElementById('logs-output');
    const searchTerm = document.getElementById('log-search').value.toLowerCase();
    const statsEl = document.getElementById('log-stats');
    const count = getLines();

    // Get recent lines based on config
    const displayedLines = allLines.length > count ? allLines.slice(-count) : allLines;

    // Filter by search term
    const filtered = searchTerm
        ? displayedLines.filter(line => line.toLowerCase().includes(searchTerm))
        : displayedLines;

    // Colorize log levels
    const html = filtered.map(line => colorizeLine(line)).join('\n');

    output.innerHTML = html || 'No logs found';

    // Auto-scroll in tail mode when at bottom
    if (scrollLocked && isTailMode && !searchTerm) {
        requestAnimationFrame(() => {
            output.scrollTop = output.scrollHeight;
        });
    }

    // Update stats
    if (statsEl) {
        statsEl.textContent = `${filtered.length} lines`
            + (allLines.length !== displayedLines.length ? ` / ${allLines.length} total` : '')
            + (searchTerm ? ` (filtered)` : '');
    }
}

function colorizeLine(line) {
    // Escape HTML entities
    const escaped = line
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Color by log level — single regex pass
    if (/^\d{4}-\d{2}-\d{2}/.test(escaped)) {
        const match = escaped.match(/(?:ERROR|CRITICAL|WARNING|WARN|DEBUG|INFO)/);
        if (match) {
            const levelClass = match[0].toUpperCase();
            const cls = levelClass === 'WARN' ? 'warning'
                : levelClass === 'CRITICAL' ? 'error'
                : levelClass.toLowerCase();
            return `<span class="log-level-${cls}">${escaped}</span>`;
        }
    }
    return `<span class="log-line">${escaped}</span>`;
}

async function loadLogs() {
    stopTail();
    const lines = getLines();
    const params = new URLSearchParams({ source: currentSource, lines: lines });

    try {
        const response = await fetch(`/api/v1/logs?${params}`);
        const data = await response.json();
        allLines = data.logs.map(l => l.text);
        scrollLocked = true;
        renderFilteredLogs();
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

async function clearLogs() {
    if (!confirm('Clear all logs for ' + currentSource + '?')) return;
    try {
        const response = await fetch(`/api/v1/logs?source=${encodeURIComponent(currentSource)}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            allLines = [];
            document.getElementById('logs-output').innerHTML = '';
            const statsEl = document.getElementById('log-stats');
            if (statsEl) statsEl.textContent = 'Logs cleared';
        } else {
            console.error('Failed to clear logs:', data.message);
        }
    } catch (error) {
        console.error('Failed to clear logs:', error);
    }
}

async function togglePause() {
    const btn = document.getElementById('pause-btn');
    if (isTailMode) {
        stopTail();
        scrollLocked = false;
        btn.textContent = 'Resume';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
    } else {
        startTail();
        scrollLocked = true;
        btn.textContent = 'Pause';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
    }
}

function escAttr(s) {
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
