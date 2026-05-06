(function () {
    "use strict";

    const chatHistory = document.getElementById("chat-history");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("sigma-file-input");
    const uploadedFilename = document.getElementById("uploaded-filename");
    const clearBtn = document.getElementById("clear-btn");
    const chatStatus = document.getElementById("chat-status");

    let chatMessages = [];
    let uploadedFile = null;

    function getTimestamp() {
        return new Date().toLocaleTimeString();
    }

    function getCurrentMode() {
        const checked = document.querySelector('input[name="mode"]:checked');
        return checked ? checked.value : "search";
    }

    function addBubble(role, content) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        bubble.innerHTML = `${content}<span class="timestamp">${getTimestamp()}</span>`;
        chatHistory.appendChild(bubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        chatMessages.push({ role, content, timestamp: getTimestamp() });
        if (chatMessages.length > 50) {
            chatMessages = chatMessages.slice(-50);
        }
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
        const files = e.dataTransfer.files;
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
        const validExts = [".yaml", ".yml"];
        const ext = file.name.substring(file.name.lastIndexOf("."));
        if (!validExts.includes(ext)) {
            addBubble("assistant", "Please upload a .yaml or .yml Sigma rule file.");
            return;
        }

        uploadedFile = file;
        uploadedFilename.textContent = file.name;
        setStatus(`Uploaded: ${file.name}`);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const resp = await fetch("/api/v1/chat/upload", {
                method: "POST",
                body: formData,
            });
            const data = await resp.json();
            if (resp.ok) {
                addBubble(
                    "assistant",
                    `Rule "<strong>${data.rule_name}</strong>" validated successfully. Switch to Explain mode for analysis.`
                );
            } else {
                addBubble("error", data.detail || "Upload failed: " + JSON.stringify(data));
            }
        } catch (err) {
            addBubble("error", "Upload error: " + err.message);
        }
    }

    chatForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        addBubble("user", message);
        messageInput.value = "";
        setStatus("Thinking...");

        const useStreaming = true;

        if (useStreaming) {
            await handleStreamingMessage(message);
        } else {
            await handleRegularMessage(message);
        }
    });

    async function handleRegularMessage(message) {
        try {
            const resp = await fetch("/api/v1/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message, mode: getCurrentMode() }),
            });
            const data = await resp.json();

            if (resp.ok) {
                addBubble("assistant", formatResponse(data));
                setStatus("");
            } else {
                addBubble("error", data.detail || "Request failed.");
                setStatus("");
            }
        } catch (err) {
            addBubble("error", "Network error: " + err.message);
            setStatus("");
        }
    }

    async function handleStreamingMessage(message) {
        try {
            const resp = await fetch("/api/v1/chat/message/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message, mode: getCurrentMode() }),
            });

            if (!resp.ok) {
                addBubble("error", "Stream request failed.");
                setStatus("");
                return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let bubble = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.slice(6);
                        if (data === "[DONE]") {
                            setStatus("");
                            return;
                        }
                        accumulated += data;

                        if (!bubble) {
                            bubble = addBubble("assistant", accumulated);
                        } else {
                            bubble.innerHTML = formatResponse({ response: accumulated }) +
                                `<span class="timestamp">${getTimestamp()}</span>`;
                        }
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }
                }
            }
            setStatus("");
        } catch (err) {
            addBubble("error", "Stream error: " + err.message);
            setStatus("");
        }
    }

    function formatResponse(data) {
        if (!data.response) return "";
        let html = data.response.replace(/\n/g, "<br>");
        if (data.citations && data.citations.length > 0) {
            html += "<br><em>Sources: " + data.citations.map(c => `[${c}]`).join(" ") + "</em>";
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
})();
