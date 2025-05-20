document.addEventListener('DOMContentLoaded', function() {
    // Elementos da interface
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const resetButton = document.getElementById('reset-button');
    
    // Função para obter a hora atual formatada (HH:MM)
    function getCurrentTime() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    
    // Carregar mensagens iniciais
    function loadMessages() {
        fetch('/get_messages')
        .then(response => response.json())
        .then(data => {
            updateChatMessages(data.messages);
        })
        .catch(error => {
            console.error('Erro ao carregar mensagens:', error);
            // Exibir mensagem de fallback em caso de erro
            chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-avatar">C</div>
                    <div>
                        <div class="message-content">
                            Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.
                        </div>
                        <div class="message-time">${getCurrentTime()}</div>
                    </div>
                </div>
            `;
        });
    }
    
    // Carregar mensagens quando a página carrega
    loadMessages();
    
    // Enviar mensagem
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (message) {
            // Desabilita a entrada durante o envio
            userInput.disabled = true;
            sendButton.disabled = true;
            
            // Adiciona classe de "carregando" ao botão
            sendButton.classList.add('loading');
            sendButton.textContent = 'Enviando...';
            
            // Formata os dados para envio
            const formData = new FormData();
            formData.append('message', message);
            
            fetch('/send_message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Atualiza o chat com as novas mensagens
                updateChatMessages(data.messages);
                
                // Limpa e reativa o campo de entrada
                userInput.value = '';
                userInput.disabled = false;
                userInput.focus();
                
                // Restaura o botão
                sendButton.disabled = false;
                sendButton.classList.remove('loading');
                sendButton.innerHTML = 'Enviar <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
            })
            .catch(error => {
                console.error('Erro ao enviar mensagem:', error);
                
                // Restaura a interface em caso de erro
                userInput.disabled = false;
                sendButton.disabled = false;
                sendButton.classList.remove('loading');
                sendButton.innerHTML = 'Enviar <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
                
                // Adiciona mensagem de erro ao chat
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message assistant';
                errorMsg.innerHTML = `
                    <div class="message-avatar">C</div>
                    <div>
                        <div class="message-content">
                            Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.
                        </div>
                        <div class="message-time">${getCurrentTime()}</div>
                    </div>
                `;
                chatMessages.appendChild(errorMsg);
                
                // Rola para a última mensagem
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        }
    }
    
    // Atualizar mensagens no chat
    function updateChatMessages(messages) {
        chatMessages.innerHTML = '';
        
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.role}`;
            
            if (msg.role === 'assistant') {
                // Mensagem do assistente com avatar C
                messageDiv.innerHTML = `
                    <div class="message-avatar">C</div>
                    <div>
                        <div class="message-content">
                            ${msg.content}
                        </div>
                        <div class="message-time">${msg.time || getCurrentTime()}</div>
                    </div>
                `;
            } else {
                // Mensagem do usuário com badge amarelo V
                messageDiv.innerHTML = `
                    <div>
                        <div class="message-content">
                            ${msg.content}
                        </div>
                        <div class="message-time">${msg.time || getCurrentTime()}</div>
                    </div>
                    <div class="user-badge">V</div>
                `;
            }
            
            chatMessages.appendChild(messageDiv);
        });
        
        // Rola para a última mensagem
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Resetar conversa
    function resetConversation() {
        // Desabilita o botão durante o reset
        resetButton.disabled = true;
        resetButton.textContent = 'Reiniciando...';
        
        fetch('/reset', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            updateChatMessages(data.messages);
            
            // Limpa e foca no campo de entrada
            userInput.value = '';
            userInput.focus();
            
            // Restaura o botão
            resetButton.disabled = false;
            resetButton.textContent = 'Nova Consulta';
        })
        .catch(error => {
            console.error('Erro ao reiniciar conversa:', error);
            resetButton.disabled = false;
            resetButton.textContent = 'Nova Consulta';
        });
    }
    
    // Inicializa os eventos
    sendButton.innerHTML = 'Enviar <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    resetButton.addEventListener('click', resetConversation);
    
    // Foca no campo de entrada ao carregar a página
    userInput.focus();
});
