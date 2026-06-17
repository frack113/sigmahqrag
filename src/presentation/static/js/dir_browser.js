/* Shared Directory Browser — reusable tree/flat file selection */

function escAttr(s) {
	if (s == null) return "";
	return String(s)
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

function escHtml(s) {
	if (s == null) return "";
	return String(s)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

class DirBrowser {
	constructor(containerId, options) {
		this.container = document.getElementById(containerId);
		if (!this.container) throw new Error(`Container #${containerId} not found`);

		this.opts = {
			mode: "flat",
			endpoints: {},
			saveMethod: "PUT",
			saveOnChange: true,
			selectedCountEl: null,
			onSelectionChange: null,
			...options,
		};

		this.selected = new Set();
		this._loaded = false;
		this._boundChange = null;
		this._boundClick = null;

		var prefix = containerId;
		if (prefix.endsWith("-tree")) prefix = prefix.slice(0, -5);
		window[`_db_expand_${prefix}`] = this.expandAll.bind(this);
		window[`_db_collapse_${prefix}`] = this.collapseAll.bind(this);

		this._delegateEvents();
	}

	destroy() {
		if (this._boundChange) {
			this.container.removeEventListener("change", this._boundChange);
			this._boundChange = null;
		}
		if (this._boundClick) {
			this.container.removeEventListener("click", this._boundClick);
			this._boundClick = null;
		}
		var prefix = this.container.id;
		if (prefix.endsWith("-tree")) prefix = prefix.slice(0, -5);
		delete window[`_db_expand_${prefix}`];
		delete window[`_db_collapse_${prefix}`];
	}

	_delegateEvents() {
		this._boundChange = function (e) {
			var cb = e.target;
			if (
				(cb.type === "checkbox" && cb.classList.contains("tree-checkbox")) ||
				cb.classList.contains("dir-checkbox-inner")
			) {
				if (cb.checked) {
					this.selected.add(cb.value);
				} else {
					this.selected.delete(cb.value);
				}
				this._onChange();
			}
		}.bind(this);
		this.container.addEventListener("change", this._boundChange);

		this._boundClick = ((e) => {
			var btn = e.target.closest(".tree-toggle");
			if (btn) {
				var li = btn.closest(".tree-node");
				var children = li?.querySelector(".tree-children");
				if (children) {
					var isExpanded = children.style.display !== "none";
					children.style.display = isExpanded ? "none" : "block";
					btn.innerHTML = isExpanded ? "&#9658;" : "&#9660;";
				}
			}
		}).bind(this);
		this.container.addEventListener("click", this._boundClick);
	}

	async load() {
		try {
			const { endpoints, mode } = this.opts;

			if (mode === "tree") {
				var treeResp, selResp;
				if (endpoints.selected) {
					var resps = await Promise.all([
						fetch(endpoints.list),
						fetch(endpoints.selected),
					]);
					treeResp = resps[0];
					selResp = resps[1];
				} else {
					treeResp = await fetch(endpoints.list);
				}

				const data = await treeResp.json();
				if (!data.success) {
					this._showError(data.error || "Failed to load directory tree");
					return;
				}
				var tree =
					data.tree ||
					(data.data?.dirs
						? data.data.dirs.map((d) => ({ name: d, path: d }))
						: []);
				if (tree.length === 0) {
					this._showEmpty("No directories found.");
					return;
				}

				if (selResp) {
					const selData = await selResp.json();
					var selected = selData.data?.selected ? selData.data.selected : [];
					selected.forEach(
						function (d) {
							this.selected.add(d);
						}.bind(this),
					);
				} else {
					this._collectSelected(tree);
				}

				this._renderTree(tree);
			} else {
				const [listResp, selResp] = await Promise.all([
					fetch(endpoints.list),
					fetch(endpoints.selected),
				]);
				const listData = await listResp.json();
				const selData = await selResp.json();

				if (!listData.success) {
					this._showError(listData.error || "Failed to load directories");
					return;
				}
				const dirs = listData.data?.dirs || [];
				if (dirs.length === 0) {
					this._showEmpty("No directories found.");
					return;
				}
				const selected = selData.data?.selected || [];
				selected.forEach(
					function (d) {
						this.selected.add(d);
					}.bind(this),
				);
				this._renderFlat(dirs);
			}

			this._loaded = true;
		} catch (err) {
			console.error("DirBrowser load error:", err);
			this._showError("Error loading directories.");
		}
	}

	async save() {
		const { endpoints, saveMethod } = this.opts;
		const selected = Array.from(this.selected);

		try {
			const resp = await fetch(endpoints.save, {
				method: saveMethod,
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ selected }),
			});
			const data = await resp.json();
			if (!data.success) {
				console.error("DirBrowser save failed:", data.error);
			}
		} catch (err) {
			console.error("DirBrowser save error:", err);
		}
	}

	_onChange() {
		this._updateCount();
		if (this.opts.saveOnChange) {
			this.save();
		}
		if (this.opts.onSelectionChange) {
			this.opts.onSelectionChange(Array.from(this.selected));
		}
	}

	_collectSelected(nodes) {
		for (var i = 0; i < nodes.length; i++) {
			var node = nodes[i];
			if (node.selected) this.selected.add(node.path);
			if (node.children) this._collectSelected(node.children);
		}
	}

	_renderTree(nodes) {
		this.container.innerHTML = `<ul class="tree-root">${this._renderTreeNodes(nodes)}</ul>`;
		this._updateCount();
	}

	_renderTreeNodes(nodes) {
		var html = "";
		for (var i = 0; i < nodes.length; i++) {
			var node = nodes[i];
			var hasChildren = node.children && node.children.length > 0;
			var isChecked = this.selected.has(node.path);
			var childrenHtml = hasChildren
				? '<ul class="tree-children" style="display:none;">' +
					this._renderTreeNodes(node.children) +
					"</ul>"
				: "";
			html +=
				'<li class="tree-node">' +
				'<div class="tree-item">' +
				(hasChildren
					? '<button class="tree-toggle" type="button">&#9658;</button>'
					: '<span class="tree-spacer"></span>') +
				'<input type="checkbox" class="tree-checkbox" value="' +
				escAttr(node.path) +
				'" ' +
				(isChecked ? "checked" : "") +
				">" +
				'<span class="tree-folder-icon">&#128193;</span>' +
				'<span class="tree-folder-name">' +
				escHtml(node.name) +
				"</span>" +
				"</div>" +
				childrenHtml +
				"</li>";
		}
		return html;
	}

	_renderFlat(dirs) {
		var html = "";
		for (var i = 0; i < dirs.length; i++) {
			var d = dirs[i];
			var isChecked = this.selected.has(d);
			html +=
				'<label class="dir-checkbox">' +
				'<input type="checkbox" class="dir-checkbox-inner" value="' +
				escAttr(d) +
				'" ' +
				(isChecked ? "checked" : "") +
				">" +
				escHtml(d) +
				"</label>";
		}
		this.container.innerHTML = html;
		this._updateCount();
	}

	expandAll() {
		var children = this.container.querySelectorAll(".tree-children");
		for (var i = 0; i < children.length; i++) {
			children[i].style.display = "block";
		}
		var toggles = this.container.querySelectorAll(".tree-toggle");
		for (var i = 0; i < toggles.length; i++) {
			toggles[i].innerHTML = "&#9660;";
		}
	}

	collapseAll() {
		var children = this.container.querySelectorAll(".tree-children");
		for (var i = 0; i < children.length; i++) {
			children[i].style.display = "none";
		}
		var toggles = this.container.querySelectorAll(".tree-toggle");
		for (var i = 0; i < toggles.length; i++) {
			toggles[i].innerHTML = "&#9658;";
		}
	}

	_updateCount() {
		var countEl = this.opts.selectedCountEl
			? typeof this.opts.selectedCountEl === "string"
				? document.getElementById(this.opts.selectedCountEl)
				: this.opts.selectedCountEl
			: null;
		if (countEl) {
			var count = this.selected.size;
			countEl.textContent = count > 0 ? `${count} folder(s) selected` : "";
		}
	}

	_showError(msg) {
		this.container.innerHTML = `<p class="dir-browser-empty">${escHtml(msg)}</p>`;
	}

	_showEmpty(msg) {
		this.container.innerHTML = `<p class="dir-browser-empty">${escHtml(msg)}</p>`;
	}
}
