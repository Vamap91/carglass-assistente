from flask import Flask, render_template, request, jsonify
import random
import re
import os
import openai
import json
import time

app = Flask(__name__)
app.secret_key = 'carglass-secreto'

# Configuração da OpenAI API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY

# Lista para armazenar mensagens (em uma aplicação real, usaria banco de dados)
MENSAGENS = []

# Estado de identificação do cliente
CLIENTE_IDENTIFICADO = False
CLIENTE_INFO = None

# Histórico de conversação para contexto
CONVERSA_HISTORICA = []

# Exemplos de perguntas e respostas para orientar o modelo
EXEMPLOS_PERGUNTAS_RESPOSTAS = [
    {
        "pergunta": "Quando meu carro ficará pronto?",
        "resposta": "Seu serviço de Troca de Parabrisa está em andamento. Pela nossa estimativa, o veículo deve ficar pronto ainda hoje. Posso verificar mais detalhes com nossa equipe técnica se precisar de um horário mais específico."
    },
    {
        "pergunta": "Qual a garantia do serviço?",
        "resposta": "A garantia do serviço de Troca de Parabrisa é de 12 meses a partir da data de conclusão. Ela cobre problemas relacionados à instalação como infiltrações e vedação. Manteremos seu histórico em nosso sistema caso precise acionar a garantia no futuro."
    },
    {
        "pergunta": "Posso trocar o local de entrega?",
        "resposta": "Sim, podemos alterar o local de entrega do seu veículo. Para isso, precisamos verificar a disponibilidade com nossa equipe logística. Você prefere retirar em outra loja ou gostaria de entrega em algum endereço específico? Por favor, informe o endereço desejado para eu verificar a possibilidade."
    },
    {
        "pergunta": "Qual a loja mais próxima?",
        "resposta": "A loja CarGlass mais próxima de você fica na Av. Paulista, 1000 - São Paulo. O horário de funcionamento é das 8h às 18h de segunda a sexta, e das 9h às 13h aos sábados. Deseja que eu agende um horário para você?"
    }
]

# Lojas CarGlass (fictícias)
LOJAS_CARGLASS = [
    {
        "nome": "CarGlass Paulista",
        "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
        "telefone": "(11) 3456-7890",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h"
    },
    {
        "nome": "CarGlass Morumbi",
        "endereco": "Av. Morumbi, 2000 - Morumbi, São Paulo - SP",
        "telefone": "(11) 3456-7891",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h"
    },
    {
        "nome": "CarGlass Tatuapé",
        "endereco": "Rua Tuiuti, 1500 - Tatuapé, São Paulo - SP",
        "telefone": "(11) 3456-7892",
        "horario": "Seg-Sex: 8h às 18h, Sáb: 9h às 13h"
    }
]

# Informações sobre serviços
SERVICOS_INFO = {
    "Troca de Parabrisa": {
        "garantia": "12 meses",
        "tempo_medio": "4 horas",
        "descricao": "Substituição completa do parabrisa com materiais homologados e vedação de alta qualidade."
    },
    "Reparo de Trinca": {
        "garantia": "6 meses",
        "tempo_medio": "1 hora",
        "descricao": "Reparo de trincas de até 10cm utilizando resina especial que restaura a resistência do vidro."
    },
    "Troca de Vidro Lateral": {
        "garantia": "12 meses",
        "tempo_medio": "2 horas",
        "descricao": "Substituição do vidro lateral com material original ou similar aprovado."
    }
}

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
                "email": "carlos.teste@exemplo.com",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "data_entrada": "18/05/2025",
                "previsao_conclusao": "19/05/2025",
                "loja": "CarGlass Paulista",
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

