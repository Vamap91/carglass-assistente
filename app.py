from flask import Flask, render_template, request, jsonify
import random
import re
import os
import openai
import json
import time
import uuid

app = Flask(__name__)
app.secret_key = 'carglass-secreto'

# Configuração da OpenAI API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Lista para armazenar mensagens da UI (em uma aplicação real, usaria banco de dados)
MENSAGENS = []

# Estado de identificação do cliente
CLIENTE_IDENTIFICADO = False
CLIENTE_INFO = None

# Contexto completo da conversa para o OpenAI
HISTORICO_OPENAI = []

# Controle de escalonamento
ESCALATION_NEEDED = False
ESCALATION_REASON = ""
ESCALATION_ID = ""

# Contador de tentativas falhas consecutivas
CONSECUTIVE_FAILURES = 0
MAX_FAILURES_BEFORE_ESCALATION = 2

# Status de serviço e explicações detalhadas
STATUS_SERVICO = {
    "Agendado": "O serviço está agendado, mas ainda não iniciamos o trabalho no veículo.",
    "Em andamento": "Nossa equipe técnica está trabalhando no veículo neste momento. O serviço inclui a remoção do vidro antigo, preparação da superfície, aplicação de adesivos e instalação do novo vidro.",
    "Concluído": "O serviço foi finalizado com sucesso e o veículo está pronto para retirada.",
    "Aguardando peça": "Estamos aguardando a chegada da peça necessária para realizar o serviço.",
    "Em inspeção final": "O serviço foi realizado e está na fase de inspeção final para garantir qualidade."
}

# Informações específicas de garantia por tipo de serviço
GARANTIAS = {
    "Troca de Parabrisa": {
        "prazo": "12 meses",
        "cobertura": "Infiltrações, problemas de vedação, defeitos de instalação",
        "requisitos": "Manter nota fiscal, não realizar modificações no vidro (películas, adesivos)",
        "observacoes": "A garantia não cobre danos causados por impactos, vandalismo ou desastres naturais."
    },
    "Reparo de Trinca": {
        "prazo": "6 meses",
        "cobertura": "Reabertura da trinca original",
        "requisitos": "Manter nota fiscal, fotografias do reparo",
        "observacoes": "A garantia não cobre novas trincas ou extensões além da original."
    },
    "Troca de Vidro Lateral": {
        "prazo": "12 meses",
        "cobertura": "Problemas de instalação, vedação e funcionamento",
        "requisitos": "Manter nota fiscal, não realizar modificações",
        "observacoes": "A garantia não cobre danos causados por impactos ou uso indevido."
    }
}

# Lojas CarGlass em São Paulo (fictícias)
LOJAS_CARGLASS = [
    {
        "nome": "CarGlass Paulista",
        "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
        "telefone": "(11) 3456-7890",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h",
        "coordenadas": "-23.565868,-46.652444"
    },
    {
        "nome": "CarGlass Morumbi",
        "endereco": "Av. Morumbi, 2000 - Morumbi, São Paulo - SP",
        "telefone": "(11) 3456-7891",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h",
        "coordenadas": "-23.621735,-46.702531"
    },
    {
        "nome": "CarGlass Tatuapé",
        "endereco": "Rua Tuiuti, 1500 - Tatuapé, São Paulo - SP",
        "telefone": "(11) 3456-7892",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h",
        "coordenadas": "-23.537103,-46.576355"
    }
]

# Critérios para escalonamento
ESCALATION_CRITERIA = [
    # Solicitações de mudanças no serviço
    "mudança de loja", "troca de loja", "transferir", "transferência", "mudar loja", "outra loja",
    "cancelar", "cancelamento", "desistir", "desistência", "não quero mais",
    
    # Questões financeiras
    "reembolso", "devolução", "ressarcimento", "estorno", "dinheiro de volta", "pagamento",
    "desconto", "abatimento", "valor", "caro", "preço", "orçamento", "cobrança", "cobrou errado",
    "nota fiscal", "recibo", "seguradora", "franquia",
    
    # Problemas e reclamações
    "insatisfeito", "reclamação", "problema", "erro", "errado", "danificado", "ruim", "péssimo",
    "defeito", "vazamento", "quebrado", "trincado", "não funciona", "com defeito", "mal feito",
    "mal instalado", "insatisfeito", "decepcionado", "frustrado", "irritado", "não gostei",
    
    # Prazos e atrasos
    "atraso", "atrasado", "demora", "demorado", "urgente", "emergência", "prazo", "quando fica pronto",
    "preciso hoje", "preciso agora", "preciso urgente", "para ontem", "já deveria estar pronto",
    
    # Solicitações de atendimento humano
    "falar com supervisor", "gerente", "responsável", "atendente", "atendente humano", "pessoa real",
    "humano", "falar com alguém", "quero falar", "preciso falar", "necessito falar", "chat", "email",
    
    # Emoções e linguagem agressiva
    "péssimo", "horrível", "indignado", "furioso", "absurdo", "inaceitável", "ridículo", "revoltante",
    "imperdoável", "fodendo", "foda", "caramba", "demais", "impossível", "lixo", "droga", "merda",
    
    # Tópicos específicos complexos
    "processo", "processar", "judicial", "advogado", "jurídico", "procon", "defesa do consumidor",
    "sinistro", "acidente", "batida", "colisão", "furto", "roubo", "policial", "bo", "boletim",
    
    # Problemas técnicos específicos
    "vidro errado", "cor errada", "modelo errado", "infiltração", "goteira", "barulho", "ruído",
    "vedação", "sensores", "calibragem", "radar", "câmera", "adas", "sistema", "programação",
    
    # Solicitações especiais
    "preferencial", "prioridade", "transporte", "buscar", "entregar", "delivery", "em casa", "domicílio"
]

# Detecta o tipo de identificador (CPF, placa, etc)
def detect_identifier_type(text):
    # Remove caracteres não alfanuméricos
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text)
    
    # Verifica CPF (11 dígitos numéricos)
    if re.match(r'^\d{11}$', clean_text):
        return "cpf", clean_text
    
    # Verifica telefone (padrões brasileiros)
    # Suporta: celulares (9 dígitos + DDD), fixos (8 dígitos + DDD), com/sem código do país
    # Exemplos: 11987654321, 1187654321, 5511987654321, 551187654321
    elif (re.match(r'^\d{10,11}
    
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
                "email": "carlos.teste@exemplo.com",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "data_entrada": "18/05/2025",
                "previsao_conclusao": "19/05/2025",
                "loja": "CarGlass Paulista",
                "loja_original": "CarGlass Paulista",
                "valor_servico": "R$ 1.250,00",
                "forma_pagamento": "Cartão de Crédito",
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234",
                    "ano": "2022",
                    "cor": "Prata"
                },
                "historico": [
                    {"data": "18/05/2025 10:15", "status": "Veículo recebido na loja"},
                    {"data": "18/05/2025 14:30", "status": "Início do serviço"},
                    {"data": "19/05/2025 08:45", "status": "Parabrisa em instalação"}
                ],
                "observacoes": "Cliente solicitou prioridade na entrega"
            }
        }
    return {"sucesso": False, "mensagem": "Cliente não encontrado"}

