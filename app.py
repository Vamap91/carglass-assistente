from flask import Flask, render_template, request, jsonify
import random
import re
import os
import openai
import time
import uuid
import requests
import logging
import traceback

app = Flask(__name__)
app.secret_key = 'carglass-secreto'

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração da OpenAI API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY
OPENAI_MODEL = "gpt-4-turbo"  # Usando GPT-4 Turbo para respostas mais precisas

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens
MENSAGENS = []

# Estado de identificação do cliente
CLIENTE_IDENTIFICADO = False
CLIENTE_INFO = None

# Detecta o tipo de identificador (CPF, placa, etc)
def detect_identifier_type(text):
    # Remove caracteres não alfanuméricos
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text)
    
    logger.info(f"Detectando tipo para: '{clean_text}'")
    
    # Verifica CPF (11 dígitos numéricos)
    if re.match(r'^\d{11}$', clean_text):
        logger.info("Identificado como CPF")
        return "cpf", clean_text
    
    # Verifica telefone (10-11 dígitos)
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 1-8 dígitos)
    elif re.match(r'^\d{1,8}$', clean_text):
        logger.info(f"Identificado como ordem de serviço: {clean_text}")
        return "ordem", clean_text
    
    # Não identificado
    logger.warning(f"Tipo de identificador não reconhecido: '{clean_text}'")
    return None, clean_text

# Busca dados do cliente na API Fusion da CarGlass
def get_client_data(tipo, valor):
    """
    Busca dados do cliente na API Fusion da CarGlass.
    Se USE_REAL_API = True, consulta API real, caso contrário retorna dados mockados.
    """
    logger.info(f"Buscando dados com tipo={tipo}, valor={valor}, modo={'API REAL' if USE_REAL_API else 'SIMULAÇÃO'}")
    
    if USE_REAL_API:
        # Mapeamento de tipos para endpoints da API
        endpoints = {
            "cpf": f"{API_BASE_URL}/cpf/{valor}",
            "telefone": f"{API_BASE_URL}/telefone/{valor}",
            "ordem": f"{API_BASE_URL}/ordem/{valor}",
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Incluído, mesmo que possa não estar disponível ainda
        }
        
        # Verifica se o tipo de consulta é suportado
        if tipo not in endpoints:
            logger.warning(f"Tipo de consulta '{tipo}' não suportado pela API")
            return {"sucesso": False, "mensagem": f"Tipo de consulta '{tipo}' não suportado"}
        
        try:
            # Configuração dos headers da requisição
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Log da requisição
            logger.info(f"Consultando API: {endpoints[tipo]}")
            
            # Faz a requisição à API
            response = requests.get(endpoints[tipo], headers=headers, timeout=10)
            
            # Verifica o status da resposta
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"Resposta da API recebida com sucesso: {data.get('sucesso')}")
                    return data
                except Exception as e:
                    logger.error(f"Erro ao processar JSON da resposta: {str(e)}")
                    return {
                        "sucesso": False,
                        "mensagem": f"Erro ao processar resposta da API: {str(e)}"
                    }
            else:
                # Trata erros de status HTTP
                logger.error(f"Erro ao consultar API: Status {response.status_code}")
                return {
                    "sucesso": False, 
                    "mensagem": f"Erro ao consultar API: Status {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            # Trata erros de conexão
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao processar requisição: {str(e)}"
            }
    else:
        # Usando dados mockados (versão original)
        return get_mock_client_data(tipo, valor)

