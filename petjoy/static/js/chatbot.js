document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatbot-container');
    const toggleButton = document.querySelector('.chatbot-toggle-button');
    const sendButton = document.getElementById('chatbot-send');
    const inputField = document.getElementById('chatbot-input');
    const chatBody = document.getElementById('chat-response');
    
    const csrfElem = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfElem ? csrfElem.value : '';

    // ปุ่มเปิด-ปิด
    if (toggleButton && chatContainer) {
        toggleButton.addEventListener('click', () => {
            chatContainer.classList.toggle('hidden');
            if (!chatContainer.classList.contains('hidden')) {
                scrollToBottom();
                setTimeout(() => inputField.focus(), 100);
            }
        });
    }

    // ปุ่มส่ง และ Enter
    if (sendButton && inputField) {
        sendButton.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    async function sendMessage() {
        const userMessage = inputField.value.trim();
        if (!userMessage) return;

        inputField.value = '';
        addMessage(userMessage, 'user');

        const loadingId = showLoading();
        scrollToBottom();

        try {
            const response = await fetch('/ask-ai/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ message: userMessage })
            });

            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();

            removeLoading(loadingId);
            addMessage(data.reply, 'bot');

        } catch (error) {
            removeLoading(loadingId);
            console.error('Chat Error:', error);
            addMessage('ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งนะคะ 😢', 'bot');
        }
    }

    function addMessage(message, sender) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `msg-wrapper ${sender}`;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = sender === 'bot' ? '🐶' : '👤';

        const messageDiv = document.createElement('div');
        messageDiv.className = sender === 'bot' ? 'bot-msg' : 'user-msg';
        
        // ใช้ฟังก์ชัน formatText ใหม่ที่แก้เรื่อง ##
        messageDiv.innerHTML = formatText(message);

        if (sender === 'bot') {
            messageWrapper.appendChild(avatar);
            messageWrapper.appendChild(messageDiv);
        } else {
            messageWrapper.appendChild(messageDiv);
            messageWrapper.appendChild(avatar); // คนส่ง Avatar อยู่ขวา
        }

        chatBody.appendChild(messageWrapper);
        scrollToBottom();
    }

    // --- แก้ไขจุดสำคัญตรงนี้ (จัดการ ## และตัวหนา) ---
    function formatText(text) {
        if (!text) return '';
        
        let formatted = text
            // 1. ลบ ## ออกแล้วทำเป็นตัวหนาแทน
            .replace(/##\s*(.*?)(?:\n|$)/g, '<strong>$1</strong><br>') 
            // 2. แปลง Markdown ตัวหนา **คำ** เป็น <b>คำ</b>
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // 3. แปลง Markdown รายการ - เป็น bullet point
            .replace(/- (.*?)(?=\n|$)/g, '<li>$1</li>')
            // 4. แปลงบรรทัดใหม่
            .replace(/\n/g, '<br>');

        // ห่อ list ด้วย <ul>
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/((<li>.*<\/li>\s*)+)/g, '<ul class="chat-list">$1</ul>');
        }
        return formatted;
    }

    function showLoading() {
        const id = 'loading-' + Date.now();
        const wrapper = document.createElement('div');
        wrapper.className = 'msg-wrapper bot';
        wrapper.id = id;
        wrapper.innerHTML = `
            <div class="chat-avatar">🐶</div>
            <div class="bot-msg typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        chatBody.appendChild(wrapper);
        return id;
    }

    function removeLoading(id) {
        const element = document.getElementById(id);
        if (element) element.remove();
    }

    function scrollToBottom() {
        chatBody.scrollTop = chatBody.scrollHeight;
    }
});