# Verifica se a mensagem contém critérios para escalonamento
def check_escalation_needed(mensagem, cliente_info=None):
    global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID, CONSECUTIVE_FAILURES
    
    mensagem_lower = mensagem.lower()
    
    # Verifica palavras-chave para escalonamento
    for criterio in ESCALATION_CRITERIA:
        if criterio in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Critério de escalonamento detectado: '{criterio}'"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica solicitações específicas de mudança
    if cliente_info and ("mudar" in mensagem_lower or "trocar" in mensagem_lower or "transferir" in mensagem_lower):
        if "loja" in mensagem_lower or "local" in mensagem_lower or "lugar" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação de mudança de loja"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica pedidos explícitos de atendente humano
    if ("atendente" in mensagem_lower or "humano" in mensagem_lower or "pessoa" in mensagem_lower or 
        "gente" in mensagem_lower or "alguém" in mensagem_lower):
        if ("falar" in mensagem_lower or "quero" in mensagem_lower or "preciso" in mensagem_lower or
            "contato" in mensagem_lower or "ajuda" in mensagem_lower):
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação explícita de atendente humano"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica perguntas complexas técnicas ou financeiras
    if "quanto" in mensagem_lower and ("custa" in mensagem_lower or "valor" in mensagem_lower or "preço" in mensagem_lower):
        if not cliente_info or "valor_servico" not in cliente_info['dados']:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Pergunta sobre valores sem informação disponível"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica sinais de frustração ou mensagens repetitivas (indicando que o cliente não está satisfeito com as respostas)
    if CONSECUTIVE_FAILURES > 0:
        # Procura por sinais de frustração
        frustration_indicators = ["não entendi", "não compreendi", "não é isso", "não foi isso", 
                                 "não respondeu", "não está respondendo", "mesma coisa", "repetindo",
                                 "já perguntei", "de novo", "outra vez", "repeti", "não ajudou"]
        
        for indicator in frustration_indicators:
            if indicator in mensagem_lower:
                CONSECUTIVE_FAILURES += 1
                if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                    ESCALATION_NEEDED = True
                    ESCALATION_REASON = "Frustração detectada após múltiplas tentativas"
                    ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                    return True
                break
    
    # Detecta se a mensagem contém muitas perguntas (complexidade alta)
    question_count = mensagem_lower.count("?")
    if question_count >= 3:
        ESCALATION_NEEDED = True
        ESCALATION_REASON = "Múltiplas perguntas em uma única mensagem"
        ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        return True
    
    # Verifica tamanho da mensagem (mensagens muito longas podem indicar problemas complexos)
    if len(mensagem) > 200:
        ESCALATION_NEEDED = True
        ESCALATION_REASON = "Mensagem extensa indicando questão complexa"
        ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        return True
        
    return False

