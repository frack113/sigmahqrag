function safeCall(fn) {
	try {
		if (fn) fn();
	} catch (e) {
		console.error("ProgressBar callback error:", e);
	}
}

function safeCall1(fn, arg) {
	try {
		if (fn) fn(arg);
	} catch (e) {
		console.error("ProgressBar callback error:", e);
	}
}

// biome-ignore lint/correctness/noUnusedVariables: used from Jinja2 templates
class ProgressBar {
	constructor(opts) {
		const options = opts || {};
		this.container =
			typeof options.container === "string"
				? document.getElementById(options.container)
				: options.container;
		this.fill =
			typeof options.fill === "string"
				? document.getElementById(options.fill)
				: options.fill;
		this.text =
			typeof options.text === "string"
				? document.getElementById(options.text)
				: options.text;
		this.label =
			typeof options.label === "string"
				? document.getElementById(options.label)
				: options.label;
		this._onComplete = options.onComplete || null;
		this._onError = options.onError || null;
	}

	setProgress(pct) {
		if (this.fill) {
			const clamped = Math.min(100, Math.max(0, Number(pct) || 0));
			this.fill.style.width = `${clamped}%`;
			this.fill.style.background = clamped === 100 ? "#4caf50" : "";
		}
		if (this.container) {
			this.container.style.display = "block";
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
			this.container.style.display = "block";
		}
	}

	hide() {
		if (this.container) {
			this.container.style.display = "none";
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
		const endpoint = opts.endpoint;
		const downloadId = opts.downloadId;
		const onUpdate = opts.onUpdate || (() => {});
		const onComplete = opts.onComplete || (() => {});
		const onError = opts.onError || (() => {});
		const intervalMs = opts.interval || 1000;
		const pollId = setInterval(() => {
			fetch(endpoint)
				.then((r) => {
					if (!r.ok) throw new Error(`HTTP ${r.status}`);
					return r.json();
				})
				.then((data) => {
					const task = data.downloads ? data.downloads[downloadId] : null;
					if (!task) {
						clearInterval(pollId);
						safeCall1(onError, "Download task not found");
						return;
					}
					const downloaded = task.bytes_downloaded || 0;
					const total = task.total_bytes || 1;
					const pct = Math.round((downloaded / total) * 100);
					const text =
						pct +
						"% (" +
						Math.round(downloaded / 1024 / 1024) +
						"MB / " +
						Math.round(total / 1024 / 1024) +
						"MB)";
					safeCall1(onUpdate, pct, text);
					if (task.status === "completed") {
						clearInterval(pollId);
						safeCall(onComplete);
					} else if (task.status === "failed") {
						clearInterval(pollId);
						safeCall1(onError, task.error || "Download failed");
					}
				})
				.catch((e) => {
					clearInterval(pollId);
					safeCall1(onError, e.message || "Poll error");
				});
		}, intervalMs);
		return pollId;
	}

	static pollProgressEndpoint(opts) {
		if (!opts) return 0;
		const url = opts.url;
		const onUpdate = opts.onUpdate || (() => {});
		const onComplete = opts.onComplete || (() => {});
		const onError = opts.onError || (() => {});
		const intervalMs = opts.interval || 2000;
		const pollId = setInterval(() => {
			fetch(url)
				.then((r) =>
					r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
				)
				.then((d) => {
					const p = Number(d.progress) || 0;
					const status = d.status || "";
					safeCall1(onUpdate, p, status);
					if (p >= 100 || status === "completed") {
						clearInterval(pollId);
						safeCall1(onComplete, d);
					}
				})
				.catch((e) => {
					clearInterval(pollId);
					safeCall1(onError, e.message || "Poll error");
				});
		}, intervalMs);
		return pollId;
	}
}
