(function () {
    "use strict";

    function escHtml(s) {
        if (s == null) return '';
        var m = { '&': '\x26amp;', '<': '\x26lt;', '>': '\x26gt;', '"': '\x26quot;', "'": '\x26#39;' };
        return String(s).replace(/[&<>"']/g, function(c) { return m[c]; });
    }

    function init() {
        var chatHistory = document.getElementById("chat-history");
        var chatForm = document.getElementById("chat-form");
        var messageInput = document.getElementById("message-input");
        var uploadZone = document.getElementById("upload-zone");
        var fileInput = document.getElementById("sigma-file-input");
        var uploadedFilename = document.getElementById("uploaded-filename");
        var clearBtn = document.getElementById("clear-btn");
        var chatStatus = document.getElementById("chat-status");

        if (!chatHistory || !chatForm || !messageInput || !uploadZone || !fileInput || !clearBtn || !chatStatus) {
            return;
        }

        var chatMessages = [];
        var uploadedFile = null;

        function getTimestamp() {
            return new Date().toLocaleTimeString();
        }

        function getCurrentMode() {
            var checked = document.querySelector('input[name="mode"]:checked');
            return checked ? checked.value : "search";
        }

        function addBubble(role, content) {
            var bubble = document.createElement("div");
            bubble.className = "chat-bubble " + role;
            // For user and error messages, escape content. For assistant, content may contain safe HTML.
            var safeContent;
            if (role === "assistant") {
                safeContent = content;
            } else {
                safeContent = escHtml(content);
            }
            bubble.innerHTML = safeContent + '<span class="timestamp">' + getTimestamp() + '</span>';
            chatHistory.appendChild(bubble);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            chatMessages.push({ role: role, content: content, timestamp: getTimestamp() });
            if (chatMessages.length > 50) {
                chatMessages = chatMessages.slice(-50);
            }
            return bubble;
        }

        function setStatus(msg) {
            chatStatus.textContent = msg;
        }

        uploadZone.addEventListener("click", function () {
            fileInput.click();
        });

        uploadZone.addEventListener("dragover", function (e) {
            e.preventDefault();
            uploadZone.classList.add("dragover");
        });

        uploadZone.addEventListener("dragleave", function () {
            uploadZone.classList.remove("dragover");
        });

        uploadZone.addEventListener("drop", function (e) {
            e.preventDefault();
            uploadZone.classList.remove("dragover");
            var files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                handleFile(fileInput.files[0]);
            }
        });

        async function handleFile(file) {
            var validExts = [".yaml", ".yml"];
            var ext = file.name.substring(file.name.lastIndexOf("."));
            if (!validExts.includes(ext)) {
                addBubble("assistant", "Please upload a .yaml or .yml Sigma rule file.");
                return;
            }

            uploadedFile = file;
            uploadedFilename.textContent = file.name;
            setStatus("Uploaded: " + file.name);

            var formData = new FormData();
            formData.append("file", file);

            try {
                var resp = await fetch("/api/v1/chat/upload", {
                    method: "POST",
                    body: formData,
                });
                var data = await resp.json();
                if (resp.ok) {
                    addBubble(
                        "assistant",
                        'Rule "<strong>' + escHtml(data.rule_name) + '</strong>" validated successfully. Switch to Explain mode for analysis.'
                    );
                } else {
                    addBubble("error", "Upload failed: " + escHtml(data.detail || JSON.stringify(data)));
                }
            } catch (err) {
                addBubble("error", "Upload error: " + escHtml(err.message));
            }
        }

        chatForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            var message = messageInput.value.trim();
            if (!message) return;

            addBubble("user", message);
            messageInput.value = "";
            setStatus("Thinking...");

            await handleStreamingMessage(message);
        });

        async function handleStreamingMessage(message) {
            try {
                var resp = await fetch("/api/v1/chat/message/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: message, mode: getCurrentMode() }),
                });

                if (!resp.ok) {
                    addBubble("error", "Stream request failed.");
                    setStatus("");
                    return;
                }

                var reader = resp.body.getReader();
                var decoder = new TextDecoder();
                var accumulated = "";
                var bubble = null;

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
                                setStatus("");
                                return;
                            }
                            accumulated += data;

                            if (!bubble) {
                                bubble = addBubble("assistant", accumulated);
                            } else {
                                bubble.innerHTML = formatResponse({ response: accumulated }) +
                                    '<span class="timestamp">' + getTimestamp() + '</span>';
                            }
                            chatHistory.scrollTop = chatHistory.scrollHeight;
                        }
                    }
                }
                setStatus("");
            } catch (err) {
                addBubble("error", "Stream error: " + escHtml(err.message));
                setStatus("");
            }
        }

        function formatResponse(data) {
            if (!data.response) return "";
            var html = escHtml(data.response).replace(/\n/g, "<br>");
            if (data.citations && data.citations.length > 0) {
                html += "<br><em>Sources: " + data.citations.map(function(c) { return '[' + escHtml(c) + ']'; }).join(" ") + "</em>";
            }
            return html;
        }

        clearBtn.addEventListener("click", function () {
            chatHistory.innerHTML = "";
            chatMessages = [];
            uploadedFile = null;
            uploadedFilename.textContent = "No file selected";
            setStatus("Chat cleared.");
        });
    }

    document.addEventListener("DOMContentLoaded", init);
})();