# Detecta perda de contexto comparando resposta anterior com pergunta atual
def detect_context_loss(pergunta, resposta_anterior):
    try:
        prompt = f"""
        Analise a seguinte interação de atendimento ao cliente:
        
        Resposta anterior do assistente: "{resposta_anterior}"
        Pergunta atual do cliente: "{pergunta}"
        
        Verifique se a pergunta do cliente está diretamente relacionada à resposta anterior e se parece que o cliente está confuso ou insatisfeito com a resposta.
        
        Escolha UMA das seguintes opções:
        1. CONTEXTUAL - A pergunta está diretamente relacionada à resposta anterior e segue naturalmente a conversa
        2. NOVO_TÓPICO - A pergunta muda para um novo tópico, mas não indica problemas com a resposta anterior
        3. CONFUSÃO - A pergunta sugere que o cliente está confuso com a resposta anterior ou está repetindo a mesma pergunta
        4. INSATISFAÇÃO - A pergunta indica que o cliente está insatisfeito com a resposta anterior
        
        Retorne apenas o número da opção sem explicação adicional.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1,
        )
        
        result = response.choices[0].message['content'].strip()
        
        if "3" in result or "4" in result:
            return True
        return False
    except Exception as e:
        print(f"Erro ao detectar perda de contexto: {e}")
        return False

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    global HISTORICO_OPENAI, CONSECUTIVE_FAILURES, ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
    
    # Verifica escalonamento por critérios
    if check_escalation_needed(pergunta, cliente_info):
        return generate_escalation_response()
    
    # Analisa o sentimento do cliente
    needs_escalation, reason = analyze_sentiment(pergunta)
    if needs_escalation:
        ESCALATION_NEEDED = True
        ESCALATION_REASON = reason
        ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        return generate_escalation_response()
    
    # Verifica se há perda de contexto apenas se houver histórico
    if len(HISTORICO_OPENAI) >= 2:
        # Pega a última resposta do assistente
        ultima_resposta = None
        for msg in reversed(HISTORICO_OPENAI):
            if msg["role"] == "assistant":
                ultima_resposta = msg["content"]
                break
        
        if ultima_resposta and detect_context_loss(pergunta, ultima_resposta):
            CONSECUTIVE_FAILURES += 1
            print(f"Possível perda de contexto detectada. Falhas consecutivas: {CONSECUTIVE_FAILURES}")
            
            if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                # Escalonar para atendimento humano após falhas consecutivas
                ESCALATION_NEEDED = True
                ESCALATION_REASON = "Perda de contexto detectada após múltiplas tentativas"
                ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                return generate_escalation_response()
    
    try:
        # Limitamos o histórico para evitar tokens excessivos (mantemos os últimos 10 turnos)
        if len(HISTORICO_OPENAI) > 20:
            # Mantém a primeira mensagem (sistema) e os últimos 9 turnos
            system_message = HISTORICO_OPENAI[0] if HISTORICO_OPENAI[0]["role"] == "system" else None
            HISTORICO_OPENAI = HISTORICO_OPENAI[-18:]
            if system_message:
                HISTORICO_OPENAI = [system_message] + HISTORICO_OPENAI
        
        # Constrói o sistema prompt com todas as informações relevantes
        system_prompt = f"""
        Você é o assistente virtual especializado da CarGlass, empresa líder em reparo e substituição de vidros automotivos. 
        
        DADOS DO CLIENTE:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Cor: {cliente_info['dados']['veiculo']['cor']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        DADOS DO ATENDIMENTO ATUAL:
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Status atual: {cliente_info['dados']['status']}
        - Detalhes do status: {STATUS_SERVICO.get(cliente_info['dados']['status'], "Sem detalhes adicionais")}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Data de entrada: {cliente_info['dados']['data_entrada']}
        - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
        - Loja atual: {cliente_info['dados']['loja']}
        - Valor do serviço: {cliente_info['dados']['valor_servico']}
        
        HISTÓRICO DO ATENDIMENTO:
        {json.dumps(cliente_info['dados']['historico'], indent=2, ensure_ascii=False)}
        
        INFORMAÇÕES DE GARANTIA:
        {json.dumps(GARANTIAS.get(cliente_info['dados']['tipo_servico'], {"prazo": "12 meses", "cobertura": "Padrão"}), indent=2, ensure_ascii=False)}
        
        DIRETRIZES DE ATENDIMENTO:
        1. Seja EXTREMAMENTE específico ao mencionar informações do cliente acima.
        2. Mantenha respostas concisas entre 2-4 frases, sendo direto ao ponto.
        3. Use uma linguagem cordial mas objetiva, compatível com uma empresa profissional.
        4. Nunca invente informações que não estão nos dados fornecidos.
        5. Se o cliente fizer perguntas sobre aspectos não cobertos nos dados (como mudança de loja ou cancelamento), indique que precisará transferir para um atendente humano.
        6. Sempre relate apenas a loja atual do cliente ({cliente_info['dados']['loja']}) quando perguntado sobre localização.
        7. Mencione sempre a data exata de previsão de conclusão ({cliente_info['dados']['previsao_conclusao']}) quando perguntado sobre prazos.
        8. Se o cliente perguntar "o que é" algum status, use a descrição detalhada do STATUS_SERVICO.
        9. Se o cliente parecer confuso sobre a mesma questão repetidamente, ofereça transferir para um atendente humano.
        10. Forneça sempre informações precisas e específicas sobre o caso atual, nunca genéricas.
        
        EVITE ESTES ERROS COMUNS:
        - Não fale sobre outras lojas além da CarGlass {cliente_info['dados']['loja']} sem ser explicitamente perguntado
        - Não mencione "verificar com a equipe técnica" para informações que você já possui
        - Não use expressões genéricas como "nossos especialistas" quando pode dar informações específicas
        - Não ofereça serviços adicionais não solicitados

        ### IMPORTANTE ###
        Você DEVE ser extremamente específico sobre:
        1. O status atual: "{cliente_info['dados']['status']}"
        2. A loja onde o veículo está: "{cliente_info['dados']['loja']}"
        3. A previsão de conclusão: "{cliente_info['dados']['previsao_conclusao']}"
        4. O histórico exato do atendimento com as datas
        """
        
        # Verifica se já existe uma mensagem de sistema no histórico
        if not HISTORICO_OPENAI or HISTORICO_OPENAI[0]["role"] != "system":
            HISTORICO_OPENAI = [{"role": "system", "content": system_prompt}] + HISTORICO_OPENAI
        else:
            # Atualiza a mensagem de sistema existente
            HISTORICO_OPENAI[0] = {"role": "system", "content": system_prompt}
        
        # Adiciona a pergunta atual ao histórico
        HISTORICO_OPENAI.append({"role": "user", "content": pergunta})
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=HISTORICO_OPENAI,
            max_tokens=200,
            temperature=0.5,
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona a resposta ao histórico
        HISTORICO_OPENAI.append({"role": "assistant", "content": ai_response})
        
        # Reseta contador de falhas consecutivas após resposta bem-sucedida
        CONSECUTIVE_FAILURES = 0
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        CONSECUTIVE_FAILURES += 1
        
        # Após várias falhas consecutivas, escalonar para humano
        if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Falhas técnicas consecutivas: {e}"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return generate_escalation_response()
            
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento na loja {cliente_info['dados']['loja']} e a previsão de conclusão é {cliente_info['dados']['previsao_conclusao']}.",
            f"Seu Honda Civic está na etapa de '{cliente_info['dados']['historico'][-1]['status']}' em nossa loja {cliente_info['dados']['loja']}, com previsão de conclusão para {cliente_info['dados']['previsao_conclusao']}.",
            f"A última atualização do seu atendimento foi '{cliente_info['dados']['historico'][-1]['status']}' em {cliente_info['dados']['historico'][-1]['data']}. Continuamos trabalhando para entregar seu veículo em {cliente_info['dados']['previsao_conclusao']}."
        ]
        return random.choice(fallback_responses)info):
    global HISTORICO_OPENAI, CONSECUTIVE_FAILURES
    
    # Verifica escalonamento
    if check_escalation_needed(pergunta, cliente_info):
        return generate_escalation_response()
    
    # Verifica se há perda de contexto apenas se houver histórico
    if len(HISTORICO_OPENAI) >= 2:
        # Pega a última resposta do assistente
        ultima_resposta = None
        for msg in reversed(HISTORICO_OPENAI):
            if msg["role"] == "assistant":
                ultima_resposta = msg["content"]
                break
        
        if ultima_resposta and detect_context_loss(pergunta, ultima_resposta):
            CONSECUTIVE_FAILURES += 1
            print(f"Possível perda de contexto detectada. Falhas consecutivas: {CONSECUTIVE_FAILURES}")
            
            if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                # Escalonar para atendimento humano após falhas consecutivas
                global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
                ESCALATION_NEEDED = True
                ESCALATION_REASON = "Perda de contexto detectada após múltiplas tentativas"
                ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                return generate_escalation_response()
    
    try:
        # Limitamos o histórico para evitar tokens excessivos (mantemos os últimos 10 turnos)
        if len(HISTORICO_OPENAI) > 20:
            # Mantém a primeira mensagem (sistema) e os últimos 9 turnos
            system_message = HISTORICO_OPENAI[0] if HISTORICO_OPENAI[0]["role"] == "system" else None
            HISTORICO_OPENAI = HISTORICO_OPENAI[-18:]
            if system_message:
                HISTORICO_OPENAI = [system_message] + HISTORICO_OPENAI
        
        # Constrói o sistema prompt com todas as informações relevantes
        system_prompt = f"""
        Você é o assistente virtual especializado da CarGlass, empresa líder em reparo e substituição de vidros automotivos. 
        
        DADOS DO CLIENTE:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Cor: {cliente_info['dados']['veiculo']['cor']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        DADOS DO ATENDIMENTO ATUAL:
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Status atual: {cliente_info['dados']['status']}
        - Detalhes do status: {STATUS_SERVICO.get(cliente_info['dados']['status'], "Sem detalhes adicionais")}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Data de entrada: {cliente_info['dados']['data_entrada']}
        - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
        - Loja atual: {cliente_info['dados']['loja']}
        - Valor do serviço: {cliente_info['dados']['valor_servico']}
        
        HISTÓRICO DO ATENDIMENTO:
        {json.dumps(cliente_info['dados']['historico'], indent=2, ensure_ascii=False)}
        
        INFORMAÇÕES DE GARANTIA:
        {json.dumps(GARANTIAS.get(cliente_info['dados']['tipo_servico'], {"prazo": "12 meses", "cobertura": "Padrão"}), indent=2, ensure_ascii=False)}
        
        DIRETRIZES DE ATENDIMENTO:
        1. Seja EXTREMAMENTE específico ao mencionar informações do cliente acima.
        2. Mantenha respostas concisas entre 2-4 frases, sendo direto ao ponto.
        3. Use uma linguagem cordial mas objetiva, compatível com uma empresa profissional.
        4. Nunca invente informações que não estão nos dados fornecidos.
        5. Se o cliente fizer perguntas sobre aspectos não cobertos nos dados (como mudança de loja ou cancelamento), indique que precisará transferir para um atendente humano.
        6. Sempre relate apenas a loja atual do cliente ({cliente_info['dados']['loja']}) quando perguntado sobre localização.
        7. Mencione sempre a data exata de previsão de conclusão ({cliente_info['dados']['previsao_conclusao']}) quando perguntado sobre prazos.
        8. Se o cliente perguntar "o que é" algum status, use a descrição detalhada do STATUS_SERVICO.
        9. Se o cliente parecer confuso sobre a mesma questão repetidamente, ofereça transferir para um atendente humano.
        10. Forneça sempre informações precisas e específicas sobre o caso atual, nunca genéricas.
        
        EVITE ESTES ERROS COMUNS:
        - Não fale sobre outras lojas além da CarGlass {cliente_info['dados']['loja']} sem ser explicitamente perguntado
        - Não mencione "verificar com a equipe técnica" para informações que você já possui
        - Não use expressões genéricas como "nossos especialistas" quando pode dar informações específicas
        - Não ofereça serviços adicionais não solicitados

        ### IMPORTANTE ###
        Você DEVE ser extremamente específico sobre:
        1. O status atual: "{cliente_info['dados']['status']}"
        2. A loja onde o veículo está: "{cliente_info['dados']['loja']}"
        3. A previsão de conclusão: "{cliente_info['dados']['previsao_conclusao']}"
        4. O histórico exato do atendimento com as datas
        """
        
        # Verifica se já existe uma mensagem de sistema no histórico
        if not HISTORICO_OPENAI or HISTORICO_OPENAI[0]["role"] != "system":
            HISTORICO_OPENAI = [{"role": "system", "content": system_prompt}] + HISTORICO_OPENAI
        else:
            # Atualiza a mensagem de sistema existente
            HISTORICO_OPENAI[0] = {"role": "system", "content": system_prompt}
        
        # Adiciona a pergunta atual ao histórico
        HISTORICO_OPENAI.append({"role": "user", "content": pergunta})
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=HISTORICO_OPENAI,
            max_tokens=200,
            temperature=0.5,
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona a resposta ao histórico
        HISTORICO_OPENAI.append({"role": "assistant", "content": ai_response})
        
        # Reseta contador de falhas consecutivas após resposta bem-sucedida
        CONSECUTIVE_FAILURES = 0
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        CONSECUTIVE_FAILURES += 1
        
        # Após várias falhas consecutivas, escalonar para humano
        if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
            global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Falhas técnicas consecutivas: {e}"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return generate_escalation_response()
            
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento na loja {cliente_info['dados']['loja']} e a previsão de conclusão é {cliente_info['dados']['previsao_conclusao']}.",
            f"Seu Honda Civic está na etapa de '{cliente_info['dados']['historico'][-1]['status']}' em nossa loja {cliente_info['dados']['loja']}, com previsão de conclusão para {cliente_info['dados']['previsao_conclusao']}.",
            f"A última atualização do seu atendimento foi '{cliente_info['dados']['historico'][-1]['status']}' em {cliente_info['dados']['historico'][-1]['data']}. Continuamos trabalhando para entregar seu veículo em {cliente_info['dados']['previsao_conclusao']}."
        ]
        return random.choice(fallback_responses)

# Gera resposta para escalonamento para atendente humano
def generate_escalation_response():
    return f"""
    Entendo a complexidade da sua solicitação e para melhor atendê-lo, vou transferir para um de nossos atendentes especializados.
    
    Seu protocolo de atendimento é: {ESCALATION_ID}
    
    Um atendente entrará em contato em breve através do telefone {CLIENTE_INFO['dados']['telefone']}. Você também pode ligar diretamente para nossa central: 0800-727-2327.
    
    Agradeço sua compreensão e paciência.
    """

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Inicializa as variáveis globais
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
        HISTORICO_OPENAI = []
        ESCALATION_NEEDED = False
        CONSECUTIVE_FAILURES = 0
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Log para debug
    print(f"Mensagem recebida: {user_input}")
    start_time = time.time()
    
    # Se escalonamento já foi acionado anteriormente
    if ESCALATION_NEEDED:
        # Adiciona resposta do assistente
        response = "Um atendente humano já foi solicitado e entrará em contato em breve. Você pode continuar enviando informações que serão registradas em seu protocolo."
        MENSAGENS.append({"role": "assistant", "content": response})
        return jsonify({'messages': MENSAGENS})
    
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
                Loja: {client_data['dados']['loja']}
                Previsão de conclusão: {client_data['dados']['previsao_conclusao']}
                
                Como posso ajudar você hoje?
                """
                
                # Inicializa o histórico para OpenAI
                HISTORICO_OPENAI = [
                    {"role": "assistant", "content": f"Olá {client_data['dados']['nome']}! Encontrei suas informações. Seu atendimento está com status: {client_data['dados']['status']}. O serviço de {client_data['dados']['tipo_servico']} para seu veículo {client_data['dados']['veiculo']['modelo']} está sendo realizado na loja {client_data['dados']['loja']} com previsão de conclusão para {client_data['dados']['previsao_conclusao']}."},
                    {"role": "user", "content": "Obrigado por encontrar minhas informações."}
                ]
            else:
                # Cliente não encontrado
                response = f"""
                Não consegui encontrar informações com o {tipo} fornecido.
                
                Por favor, tente novamente ou use outro identificador como CPF (11 dígitos), telefone ou placa do veículo.
                """
        else:
            # Formato inválido
            response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida. Exemplo de formato: 12345678900 (CPF), 11987654321 (telefone) ou ABC1234 (placa)."
    else:
        # Cliente já identificado, processa pergunta com IA
        response = get_ai_response(user_input, CLIENTE_INFO)
    
    # Adiciona resposta do assistente
    MENSAGENS.append({"role": "assistant", "content": response})
    
    # Log de tempo de resposta para análise de desempenho
    elapsed_time = time.time() - start_time
    print(f"Tempo de processamento da resposta: {elapsed_time:.2f} segundos")
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Limpa as variáveis globais
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    HISTORICO_OPENAI = []
    ESCALATION_NEEDED = False
    CONSECUTIVE_FAILURES = 0
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
, clean_text) or  # Formato comum: DDD + número
          re.match(r'^55\d{10,11}
    
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
                "email": "carlos.teste@exemplo.com",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "data_entrada": "18/05/2025",
                "previsao_conclusao": "19/05/2025",
                "loja": "CarGlass Paulista",
                "loja_original": "CarGlass Paulista",
                "valor_servico": "R$ 1.250,00",
                "forma_pagamento": "Cartão de Crédito",
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234",
                    "ano": "2022",
                    "cor": "Prata"
                },
                "historico": [
                    {"data": "18/05/2025 10:15", "status": "Veículo recebido na loja"},
                    {"data": "18/05/2025 14:30", "status": "Início do serviço"},
                    {"data": "19/05/2025 08:45", "status": "Parabrisa em instalação"}
                ],
                "observacoes": "Cliente solicitou prioridade na entrega"
            }
        }
    return {"sucesso": False, "mensagem": "Cliente não encontrado"}

