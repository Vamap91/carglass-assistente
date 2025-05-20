from flask import Flask, render_template, request, jsonify
import random
import re
import os
import openai

app = Flask(__name__)
app.secret_key = 'carglass-secreto'

# Configuração da OpenAI API
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
MENSAGENS = []

# Estado de identificação do cliente
CLIENTE_IDENTIFICADO = False
CLIENTE_INFO = None

# Detecta o tipo de identificador (CPF, placa, etc)
def detect_identifier_type(text):
    # Remove caracteres não alfanuméricos
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text)
    
    # Verifica CPF (11 dígitos numéricos)
    if re.match(r'^\d{11}$', clean_text):
        return "cpf", clean_text
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        return "placa", clean_text.upper()
    
    # Não identificado
    return None, clean_text

# Simula busca de dados (em produção, seria uma API real)
def get_client_data(tipo, valor):
    # Aceita qualquer CPF válido com 11 dígitos
    if (tipo == "cpf" and len(valor) == 11) or tipo == "telefone":
        return {
            "sucesso": True,
            "tipo": tipo,
            "valor": valor,
            "dados": {
                "nome": "Carlos Teste",
                "cpf": "12345678900",
                "telefone": "11987654321",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234",
                    "ano": "2022"
                }
            }
        }
    return {"sucesso": False, "mensagem": "Cliente não encontrado"}

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    # Primeiramente, tentamos identificar perguntas específicas com palavras-chave
    pergunta_lower = pergunta.lower()
    
    # Perguntas sobre lojas/locais de atendimento
    if any(keyword in pergunta_lower for keyword in ['loja', 'local', 'mudar local', 'onde', 'endereço', 'filial', 'disponíve']):
        return """
        A CarGlass possui diversas lojas na região. As lojas mais próximas são:
        
        - CarGlass Morumbi: Av. Professor Francisco Morato, 2307 - Butantã, São Paulo
        - CarGlass Vila Mariana: Rua Domingos de Morais, 1267 - Vila Mariana, São Paulo
        - CarGlass Santo André: Av. Industrial, 600 - Santo André
        
        Se deseja mudar o local do seu atendimento, por favor entre em contato com nossa central: 0800-727-2327.
        """
    
    # Perguntas sobre garantia
    if any(keyword in pergunta_lower for keyword in ['garantia', 'seguro', 'cobertura']):
        return f"""
        A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão.
        
        Esta garantia cobre:
        - Defeitos de instalação
        - Problemas de vedação
        - Infiltrações relacionadas ao serviço
        
        Em caso de dúvidas específicas sobre a garantia, entre em contato com nossa central: 0800-727-2327.
        """
    
    # Se não for uma pergunta específica que sabemos responder, usamos a OpenAI
    try:
        # Constrói o prompt para a OpenAI API com contexto do cliente
        system_message = f"""
        Você é Clara, a assistente virtual da CarGlass. Você está conversando com {cliente_info['dados']['nome']}, 
        que tem um atendimento com as seguintes informações:
        - Status: {cliente_info['dados']['status']}
        - Ordem: {cliente_info['dados']['ordem']}
        - Serviço: {cliente_info['dados']['tipo_servico']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} - {cliente_info['dados']['veiculo']['ano']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        Informações importantes a saber:
        - A CarGlass possui lojas em São Paulo, Santo André, São Bernardo e Guarulhos
        - A garantia é de 12 meses para todos os serviços
        - O prazo médio para troca de parabrisa é de 2 dias úteis
        - Para mudar o local de atendimento, o cliente deve ligar para 0800-727-2327
        
        Forneça uma resposta personalizada considerando o contexto do atendimento. 
        Seja simpática, breve e objetiva. Não invente informações que não constam nos dados acima.
        Se o cliente pedir informações como prazo de conclusão ou detalhes específicos do serviço que 
        não estão nos dados acima, explique que você precisará verificar com a equipe técnica 
        e sugira entrar em contato pelo telefone 0800-727-2327.
        
        A pergunta do cliente é: {pergunta}
        """
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": pergunta}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Olá! Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses)

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS
    
    # Inicializa as mensagens, se estiverem vazias
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Se ainda não identificou o cliente
    if not CLIENTE_IDENTIFICADO:
        tipo, valor = detect_identifier_type(user_input)
        
        if tipo:
            client_data = get_client_data(tipo, valor)
            
            if client_data.get('sucesso'):
                # Cliente encontrado
                CLIENTE_INFO = client_data
                CLIENTE_IDENTIFICADO = True
                
                # Formata status
                status = client_data['dados']['status']
                status_tag = f'<span class="status-tag">{status}</span>'
                
                # Barra de progresso - Criada uma única vez
                progress_bar = ''
                if status == "Em andamento":
                    progress_bar = '''
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-steps">
                                <div class="step complete">
                                    <div class="step-node"></div>
                                    <div class="step-label">Recebido</div>
                                </div>
                                <div class="step active">
                                    <div class="step-node"></div>
                                    <div class="step-label">Em andamento</div>
                                </div>
                                <div class="step">
                                    <div class="step-node"></div>
                                    <div class="step-label">Instalação</div>
                                </div>
                                <div class="step">
                                    <div class="step-node"></div>
                                    <div class="step-label">Inspeção</div>
                                </div>
                                <div class="step">
                                    <div class="step-node"></div>
                                    <div class="step-label">Concluído</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    '''
                
                # Mensagem de resposta com uma única barra de progresso
                response = f"""
                Olá {client_data['dados']['nome']}! Encontrei suas informações.
                
                Seu atendimento está com status: {status_tag}
                
                {progress_bar}
                
                Ordem de serviço: {client_data['dados']['ordem']}
                Serviço: {client_data['dados']['tipo_servico']}
                Veículo: {client_data['dados']['veiculo']['modelo']} ({client_data['dados']['veiculo']['ano']})
                Placa: {client_data['dados']['veiculo']['placa']}
                
                Como posso ajudar você hoje?
                """
            else:
                # Cliente não encontrado
                response = f"""
                Não consegui encontrar informações com o {tipo} fornecido.
                
                Por favor, tente novamente ou use outro identificador.
                """
        else:
            # Formato inválido
            response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida."
    else:
        # Cliente já identificado, processa pergunta com IA
        response = get_ai_response(user_input, CLIENTE_INFO)
    
    # Adiciona resposta do assistente
    MENSAGENS.append({"role": "assistant", "content": response})
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO
    
    # Limpa as mensagens
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