# Versão mockada da função get_client_data para testes locais
def get_mock_client_data(tipo, valor):
    """
    Versão mock da função get_client_data para testes locais quando a API estiver indisponível.
    """
    # Dados simulados (mantidos do código original)
    mock_data = {
        "12345678900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "12345678900",
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
        },
        "98765432100": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "98765432100",
            "dados": {
                "nome": "Maria Silva",
                "cpf": "98765432100",
                "telefone": "11976543210",
                "ordem": "ORD67890",
                "status": "Serviço agendado com sucesso",
                "tipo_servico": "Reparo de Trinca",
                "veiculo": {
                    "modelo": "Toyota Corolla",
                    "placa": "DEF5678",
                    "ano": "2021"
                }
            }
        },
        # [...outros dados mockados mantidos do código original...]
    }
    
    # Mapeamento de ordens para CPF (simplificado para os testes)
    ordem_para_cpf = {
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900"    # Número de ordem do seu teste
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simplificada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simplificada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso (mantida do código original)
def get_progress_bar_html(client_data):
    # Determinar o status atual baseado nos dados do cliente
    status = client_data['dados']['status']
    current_time = time.strftime("%d/%m/%Y - %H:%M")
    
    # Definir etapas padrão e seus estados iniciais
    steps = [
        {"label": "Ordem Aberta", "state": "pending"},
        {"label": "Aguardando Fotos", "state": "pending"},
        {"label": "Peça Identificada", "state": "pending"},
        {"label": "Agendado", "state": "pending"},
        {"label": "Execução", "state": "pending"},
        {"label": "Inspeção", "state": "pending"},
        {"label": "Concluído", "state": "pending"}
    ]
    
    # Configurar baseado no status (lógica mantida do código original)
    # ... [código mantido do original]
    
    # Código simplificado para exemplo - na implementação real, mantenha a lógica completa
    progress_percentage = "50%"  # Valor de exemplo
    status_class = "andamento"   # Valor de exemplo
    
    # Construir o HTML para as etapas - lógica simplificada para exemplo
    steps_html = ""
    for step in steps:
        state = step["state"]
        next_highlight = '<div class="step-highlight">Próxima etapa</div>' if state == "next" else ''
        steps_html += f'''
        <div class="timeline-step {state}">
            <div class="step-node"></div>
            <div class="step-label">{step["label"]}</div>
            {next_highlight}
        </div>
        '''
    
    # HTML completo da barra de progresso
    html = f'''
    <div class="status-progress-container">
        <div class="status-current">
            <span class="status-tag {status_class}">{status}</span>
            <span class="status-date">{current_time}</span>
        </div>
        
        <div class="progress-timeline">
            <div class="timeline-track" style="--progress-width: {progress_percentage};">
                {steps_html}
            </div>
        </div>
    </div>
    '''
    
    return html

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    # Função mantida quase idêntica, apenas com mudança do modelo da OpenAI
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
        
        # Chamada para a API da OpenAI - ATUALIZADA para GPT-4 Turbo
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
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
            "content": "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.",
            "time": time.strftime("%H:%M")
        }]
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para testar API
@app.route('/api_test')
def api_test():
    """
    Rota para testar a conexão com a API
    Acesse /api_test?tipo=cpf&valor=12345678900 para testar
    """
    global USE_REAL_API  # Movida para o início da função
    
    tipo = request.args.get('tipo', 'cpf')
    valor = request.args.get('valor', '12345678900')
    
    # Força uso da API real para este teste
    old_setting = USE_REAL_API
    USE_REAL_API = True
    
    result = get_client_data(tipo, valor)
    
    # Restaura configuração
    USE_REAL_API = old_setting
    
    return jsonify({
        "teste": "API Fusion CarGlass",
        "configuracao": {
            "tipo": tipo,
            "valor": valor,
            "endpoint": f"{API_BASE_URL}/{tipo}/{valor}"
        },
        "resultado": result
    })

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO
    
    try:
        user_input = request.form.get('message', '')
        logger.info(f"Mensagem recebida: '{user_input}'")
        
        # Obtém o horário atual real
        current_time = time.strftime("%H:%M")
        
        # Adiciona mensagem do usuário
        MENSAGENS.append({
            "role": "user", 
            "content": user_input,
            "time": current_time
        })
        
        # Se ainda não identificou o cliente
        if not CLIENTE_IDENTIFICADO:
            tipo, valor = detect_identifier_type(user_input)
            
            if tipo:
                client_data = get_client_data(tipo, valor)
                logger.info(f"Resultado da busca: {client_data.get('sucesso')}")
                
                if client_data.get('sucesso'):
                    # Cliente encontrado
                    CLIENTE_INFO = client_data
                    CLIENTE_IDENTIFICADO = True
                    
                    # Formata status com classe CSS baseada no status
                    status = client_data['dados']['status']
                    status_class = "andamento"  # Padrão
                    
                    # Define a classe CSS de acordo com o status
                    if "agendado" in status.lower():
                        status_class = "agendado"
                    elif "andamento" in status.lower():
                        status_class = "andamento"
                    elif "liberada" in status.lower():
                        status_class = "liberada"
                    elif "identificada" in status.lower():
                        status_class = "identificada"
                    elif "recebidas" in status.lower():
                        status_class = "recebidas"
                    elif "aguardando" in status.lower():
                        status_class = "aguardando"
                    elif "aberta" in status.lower():
                        status_class = "aberta"
                    elif "concluído" in status.lower():
                        status_class = "concluido"
                    
                    status_tag = f'<span class="status-tag {status_class}">{status}</span>'
                    
                    # Gera a barra de progresso dinâmica
                    progress_bar = get_progress_bar_html(client_data)
                    
                    # Mensagem de resposta com a barra de progresso
                    response = f"""
                    Olá {client_data['dados']['nome']}! Encontrei suas informações. Seu atendimento está com status: {status_tag}
                    
                    {progress_bar}
                    
                    Ordem de serviço: {client_data['dados']['ordem']} 
                    Serviço: {client_data['dados']['tipo_servico']} 
                    Veículo: {client_data['dados']['veiculo']['modelo']} ({client_data['dados']['veiculo']['ano']}) 
                    Placa: {client_data['dados']['veiculo']['placa']} 
                    
                    Como posso ajudar você hoje?
                    """
                else:
                    # Cliente não encontrado
                    if 'mensagem' in client_data:
                        erro_mensagem = client_data['mensagem']
                    else:
                        erro_mensagem = "Informações não encontradas"
                    
                    response = f"""
                    Não consegui encontrar informações com o {tipo} fornecido.
                    
                    Detalhes: {erro_mensagem}
                    
                    Por favor, tente novamente ou use outro identificador.
                    """
            else:
                # Formato inválido
                response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida."
        else:
            # Cliente já identificado, processa pergunta com IA
            response = get_ai_response(user_input, CLIENTE_INFO)
        
        # Adiciona resposta do assistente
        MENSAGENS.append({
            "role": "assistant", 
            "content": response,
            "time": current_time
        })
        
        return jsonify({
            'messages': MENSAGENS
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Horário atual
        current_time = time.strftime("%H:%M")
        
        # Adiciona resposta de erro
        error_message = {
            "role": "assistant", 
            "content": f"Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
            "time": current_time
        }
        
        MENSAGENS.append(error_message)
        
        return jsonify({
            'messages': MENSAGENS,
            'error': str(e)
        })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO
    
    # Limpa as mensagens
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.",
        "time": time.strftime("%H:%M")
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para alternar modo API
@app.route('/toggle_api_mode', methods=['POST'])
def toggle_api_mode():
    """
    Rota para alternar entre API real e mockada
    """
    global USE_REAL_API
    USE_REAL_API = not USE_REAL_API
    
    logger.info(f"Modo de API alterado para: {'REAL' if USE_REAL_API else 'SIMULAÇÃO'}")
    
    return jsonify({
        'status': 'success',
        'api_mode': 'real' if USE_REAL_API else 'mock',
        'message': f"Modo de API alterado para: {'REAL' if USE_REAL_API else 'SIMULAÇÃO'}"
    })

if __name__ == '__main__':
    # Configuração de log
    logger.info(f"Iniciando aplicação no modo: {'API REAL' if USE_REAL_API else 'API SIMULADA'}")
    logger.info(f"Base URL da API: {API_BASE_URL}")
    logger.info(f"Modelo OpenAI: {OPENAI_MODEL}")
    
    # Executa a aplicação
    app.run(debug=True)
