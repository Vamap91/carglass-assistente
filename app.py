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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY
OPENAI_MODEL = "gpt-4-turbo"  # Usando GPT-4 Turbo para respostas mais precisas

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    if re.match(r'^\d{11}from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses), clean_text):
        logger.info("Identificado como CPF")
        return "cpf", clean_text
    
    # Verifica telefone (10-11 dígitos)
    elif re.match(r'^\d{10,11}from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses), clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa (formatos antigo e novo)
    elif re.match(r'^[A-Za-z]{3}\d{4}from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses), clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses), clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 1 a 8 dígitos)
    elif re.match(r'^\d{1,8}from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses), clean_text):
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de telefones para CPF
    telefone_para_cpf = {
        "11987654321": "12345678900",
        "11976543210": "98765432100",
        "11955556666": "11122233344",
        "11944443333": "44455566677",
        "11933332222": "77788899900",
        "11922221111": "22233344455",
        "11911110000": "55566677788",
        "11900009999": "33344455566"
    }
    
    # Mapeamento de ordens para CPF
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Mapeamento de placas para CPF
    placa_para_cpf = {
        "ABC1234": "12345678900",
        "DEF5678": "98765432100",
        "GHI9012": "11122233344",
        "JKL3456": "44455566677",
        "MNO7890": "77788899900",
        "PQR1234": "22233344455",
        "STU5678": "55566677788",
        "VWX9012": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone
    elif tipo == "telefone" and valor in telefone_para_cpf:
        cpf = telefone_para_cpf[valor]
        logger.info(f"Telefone {valor} mapeado para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação por placa
    elif tipo == "placa" and valor in placa_para_cpf:
        cpf = placa_para_cpf[valor]
        logger.info(f"Placa {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        
        # Chamada para a API da OpenAI usando GPT-4 Turbo
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,  # Usando GPT-4 Turbo definido na variável global
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
        logger.error(traceback.format_exc())
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

# Rota para testar API por tipo e valor
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

# Rota para testar todos os endpoints disponíveis
@app.route('/api_test_all')
def api_test_all():
    """
    Rota para testar todos os endpoints da API com um valor específico
    Acesse /api_test_all?valor=12345678900 para testar
    """
    global USE_REAL_API
    
    valor = request.args.get('valor', '12345678900')
    
    # Força uso da API real para este teste
    old_setting = USE_REAL_API
    USE_REAL_API = True
    
    # Testa cada endpoint disponível
    endpoints = ["cpf", "telefone", "ordem", "placa"]
    results = {}
    
    for tipo in endpoints:
        try:
            resultado = get_client_data(tipo, valor)
            results[tipo] = resultado
        except Exception as e:
            results[tipo] = {"erro": str(e)}
    
    # Restaura configuração
    USE_REAL_API = old_setting
    
    return jsonify({
        "teste": "API Fusion CarGlass - Todos os endpoints",
        "valor_testado": valor,
        "resultados": results
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

# Rota para verificar status do sistema
@app.route('/system_status')
def system_status():
    """
    Rota para verificar o status do sistema, incluindo conectividade com a API
    """
    status = {
        "app": {
            "status": "online",
            "versão": "1.0.2",
            "modo_api": "real" if USE_REAL_API else "simulação",
            "modelo_ai": OPENAI_MODEL
        },
        "conexões": {}
    }
    
    # Testa todos os endpoints da API
    endpoints = ["cpf", "telefone", "ordem", "placa"]
    api_status = {}
    
    for tipo in endpoints:
        try:
            # Usa um valor padrão para teste
            valor = "123456" if tipo == "ordem" else "12345678900"
            
            start_time = time.time()
            response = requests.get(f"{API_BASE_URL}/{tipo}/{valor}", 
                                   headers={"Content-Type": "application/json", "Accept": "application/json"}, 
                                   timeout=3)
            end_time = time.time()
            
            api_status[tipo] = {
                "status": "online" if response.status_code == 200 else "erro",
                "codigo_resposta": response.status_code,
                "tempo_resposta": f"{(end_time - start_time):.3f}s"
            }
        except Exception as e:
            api_status[tipo] = {
                "status": "offline",
                "erro": str(e)
            }
    
    status["conexões"]["api_fusion"] = api_status
    
    # Testa OpenAI
    try:
        if OPENAI_API_KEY:
            start_time = time.time()
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": "Olá"}],
                max_tokens=5
            )
            end_time = time.time()
            
            status["conexões"]["openai"] = {
                "status": "online",
                "modelo": OPENAI_MODEL,
                "tempo_resposta": f"{(end_time - start_time):.3f}s"
            }
        else:
            status["conexões"]["openai"] = {
                "status": "desativado",
                "motivo": "Chave API não configurada"
            }
    except Exception as e:
        status["conexões"]["openai"] = {
            "status": "erro",
            "erro": str(e)
        }
    
    return jsonify(status)

if __name__ == '__main__':
    # Configuração de log
    logger.info(f"Iniciando aplicação no modo: {'API REAL' if USE_REAL_API else 'API SIMULADA'}")
    logger.info(f"Base URL da API: {API_BASE_URL}")
    logger.info(f"Modelo OpenAI: {OPENAI_MODEL}")
    
    # Executa a aplicação
    app.run(debug=True)from flask import Flask, render_template, request, jsonify
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
# Na produção, use variáveis de ambiente ou secrets.toml
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Configuração para usar API real ou mockada
USE_REAL_API = True  # Mude para True para usar API real da CarGlass
API_BASE_URL = "http://fusion-hml.carglass.hml.local:3000/api/status"

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
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
    
    # Verifica telefone
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info("Identificado como telefone")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info("Identificado como placa")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço (número de 5 a 8 dígitos)
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
            "placa": f"{API_BASE_URL}/placa/{valor}"  # Podemos incluir, mas talvez não esteja disponível
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
                    
                    # Verifica se a resposta tem a estrutura esperada
                    if 'sucesso' in data:
                        return data
                    else:
                        logger.error(f"Formato de resposta inesperado: {data}")
                        return {
                            "sucesso": False,
                            "mensagem": "Formato de resposta da API inesperado"
                        }
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
                
        except requests.exceptions.Timeout:
            # Trata timeout específico
            logger.error("Timeout ao conectar à API")
            return {
                "sucesso": False,
                "mensagem": "Timeout ao conectar à API. A solicitação demorou muito tempo."
            }
        except requests.exceptions.ConnectionError:
            # Trata erros de conexão
            logger.error("Erro de conexão com a API - servidor inacessível")
            return {
                "sucesso": False,
                "mensagem": "Não foi possível conectar à API. Servidor inacessível."
            }
        except requests.exceptions.RequestException as e:
            # Trata outros erros de request
            logger.error(f"Erro de requisição com a API: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro ao conectar com a API: {str(e)}"
            }
        except Exception as e:
            # Trata outros erros
            logger.error(f"Erro ao processar requisição: {str(e)}")
            logger.error(traceback.format_exc())
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
    Retorna os mesmos dados mockados da versão original.
    """
    logger.info(f"Usando dados mockados para tipo={tipo}, valor={valor}")
    
    # Dados simulados para diferentes status de atendimento
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
        "11122233344": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "11122233344",
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023"
                }
            }
        },
        "44455566677": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "44455566677",
            "dados": {
                "nome": "Ana Souza",
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Peça Identificada",
                "tipo_servico": "Troca de Retrovisor",
                "veiculo": {
                    "modelo": "Fiat Pulse",
                    "placa": "JKL3456",
                    "ano": "2024"
                }
            }
        },
        "77788899900": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "77788899900",
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "MNO7890",
                    "ano": "2023"
                }
            }
        },
        "22233344455": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "22233344455",
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {
                    "modelo": "Hyundai HB20",
                    "placa": "PQR1234",
                    "ano": "2022"
                }
            }
        },
        "55566677788": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "55566677788",
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {
                    "modelo": "Chevrolet Onix",
                    "placa": "STU5678",
                    "ano": "2021"
                }
            }
        },
        "33344455566": {
            "sucesso": True,
            "tipo": "cpf",
            "valor": "33344455566",
            "dados": {
                "nome": "Lúcia Costa",
                "cpf": "33344455566",
                "telefone": "11900009999",
                "ordem": "ORD80246",
                "status": "Concluído",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {
                    "modelo": "Renault Kwid",
                    "placa": "VWX9012",
                    "ano": "2020"
                }
            }
        }
    }
    
    # Mapeamento de ordens para CPF (para teste)
    ordem_para_cpf = {
        "12345": "12345678900",
        "67890": "98765432100",
        "54321": "11122233344",
        "98765": "44455566677",
        "24680": "77788899900",
        "13579": "22233344455",
        "36925": "55566677788",
        "80246": "33344455566",
        "123456": "12345678900",    # Número de ordem do seu teste
        "2653616": "12345678900",   # Número de ordem do seu teste
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "44455566677",
        "ORD24680": "77788899900",
        "ORD13579": "22233344455",
        "ORD36925": "55566677788",
        "ORD80246": "33344455566"
    }
    
    # Verificação por CPF
    if tipo == "cpf" and valor in mock_data:
        return mock_data[valor]
    
    # Verificação de ordem
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf = ordem_para_cpf[valor]
        logger.info(f"Ordem {valor} mapeada para CPF {cpf}")
        return mock_data[cpf]
    
    # Verificação de telefone (simulada)
    elif tipo == "telefone":
        # Para teste, retorna dados do primeiro cliente
        return mock_data["12345678900"]
    
    # Verificação por placa (simulada)
    elif tipo == "placa" and valor == "ABC1234":
        return mock_data["12345678900"]
    elif tipo == "placa" and valor == "DEF5678":
        return mock_data["98765432100"]
    
    # Cliente não encontrado
    logger.warning(f"Cliente não encontrado para tipo={tipo}, valor={valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# Função para gerar o HTML da barra de progresso
def get_progress_bar_html(client_data):
    """
    Gera o HTML da barra de progresso baseado no status do cliente.
    """
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
    
    # Configurar os estados das etapas e a largura do progresso com base no status
    progress_percentage = "0%"
    next_step_index = 0
    status_class = "andamento"  # Classe CSS padrão
    
    # Configurar baseado no status
    if status == "Ordem de Serviço Aberta":
        steps[0]["state"] = "active"
        next_step_index = 1
        progress_percentage = "0%"
        status_class = "aberta"
        
    elif status == "Aguardando fotos para liberação da ordem":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "active"
        next_step_index = 2
        progress_percentage = "14%"  # 1/7 completo
        status_class = "aguardando"
        
    elif status == "Fotos Recebidas":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "active"
        next_step_index = 3
        progress_percentage = "28%"  # 2/7 completo
        status_class = "recebidas"
        
    elif status == "Peça Identificada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "active"
        next_step_index = 4
        progress_percentage = "42%"  # 3/7 completo
        status_class = "identificada"
        
    elif status == "Ordem de Serviço Liberada":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "liberada"
        
    elif status == "Serviço agendado com sucesso":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "active"
        next_step_index = 5
        progress_percentage = "57%"  # 4/7 completo
        status_class = "agendado"
        
    elif status == "Em andamento":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "active"
        next_step_index = 6
        progress_percentage = "71%"  # 5/7 completo
        status_class = "andamento"
        
    elif status == "Concluído":
        steps[0]["state"] = "completed"
        steps[1]["state"] = "completed"
        steps[2]["state"] = "completed"
        steps[3]["state"] = "completed"
        steps[4]["state"] = "completed"
        steps[5]["state"] = "completed"
        steps[6]["state"] = "active"
        next_step_index = 6  # Não há próximo quando concluído
        progress_percentage = "100%"
        status_class = "concluido"
    
    # Definir a próxima etapa (se houver)
    if next_step_index < len(steps) and next_step_index != 6:  # Se não for a última etapa
        steps[next_step_index]["state"] = "next"
    
    # Construir o HTML para as etapas
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
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'status', 'fase']):
        status = cliente_info['dados']['status']
        
        if status == "Serviço agendado com sucesso":
            return """
            Seu serviço foi agendado com sucesso e está aguardando a data marcada para execução.
            
            As próximas etapas serão:
            1. Abertura da ordem de serviço
            2. Identificação da peça necessária
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Liberada":
            return """
            Sua ordem de serviço já foi liberada! Isso significa que já identificamos o serviço necessário e autorizamos sua execução.
            
            As próximas etapas são:
            1. Separação da peça para o serviço
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Peça Identificada":
            return """
            A peça necessária para o seu veículo já foi identificada e separada em nosso estoque.
            
            As próximas etapas são:
            1. Execução do serviço
            2. Inspeção de qualidade
            3. Entrega do veículo
            """
        elif status == "Fotos Recebidas":
            return """
            Recebemos as fotos do seu veículo e estamos analisando para preparar tudo para o atendimento.
            
            As próximas etapas são:
            1. Confirmação da peça necessária
            2. Execução do serviço
            3. Inspeção de qualidade
            4. Entrega do veículo
            """
        elif status == "Aguardando fotos para liberação da ordem":
            return """
            Estamos aguardando as fotos do seu veículo para liberação da ordem de serviço.
            
            Você pode enviar as fotos pelo WhatsApp (11) 4003-8070 ou pelo e-mail atendimento@carglass.com.br.
            
            Após recebermos as fotos, as próximas etapas serão:
            1. Liberação da ordem de serviço
            2. Identificação da peça
            3. Execução do serviço
            4. Inspeção de qualidade
            5. Entrega do veículo
            """
        elif status == "Ordem de Serviço Aberta":
            return """
            Sua ordem de serviço já foi aberta! Estamos nos preparando para realizar o atendimento.
            
            As próximas etapas são:
            1. Envio e análise de fotos
            2. Liberação da ordem
            3. Identificação da peça
            4. Execução do serviço
            5. Inspeção de qualidade
            6. Entrega do veículo
            """
    
    # Perguntas sobre opções de serviço
    if any(keyword in pergunta_lower for keyword in ['opção', 'opções', 'que serviços', 'posso fazer', 'oferecem']):
        return """
        A CarGlass oferece diversos serviços para seu veículo:
        
        1. Troca de Parabrisa
        2. Reparo de Trincas
        3. Troca de Vidros Laterais
        4. Troca de Vidro Traseiro
        5. Calibração ADAS (sistemas avançados de assistência ao motorista)
        6. Polimento de Faróis
        7. Reparo e Troca de Retrovisores
        8. Película de Proteção Solar
        
        Qual serviço você gostaria de conhecer melhor?
        """
    
    # Perguntas sobre atendente humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente humano', 'falar com atendente', 'falar com humano']):
        return """
        Entendo que você prefere falar com um atendente humano. 
        
        Você pode entrar em contato com nossa central de atendimento pelos seguintes canais:
        
        - Telefone: 0800-727-2327
        - WhatsApp: (11) 4003-8070
        
        Nosso horário de atendimento é de segunda a sexta, das 8h às 20h, e aos sábados das 8h às 16h.
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
        logger.error(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "Temos lojas em São Paulo, Santo André, São Bernardo e Guarulhos. Para mais detalhes ou para mudar o local do seu atendimento, entre em contato com nossa central: 0800-727-2327.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses)
