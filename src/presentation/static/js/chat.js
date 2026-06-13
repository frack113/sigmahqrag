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
        var promptSelect = document.getElementById("prompt-select");

        if (!messagesEl || !chatForm || !input || !sendBtn) return;

        if (typeof marked !== "undefined") {
            marked.setOptions({ gfm: true, breaks: true });
        }

        function renderMarkdown(text) {
            if (typeof marked !== "undefined") {
                var normalized = text
                    .replace(/([^\n])\n*(#{1,6}\s)/g, '$1\n\n$2')
                    .replace(/([^\n])\n*(\|)/g, '$1\n\n$2');
                return marked.parse(normalized);
            }
            var div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }

        var currentAbort = null;

        function extractThinkContent(raw) {
            var openIdx = raw.indexOf("<think>");
            var closeIdx = raw.indexOf("</think>");

            if (openIdx === -1) {
                // Suppress flash: if raw starts with < but no full tag yet
                var lastOpen = raw.lastIndexOf("<");
                var lastClose = raw.lastIndexOf(">");
                if (lastOpen > lastClose && raw.trim().length < 10) {
                    return { thinking: null, answer: "" };
                }
                return { thinking: null, answer: raw };
            }

            if (closeIdx !== -1 && closeIdx > openIdx) {
                return {
                    thinking: raw.substring(openIdx + 7, closeIdx),
                    answer: raw.substring(closeIdx + 8),
                };
            }

            return {
                thinking: raw.substring(openIdx + 7),
                answer: raw.substring(0, openIdx),
            };
        }

        function populatePromptSelect(prompts) {
            if (!promptSelect) return;
            promptSelect.innerHTML = "";

            if (!prompts || prompts.length === 0) {
                var emptyOpt = document.createElement("option");
                emptyOpt.value = "";
                emptyOpt.textContent = "— No prompts —";
                promptSelect.appendChild(emptyOpt);
                return;
            }

            var activeId = null;
            prompts.forEach(function (p) {
                var opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                promptSelect.appendChild(opt);
                if (p.is_active) {
                    activeId = p.id;
                }
            });

            if (activeId) {
                promptSelect.value = activeId;
            } else {
                promptSelect.selectedIndex = 0;
            }
        }

        function loadPrompts() {
            if (window.__INITIAL_PROMPTS && window.__INITIAL_PROMPTS.length > 0) {
                populatePromptSelect(window.__INITIAL_PROMPTS);
                return;
            }
            fetch("/api/v1/admin/prompts")
                .then(function (r) { return r.json(); })
                .then(function (prompts) {
                    populatePromptSelect(prompts);
                })
                .catch(function () {
                    if (promptSelect) {
                        promptSelect.innerHTML = "<option value=\"\">— No prompts —</option>";
                    }
                });
        }

        function getSelectedPrompt() {
            if (promptSelect) return promptSelect.value || "";
            return "";
        }

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

        function createMessageActions(role, bodyEl) {
            var actions = document.createElement("div");
            actions.className = "message-actions";

            var copyBtn = document.createElement("button");
            copyBtn.className = "btn btn-ghost btn-sm";
            copyBtn.textContent = "\u{1F4CB} Copier";
            copyBtn.addEventListener("click", function () {
                var text = getAnswerText(bodyEl);
                navigator.clipboard.writeText(text).then(function () {
                    showToast("Copi\u00E9 !");
                }).catch(function () {
                    showToast("Erreur de copie");
                });
            });
            actions.appendChild(copyBtn);
            return actions;
        }

        function getAnswerText(bodyEl) {
            var thinkBlock = bodyEl.querySelector(".thinking-block");
            var clone = bodyEl.cloneNode(true);
            var thinkClone = clone.querySelector(".thinking-block");
            if (thinkClone) thinkClone.remove();
            return clone.textContent || clone.innerText || "";
        }

        function updateMessageBody(bodyEl, thinking, answer, formatted) {
            bodyEl.innerHTML = "";

            if (thinking !== null) {
                var details = document.createElement("details");
                details.className = "thinking-block";
                var summary = document.createElement("summary");
                summary.textContent = "Thinking";
                details.appendChild(summary);
                var content = document.createElement("div");
                content.className = "thinking-content";
                if (formatted) {
                    content.innerHTML = renderMarkdown(thinking);
                } else {
                    content.textContent = thinking;
                }
                details.appendChild(content);
                bodyEl.appendChild(details);
            }

            if (answer) {
                var answerDiv = document.createElement("div");
                answerDiv.className = "answer-content";
                if (formatted) {
                    answerDiv.innerHTML = renderMarkdown(answer);
                } else {
                    answerDiv.textContent = answer;
                }
                bodyEl.appendChild(answerDiv);
            }
        }

        function makeMessageEl(role, bodyContent, append) {
            var div = document.createElement("div");
            div.className = "message " + role;

            var header = createMessageHeader(role);
            div.appendChild(header);

            var body = document.createElement("div");
            body.className = "message-body";

            if (role === "user") {
                body.textContent = bodyContent;
            } else {
                var parsed = extractThinkContent(bodyContent);
                updateMessageBody(body, parsed.thinking, parsed.answer, true);
            }
            div.appendChild(body);

            var actions = createMessageActions(role, body);
            div.appendChild(actions);

            if (append !== false) {
                messagesEl.appendChild(div);
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
            return { el: div, bodyEl: body };
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
                            makeMessageEl(msg.role, msg.content, true);
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

        loadPrompts();
        loadHistory();

        /* ---- Chat submit ---- */
        chatForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            var text = input.value.trim();
            if (!text) return;

            if (currentAbort) {
                currentAbort.abort();
                currentAbort = null;
            }

            makeMessageEl("user", text, true);
            input.value = "";
            input.style.height = "auto";
            setLoading(true);

            if (welcome) { welcome.remove(); welcome = null; }

            var promptId = getSelectedPrompt();

            currentAbort = new AbortController();
            var resp;
            try {
                resp = await fetch("/api/v1/chat/message/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, mode: "search", model: "", prompt_id: promptId }),
                    signal: currentAbort.signal,
                });
            } catch (err) {
                if (err.name !== "AbortError") {
                    makeMessageEl("error", "Erreur r\u00E9seau: " + err.message, true);
                }
                setLoading(false);
                currentAbort = null;
                return;
            }

            if (!resp.ok) {
                makeMessageEl("error", "Request failed with status " + resp.status, true);
                setLoading(false);
                currentAbort = null;
                return;
            }

            var reader = resp.body.getReader();
            var decoder = new TextDecoder();
            var accumulated = "";
            var bubbleInfo = null;
            var gotToken = false;
            var sseBuffer = "";

            try {
                while (true) {
                    var result;
                    try {
                        result = await reader.read();
                    } catch (err) {
                        if (err.name !== "AbortError") {
                            makeMessageEl("error", "Erreur de lecture du flux: " + err.message, true);
                        }
                        break;
                    }
                    if (result.done) break;

                    sseBuffer += decoder.decode(result.value, { stream: true });

                    var eventEnd;
                    while ((eventEnd = sseBuffer.indexOf("\n\n")) !== -1) {
                        var event = sseBuffer.substring(0, eventEnd);
                        sseBuffer = sseBuffer.substring(eventEnd + 2);

                        if (!event.startsWith("data: ")) continue;

                        var data = event.slice(6);

                        if (data === "[DONE]") {
                            if (!gotToken && !bubbleInfo) {
                                makeMessageEl("assistant", "(aucune r\u00E9ponse du LLM)", true);
                            }
                            setLoading(false);

                            if (bubbleInfo) {
                                var finalParsed = extractThinkContent(accumulated);
                                updateMessageBody(bubbleInfo.bodyEl, finalParsed.thinking, finalParsed.answer, true);
                                var ts = document.createElement("div");
                                ts.className = "message-timestamp";
                                ts.textContent = "\u00E0 l'instant";
                                bubbleInfo.el.appendChild(ts);
                            }

                            currentAbort = null;
                            return;
                        }

                        if (data.indexOf("__CITATIONS__:") === 0) {
                            continue;
                        }

                        accumulated += data;
                        gotToken = true;

                        if (!bubbleInfo) {
                            hideTyping();
                            bubbleInfo = makeMessageEl("assistant", "", true);
                        }

                        var parsed = extractThinkContent(accumulated);
                        updateMessageBody(bubbleInfo.bodyEl, parsed.thinking, parsed.answer, true);
                        messagesEl.scrollTop = messagesEl.scrollHeight;
                    }
                }

                if (!gotToken && !bubbleInfo) {
                    makeMessageEl("assistant", "(aucune r\u00E9ponse du LLM)", true);
                }
            } catch (err) {
                if (err.name !== "AbortError") {
                    makeMessageEl("error", "Error: " + err.message, true);
                }
            }
            setLoading(false);
            currentAbort = null;
        });

        input.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = this.scrollHeight + "px";
        });
    }

    document.addEventListener("DOMContentLoaded", init);
})();
