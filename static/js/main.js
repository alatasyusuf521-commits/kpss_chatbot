let currentSessionId = null;
let pollInterval = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    // Default start new chat if no session
    if (!currentSessionId) {
        startNewChat();
    }
});

// API Helpers
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);
    
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: error.message };
    }
}

// UI Helpers
function scrollToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(role, content) {
    const chatMessages = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message-container ${role}`;
    
    const icon = role === 'bot' ? 'fa-robot' : 'fa-user';
    
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid ${icon}"></i></div>
        <div class="message-bubble">${content}</div>
    `;
    
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message-container bot typing-box';
    msgDiv.id = 'typing-indicator';
    
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// Chat Functions
async function startNewChat() {
    const res = await apiCall('/new_session', 'POST');
    if (res.session_id) {
        currentSessionId = res.session_id;
        document.getElementById('current-chat-title').textContent = "Yeni Sohbet";
        
        // Clear chat area
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="message-container bot">
                <div class="avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="message-bubble">
                    Merhaba! Ben KPSS kaynaklarına dayalı AI asistanınızım. Size nasıl yardımcı olabilirim?
                </div>
            </div>
        `;
        
        loadHistory(); // Refresh history list
    }
}

async function loadHistory() {
    const res = await apiCall('/history');
    if (res.sessions) {
        const historyList = document.getElementById('history-list');
        historyList.innerHTML = '';
        
        res.sessions.forEach(session => {
            const li = document.createElement('li');
            li.className = `history-item ${session.id === currentSessionId ? 'active' : ''}`;
            li.onclick = () => loadSession(session.id, session.title);
            li.innerHTML = `<i class="fa-regular fa-message"></i> ${session.title}`;
            historyList.appendChild(li);
        });
    }
}

async function loadSession(sessionId, title) {
    currentSessionId = sessionId;
    document.getElementById('current-chat-title').textContent = title;
    
    const res = await apiCall(`/history/${sessionId}`);
    if (res.messages) {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
        
        if (res.messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="message-container bot">
                    <div class="avatar"><i class="fa-solid fa-robot"></i></div>
                    <div class="message-bubble">
                        Merhaba! Ben KPSS kaynaklarına dayalı AI asistanınızım. Size nasıl yardımcı olabilirim?
                    </div>
                </div>
            `;
        } else {
            res.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
        }
        
        loadHistory(); // Update active class
    }
}

async function sendMessage(event) {
    event.preventDefault();
    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();
    
    if (!message || !currentSessionId) return;
    
    // UI Update
    input.value = '';
    sendBtn.disabled = true;
    appendMessage('user', message);
    showTypingIndicator();
    
    // API Call
    const res = await apiCall('/chat', 'POST', {
        session_id: currentSessionId,
        message: message
    });
    
    removeTypingIndicator();
    sendBtn.disabled = false;
    input.focus();
    
    if (res.error) {
        appendMessage('bot', `⚠️ Hata: ${res.error}`);
    } else {
        appendMessage('bot', res.response);
        loadHistory(); // Title might have updated
    }
}

// PDF Processing
async function processPDFs() {
    const modal = document.getElementById('loading-modal');
    modal.classList.remove('hidden');
    
    const res = await apiCall('/process_pdfs', 'POST');
    
    if (res.status === 'already_processing' || res.status === 'started') {
        // Start polling status
        pollInterval = setInterval(checkProcessStatus, 2000);
    } else {
        modal.classList.add('hidden');
        alert("Başlatılamadı: " + (res.error || "Bilinmeyen Hata"));
    }
}

async function checkProcessStatus() {
    const res = await apiCall('/process_status');
    const statusText = document.getElementById('modal-status-text');
    
    if (res) {
        statusText.textContent = res.message;
        
        if (!res.is_processing) {
            clearInterval(pollInterval);
            setTimeout(() => {
                document.getElementById('loading-modal').classList.add('hidden');
                statusText.textContent = "Bu işlem PDF boyutlarına bağlı olarak birkaç dakika sürebilir. Lütfen bekleyin...";
                
                // Show a toast or update header
                const processHeaderStatus = document.getElementById('processing-status');
                processHeaderStatus.classList.remove('hidden');
                processHeaderStatus.innerHTML = '<i class="fa-solid fa-check"></i> <span style="color:var(--accent);">PDF\'ler İşlendi</span>';
                
                setTimeout(() => processHeaderStatus.classList.add('hidden'), 5000);
            }, 1500);
        }
    }
}
