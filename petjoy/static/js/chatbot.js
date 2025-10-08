
document.addEventListener('DOMContentLoaded', () => {
    // ดึง Element ต่างๆ จากหน้า HTML มาเก็บในตัวแปร
    const chatContainer = document.getElementById('chatbot-container');
    const toggleButton = document.querySelector('.chatbot-toggle-button'); // เปลี่ยนเป็น class ของปุ่ม toggle
    const sendButton = document.getElementById('chatbot-send');
    const inputField = document.getElementById('chatbot-input');
    const chatBody = document.getElementById('chat-response');
    // ดึงบัตรผ่าน (CSRF Token) ที่เราใส่ไว้ใน HTML -- guard in case it's not present
    const csrfElem = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfElem ? csrfElem.value : null;

    // --- ฟังก์ชันควบคุมการทำงาน ---

    // 1. ฟังก์ชันเปิด-ปิดหน้าต่างแชท
    if (toggleButton && chatContainer) {
        toggleButton.addEventListener('click', () => {
            chatContainer.classList.toggle('hidden');
        });
    } else {
        // If elements are missing, skip wiring but do not throw.
        console.warn('Chatbot elements not found; toggle unavailable.');
        return; // nothing more to do
    }

    // 2. ฟังก์ชันส่งข้อความ (เมื่อกดปุ่ม "ส่ง")
    if (sendButton) {
        sendButton.addEventListener('click', () => {
            sendMessage();
        });
    }

    // 3. ฟังก์ชันส่งข้อความ (เมื่อกดปุ่ม "Enter" บนคีย์บอร์ด)
    if (inputField) {
        inputField.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault(); // ไม่ให้ฟอร์มขึ้นบรรทัดใหม่
                sendMessage();
            }
        });
    }

    // --- ฟังก์ชันหลักในการส่งและรับข้อความ ---

    async function sendMessage() {
        const userMessage = inputField.value.trim();
        if (userMessage === '') return; // ไม่ส่งถ้าข้อความว่าง

        // แสดงข้อความของผู้ใช้บนหน้าจอ
        addMessage(userMessage, 'user');
        inputField.value = ''; // เคลียร์ช่องพิมพ์

        try {
            // ส่งข้อความไปหา Django ที่ URL '/ask-ai/'
            const response = await fetch('/ask-ai/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken // แนบบัตรผ่านไปด้วย
                },
                body: JSON.stringify({ message: userMessage })
            });

            const data = await response.json();

            // แสดงคำตอบจาก AI บนหน้าจอ
            addMessage(data.reply, 'bot');

        } catch (error) {
            console.error('Error:', error);
            addMessage('ขออภัยค่ะ, ระบบขัดข้อง โปรดลองอีกครั้ง', 'bot');
        }
    }

    // --- ฟังก์ชันช่วยแสดงผล ---

    // ฟังก์ชันสร้างและเพิ่มกล่องข้อความลงในแชท
    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        
        if (sender === 'user') {
            // สไตล์สำหรับข้อความผู้ใช้
            messageDiv.className = 'user-msg';
            messageDiv.textContent = message;
        } else {
            // สไตล์สำหรับข้อความบอท
            messageDiv.className = 'bot-msg'; // ใช้คลาส bot-msg สำหรับข้อความทั่วไปของบอท
            messageDiv.textContent = message;
        }

        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight; // เลื่อนไปที่ข้อความล่าสุดเสมอ
    }
});