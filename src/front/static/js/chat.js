(function () {
    "use strict";

    function init() {
        var messagesEl = document.getElementById("chat-messages");
        var chatForm = document.getElementById("chat-form");
        var input = document.getElementById("message-input");
        var sendBtn = document.getElementById("send-btn");
        var welcome = document.getElementById("chat-welcome");
        var newChatBtn = document.getElementById("new-chat-btn");
        var typingEl = document.getElementById("typing-indicator");

        if (typeof marked !== "undefined") {
            marked.setOptions({ gfm: true, breaks: true });
        }

        function renderMarkdown(text) {
            if (typeof marked !== "undefined") {
                return marked.parse(text);
            }
            var div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }

        if (!messagesEl || !chatForm || !input || !sendBtn) return;

        function showTyping() {
            if (typingEl) typingEl.hidden = false;
        }

        function hideTyping() {
            if (typingEl) typingEl.hidden = true;
        }

        function createMessageHeader(role) {
            var header = document.createElement("div");
            header.className = "message-header";
            var icon = document.createElement("span");
            icon.className = "message-role-icon";
            icon.textContent = role === "user" ? "\u{1F464}" : "\u{1F916}";
            header.appendChild(icon);
            var label = document.createElement("span");
            label.textContent = role === "user" ? "Vous" : "SigmaHQ RAG";
            header.appendChild(label);
            return header;
        }

        function createMessageActions(role, contentEl) {
            var actions = document.createElement("div");
            actions.className = "message-actions";
            var copyBtn = document.createElement("button");
            copyBtn.className = "message-action-btn";
            copyBtn.textContent = "\u{1F4CB} Copier";
            copyBtn.addEventListener("click", function () {
                var text = contentEl.textContent || contentEl.innerText || "";
                navigator.clipboard.writeText(text).then(function () {
                    showToast("Copi\u00E9 !");
                }).catch(function () {
                    showToast("Erreur de copie");
                });
            });
            actions.appendChild(copyBtn);
            return actions;
        }

        function showToast(msg) {
            var existing = document.querySelector(".copy-toast");
            if (existing) existing.remove();
            var toast = document.createElement("div");
            toast.className = "copy-toast show";
            toast.textContent = msg;
            document.body.appendChild(toast);
            setTimeout(function () {
                toast.classList.remove("show");
                setTimeout(function () { toast.remove(); }, 300);
            }, 1500);
        }

        function addMessage(role, content) {
            var div = document.createElement("div");
            div.className = "message " + role;

            var header = createMessageHeader(role);
            div.appendChild(header);

            var body = document.createElement("div");
            body.className = "message-body";
            if (role === "user") {
                body.textContent = content;
            } else {
                body.innerHTML = renderMarkdown(content);
            }
            div.appendChild(body);

            var actions = createMessageActions(role, body);
            div.appendChild(actions);

            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            return div;
        }

        function setLoading(loading) {
            sendBtn.disabled = loading;
            sendBtn.textContent = loading ? "Envoi..." : "Send";
            if (loading) {
                showTyping();
            } else {
                hideTyping();
            }
        }

        function loadHistory() {
            fetch("/api/v1/chat/history")
                .then(function (resp) { return resp.json(); })
                .then(function (history) {
                    if (history && history.length > 0) {
                        if (welcome) { welcome.remove(); welcome = null; }
                        history.forEach(function (msg) {
                            addMessage(msg.role, msg.content);
                        });
                    }
                })
                .catch(function () {});
        }

        function clearChat() {
            fetch("/api/v1/chat/history", { method: "DELETE" })
                .then(function () {
                    messagesEl.querySelectorAll(".message").forEach(function (el) { el.remove(); });
                    if (!welcome) {
                        var w = document.createElement("div");
                        w.className = "chat-welcome";
                        w.innerHTML = "<h2>SigmaHQ RAG</h2><p>Posez vos questions sur les r\u00E8gles Sigma</p>";
                        messagesEl.appendChild(w);
                        welcome = w;
                    } else {
                        welcome.hidden = false;
                    }
                    hideTyping();
                })
                .catch(function () {
                    showToast("Erreur lors de l'effacement");
                });
        }

        if (newChatBtn) {
            newChatBtn.addEventListener("click", clearChat);
        }

        loadHistory();

        chatForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            var text = input.value.trim();
            if (!text) return;

            addMessage("user", text);
            input.value = "";
            input.style.height = "auto";
            setLoading(true);

            if (welcome) { welcome.remove(); welcome = null; }

            var resp;
            try {
                resp = await fetch("/api/v1/chat/message/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, mode: "search" }),
                });
            } catch (err) {
                addMessage("error", "Erreur réseau: " + err.message);
                setLoading(false);
                return;
            }

            if (!resp.ok) {
                addMessage("error", "Request failed with status " + resp.status);
                setLoading(false);
                return;
            }

            var reader = resp.body.getReader();
            var decoder = new TextDecoder();
            var accumulated = "";
            var bubble = null;
            var gotToken = false;

            try {
                while (true) {
                    var result;
                    try {
                        result = await reader.read();
                    } catch (err) {
                        addMessage("error", "Erreur de lecture du flux: " + err.message);
                        break;
                    }
                    if (result.done) break;

                    var chunk = decoder.decode(result.value, { stream: true });
                    var lines = chunk.split("\n\n");

                    for (var j = 0; j < lines.length; j++) {
                        var line = lines[j];
                        if (line.startsWith("data: ")) {
                            var data = line.slice(6);
                            if (data === "[DONE]") {
                                if (!gotToken && !bubble) {
                                    addMessage("assistant", "(aucune réponse du LLM)");
                                }
                                setLoading(false);
                                return;
                            }
                            accumulated += data;
                            gotToken = true;
                            if (!bubble) {
                                hideTyping();
                                bubble = addMessage("assistant", "");
                            }
                            bubble.querySelector(".message-body").innerHTML = renderMarkdown(accumulated);
                            messagesEl.scrollTop = messagesEl.scrollHeight;
                        }
                    }
                }
                if (!gotToken && !bubble) {
                    addMessage("assistant", "(aucune réponse du LLM)");
                }
            } catch (err) {
                addMessage("error", "Error: " + err.message);
            }
            setLoading(false);
        });

        input.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = this.scrollHeight + "px";
        });

        input.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event("submit"));
            }
        });
    }

    document.addEventListener("DOMContentLoaded", init);
})();