# Analisa a intenção da pergunta do usuário
def analisar_intencao(pergunta):
    try:
        prompt = f"""
        Analise a pergunta do cliente e determine a intenção principal.
        
        Pergunta: "{pergunta}"
        
        Escolha uma das seguintes categorias:
        1. Status do atendimento (andamento, conclusão, prazo)
        2. Informação do veículo (detalhes, documentos necessários)
        3. Garantia e pós-serviço (prazo, condições)
        4. Pagamento (valores, métodos, parcelamento)
        5. Localização e horários (lojas próximas, funcionamento)
        6. Alteração de serviço (mudança de escopo, adicionais)
        7. Agendamento (marcar, remarcar)
        8. Reclamação ou problema
        9. Saudação ou conversa casual
        10. Outro

        Retorne apenas o número da categoria identificada e uma breve justificativa.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.2,
        )
        
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(f"Erro ao analisar intenção: {e}")
        return "9"  # Fallback para conversa casual

# Gera resposta contextualizada usando a OpenAI API
def get_ai_response(pergunta, cliente_info):
    global CONVERSA_HISTORICA
    
    try:
        # Limitamos o histórico para evitar tokens excessivos
        if len(CONVERSA_HISTORICA) > 10:
            CONVERSA_HISTORICA = CONVERSA_HISTORICA[-10:]
        
        # Análise da intenção para direcionar a resposta
        intencao = analisar_intencao(pergunta)
        print(f"Intenção detectada: {intencao}")
        
        # Preparar informações extras baseadas na intenção
        info_extra = ""
        if "1" in intencao:  # Status
            info_extra = f"""
            Detalhes adicionais do status:
            - Data de entrada: {cliente_info['dados']['data_entrada']}
            - Previsão de conclusão: {cliente_info['dados']['previsao_conclusao']}
            - Histórico recente: {json.dumps(cliente_info['dados']['historico'][-1]) if cliente_info['dados'].get('historico') else 'Não disponível'}
            """
        elif "3" in intencao:  # Garantia
            servico = cliente_info['dados']['tipo_servico']
            if servico in SERVICOS_INFO:
                info_extra = f"""
                Detalhes do serviço {servico}:
                - Garantia: {SERVICOS_INFO[servico]['garantia']}
                - Descrição: {SERVICOS_INFO[servico]['descricao']}
                """
        elif "5" in intencao:  # Localização
            info_extra = f"""
            Detalhes de lojas próximas:
            {json.dumps(LOJAS_CARGLASS, indent=2)}
            """
        
        # Constrói o prompt para a OpenAI API com contexto do cliente
        system_message = f"""
        Você é o assistente virtual da CarGlass, especializado em atendimento ao cliente sobre serviços de vidros automotivos.
        
        DADOS DO CLIENTE E ATENDIMENTO:
        - Nome: {cliente_info['dados']['nome']}
        - Veículo: {cliente_info['dados']['veiculo']['modelo']} ({cliente_info['dados']['veiculo']['ano']}) - Placa: {cliente_info['dados']['veiculo']['placa']}
        - Status atual: {cliente_info['dados']['status']}
        - Ordem de serviço: {cliente_info['dados']['ordem']}
        - Tipo de serviço: {cliente_info['dados']['tipo_servico']}
        - Loja: {cliente_info['dados'].get('loja', 'CarGlass Paulista')}
        - Valor: {cliente_info['dados'].get('valor_servico', 'Não disponível')}
        
        {info_extra}
        
        INSTRUÇÕES DE RESPOSTA:
        1. Seja cordial, claro e objetivo.
        2. Personalize as respostas usando o nome do cliente e dados do veículo quando apropriado.
        3. Não invente informações que não estão nos dados fornecidos.
        4. Se o cliente perguntar sobre algo específico que não consta nos dados, explique que precisa verificar com a equipe técnica.
        5. Para dúvidas sobre prazos não informados, oriente a ligar para 0800-727-2327.
        6. Use linguagem simples e direta, explicando termos técnicos quando necessário.
        7. Suas respostas devem ter entre 2-4 frases, sendo concisas e diretas ao ponto.
        
        EXEMPLOS DE RESPOSTAS ADEQUADAS:
        {json.dumps(EXEMPLOS_PERGUNTAS_RESPOSTAS, indent=2, ensure_ascii=False)}
        
        HISTÓRICO DA CONVERSA:
        {json.dumps(CONVERSA_HISTORICA, indent=2, ensure_ascii=False)}
        """
        
        # Chamada para a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": pergunta}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        # Extrai a resposta
        ai_response = response.choices[0].message['content'].strip()
        
        # Adiciona à conversa histórica
        CONVERSA_HISTORICA.append({"role": "user", "content": pergunta})
        CONVERSA_HISTORICA.append({"role": "assistant", "content": ai_response})
        
        return ai_response
        
    except Exception as e:
        print(f"Erro ao chamar a API OpenAI: {e}")
        # Respostas de fallback em caso de erro na API
        fallback_responses = [
            f"Olá! Seu serviço de {cliente_info['dados']['tipo_servico']} está em andamento. Nossa equipe está trabalhando para entregar o melhor resultado.",
            f"Seu veículo {cliente_info['dados']['veiculo']['modelo']} está sendo atendido por nossa equipe técnica especializada.",
            "A loja mais próxima fica na Av. Paulista, 1000 - São Paulo. Funciona das 8h às 18h.",
            f"A garantia do serviço de {cliente_info['dados']['tipo_servico']} é de 12 meses a partir da data de conclusão."
        ]
        return random.choice(fallback_responses)

# Rota da página inicial
@app.route('/')
def index():
    global MENSAGENS, CONVERSA_HISTORICA
    
    # Inicializa as mensagens, se estiverem vazias
    if not MENSAGENS:
        MENSAGENS = [{
            "role": "assistant", 
            "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        }]
        CONVERSA_HISTORICA = []
    
    return render_template('index.html')

# Rota para obter mensagens
@app.route('/get_messages')
def get_messages():
    return jsonify({"messages": MENSAGENS})

# Rota para processar mensagens
@app.route('/send_message', methods=['POST'])
def send_message():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, CONVERSA_HISTORICA
    
    user_input = request.form.get('message', '')
    
    # Adiciona mensagem do usuário
    MENSAGENS.append({"role": "user", "content": user_input})
    
    # Log para debug
    print(f"Mensagem recebida: {user_input}")
    start_time = time.time()
    
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
                
                # Inicializa a conversa histórica
                CONVERSA_HISTORICA = [
                    {"role": "assistant", "content": f"Olá {client_data['dados']['nome']}! Encontrei suas informações do atendimento com status: {client_data['dados']['status']}"},
                    {"role": "user", "content": "Obrigado por encontrar minhas informações."}
                ]
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
    
    # Log de tempo de resposta para análise de desempenho
    elapsed_time = time.time() - start_time
    print(f"Tempo de processamento da resposta: {elapsed_time:.2f} segundos")
    
    return jsonify({
        'messages': MENSAGENS
    })

# Rota para reiniciar conversa
@app.route('/reset', methods=['POST'])
def reset():
    global MENSAGENS, CLIENTE_IDENTIFICADO, CLIENTE_INFO, CONVERSA_HISTORICA
    
    # Limpa as mensagens
    MENSAGENS = [{
        "role": "assistant", 
        "content": "Olá! Sou o assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
    }]
    CLIENTE_IDENTIFICADO = False
    CLIENTE_INFO = None
    CONVERSA_HISTORICA = []
    
    return jsonify({
        'messages': MENSAGENS
    })

if __name__ == '__main__':
    app.run(debug=True)