# Verifica se a mensagem contém critérios para escalonamento
def check_escalation_needed(mensagem, cliente_info=None):
    global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
    
    mensagem_lower = mensagem.lower()
    
    # Verifica palavras-chave para escalonamento
    for criterio in ESCALATION_CRITERIA:
        if criterio in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Critério de escalonamento detectado: '{criterio}'"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica solicitações específicas de mudança
    if cliente_info and ("mudar" in mensagem_lower or "trocar" in mensagem_lower):
        if "loja" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação de mudança de loja"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica pedidos explícitos de atendente humano
    if "atendente" in mensagem_lower or "humano" in mensagem_lower or "pessoa" in mensagem_lower:
        if "falar" in mensagem_lower or "quero" in mensagem_lower or "preciso" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação explícita de atendente humano"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    return False

# Detecta perda de contexto comparando resposta anterior com pergunta atual
def detect_context_loss(pergunta, resposta_anterior):
    try:
        prompt = f"""
        Analise a seguinte interação de atendimento ao cliente:
        
        Resposta anterior do assistente: "{resposta_anterior}"
        Pergunta atual do cliente: "{pergunta}"
        
        Verifique se a pergunta do cliente está diretamente relacionada à resposta anterior e se parece que o cliente está confuso ou insatisfeito com a resposta.
        
        Escolha UMA das seguintes opções:
        1. CONTEXTUAL - A pergunta está diretamente relacionada à resposta anterior e segue naturalmente a conversa
        2. NOVO_TÓPICO - A pergunta muda para um novo tópico, mas não indica problemas com a resposta anterior
        3. CONFUSÃO - A pergunta sugere que o cliente está confuso com a resposta anterior ou está repetindo a mesma pergunta
        4. INSATISFAÇÃO - A pergunta indica que o cliente está insatisfeito com a resposta anterior
        
        Retorne apenas o número da opção sem explicação adicional.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1,
        )
        
        result = response.choices[0].message['content'].strip()
        
        if "3" in result or "4" in result:
            return True
        return False
    except Exception as e:
        print(f"Erro ao detectar perda de contexto: {e}")
        return False

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    global HISTORICO_OPENAI, CONSECUTIVE_FAILURES, ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
    
    # Verifica escalonamento por critérios
    if check_escalation_needed(pergunta, cliente_info):
        return generate_escalation_response()
    
    # Analisa o sentimento do cliente
    needs_escalation, reason = analyze_sentiment(pergunta)
    if needs_escalation:
        ESCALATION_NEEDED = True
        ESCALATION_REASON = reason
        ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        return generate_escalation_response()
    
    # Verifica se há perda de contexto apenas se houver histórico
    if len(HISTORICO_OPENAI) >= 2:
        # Pega a última resposta do assistente
        ultima_resposta = None
        for msg in reversed(HISTORICO_OPENAI):
            if msg["role"] == "assistant":
                ultima_resposta = msg["content"]
                break
        
        if ultima_resposta and detect_context_loss(pergunta, ultima_resposta):
            CONSECUTIVE_FAILURES += 1
            print(f"Possível perda de contexto detectada. Falhas consecutivas: {CONSECUTIVE_FAILURES}")
            
            if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                # Escalonar para atendimento humano após falhas consecutivas
                ESCALATION_NEEDED = True
                ESCALATION_REASON = "Perda de contexto detectada após múltiplas tentativas"
                ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                return generate_escalation_response()
    
    try:
        # Limitamos o histórico para evitar tokens excessivos (mantemos os últimos 10 turnos)
        if len(HISTORICO_OPENAI) > 20:
            # Mantém a primeira mensagem (sistema) e os últimos 9 turnos
            system_message = HISTORICO_OPENAI[0] if HISTORICO_OPENAI[0]["role"] == "system" else None
            HISTORICO_OPENAI = HISTORICO_OPENAI[-18:]
            if system_message:
                HISTORICO_OPENAI = [system_message] + HISTORICO_OPENAI
        
        # Constrói o sistema prompt com todas as informações relevantes
        system_prompt = f"""
        Você é o assistente virtual especializado da CarGlass, empresa líder em reparo e substituição de vidros automotivos. 
        
        DADOS DO CLIENTE:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Cor: {cliente_info['dados']['veiculo']['cor']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        DADOS DO ATENDIMENTO ATUAL:
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Status atual: {cliente_info['dados']['status']}
        - Detalhes do status: {STATUS_SERVICO.get(cliente_info['dados']['status'], "Sem detalhes adicionais")}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Data de entrada: {cliente_info['dados']['data_entrada']}
        - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
        - Loja atual: {cliente_info['dados']['loja']}
        - Valor do serviço: {cliente_info['dados']['valor_servico']}
        
        HISTÓRICO DO ATENDIMENTO:
        {json.dumps(cliente_info['dados']['historico'], indent=2, ensure_ascii=False)}
        
        INFORMAÇÕES DE GARANTIA:
        {json.dumps(GARANTIAS.get(cliente_info['dados']['tipo_servico'], {"prazo": "12 meses", "cobertura": "Padrão"}), indent=2, ensure_ascii=False)}
        
        DIRETRIZES DE ATENDIMENTO:
        1. Seja EXTREMAMENTE específico ao mencionar informações do cliente acima.
        2. Mantenha respostas concisas entre 2-4 frases, sendo direto ao ponto.
        3. Use uma linguagem cordial mas objetiva, compatível com uma empresa profissional.
        4. Nunca invente informações que não estão nos dados fornecidos.
        5. Se o cliente fizer perguntas sobre aspectos não cobertos nos dados (como mudança de loja ou cancelamento), indique que precisará transferir para um atendente humano.
        6. Sempre relate apenas a loja atual do cliente ({cliente_info['dados']['loja']}) quando perguntado sobre localização.
        7. Mencione sempre a data exata de previsão de conclusão ({cliente_info['dados']['previsao_conclusao']}) quando perguntado sobre prazos.
        8. Se o cliente perguntar "o que é" algum status, use a descrição detalhada do STATUS_SERVICO.
        9. Se o cliente parecer confuso sobre a mesma questão repetidamente, ofereça transferir para um atendente humano.
        10. Forneça sempre informações precisas e específicas sobre o caso atual, nunca genéricas.
        
        EVITE ESTES ERROS COMUNS:
        - Não fale sobre outras lojas além da CarGlass {cliente_info['dados']['loja']} sem ser explicitamente perguntado
        - Não mencione "verificar com a equipe técnica" para informações que você já possui
        - Não use expressões genéricas como "nossos especialistas" quando pode dar informações específicas
        - Não ofereça serviços adicionais não solicitados

        ### IMPORTANTE ###
        Você DEVE ser extremamente específico sobre:
        1. O status atual: "{cliente_info['dados']['status']}"
        2. A loja onde o veículo está: "{cliente_info['dados']['loja']}"
        3. A previsão de conclusão: "{cliente_info['dados']['previsao_conclusao']}"
        4. O histórico exato do atendimento com as datas
        """
        
        # Verifica se já existe uma mensagem de sistema no histórico
        if not HISTORICO_OPENAI or HISTORICO_OPENAI[0]["role"] != "system":
            HISTORICO_OPENAI = [{"role": "system", "content": system_prompt}] + HISTORICO_OPENAI
        else:
            # Atualiza a mensagem de sistema existente
            HISTORICO_OPENAI[0] = {"role": "system", "content": system_prompt}
        
        # Adiciona a pergunta atual ao histórico
        HISTORICO_OPENAI.append({"role": "user", "content": pergunta})
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=HISTORICO_OPENAI,
            max_tokens=200,
            temperature=0.5,
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona a resposta ao histórico
        HISTORICO_OPENAI.append({"role": "assistant", "content": ai_response})
        
        # Reseta contador de falhas consecutivas após resposta bem-sucedida
        CONSECUTIVE_FAILURES = 0
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        CONSECUTIVE_FAILURES += 1
        
        # Após várias falhas consecutivas, escalonar para humano
        if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Falhas técnicas consecutivas: {e}"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return generate_escalation_response()
            
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento na loja {cliente_info['dados']['loja']} e a previsão de conclusão é {cliente_info['dados']['previsao_conclusao']}.",
            f"Seu Honda Civic está na etapa de '{cliente_info['dados']['historico'][-1]['status']}' em nossa loja {cliente_info['dados']['loja']}, com previsão de conclusão para {cliente_info['dados']['previsao_conclusao']}.",
            f"A última atualização do seu atendimento foi '{cliente_info['dados']['historico'][-1]['status']}' em {cliente_info['dados']['historico'][-1]['data']}. Continuamos trabalhando para entregar seu veículo em {cliente_info['dados']['previsao_conclusao']}."
        ]
        return random.choice(fallback_responses)

# Gera resposta para escalonamento para atendente humano
def generate_escalation_response():
    return f"""
    Entendo a complexidade da sua solicitação e para melhor atendê-lo, vou transferir para um de nossos atendentes especializados.
    
    Seu protocolo de atendimento é: {ESCALATION_ID}
    
    Um atendente entrará em contato em breve através do telefone {CLIENTE_INFO['dados']['telefone']}. Você também pode ligar diretamente para nossa central: 0800-727-2327.
    
    Agradeço sua compreensão e paciência.
    """

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Inicializa as variáveis globais
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
        HISTORICO_OPENAI = []
        ESCALATION_NEEDED = False
        CONSECUTIVE_FAILURES = 0
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Log para debug
    print(f"Mensagem recebida: {user_input}")
    start_time = time.time()
    
    # Se escalonamento já foi acionado anteriormente
    if ESCALATION_NEEDED:
        # Adiciona resposta do assistente
        response = "Um atendente humano já foi solicitado e entrará em contato em breve. Você pode continuar enviando informações que serão registradas em seu protocolo."
        MENSAGENS.append({"role": "assistant", "content": response})
        return jsonify({'messages': MENSAGENS})
    
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
                Loja: {client_data['dados']['loja']}
                Previsão de conclusão: {client_data['dados']['previsao_conclusao']}
                
                Como posso ajudar você hoje?
                """
                
                # Inicializa o histórico para OpenAI
                HISTORICO_OPENAI = [
                    {"role": "assistant", "content": f"Olá {client_data['dados']['nome']}! Encontrei suas informações. Seu atendimento está com status: {client_data['dados']['status']}. O serviço de {client_data['dados']['tipo_servico']} para seu veículo {client_data['dados']['veiculo']['modelo']} está sendo realizado na loja {client_data['dados']['loja']} com previsão de conclusão para {client_data['dados']['previsao_conclusao']}."},
                    {"role": "user", "content": "Obrigado por encontrar minhas informações."}
                ]
            else:
                # Cliente não encontrado
                response = f"""
                Não consegui encontrar informações com o {tipo} fornecido.
                
                Por favor, tente novamente ou use outro identificador como CPF (11 dígitos), telefone ou placa do veículo.
                """
        else:
            # Formato inválido
            response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida. Exemplo de formato: 12345678900 (CPF), 11987654321 (telefone) ou ABC1234 (placa)."
    else:
        # Cliente já identificado, processa pergunta com IA
        response = get_ai_response(user_input, CLIENTE_INFO)
    
    # Adiciona resposta do assistente
    MENSAGENS.append({"role": "assistant", "content": response})
    
    # Log de tempo de resposta para análise de desempenho
    elapsed_time = time.time() - start_time
    print(f"Tempo de processamento da resposta: {elapsed_time:.2f} segundos")
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Limpa as variáveis globais
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    HISTORICO_OPENAI = []
    ESCALATION_NEEDED = False
    CONSECUTIVE_FAILURES = 0
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
, clean_text) or  # Com código do Brasil (55)
          re.match(r'^\+55\d{10,11}
    
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
                "email": "carlos.teste@exemplo.com",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "data_entrada": "18/05/2025",
                "previsao_conclusao": "19/05/2025",
                "loja": "CarGlass Paulista",
                "loja_original": "CarGlass Paulista",
                "valor_servico": "R$ 1.250,00",
                "forma_pagamento": "Cartão de Crédito",
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234",
                    "ano": "2022",
                    "cor": "Prata"
                },
                "historico": [
                    {"data": "18/05/2025 10:15", "status": "Veículo recebido na loja"},
                    {"data": "18/05/2025 14:30", "status": "Início do serviço"},
                    {"data": "19/05/2025 08:45", "status": "Parabrisa em instalação"}
                ],
                "observacoes": "Cliente solicitou prioridade na entrega"
            }
        }
    return {"sucesso": False, "mensagem": "Cliente não encontrado"}

