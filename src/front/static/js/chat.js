(function () {
    "use strict";

    function init() {
        var messagesEl = document.getElementById("chat-messages");
        var chatForm = document.getElementById("chat-form");
        var input = document.getElementById("message-input");
        var sendBtn = document.getElementById("send-btn");
        var welcome = document.getElementById("chat-welcome");

        if (!messagesEl || !chatForm || !input || !sendBtn) return;

        function addMessage(role, content) {
            var div = document.createElement("div");
            div.className = "message " + role;
            if (role === "user") {
                div.textContent = content;
            } else {
                div.innerHTML = marked.parse(content);
            }
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            return div;
        }

        function setLoading(loading) {
            sendBtn.disabled = loading;
            sendBtn.textContent = loading ? "..." : "Send";
        }

        chatForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            var text = input.value.trim();
            if (!text) return;

            addMessage("user", text);
            input.value = "";
            input.style.height = "auto";
            setLoading(true);

            if (welcome) { welcome.remove(); welcome = null; }

            try {
                var resp = await fetch("/api/v1/chat/message/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, mode: "search" }),
                }).catch(function(err) {
                    addMessage("error", "Erreur réseau: " + err.message);
                    setLoading(false);
                    return null;
                });
                if (!resp) return;

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

                while (true) {
                    var result = await reader.read();
                    if (result.done) break;

                    var chunk = decoder.decode(result.value, { stream: true });
                    var lines = chunk.split("\n\n");

                    for (var j = 0; j < lines.length; j++) {
                        var line = lines[j];
                        if (line.startsWith("data: ")) {
                            var data = line.slice(6);
                            if (data === "[DONE]") {
                                setLoading(false);
                                if (!gotToken && !bubble) {
                                    addMessage("assistant", "(aucune réponse du LLM)");
                                }
                                return;
                            }
                            accumulated += data;
                            gotToken = true;
                            if (!bubble) {
                                bubble = addMessage("assistant", "");
                            }
                            bubble.innerHTML = marked.parse(accumulated);
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
