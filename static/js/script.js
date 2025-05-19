document.addEventListener('DOMContentLoaded', function() {
    // Elementos da interface
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const resetButton = document.getElementById('reset-button');
    
    // Variável para evitar respostas duplicadas
    let lastUserMessage = '';
    
    // Variável para controlar animação de digitação
    let typingIndicator = null;
    
    // Formato de data e hora
    function getFormattedTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
            chatMessages.innerHTML = createMessageHTML({
                role: 'assistant',
                content: 'Olá! Sou Clara, assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.'
            });
        });
    }
    
    // Carregar mensagens quando a página carrega
    loadMessages();
    
    // Criar HTML para mensagem
    function createMessageHTML(msg) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.role}`;
        
        // Adiciona avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        if (msg.role === 'assistant') {
            avatarDiv.innerHTML = 'C';
        } else {
            avatarDiv.innerHTML = 'V';
        }
        
        // Adiciona conteúdo da mensagem
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Processa status tags na mensagem
        let content = msg.content;
        
        // Processa status tags
        const statusRegex = /<span class="status-tag">(.*?)<\/span>/g;
        content = content.replace(statusRegex, (match, status) => {
            let statusClass = '';
            
            if (status.toLowerCase().includes('andamento')) {
                statusClass = 'em-andamento';
            } else if (status.toLowerCase().includes('concluído')) {
                statusClass = 'concluido';
            } else if (status.toLowerCase().includes('agendado')) {
                statusClass = 'agendado';
            } else if (status.toLowerCase().includes('aguardando')) {
                statusClass = 'aguardando';
            }
            
            return `<span class="status-tag ${statusClass}">${status}</span>`;
        });
        
        // Detecta se a mensagem inclui escalation
        if (msg.role === 'assistant' && content.includes('protocolo de atendimento')) {
            // Extrai o ID do protocolo
            const protocoloMatch = content.match(/protocolo de atendimento é: ([A-Z0-9-]+)/);
            const protocoloID = protocoloMatch ? protocoloMatch[1] : 'ESC-00000000';
            
            // Cria um container de escalação mais visual
            const escalationHTML = `
                <div class="escalation-container">
                    <div class="escalation-header">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        Transferência para Atendente Humano
                    </div>
                    <div class="escalation-details">
                        <div class="escalation-detail">
                            <div class="escalation-label">Protocolo:</div>
                            <div class="escalation-value">${protocoloID}</div>
                        </div>
                        <div class="escalation-detail">
                            <div class="escalation-label">Status:</div>
                            <div class="escalation-value">Aguardando atendente</div>
                        </div>
                    </div>
                </div>
            `;
            
            // Substitui o texto original pelo formato visual
            content = content.replace(/Entendo.*?breve\./s, escalationHTML);
        }
        
        contentDiv.innerHTML = content;
        
        // Adiciona timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = getFormattedTime();
        
        // Adiciona tudo à mensagem
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        contentDiv.appendChild(timeDiv);
        
        return messageDiv;
    }
    
    // Adiciona indicador de digitação
    function showTypingIndicator() {
        // Remove indicador anterior se existir
        removeTypingIndicator();
        
        // Cria novo indicador
        typingIndicator = document.createElement('div');
        typingIndicator.className = 'message assistant typing';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.textContent = 'C';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        typingIndicator.appendChild(avatarDiv);
        typingIndicator.appendChild(contentDiv);
        
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Remove indicador de digitação
    function removeTypingIndicator() {
        if (typingIndicator && typingIndicator.parentNode) {
            typingIndicator.parentNode.removeChild(typingIndicator);
            typingIndicator = null;
        }
    }
    
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
            
            // Adiciona mensagem do usuário imediatamente para melhor UX
            const userMessageDiv = createMessageHTML({
                role: "user", 
                content: message
            });
            chatMessages.appendChild(userMessageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Mostra indicador de digitação
            showTypingIndicator();
            
            // Formata os dados para envio
            const formData = new FormData();
            formData.append('message', message);
            
            fetch('/send_message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Remove indicador de digitação
                removeTypingIndicator();
                
                // Atualiza o chat apenas com a nova resposta do assistente
                const lastMessage = data.messages[data.messages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                    const assistantMessageDiv = createMessageHTML(lastMessage);
                    chatMessages.appendChild(assistantMessageDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                
                // Limpa e reativa o campo de entrada
                userInput.value = '';
                userInput.disabled = false;
                userInput.focus();
                
                // Restaura o botão
                sendButton.disabled = false;
                sendButton.classList.remove('loading');
            })
            .catch(error => {
                console.error('Erro ao enviar mensagem:', error);
                
                // Remove indicador de digitação
                removeTypingIndicator();
                
                // Restaura a interface em caso de erro
                userInput.disabled = false;
                sendButton.disabled = false;
                sendButton.classList.remove('loading');
                
                // Adiciona mensagem de erro ao chat
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message assistant';
                errorMsg.innerHTML = `
                    <div class="message-avatar">C</div>
                    <div class="message-content">
                        Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.
                        <div class="message-time">${getFormattedTime()}</div>
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
                
                // Cria e adiciona mensagem
                const messageDiv = createMessageHTML(msg);
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
        
        // Mostra indicador de carregamento
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
    
    // Melhorar visualização de status do atendimento
    function enhanceStatusDisplay() {
        // Procura por todas as mensagens contendo informações de status
        const statusMessages = document.querySelectorAll('.message-content');
        
        statusMessages.forEach(message => {
            // Verifica se a mensagem contém informações de status
            if (message.textContent.includes('status:') && message.textContent.includes('Ordem de serviço:')) {
                // Procura pelas informações do status atual
                const statusMatch = message.innerHTML.match(/<span class="status-tag.*?">(.*?)<\/span>/);
                
                if (statusMatch) {
                    const currentStatus = statusMatch[1].toLowerCase();
                    
                    // Define quais etapas já foram concluídas
                    const stageProgress = {
                        'recebido': 1,
                        'em andamento': 2,
                        'em instalação': 3,
                        'em inspeção': 4,
                        'concluído': 5
                    };
                    
                    // Determina a etapa atual
                    let currentStage = 0;
                    for (const [stage, value] of Object.entries(stageProgress)) {
                        if (currentStatus.includes(stage)) {
                            currentStage = value;
                            break;
                        }
                    }
                    
                    // Se for status em andamento, adiciona uma barra de progresso visual
                    if (currentStage > 0 && currentStage < 5) {
                        // Cria o HTML da barra de progresso
                        const progressHTML = `
                            <div class="service-progress">
                                <div class="service-progress-bar" style="width: ${currentStage * 20}%"></div>
                            </div>
                            <div class="service-stages">
                                <div class="service-stage-line"></div>
                                <div class="service-stage ${currentStage >= 1 ? 'completed' : ''} ${currentStage === 1 ? 'active' : ''}">
                                    <div class="service-stage-dot"></div>
                                    <div class="service-stage-label">Recebido</div>
                                </div>
                                <div class="service-stage ${currentStage >= 2 ? 'completed' : ''} ${currentStage === 2 ? 'active' : ''}">
                                    <div class="service-stage-dot"></div>
                                    <div class="service-stage-label">Em andamento</div>
                                </div>
                                <div class="service-stage ${currentStage >= 3 ? 'completed' : ''} ${currentStage === 3 ? 'active' : ''}">
                                    <div class="service-stage-dot"></div>
                                    <div class="service-stage-label">Instalação</div>
                                </div>
                                <div class="service-stage ${currentStage >= 4 ? 'completed' : ''} ${currentStage === 4 ? 'active' : ''}">
                                    <div class="service-stage-dot"></div>
                                    <div class="service-stage-label">Inspeção</div>
                                </div>
                                <div class="service-stage ${currentStage >= 5 ? 'completed' : ''} ${currentStage === 5 ? 'active' : ''}">
                                    <div class="service-stage-dot"></div>
                                    <div class="service-stage-label">Concluído</div>
                                </div>
                            </div>
                        `;
                        
                        // Insere após a tag de status
                        message.innerHTML = message.innerHTML.replace(
                            /<span class="status-tag.*?<\/span>/,
                            match => match + progressHTML
                        );
                    }
                }
            }
        });
    }
    
    // Customizar primeira mensagem
    function customizeFirstMessage() {
        if (chatMessages.children.length > 0 && 
            chatMessages.children[0].classList.contains('assistant')) {
            const firstMessage = chatMessages.children[0];
            
            // Verifica se é a mensagem inicial
            if (firstMessage.querySelector('.message-content').textContent.includes('Digite seu CPF')) {
                // Adiciona classe especial para estilização
                firstMessage.classList.add('welcome-message');
                
                // Modifica o texto para incluir a Clara
                const contentDiv = firstMessage.querySelector('.message-content');
                
                // Substitui o texto padrão por um mais amigável com a Clara
                contentDiv.innerHTML = contentDiv.innerHTML.replace(
                    'Olá! Sou o assistente virtual da CarGlass.',
                    'Olá! Sou Clara, sua assistente virtual da CarGlass 👋'
                );
            }
        }
    }
    
    // Ativar animações e melhorias visuais após carregar mensagens
    function applyVisualEnhancements() {
        // Melhora visualização de status
        enhanceStatusDisplay();
        
        // Customiza primeira mensagem
        customizeFirstMessage();
    }
    
    // Processar envio de mensagem ao pressionar Enter
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Configurar eventos
    sendButton.addEventListener('click', sendMessage);
    resetButton.addEventListener('click', resetConversation);
    
    // Observer para aplicar melhorias visuais quando novas mensagens são adicionadas
    const observer = new MutationObserver(applyVisualEnhancements);
    observer.observe(chatMessages, { childList: true });
    
    // Foca no campo de entrada ao carregar a página
    userInput.focus();
    
    // Aplica melhorias visuais nas mensagens iniciais
    setTimeout(applyVisualEnhancements, 500);
});
