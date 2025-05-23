"""
Aplicação principal do Assistente Virtual CarGlass - Versão 2.0
Otimizada para Render com fallback completo em memória
"""
import os
import logging
import traceback
import time
import uuid
import random
import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from functools import wraps
import json

from flask import Flask, render_template, request, jsonify, session

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== CONFIGURAÇÃO =====
@dataclass
class Config:
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'carglass-secreto-render-key')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4-turbo')
    CARGLASS_API_URL: str = os.getenv('CARGLASS_API_URL', 'http://10.10.100.240:3000/api/status')
    USE_REAL_API: bool = os.getenv('USE_REAL_API', 'true').lower() == 'true'
    SESSION_TIMEOUT: int = int(os.getenv('SESSION_TIMEOUT', '1800'))
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '300'))

config = Config()

# ===== UTILITÁRIOS =====
def get_current_time() -> str:
    return time.strftime("%H:%M")

def get_current_datetime() -> str:
    return time.strftime("%d/%m/%Y - %H:%M")

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    return text

def validate_cpf(cpf: str) -> bool:
    if not cpf or len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        return False
    
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == digito2

def detect_identifier_type(text: str) -> Tuple[Optional[str], str]:
    if not text:
        return None, ""
    
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
    logger.info(f"Detectando tipo para: '{clean_text[:4]}***'")
    
    if re.match(r'^\d{11}$', clean_text):
        if validate_cpf(clean_text):
            return "cpf", clean_text
        else:
            return None, clean_text
    elif re.match(r'^\d{10,11}$', clean_text):
        return "telefone", clean_text
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        return "placa", clean_text.upper()
    elif re.match(r'^\d{1,8}$', clean_text):
        return "ordem", clean_text
    
    return None, clean_text

# ===== CACHE EM MEMÓRIA =====
class MemoryCache:
    def __init__(self):
        self.cache = {}
        self.max_items = 1000
    
    def get(self, key: str) -> Any:
        item = self.cache.get(key)
        if item and item['expires'] > time.time():
            return item['value']
        elif item:
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        if len(self.cache) >= self.max_items:
            # Remove 20% dos itens mais antigos
            old_keys = list(self.cache.keys())[:int(self.max_items * 0.2)]
            for old_key in old_keys:
                del self.cache[old_key]
        
        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]

cache = MemoryCache()

# ===== SESSÕES =====
@dataclass
class SessionData:
    session_id: str
    created_at: float
    last_activity: float
    client_identified: bool
    client_info: Optional[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT
    
    def update_activity(self):
        self.last_activity = time.time()
    
    def add_message(self, role: str, content: str):
        message = {
            "role": role,
            "content": content,
            "time": get_current_time()
        }
        self.messages.append(message)
        self.update_activity()

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self) -> SessionData:
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        session_data = SessionData(
            session_id=session_id,
            created_at=current_time,
            last_activity=current_time,
            client_identified=False,
            client_info=None,
            messages=[]
        )
        
        session_data.add_message(
            "assistant",
            "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        )
        
        self.sessions[session_id] = session_data
        self._cleanup_expired()
        return session_data
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        if not session_id:
            return None
        
        session_data = self.sessions.get(session_id)
        if session_data and not session_data.is_expired():
            session_data.update_activity()
            return session_data
        elif session_data:
            del self.sessions[session_id]
        
        return None
    
    def _cleanup_expired(self):
        current_time = time.time()
        expired = [sid for sid, data in self.sessions.items() 
                  if current_time - data.last_activity > config.SESSION_TIMEOUT]
        for sid in expired:
            del self.sessions[sid]

session_manager = SessionManager()

# ===== API CLIENT =====
def get_client_data(tipo: str, valor: str) -> Dict[str, Any]:
    cache_key = f"client:{tipo}:{valor}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    if config.USE_REAL_API:
        import requests
        try:
            endpoint = f"{config.CARGLASS_API_URL}/{tipo}/{valor}"
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                cache.set(cache_key, data, config.CACHE_TTL)
                return data
        except Exception as e:
            logger.warning(f"API falhou, usando mock: {e}")
    
    # Dados mockados
    mock_data = get_mock_data(tipo, valor)
    cache.set(cache_key, mock_data, config.CACHE_TTL)
    return mock_data

def get_mock_data(tipo: str, valor: str) -> Dict[str, Any]:
    mock_database = {
        "12345678900": {
            "sucesso": True,
            "dados": {
                "nome": "Carlos Silva",
                "cpf": "12345678900",
                "telefone": "11987654321",
                "ordem": "ORD12345",
                "status": "Em andamento",
                "tipo_servico": "Troca de Parabrisa",
                "veiculo": {"modelo": "Honda Civic", "placa": "ABC1234", "ano": "2022"}
            }
        },
        "98765432100": {
            "sucesso": True,
            "dados": {
                "nome": "Maria Santos",
                "cpf": "98765432100",
                "telefone": "11976543210",
                "ordem": "ORD67890",
                "status": "Serviço agendado com sucesso",
                "tipo_servico": "Reparo de Trinca",
                "veiculo": {"modelo": "Toyota Corolla", "placa": "DEF5678", "ano": "2021"}
            }
        }
    }
    
    # Mapeamentos
    ordem_para_cpf = {"123456": "12345678900", "ORD12345": "12345678900"}
    telefone_para_cpf = {"11987654321": "12345678900"}
    placa_para_cpf = {"ABC1234": "12345678900"}
    
    cpf_key = None
    if tipo == "cpf" and valor in mock_database:
        cpf_key = valor
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf_key = ordem_para_cpf[valor]
    elif tipo == "telefone" and valor in telefone_para_cpf:
        cpf_key = telefone_para_cpf[valor]
    elif tipo == "placa" and valor in placa_para_cpf:
        cpf_key = placa_para_cpf[valor]
    
    if cpf_key:
        return mock_database[cpf_key]
    
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}"}

