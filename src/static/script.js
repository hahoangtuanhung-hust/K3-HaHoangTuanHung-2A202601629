const chatWindow = document.getElementById('chatWindow');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const logsBody = document.getElementById('logsBody');

let sessionId = null;

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    
    if (sender !== 'user' && typeof marked !== 'undefined') {
        msgDiv.innerHTML = marked.parse(text);
    } else {
        msgDiv.textContent = text;
    }
    
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

let typingDiv = null;

function showTyping() {
    typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    chatWindow.appendChild(typingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTyping() {
    if (typingDiv) {
        typingDiv.remove();
        typingDiv = null;
    }
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    showTyping();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_id: sessionId })
        });
        
        const data = await response.json();
        
        removeTyping();
        
        if (data.session_id) sessionId = data.session_id;

        if (data.blocked) {
            appendMessage(data.response, 'error-msg');
        } else {
            appendMessage(data.response, 'agent');
        }
    } catch (err) {
        removeTyping();
        appendMessage('Connection error. Is the server running?', 'error-msg');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
        fetchLogs(); // Force immediate log update
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function fetchLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        // Update Metrics
        if (data.metrics) {
            document.getElementById('totalReqs').textContent = data.metrics.total_requests || 0;
            document.getElementById('blockedReqs').textContent = data.metrics.blocked_requests || 0;
            document.getElementById('rateLimitHits').textContent = data.metrics.rate_limit_hits || 0;
            
            const total = data.metrics.total_requests || 0;
            const blocked = data.metrics.blocked_requests || 0;
            const rate = total > 0 ? ((blocked / total) * 100).toFixed(1) : 0;
            document.getElementById('blockRate').textContent = `${rate}%`;
        }

        // Update Logs Table
        if (data.logs && Array.isArray(data.logs)) {
            logsBody.innerHTML = '';
            // Display latest first
            const sortedLogs = [...data.logs].reverse();
            
            sortedLogs.forEach(log => {
                const tr = document.createElement('tr');
                
                // Format time
                const timeStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '-';
                
                // Format content (Input and Output)
                const inSnippet = `[USER] ${log.input ? log.input.substring(0, 30) : ''}...`;
                const outSnippet = `[AGENT] ${log.output ? log.output.substring(0, 30) : ''}...`;
                const fullText = `User: ${log.input}\nAgent: ${log.output}`;

                // Decision badge
                let decisionBadge = '';
                if (log.blocked) {
                    decisionBadge = '<span class="badge block">BLOCKED</span>';
                } else {
                    decisionBadge = '<span class="badge pass">PASSED</span>';
                }

                tr.innerHTML = `
                    <td>${timeStr}</td>
                    <td style="color: #94a3b8; font-family: monospace">${log.request_id || '-'}</td>
                    <td title="${fullText.replace(/"/g, '&quot;')}">${inSnippet}<br>${outSnippet}</td>
                    <td>${decisionBadge}</td>
                    <td><span style="color: #fbbf24">${log.layer || '-'}</span></td>
                `;
                logsBody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Error fetching logs:", err);
    }
}

// Poll every 2 seconds
setInterval(fetchLogs, 2000);
fetchLogs(); // Initial fetch
