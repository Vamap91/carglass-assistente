from flask import Flask, render_template, request, jsonify
import random
import re

app = Flask(__name__)
app.secret_key = 'carglass-secreto'

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
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text):
        return "placa", clean_text.upper()
    
    # Não identificado
    return None, clean_text

# Simula busca de dados (em produção, seria uma API real)
def get_client_data(tipo, valor):
    # Aceita qualquer CPF válido com 11 dígitos
    if (tipo == "cpf" and len(valor) == 11) or tipo == "telefone":
        return {
            "sucesso": True,
            "dados": {
                "nome": "Carlos Teste",
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

# Processa as perguntas após identificação
def process_user_query(pergunta, cliente_info):
    respostas = [
        f"Olá! Seu serviço de {cliente_info['dados']['tipo_servico']} está previsto para ser concluído hoje.",
        f"Com prazer! Seu veículo {cliente_info['dados']['veiculo']['modelo']} está atualmente na fase de instalação.",
        f"Claro! A loja mais próxima fica na Av. Paulista, 1000 - São Paulo. Funciona das 8h às 18h.",
        f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
    ]
    return random.choice(respostas)

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS
    
    # Inicializa as mensagens, se estiverem vazias
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
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
                
                # Mensagem de resposta
                response = f"""
                Olá {client_data['dados']['nome']}! Encontrei suas informações.
                
                Seu atendimento está com status: {status_tag}
                
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
        # Cliente já identificado, processa pergunta
        response = process_user_query(user_input, CLIENTE_INFO)
    
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
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
