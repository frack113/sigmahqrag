function showToast(message, type) {
    if (!type) type = 'info';
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3000);
}

function esc(s) {
    if (s == null) return '';
    var m = { '&': '\x26amp;', '<': '\x26lt;', '>': '\x26gt;', '"': '\x26quot;', "'": '\x26#39;' };
    return String(s).replace(/[&<>"']/g, function(c) { return m[c]; });
}

function escAttr(s) {
    if (s == null) return '';
    var m = { '&': '\x26amp;', '"': '\x26quot;', "'": '\x26#39;', '<': '\x26lt;', '>': '\x26gt;' };
    return String(s).replace(/[&"'<>]/g, function(c) { return m[c]; });
}