# Verifica se a mensagem contém critérios para escalonamento
def check_escalation_needed(mensagem, cliente_info=None):
    global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
    
    mensagem_lower = mensagem.lower()
    
    # Verifica palavras-chave para escalonamento
    for criterio in ESCALATION_CRITERIA:
        if criterio in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Critério de escalonamento detectado: '{criterio}'"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica solicitações específicas de mudança
    if cliente_info and ("mudar" in mensagem_lower or "trocar" in mensagem_lower):
        if "loja" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação de mudança de loja"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica pedidos explícitos de atendente humano
    if "atendente" in mensagem_lower or "humano" in mensagem_lower or "pessoa" in mensagem_lower:
        if "falar" in mensagem_lower or "quero" in mensagem_lower or "preciso" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação explícita de atendente humano"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    return False

# Detecta perda de contexto comparando resposta anterior com pergunta atual
def detect_context_loss(pergunta, resposta_anterior):
    try:
        prompt = f"""
        Analise a seguinte interação de atendimento ao cliente:
        
        Resposta anterior do assistente: "{resposta_anterior}"
        Pergunta atual do cliente: "{pergunta}"
        
        Verifique se a pergunta do cliente está diretamente relacionada à resposta anterior e se parece que o cliente está confuso ou insatisfeito com a resposta.
        
        Escolha UMA das seguintes opções:
        1. CONTEXTUAL - A pergunta está diretamente relacionada à resposta anterior e segue naturalmente a conversa
        2. NOVO_TÓPICO - A pergunta muda para um novo tópico, mas não indica problemas com a resposta anterior
        3. CONFUSÃO - A pergunta sugere que o cliente está confuso com a resposta anterior ou está repetindo a mesma pergunta
        4. INSATISFAÇÃO - A pergunta indica que o cliente está insatisfeito com a resposta anterior
        
        Retorne apenas o número da opção sem explicação adicional.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1,
        )
        
        result = response.choices[0].message['content'].strip()
        
        if "3" in result or "4" in result:
            return True
        return False
    except Exception as e:
        print(f"Erro ao detectar perda de contexto: {e}")
        return False

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    global HISTORICO_OPENAI, CONSECUTIVE_FAILURES
    
    # Verifica escalonamento
    if check_escalation_needed(pergunta, cliente_info):
        return generate_escalation_response()
    
    # Verifica se há perda de contexto apenas se houver histórico
    if len(HISTORICO_OPENAI) >= 2:
        # Pega a última resposta do assistente
        ultima_resposta = None
        for msg in reversed(HISTORICO_OPENAI):
            if msg["role"] == "assistant":
                ultima_resposta = msg["content"]
                break
        
        if ultima_resposta and detect_context_loss(pergunta, ultima_resposta):
            CONSECUTIVE_FAILURES += 1
            print(f"Possível perda de contexto detectada. Falhas consecutivas: {CONSECUTIVE_FAILURES}")
            
            if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                # Escalonar para atendimento humano após falhas consecutivas
                global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
                ESCALATION_NEEDED = True
                ESCALATION_REASON = "Perda de contexto detectada após múltiplas tentativas"
                ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                return generate_escalation_response()
    
    try:
        # Limitamos o histórico para evitar tokens excessivos (mantemos os últimos 10 turnos)
        if len(HISTORICO_OPENAI) > 20:
            # Mantém a primeira mensagem (sistema) e os últimos 9 turnos
            system_message = HISTORICO_OPENAI[0] if HISTORICO_OPENAI[0]["role"] == "system" else None
            HISTORICO_OPENAI = HISTORICO_OPENAI[-18:]
            if system_message:
                HISTORICO_OPENAI = [system_message] + HISTORICO_OPENAI
        
        # Constrói o sistema prompt com todas as informações relevantes
        system_prompt = f"""
        Você é o assistente virtual especializado da CarGlass, empresa líder em reparo e substituição de vidros automotivos. 
        
        DADOS DO CLIENTE:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Cor: {cliente_info['dados']['veiculo']['cor']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        DADOS DO ATENDIMENTO ATUAL:
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Status atual: {cliente_info['dados']['status']}
        - Detalhes do status: {STATUS_SERVICO.get(cliente_info['dados']['status'], "Sem detalhes adicionais")}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Data de entrada: {cliente_info['dados']['data_entrada']}
        - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
        - Loja atual: {cliente_info['dados']['loja']}
        - Valor do serviço: {cliente_info['dados']['valor_servico']}
        
        HISTÓRICO DO ATENDIMENTO:
        {json.dumps(cliente_info['dados']['historico'], indent=2, ensure_ascii=False)}
        
        INFORMAÇÕES DE GARANTIA:
        {json.dumps(GARANTIAS.get(cliente_info['dados']['tipo_servico'], {"prazo": "12 meses", "cobertura": "Padrão"}), indent=2, ensure_ascii=False)}
        
        DIRETRIZES DE ATENDIMENTO:
        1. Seja EXTREMAMENTE específico ao mencionar informações do cliente acima.
        2. Mantenha respostas concisas entre 2-4 frases, sendo direto ao ponto.
        3. Use uma linguagem cordial mas objetiva, compatível com uma empresa profissional.
        4. Nunca invente informações que não estão nos dados fornecidos.
        5. Se o cliente fizer perguntas sobre aspectos não cobertos nos dados (como mudança de loja ou cancelamento), indique que precisará transferir para um atendente humano.
        6. Sempre relate apenas a loja atual do cliente ({cliente_info['dados']['loja']}) quando perguntado sobre localização.
        7. Mencione sempre a data exata de previsão de conclusão ({cliente_info['dados']['previsao_conclusao']}) quando perguntado sobre prazos.
        8. Se o cliente perguntar "o que é" algum status, use a descrição detalhada do STATUS_SERVICO.
        9. Se o cliente parecer confuso sobre a mesma questão repetidamente, ofereça transferir para um atendente humano.
        10. Forneça sempre informações precisas e específicas sobre o caso atual, nunca genéricas.
        
        EVITE ESTES ERROS COMUNS:
        - Não fale sobre outras lojas além da CarGlass {cliente_info['dados']['loja']} sem ser explicitamente perguntado
        - Não mencione "verificar com a equipe técnica" para informações que você já possui
        - Não use expressões genéricas como "nossos especialistas" quando pode dar informações específicas
        - Não ofereça serviços adicionais não solicitados

        ### IMPORTANTE ###
        Você DEVE ser extremamente específico sobre:
        1. O status atual: "{cliente_info['dados']['status']}"
        2. A loja onde o veículo está: "{cliente_info['dados']['loja']}"
        3. A previsão de conclusão: "{cliente_info['dados']['previsao_conclusao']}"
        4. O histórico exato do atendimento com as datas
        """
        
        # Verifica se já existe uma mensagem de sistema no histórico
        if not HISTORICO_OPENAI or HISTORICO_OPENAI[0]["role"] != "system":
            HISTORICO_OPENAI = [{"role": "system", "content": system_prompt}] + HISTORICO_OPENAI
        else:
            # Atualiza a mensagem de sistema existente
            HISTORICO_OPENAI[0] = {"role": "system", "content": system_prompt}
        
        # Adiciona a pergunta atual ao histórico
        HISTORICO_OPENAI.append({"role": "user", "content": pergunta})
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=HISTORICO_OPENAI,
            max_tokens=200,
            temperature=0.5,
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona a resposta ao histórico
        HISTORICO_OPENAI.append({"role": "assistant", "content": ai_response})
        
        # Reseta contador de falhas consecutivas após resposta bem-sucedida
        CONSECUTIVE_FAILURES = 0
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        CONSECUTIVE_FAILURES += 1
        
        # Após várias falhas consecutivas, escalonar para humano
        if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
            global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Falhas técnicas consecutivas: {e}"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return generate_escalation_response()
            
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento na loja {cliente_info['dados']['loja']} e a previsão de conclusão é {cliente_info['dados']['previsao_conclusao']}.",
            f"Seu Honda Civic está na etapa de '{cliente_info['dados']['historico'][-1]['status']}' em nossa loja {cliente_info['dados']['loja']}, com previsão de conclusão para {cliente_info['dados']['previsao_conclusao']}.",
            f"A última atualização do seu atendimento foi '{cliente_info['dados']['historico'][-1]['status']}' em {cliente_info['dados']['historico'][-1]['data']}. Continuamos trabalhando para entregar seu veículo em {cliente_info['dados']['previsao_conclusao']}."
        ]
        return random.choice(fallback_responses)

# Gera resposta para escalonamento para atendente humano
def generate_escalation_response():
    return f"""
    Entendo a complexidade da sua solicitação e para melhor atendê-lo, vou transferir para um de nossos atendentes especializados.
    
    Seu protocolo de atendimento é: {ESCALATION_ID}
    
    Um atendente entrará em contato em breve através do telefone {CLIENTE_INFO['dados']['telefone']}. Você também pode ligar diretamente para nossa central: 0800-727-2327.
    
    Agradeço sua compreensão e paciência.
    """

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Inicializa as variáveis globais
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
        HISTORICO_OPENAI = []
        ESCALATION_NEEDED = False
        CONSECUTIVE_FAILURES = 0
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Log para debug
    print(f"Mensagem recebida: {user_input}")
    start_time = time.time()
    
    # Se escalonamento já foi acionado anteriormente
    if ESCALATION_NEEDED:
        # Adiciona resposta do assistente
        response = "Um atendente humano já foi solicitado e entrará em contato em breve. Você pode continuar enviando informações que serão registradas em seu protocolo."
        MENSAGENS.append({"role": "assistant", "content": response})
        return jsonify({'messages': MENSAGENS})
    
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
                Loja: {client_data['dados']['loja']}
                Previsão de conclusão: {client_data['dados']['previsao_conclusao']}
                
                Como posso ajudar você hoje?
                """
                
                # Inicializa o histórico para OpenAI
                HISTORICO_OPENAI = [
                    {"role": "assistant", "content": f"Olá {client_data['dados']['nome']}! Encontrei suas informações. Seu atendimento está com status: {client_data['dados']['status']}. O serviço de {client_data['dados']['tipo_servico']} para seu veículo {client_data['dados']['veiculo']['modelo']} está sendo realizado na loja {client_data['dados']['loja']} com previsão de conclusão para {client_data['dados']['previsao_conclusao']}."},
                    {"role": "user", "content": "Obrigado por encontrar minhas informações."}
                ]
            else:
                # Cliente não encontrado
                response = f"""
                Não consegui encontrar informações com o {tipo} fornecido.
                
                Por favor, tente novamente ou use outro identificador como CPF (11 dígitos), telefone ou placa do veículo.
                """
        else:
            # Formato inválido
            response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida. Exemplo de formato: 12345678900 (CPF), 11987654321 (telefone) ou ABC1234 (placa)."
    else:
        # Cliente já identificado, processa pergunta com IA
        response = get_ai_response(user_input, CLIENTE_INFO)
    
    # Adiciona resposta do assistente
    MENSAGENS.append({"role": "assistant", "content": response})
    
    # Log de tempo de resposta para análise de desempenho
    elapsed_time = time.time() - start_time
    print(f"Tempo de processamento da resposta: {elapsed_time:.2f} segundos")
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Limpa as variáveis globais
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    HISTORICO_OPENAI = []
    ESCALATION_NEEDED = False
    CONSECUTIVE_FAILURES = 0
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
, clean_text.replace('+', ''))):  # Com + no código
        
        # Remove código do país se presente
        if clean_text.startswith('55') and len(clean_text) > 11:
            clean_text = clean_text[2:]
        
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
                "email": "carlos.teste@exemplo.com",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "data_entrada": "18/05/2025",
                "previsao_conclusao": "19/05/2025",
                "loja": "CarGlass Paulista",
                "loja_original": "CarGlass Paulista",
                "valor_servico": "R$ 1.250,00",
                "forma_pagamento": "Cartão de Crédito",
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234",
                    "ano": "2022",
                    "cor": "Prata"
                },
                "historico": [
                    {"data": "18/05/2025 10:15", "status": "Veículo recebido na loja"},
                    {"data": "18/05/2025 14:30", "status": "Início do serviço"},
                    {"data": "19/05/2025 08:45", "status": "Parabrisa em instalação"}
                ],
                "observacoes": "Cliente solicitou prioridade na entrega"
            }
        }
    return {"sucesso": False, "mensagem": "Cliente não encontrado"}