# ===== BARRA DE PROGRESSO =====
def get_progress_bar_html(client_data: Dict[str, Any]) -> str:
    status = client_data['dados']['status']
    current_time = get_current_datetime()
    
    steps = [
        {"label": "Ordem Aberta", "state": "pending"},
        {"label": "Aguardando Fotos", "state": "pending"},
        {"label": "Peça Identificada", "state": "pending"},
        {"label": "Agendado", "state": "pending"},
        {"label": "Execução", "state": "pending"},
        {"label": "Inspeção", "state": "pending"},
        {"label": "Concluído", "state": "pending"}
    ]
    
    status_mapping = {
        "Ordem de Serviço Aberta": (0, "0%", "aberta"),
        "Aguardando fotos para liberação da ordem": (1, "14%", "aguardando"),
        "Fotos Recebidas": (1, "28%", "recebidas"),
        "Peça Identificada": (2, "42%", "identificada"),
        "Ordem de Serviço Liberada": (3, "57%", "liberada"),
        "Serviço agendado com sucesso": (3, "57%", "agendado"),
        "Em andamento": (4, "71%", "andamento"),
        "Concluído": (6, "100%", "concluido")
    }
    
    active_step, progress_percentage, status_class = status_mapping.get(status, (0, "0%", "desconhecido"))
    
    # Configura estados das etapas
    for i, step in enumerate(steps):
        if i < active_step:
            step["state"] = "completed"
        elif i == active_step:
            step["state"] = "active"
        elif i == active_step + 1 and active_step < len(steps) - 1:
            step["state"] = "next"
    
    # Gera HTML
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
    
    return f'''
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

# ===== AI SERVICE =====
def get_ai_response(pergunta: str, cliente_info: Dict[str, Any]) -> str:
    pergunta_lower = pergunta.lower()
    
    # Respostas predefinidas
    if any(keyword in pergunta_lower for keyword in ['loja', 'local', 'onde', 'endereço']):
        return """
        🏪 **Lojas CarGlass próximas:**
        
        • **CarGlass Morumbi**: Av. Professor Francisco Morato, 2307 - Butantã
        • **CarGlass Vila Mariana**: Rua Domingos de Morais, 1267 - Vila Mariana
        • **CarGlass Santo André**: Av. Industrial, 600 - Santo André
        
        📞 Para mudar local: **0800-727-2327**
        """
    
    if any(keyword in pergunta_lower for keyword in ['garantia', 'seguro']):
        tipo_servico = cliente_info.get('dados', {}).get('tipo_servico', 'seu serviço')
        return f"""
        🛡️ **Garantia CarGlass** para {tipo_servico}:
        
        ✅ **12 meses** a partir da conclusão
        ✅ Cobre defeitos de instalação
        ✅ Válida em qualquer unidade CarGlass
        
        📞 Central: **0800-727-2327**
        """
    
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente']):
        return """
        👥 **Falar com nossa equipe:**
        
        📞 **Central:** 0800-727-2327
        📱 **WhatsApp:** (11) 4003-8070
        
        ⏰ **Horário:**
        • Segunda a Sexta: 8h às 20h
        • Sábado: 8h às 16h
        """
    
    # Fallback usando OpenAI ou genérico
    if config.OPENAI_API_KEY:
        try:
            import openai
            openai.api_key = config.OPENAI_API_KEY
            
            dados = cliente_info.get('dados', {})
            system_message = f"""
            Você é Clara, assistente virtual da CarGlass. Cliente: {dados.get('nome', 'Cliente')}
            Status: {dados.get('status', 'N/A')}
            Serviço: {dados.get('tipo_servico', 'N/A')}
            
            Seja simpática e objetiva. Central: 0800-727-2327
            """
            
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": pergunta}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message['content'].strip()
        except Exception as e:
            logger.error(f"OpenAI erro: {e}")
    
    # Fallback genérico
    nome = cliente_info.get('dados', {}).get('nome', 'Cliente')
    return f"Entendi sua pergunta, {nome}. Para informações específicas, entre em contato: 📞 **0800-727-2327**"

# ===== FLASK APP =====
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

@app.route('/')
def index():
    try:
        session_id = session.get('session_id')
        if not session_id:
            session_data = session_manager.create_session()
            session['session_id'] = session_data.session_id
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Erro na página inicial: {e}")
        return render_template('index.html'), 500

@app.route('/get_messages')
def get_messages():
    try:
        session_id = session.get('session_id')
        if not session_id:
            session_data = session_manager.create_session()
            session['session_id'] = session_data.session_id
        else:
            session_data = session_manager.get_session(session_id)
            if not session_data:
                session_data = session_manager.create_session()
                session['session_id'] = session_data.session_id
        
        return jsonify({"messages": session_data.messages})
    except Exception as e:
        logger.error(f"Erro ao recuperar mensagens: {e}")
        return jsonify({
            "messages": [{
                "role": "assistant",
                "content": "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos.",
                "time": get_current_time()
            }]
        })

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        user_input = sanitize_input(request.form.get('message', ''))
        
        session_id = session.get('session_id')
        session_data = session_manager.get_session(session_id)
        
        if not session_data:
            session_data = session_manager.create_session()
            session['session_id'] = session_data.session_id
        
        session_data.add_message("user", user_input)
        
        if not session_data.client_identified:
            response = process_identification(user_input, session_data)
        else:
            response = get_ai_response(user_input, session_data.client_info)
        
        session_data.add_message("assistant", response)
        
        return jsonify({'messages': session_data.messages})
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return jsonify({
            'messages': [{
                "role": "assistant",
                "content": "Desculpe, ocorreu um erro. Nossa equipe foi notificada. Tente novamente em instantes.",
                "time": get_current_time()
            }]
        }), 500

def process_identification(user_input: str, session_data: SessionData) -> str:
    tipo, valor = detect_identifier_type(user_input)
    
    if not tipo:
        return """
        Por favor, forneça um identificador válido:
        
        📋 **CPF** (11 dígitos)
        📱 **Telefone** (10 ou 11 dígitos)
        🚗 **Placa do veículo**
        🔢 **Número da ordem de serviço**
        """
    
    client_data = get_client_data(tipo, valor)
    
    if not client_data.get('sucesso'):
        return f"""
        ❌ **Não encontrei informações** com o {tipo} fornecido.
        
        **Você pode tentar:**
        • Verificar se digitou corretamente
        • Usar outro identificador
        • Entrar em contato: **📞 0800-727-2327**
        """
    
    session_data.client_identified = True
    session_data.client_info = client_data
    
    dados = client_data['dados']
    nome = dados.get('nome', 'Cliente')
    status = dados.get('status', 'Em processamento')
    
    status_class = "agendado" if "agendado" in status.lower() else "andamento"
    status_tag = f'<span class="status-tag {status_class}">{status}</span>'
    
    progress_bar = get_progress_bar_html(client_data)
    
    return f"""
    👋 **Olá {nome}!** Encontrei suas informações.
    
    **Status:** {status_tag}
    
    {progress_bar}
    
    📋 **Resumo:**
    • **Ordem:** {dados.get('ordem', 'N/A')}
    • **Serviço:** {dados.get('tipo_servico', 'N/A')}
    • **Veículo:** {dados.get('veiculo', {}).get('modelo', 'N/A')} ({dados.get('veiculo', {}).get('ano', 'N/A')})
    • **Placa:** {dados.get('veiculo', {}).get('placa', 'N/A')}
    
    💬 **Como posso ajudar?**
    """

@app.route('/reset', methods=['POST'])
def reset():
    try:
        session_id = session.get('session_id')
        if session_id and session_id in session_manager.sessions:
            del session_manager.sessions[session_id]
        
        session_data = session_manager.create_session()
        session['session_id'] = session_data.session_id
        
        return jsonify({'messages': session_data.messages})
    except Exception as e:
        logger.error(f"Erro ao reiniciar: {e}")
        return jsonify({'error': 'Erro ao reiniciar'}), 500

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": get_current_time(),
        "sessions": len(session_manager.sessions),
        "cache_items": len(cache.cache)
    })

if __name__ == '__main__':
    logger.info("🚀 CarGlass Assistant v2.0 iniciando...")
    logger.info(f"Modo API: {'REAL' if config.USE_REAL_API else 'SIMULAÇÃO'}")
    logger.info(f"OpenAI: {'CONFIGURADO' if config.OPENAI_API_KEY else 'FALLBACK'}")
    
    app.run(debug=config.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
