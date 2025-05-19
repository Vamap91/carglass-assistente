document.addEventListener('DOMContentLoaded', function() {
    // Elementos da interface
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const resetButton = document.getElementById('reset-button');
    
    // Variável para evitar respostas duplicadas
    let lastUserMessage = '';
    
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
                    <div class="message-content">
                        Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.
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
        
        // Previne envio de mensagem vazia ou duplicada
        if (message && message !== lastUserMessage) {
            lastUserMessage = message;
            
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
                sendButton.textContent = 'Enviar';
            })
            .catch(error => {
                console.error('Erro ao enviar mensagem:', error);
                
                // Restaura a interface em caso de erro
                userInput.disabled = false;
                sendButton.disabled = false;
                sendButton.classList.remove('loading');
                sendButton.textContent = 'Enviar';
                
                // Adiciona mensagem de erro ao chat
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message assistant';
                errorMsg.innerHTML = `
                    <div class="message-content">
                        Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.
                    </div>
                `;
                chatMessages.appendChild(errorMsg);
                
                // Rola para a última mensagem
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        } else if (message) {
            // Apenas limpa o campo se for mensagem duplicada
            userInput.value = '';
        }
    }
    
    // Atualizar mensagens no chat
    function updateChatMessages(messages) {
        chatMessages.innerHTML = '';
        
        // Histórico de mensagens para evitar duplicatas
        const messageHistory = new Set();
        
        messages.forEach(msg => {
            // Verifica se a mensagem é duplicata (mesmo conteúdo e role)
            const msgKey = `${msg.role}-${msg.content.trim()}`;
            if (!messageHistory.has(msgKey)) {
                messageHistory.add(msgKey);
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.role}`;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.innerHTML = msg.content;
                
                messageDiv.appendChild(contentDiv);
                chatMessages.appendChild(messageDiv);
            }
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
            lastUserMessage = '';
            
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
    
    // Eventos
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