# Verifica se a mensagem contém critérios para escalonamento
def check_escalation_needed(mensagem, cliente_info=None):
    global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
    
    mensagem_lower = mensagem.lower()
    
    # Verifica palavras-chave para escalonamento
    for criterio in ESCALATION_CRITERIA:
        if criterio in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Critério de escalonamento detectado: '{criterio}'"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica solicitações específicas de mudança
    if cliente_info and ("mudar" in mensagem_lower or "trocar" in mensagem_lower):
        if "loja" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação de mudança de loja"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    # Verifica pedidos explícitos de atendente humano
    if "atendente" in mensagem_lower or "humano" in mensagem_lower or "pessoa" in mensagem_lower:
        if "falar" in mensagem_lower or "quero" in mensagem_lower or "preciso" in mensagem_lower:
            ESCALATION_NEEDED = True
            ESCALATION_REASON = "Solicitação explícita de atendente humano"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return True
    
    return False

# Detecta perda de contexto comparando resposta anterior com pergunta atual
def detect_context_loss(pergunta, resposta_anterior):
    try:
        prompt = f"""
        Analise a seguinte interação de atendimento ao cliente:
        
        Resposta anterior do assistente: "{resposta_anterior}"
        Pergunta atual do cliente: "{pergunta}"
        
        Verifique se a pergunta do cliente está diretamente relacionada à resposta anterior e se parece que o cliente está confuso ou insatisfeito com a resposta.
        
        Escolha UMA das seguintes opções:
        1. CONTEXTUAL - A pergunta está diretamente relacionada à resposta anterior e segue naturalmente a conversa
        2. NOVO_TÓPICO - A pergunta muda para um novo tópico, mas não indica problemas com a resposta anterior
        3. CONFUSÃO - A pergunta sugere que o cliente está confuso com a resposta anterior ou está repetindo a mesma pergunta
        4. INSATISFAÇÃO - A pergunta indica que o cliente está insatisfeito com a resposta anterior
        
        Retorne apenas o número da opção sem explicação adicional.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1,
        )
        
        result = response.choices[0].message['content'].strip()
        
        if "3" in result or "4" in result:
            return True
        return False
    except Exception as e:
        print(f"Erro ao detectar perda de contexto: {e}")
        return False

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    global HISTORICO_OPENAI, CONSECUTIVE_FAILURES
    
    # Verifica escalonamento
    if check_escalation_needed(pergunta, cliente_info):
        return generate_escalation_response()
    
    # Verifica se há perda de contexto apenas se houver histórico
    if len(HISTORICO_OPENAI) >= 2:
        # Pega a última resposta do assistente
        ultima_resposta = None
        for msg in reversed(HISTORICO_OPENAI):
            if msg["role"] == "assistant":
                ultima_resposta = msg["content"]
                break
        
        if ultima_resposta and detect_context_loss(pergunta, ultima_resposta):
            CONSECUTIVE_FAILURES += 1
            print(f"Possível perda de contexto detectada. Falhas consecutivas: {CONSECUTIVE_FAILURES}")
            
            if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
                # Escalonar para atendimento humano após falhas consecutivas
                global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
                ESCALATION_NEEDED = True
                ESCALATION_REASON = "Perda de contexto detectada após múltiplas tentativas"
                ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
                return generate_escalation_response()
    
    try:
        # Limitamos o histórico para evitar tokens excessivos (mantemos os últimos 10 turnos)
        if len(HISTORICO_OPENAI) > 20:
            # Mantém a primeira mensagem (sistema) e os últimos 9 turnos
            system_message = HISTORICO_OPENAI[0] if HISTORICO_OPENAI[0]["role"] == "system" else None
            HISTORICO_OPENAI = HISTORICO_OPENAI[-18:]
            if system_message:
                HISTORICO_OPENAI = [system_message] + HISTORICO_OPENAI
        
        # Constrói o sistema prompt com todas as informações relevantes
        system_prompt = f"""
        Você é o assistente virtual especializado da CarGlass, empresa líder em reparo e substituição de vidros automotivos. 
        
        DADOS DO CLIENTE:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Cor: {cliente_info['dados']['veiculo']['cor']}
        - Placa: {cliente_info['dados']['veiculo']['placa']}
        
        DADOS DO ATENDIMENTO ATUAL:
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Status atual: {cliente_info['dados']['status']}
        - Detalhes do status: {STATUS_SERVICO.get(cliente_info['dados']['status'], "Sem detalhes adicionais")}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Data de entrada: {cliente_info['dados']['data_entrada']}
        - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
        - Loja atual: {cliente_info['dados']['loja']}
        - Valor do serviço: {cliente_info['dados']['valor_servico']}
        
        HISTÓRICO DO ATENDIMENTO:
        {json.dumps(cliente_info['dados']['historico'], indent=2, ensure_ascii=False)}
        
        INFORMAÇÕES DE GARANTIA:
        {json.dumps(GARANTIAS.get(cliente_info['dados']['tipo_servico'], {"prazo": "12 meses", "cobertura": "Padrão"}), indent=2, ensure_ascii=False)}
        
        DIRETRIZES DE ATENDIMENTO:
        1. Seja EXTREMAMENTE específico ao mencionar informações do cliente acima.
        2. Mantenha respostas concisas entre 2-4 frases, sendo direto ao ponto.
        3. Use uma linguagem cordial mas objetiva, compatível com uma empresa profissional.
        4. Nunca invente informações que não estão nos dados fornecidos.
        5. Se o cliente fizer perguntas sobre aspectos não cobertos nos dados (como mudança de loja ou cancelamento), indique que precisará transferir para um atendente humano.
        6. Sempre relate apenas a loja atual do cliente ({cliente_info['dados']['loja']}) quando perguntado sobre localização.
        7. Mencione sempre a data exata de previsão de conclusão ({cliente_info['dados']['previsao_conclusao']}) quando perguntado sobre prazos.
        8. Se o cliente perguntar "o que é" algum status, use a descrição detalhada do STATUS_SERVICO.
        9. Se o cliente parecer confuso sobre a mesma questão repetidamente, ofereça transferir para um atendente humano.
        10. Forneça sempre informações precisas e específicas sobre o caso atual, nunca genéricas.
        
        EVITE ESTES ERROS COMUNS:
        - Não fale sobre outras lojas além da CarGlass {cliente_info['dados']['loja']} sem ser explicitamente perguntado
        - Não mencione "verificar com a equipe técnica" para informações que você já possui
        - Não use expressões genéricas como "nossos especialistas" quando pode dar informações específicas
        - Não ofereça serviços adicionais não solicitados

        ### IMPORTANTE ###
        Você DEVE ser extremamente específico sobre:
        1. O status atual: "{cliente_info['dados']['status']}"
        2. A loja onde o veículo está: "{cliente_info['dados']['loja']}"
        3. A previsão de conclusão: "{cliente_info['dados']['previsao_conclusao']}"
        4. O histórico exato do atendimento com as datas
        """
        
        # Verifica se já existe uma mensagem de sistema no histórico
        if not HISTORICO_OPENAI or HISTORICO_OPENAI[0]["role"] != "system":
            HISTORICO_OPENAI = [{"role": "system", "content": system_prompt}] + HISTORICO_OPENAI
        else:
            # Atualiza a mensagem de sistema existente
            HISTORICO_OPENAI[0] = {"role": "system", "content": system_prompt}
        
        # Adiciona a pergunta atual ao histórico
        HISTORICO_OPENAI.append({"role": "user", "content": pergunta})
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=HISTORICO_OPENAI,
            max_tokens=200,
            temperature=0.5,
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona a resposta ao histórico
        HISTORICO_OPENAI.append({"role": "assistant", "content": ai_response})
        
        # Reseta contador de falhas consecutivas após resposta bem-sucedida
        CONSECUTIVE_FAILURES = 0
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        CONSECUTIVE_FAILURES += 1
        
        # Após várias falhas consecutivas, escalonar para humano
        if CONSECUTIVE_FAILURES >= MAX_FAILURES_BEFORE_ESCALATION:
            global ESCALATION_NEEDED, ESCALATION_REASON, ESCALATION_ID
            ESCALATION_NEEDED = True
            ESCALATION_REASON = f"Falhas técnicas consecutivas: {e}"
            ESCALATION_ID = f"ESC-{uuid.uuid4().hex[:8].upper()}"
            return generate_escalation_response()
            
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento na loja {cliente_info['dados']['loja']} e a previsão de conclusão é {cliente_info['dados']['previsao_conclusao']}.",
            f"Seu Honda Civic está na etapa de '{cliente_info['dados']['historico'][-1]['status']}' em nossa loja {cliente_info['dados']['loja']}, com previsão de conclusão para {cliente_info['dados']['previsao_conclusao']}.",
            f"A última atualização do seu atendimento foi '{cliente_info['dados']['historico'][-1]['status']}' em {cliente_info['dados']['historico'][-1]['data']}. Continuamos trabalhando para entregar seu veículo em {cliente_info['dados']['previsao_conclusao']}."
        ]
        return random.choice(fallback_responses)

# Gera resposta para escalonamento para atendente humano
def generate_escalation_response():
    return f"""
    Entendo a complexidade da sua solicitação e para melhor atendê-lo, vou transferir para um de nossos atendentes especializados.
    
    Seu protocolo de atendimento é: {ESCALATION_ID}
    
    Um atendente entrará em contato em breve através do telefone {CLIENTE_INFO['dados']['telefone']}. Você também pode ligar diretamente para nossa central: 0800-727-2327.
    
    Agradeço sua compreensão e paciência.
    """

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Inicializa as variáveis globais
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
        HISTORICO_OPENAI = []
        ESCALATION_NEEDED = False
        CONSECUTIVE_FAILURES = 0
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Log para debug
    print(f"Mensagem recebida: {user_input}")
    start_time = time.time()
    
    # Se escalonamento já foi acionado anteriormente
    if ESCALATION_NEEDED:
        # Adiciona resposta do assistente
        response = "Um atendente humano já foi solicitado e entrará em contato em breve. Você pode continuar enviando informações que serão registradas em seu protocolo."
        MENSAGENS.append({"role": "assistant", "content": response})
        return jsonify({'messages': MENSAGENS})
    
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
                Loja: {client_data['dados']['loja']}
                Previsão de conclusão: {client_data['dados']['previsao_conclusao']}
                
                Como posso ajudar você hoje?
                """
                
                # Inicializa o histórico para OpenAI
                HISTORICO_OPENAI = [
                    {"role": "assistant", "content": f"Olá {client_data['dados']['nome']}! Encontrei suas informações. Seu atendimento está com status: {client_data['dados']['status']}. O serviço de {client_data['dados']['tipo_servico']} para seu veículo {client_data['dados']['veiculo']['modelo']} está sendo realizado na loja {client_data['dados']['loja']} com previsão de conclusão para {client_data['dados']['previsao_conclusao']}."},
                    {"role": "user", "content": "Obrigado por encontrar minhas informações."}
                ]
            else:
                # Cliente não encontrado
                response = f"""
                Não consegui encontrar informações com o {tipo} fornecido.
                
                Por favor, tente novamente ou use outro identificador como CPF (11 dígitos), telefone ou placa do veículo.
                """
        else:
            # Formato inválido
            response = "Por favor, forneça um CPF (11 dígitos), telefone ou placa válida. Exemplo de formato: 12345678900 (CPF), 11987654321 (telefone) ou ABC1234 (placa)."
    else:
        # Cliente já identificado, processa pergunta com IA
        response = get_ai_response(user_input, CLIENTE_INFO)
    
    # Adiciona resposta do assistente
    MENSAGENS.append({"role": "assistant", "content": response})
    
    # Log de tempo de resposta para análise de desempenho
    elapsed_time = time.time() - start_time
    print(f"Tempo de processamento da resposta: {elapsed_time:.2f} segundos")
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, HISTORICO_OPENAI, ESCALATION_NEEDED, CONSECUTIVE_FAILURES
    
    # Limpa as variáveis globais
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    HISTORICO_OPENAI = []
    ESCALATION_NEEDED = False
    CONSECUTIVE_FAILURES = 0
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
