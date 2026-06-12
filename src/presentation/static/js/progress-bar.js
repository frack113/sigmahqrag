function safeCall(fn) {
    try { if (fn) fn(); } catch(e) { console.error('ProgressBar callback error:', e); }
}

function safeCall1(fn, arg) {
    try { if (fn) fn(arg); } catch(e) { console.error('ProgressBar callback error:', e); }
}

class ProgressBar {
    constructor(opts) {
        var options = opts || {};
        this.container = typeof options.container === 'string'
            ? document.getElementById(options.container)
            : options.container;
        this.fill = typeof options.fill === 'string'
            ? document.getElementById(options.fill)
            : options.fill;
        this.text = typeof options.text === 'string'
            ? document.getElementById(options.text)
            : options.text;
        this.label = typeof options.label === 'string'
            ? document.getElementById(options.label)
            : options.label;
        this._onComplete = options.onComplete || null;
        this._onError = options.onError || null;
    }

    setProgress(pct) {
        if (this.fill) {
            var clamped = Math.min(100, Math.max(0, Number(pct) || 0));
            this.fill.style.width = clamped + '%';
            this.fill.style.background = clamped === 100 ? '#4caf50' : '';
        }
        if (this.container) {
            this.container.classList.add('show');
        }
    }

    setText(msg) {
        if (this.text) {
            this.text.textContent = msg;
        }
    }

    setLabel(msg) {
        if (this.label) {
            this.label.textContent = msg;
        }
    }

    show() {
        if (this.container) {
            this.container.classList.add('show');
        }
    }

    hide() {
        if (this.container) {
            this.container.classList.remove('show');
        }
    }

    complete(msg) {
        this.setProgress(100);
        if (msg) this.setText(msg);
        safeCall(this._onComplete);
    }

    error(msg) {
        if (msg && this.text) this.text.textContent = msg;
        safeCall(this._onError);
    }

    static pollDownload(opts) {
        if (!opts) return 0;
        var endpoint = opts.endpoint;
        var downloadId = opts.downloadId;
        var onUpdate = opts.onUpdate || function(){};
        var onComplete = opts.onComplete || function(){};
        var onError = opts.onError || function(){};
        var intervalMs = opts.interval || 1000;
        var pollId = setInterval(function() {
            fetch(endpoint)
                .then(function(r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return r.json();
                })
                .then(function(data) {
                    var task = data.downloads ? data.downloads[downloadId] : null;
                    if (!task) {
                        clearInterval(pollId);
                        safeCall1(onError, 'Download task not found');
                        return;
                    }
                    var downloaded = task.bytes_downloaded || 0;
                    var total = task.total_bytes || 1;
                    var pct = Math.round(downloaded / total * 100);
                    var text = pct + '% (' + Math.round(downloaded/1024/1024) + 'MB / ' + Math.round(total/1024/1024) + 'MB)';
                    safeCall1(onUpdate, pct, text);
                    if (task.status === 'completed') {
                        clearInterval(pollId);
                        safeCall(onComplete);
                    } else if (task.status === 'failed') {
                        clearInterval(pollId);
                        safeCall1(onError, task.error || 'Download failed');
                    }
                })
                .catch(function(e) {
                    clearInterval(pollId);
                    safeCall1(onError, e.message || 'Poll error');
                });
        }, intervalMs);
        return pollId;
    }

    static pollProgressEndpoint(opts) {
        if (!opts) return 0;
        var url = opts.url;
        var onUpdate = opts.onUpdate || function(){};
        var onComplete = opts.onComplete || function(){};
        var onError = opts.onError || function(){};
        var intervalMs = opts.interval || 2000;
        var pollId = setInterval(function() {
            fetch(url)
                .then(function(r) { return r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)); })
                .then(function(d) {
                    var p = Number(d.progress) || 0;
                    var status = d.status || '';
                    safeCall1(onUpdate, p, status);
                    if (p >= 100 || status === 'completed') {
                        clearInterval(pollId);
                        safeCall1(onComplete, d);
                    }
                })
                .catch(function(e) {
                    clearInterval(pollId);
                    safeCall1(onError, e.message || 'Poll error');
                });
        }, intervalMs);
        return pollId;
    }
}
