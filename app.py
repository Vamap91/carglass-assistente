"""
Aplicação principal do Assistente Virtual CarGlass - Versão 2.0
Otimizada para Render com fallback completo em memória + Integração Twilio WhatsApp
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
    
    # Configurações Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER: str = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    TWILIO_ENABLED: bool = bool(os.getenv('TWILIO_ACCOUNT_SID'))

config = Config()

# ===== TWILIO WHATSAPP HANDLER =====
class TwilioWhatsAppHandler:
    def __init__(self):
        self.account_sid = config.TWILIO_ACCOUNT_SID
        self.auth_token = config.TWILIO_AUTH_TOKEN
        self.whatsapp_number = config.TWILIO_WHATSAPP_NUMBER
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                from twilio.twiml.messaging_response import MessagingResponse
                self.client = Client(self.account_sid, self.auth_token)
                self.MessagingResponse = MessagingResponse
                logger.info("✅ Twilio WhatsApp handler inicializado com sucesso")
            except ImportError:
                logger.error("❌ Biblioteca Twilio não instalada. Execute: pip install twilio")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Twilio: {e}")
        else:
            logger.warning("⚠️ Credenciais Twilio não configuradas - WhatsApp desabilitado")
    
    def is_enabled(self) -> bool:
        """Verifica se o Twilio está configurado e habilitado"""
        return self.client is not None
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Envia mensagem WhatsApp via Twilio
        
        Args:
            to_number: Número do destinatário (formato: +5511987654321 ou 5511987654321)
            message: Texto da mensagem
            
        Returns:
            bool: True se enviou com sucesso, False caso contrário
        """
        if not self.is_enabled():
            logger.error("Twilio não está habilitado")
            return False
        
        try:
            # Formata número para WhatsApp
            clean_number = re.sub(r'[^\d+]', '', to_number)
            if not clean_number.startswith('+'):
                if clean_number.startswith('55'):
                    clean_number = '+' + clean_number
                else:
                    clean_number = '+55' + clean_number
            
            whatsapp_to = f"whatsapp:{clean_number}"
            
            # Limita tamanho da mensagem (Twilio limit: 1600 chars)
            if len(message) > 1500:
                message = message[:1500] + "...\n\n📱 *Continue no link:*\nhttps://carglass-assistente.onrender.com"
            
            # Envia mensagem
            message_instance = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=whatsapp_to
            )
            
            logger.info(f"✅ Mensagem Twilio enviada: {message_instance.sid} para {whatsapp_to}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem Twilio: {e}")
            return False
    
    def process_incoming_message(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processa mensagem recebida do webhook Twilio
        
        Args:
            request_data: Dados do webhook Twilio (request.form ou dict)
            
        Returns:
            dict: Dados processados da mensagem ou None se erro
        """
        try:
            # Extrai dados da mensagem
            from_number = request_data.get('From', '').replace('whatsapp:', '').replace('+', '')
            message_body = request_data.get('Body', '').strip()
            message_sid = request_data.get('MessageSid', '')
            
            # Limpa número (remove código do país se necessário)
            if from_number.startswith('55') and len(from_number) > 11:
                from_number = from_number[2:]  # Remove +55
            
            logger.info(f"📱 WhatsApp recebido de {from_number[:4]}***: {message_body[:50]}...")
            
            return {
                'phone': from_number,
                'message': message_body,
                'message_id': message_sid,
                'platform': 'whatsapp',
                'raw_data': dict(request_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem WhatsApp: {e}")
            return None
    
    def create_twiml_response(self, message: str = None) -> str:
        """
        Cria resposta TwiML (opcional - para resposta imediata)
        
        Args:
            message: Mensagem de resposta (opcional)
            
        Returns:
            str: XML TwiML
        """
        if not self.is_enabled():
            return ""
        
        try:
            response = self.MessagingResponse()
            if message:
                response.message(message)
            return str(response)
        except:
            return ""

# Instância global do handler Twilio
twilio_handler = TwilioWhatsAppHandler()

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
    """Valida CPF com exceções para CPFs de teste"""
    if not cpf or len(cpf) != 11:
        return False
    
    # CPFs de teste sempre válidos
    test_cpfs = [
        "12345678900",
        "11938012431", 
        "98765432100",
        "11122233344"
    ]
    
    if cpf in test_cpfs:
        return True
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação matemática normal
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

def format_for_whatsapp(html_content: str) -> str:
    """
    Converte resposta HTML para formato WhatsApp
    
    Args:
        html_content: Conteúdo com HTML tags
        
    Returns:
        str: Texto formatado para WhatsApp
    """
    text = html_content
    
    # Converte HTML para markdown WhatsApp
    text = re.sub(r'<strong>(.*?)</strong>', r'*\1*', text)  # Bold
    text = re.sub(r'<b>(.*?)</b>', r'*\1*', text)  # Bold
    text = re.sub(r'<em>(.*?)</em>', r'_\1_', text)  # Italic
    text = re.sub(r'<i>(.*?)</i>', r'_\1_', text)  # Italic
    
    # Remove componentes específicos do HTML
    text = re.sub(r'<div class="status-progress-container">.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div class="timeline-.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<span class="status-tag.*?</span>', lambda m: re.sub(r'<.*?>', '', m.group()), text)
    
    # Remove outras tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Converte entidades HTML
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    
    # Limita tamanho (WhatsApp limit: 4096 chars, mas Twilio é menor)
    if len(text) > 1400:
        text = text[:1400] + "...\n\n📱 *Para mais detalhes:*\nhttps://carglass-assistente.onrender.com"
    
    # Remove espaços extras e quebras de linha excessivas
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    
    return text

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
    platform: str = "web"  # "web" ou "whatsapp"
    phone_number: Optional[str] = None  # Para sessões WhatsApp
    
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT
    
    def update_activity(self):
        self.last_activity = time.time()
    
    def add_message(self, role: str, content: str):
        message = {
            "role": role,
            "content": content,
            "time": get_current_time(),
            "platform": self.platform
        }
        self.messages.append(message)
        self.update_activity()

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.whatsapp_sessions = {}  # phone_number -> session_id
    
    def create_session(self, platform: str = "web", phone_number: str = None) -> SessionData:
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        session_data = SessionData(
            session_id=session_id,
            created_at=current_time,
            last_activity=current_time,
            client_identified=False,
            client_info=None,
            messages=[],
            platform=platform,
            phone_number=phone_number
        )
        
        # Mensagem de boas-vindas personalizada por plataforma
        if platform == "whatsapp":
            welcome_msg = "👋 *Olá! Sou Clara, assistente virtual da CarGlass.*\n\nDigite seu *CPF*, *telefone* ou *placa do veículo* para consultar seu atendimento."
        else:
            welcome_msg = "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        
        session_data.add_message("assistant", welcome_msg)
        
        self.sessions[session_id] = session_data
        
        # Para WhatsApp, mapeia telefone -> session_id
        if platform == "whatsapp" and phone_number:
            self.whatsapp_sessions[phone_number] = session_id
        
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
            self._remove_session(session_id)
        
        return None
    
    def get_whatsapp_session(self, phone_number: str) -> Optional[SessionData]:
        """Recupera ou cria sessão WhatsApp baseada no telefone"""
        if not phone_number:
            return None
        
        session_id = self.whatsapp_sessions.get(phone_number)
        if session_id:
            session_data = self.get_session(session_id)
            if session_data:
                return session_data
            else:
                # Session expirou, remove mapeamento
                del self.whatsapp_sessions[phone_number]
        
        # Cria nova sessão WhatsApp
        return self.create_session("whatsapp", phone_number)
    
    def _remove_session(self, session_id: str):
        """Remove sessão e limpeza dos mapeamentos"""
        if session_id in self.sessions:
            session_data = self.sessions[session_id]
            if session_data.phone_number and session_data.phone_number in self.whatsapp_sessions:
                del self.whatsapp_sessions[session_data.phone_number]
            del self.sessions[session_id]
    
    def _cleanup_expired(self):
        current_time = time.time()
        expired = [sid for sid, data in self.sessions.items() 
                  if current_time - data.last_activity > config.SESSION_TIMEOUT]
        for sid in expired:
            self._remove_session(sid)

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
            # URLs específicas para cada tipo de consulta
            api_urls = {
                "cpf": "http://fusion-hml.carglass.hml.local:3000/api/status/cpf/",
                "telefone": "http://fusion-hml.carglass.hml.local:3000/api/status/telefone/",
                "ordem": "http://fusion-hml.carglass.hml.local:3000/api/status/ordem/"
            }
            
            # Verifica se o tipo é suportado
            if tipo not in api_urls:
                logger.warning(f"Tipo '{tipo}' não suportado pelas APIs")
                return {"sucesso": False, "mensagem": f"Tipo '{tipo}' não suportado"}
            
            # Monta URL completa
            endpoint = f"{api_urls[tipo]}{valor}"
            logger.info(f"Consultando API CarGlass: {endpoint}")
            
            # Faz requisição
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API CarGlass - Sucesso: {data.get('sucesso')}")
                cache.set(cache_key, data, config.CACHE_TTL)
                return data
            else:
                logger.error(f"API CarGlass - Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"API CarGlass indisponível: {e}. Usando fallback.")
        except requests.exceptions.Timeout as e:
            logger.warning(f"API CarGlass timeout: {e}. Usando fallback.")
        except Exception as e:
            logger.error(f"Erro na API CarGlass: {e}")
    
    # Fallback para dados mockados
    logger.info("Usando dados mockados como fallback")
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

def get_whatsapp_status_text(client_data: Dict[str, Any]) -> str:
    """Versão simplificada do status para WhatsApp"""
    status = client_data['dados']['status']
    
    # Mapeia status para emojis e texto simples
    status_emoji = {
        "Ordem de Serviço Aberta": "📋",
        "Aguardando fotos para liberação da ordem": "📷",
        "Fotos Recebidas": "✅",
        "Peça Identificada": "🔍",
        "Ordem de Serviço Liberada": "✅",
        "Serviço agendado com sucesso": "📅",
        "Em andamento": "🔧",
        "Concluído": "✅"
    }
    
    emoji = status_emoji.get(status, "📋")
    
    # Cria timeline simplificada para WhatsApp
    timeline_text = f"""
*📊 Timeline:*
{"✅" if status != "Ordem de Serviço Aberta" else "🔄"} Ordem Aberta
{"✅" if status not in ["Ordem de Serviço Aberta", "Aguardando fotos para liberação da ordem"] else "⏳"} Fotos/Peça
{"✅" if status in ["Em andamento", "Concluído"] else "⏳"} Agendado
{"✅" if status == "Concluído" else "🔄" if status == "Em andamento" else "⏳"} Execução
{"✅" if status == "Concluído" else "⏳"} Concluído
"""
    
    return f"{emoji} *{status}*\n\n{timeline_text}"

# ===== AI SERVICE =====
def get_ai_response(pergunta: str, cliente_info: Dict[str, Any], platform: str = "web") -> str:
    pergunta_lower = pergunta.lower()
    
    # Comandos especiais para WhatsApp
    if platform == "whatsapp":
        if pergunta_lower in ['status', 'situacao', 'situação']:
            dados = cliente_info.get('dados', {})
            status_text = get_whatsapp_status_text(cliente_info)
            return f"*Status atual do seu atendimento:*\n\n{status_text}"
        
        if pergunta_lower in ['ajuda', 'help', 'menu', 'opcoes', 'opções']:
            return """
🤖 *Comandos disponíveis:*

📋 *status* - Ver situação atual
🏪 *lojas* - Lojas próximas  
🛡️ *garantia* - Info de garantia
👥 *atendente* - Falar com pessoa
🔄 *reiniciar* - Nova consulta

💬 Ou envie sua pergunta!
"""
        
        if pergunta_lower in ['reiniciar', 'reset', 'nova consulta', 'recomeçar']:
            return "🔄 *Consulta reiniciada!*\n\nDigite seu *CPF*, *telefone* ou *placa do veículo* para nova consulta."
    
    # Respostas predefinidas (adaptadas para WhatsApp se necessário)
    if any(keyword in pergunta_lower for keyword in ['loja', 'local', 'onde', 'endereço']):
        if platform == "whatsapp":
            return """
🏪 *Lojas CarGlass próximas:*

📍 *CarGlass Morumbi*
Av. Professor Francisco Morato, 2307
Butantã - São Paulo

📍 *CarGlass Vila Mariana*  
Rua Domingos de Morais, 1267
Vila Mariana - São Paulo

📍 *CarGlass Santo André*
Av. Industrial, 600
Santo André

📞 *Mudar local:* 0800-727-2327
"""
        else:
            return """
        🏪 **Lojas CarGlass próximas:**
        
        • **CarGlass Morumbi**: Av. Professor Francisco Morato, 2307 - Butantã
        • **CarGlass Vila Mariana**: Rua Domingos de Morais, 1267 - Vila Mariana
        • **CarGlass Santo André**: Av. Industrial, 600 - Santo André
        
        📞 Para mudar local: **0800-727-2327**
        """
    
    if any(keyword in pergunta_lower for keyword in ['garantia', 'seguro']):
        tipo_servico = cliente_info.get('dados', {}).get('tipo_servico', 'seu serviço')
        if platform == "whatsapp":
            return f"""
🛡️ *Garantia CarGlass* para {tipo_servico}:

✅ *12 meses* a partir da conclusão
✅ Cobre defeitos de instalação  
✅ Válida em qualquer unidade

📞 Central: 0800-727-2327
"""
        else:
            return f"""
        🛡️ **Garantia CarGlass** para {tipo_servico}:
        
        ✅ **12 meses** a partir da conclusão
        ✅ Cobre defeitos de instalação
        ✅ Válida em qualquer unidade CarGlass
        
        📞 Central: **0800-727-2327**
        """
    
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente']):
        if platform == "whatsapp":
            return """
👥 *Falar com nossa equipe:*

📞 *Central:* 0800-727-2327
📱 *WhatsApp:* (11) 4003-8070

⏰ *Horário:*
• Segunda a Sexta: 8h às 20h
• Sábado: 8h às 16h
"""
        else:
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
            
            {"Responda em formato WhatsApp (use *negrito* e emojis)." if platform == "whatsapp" else "Seja simpática e objetiva."}
            Central: 0800-727-2327
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
    if platform == "whatsapp":
        return f"Entendi sua pergunta, {nome}! 😊\n\nPara informações específicas:\n📞 *0800-727-2327*"
    else:
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
            response = get_ai_response(user_input, session_data.client_info, session_data.platform)
        
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

@app.route('/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    """Webhook para receber mensagens WhatsApp via Twilio"""
    if not twilio_handler.is_enabled():
        logger.error("Twilio não configurado - webhook rejeitado")
        return "Twilio not configured", 400
    
    try:
        # Processa mensagem recebida
        message_data = twilio_handler.process_incoming_message(request.form)
        
        if not message_data:
            logger.error("Falha ao processar dados da mensagem WhatsApp")
            return "Bad request", 400
        
        phone = message_data['phone']
        message_text = message_data['message']
        
        logger.info(f"📱 WhatsApp processando: {phone[:4]}*** - {message_text[:30]}...")
        
        # Recupera ou cria sessão WhatsApp
        session_data = session_manager.get_whatsapp_session(phone)
        
        # Comandos especiais antes de adicionar à sessão
        if message_text.lower() in ['reiniciar', 'reset', 'nova consulta', 'recomeçar']:
            # Remove sessão atual e cria nova
            if session_data.session_id in session_manager.sessions:
                session_manager._remove_session(session_data.session_id)
            
            session_data = session_manager.create_session("whatsapp", phone)
            response = "🔄 *Consulta reiniciada!*\n\nDigite seu *CPF*, *telefone* ou *placa do veículo* para nova consulta."
        else:
            # Processa mensagem normalmente
            session_data.add_message("user", message_text)
            
            if not session_data.client_identified:
                response = process_identification(message_text, session_data)
            else:
                response = get_ai_response(message_text, session_data.client_info, "whatsapp")
            
            session_data.add_message("assistant", response)
        
        # Formata resposta para WhatsApp
        formatted_response = format_for_whatsapp(response)
        
        # Envia resposta via Twilio
        success = twilio_handler.send_message(phone, formatted_response)
        
        if success:
            logger.info(f"✅ Resposta WhatsApp enviada para {phone[:4]}***")
        else:
            logger.error(f"❌ Falha ao enviar resposta WhatsApp para {phone[:4]}***")
        
        # Retorna TwiML vazio (resposta já foi enviada via API)
        return twilio_handler.create_twiml_response(), 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook WhatsApp: {e}")
        logger.error(traceback.format_exc())
        return "Internal error", 500

def process_identification(user_input: str, session_data: SessionData) -> str:
    tipo, valor = detect_identifier_type(user_input)
    
    if not tipo:
        if session_data.platform == "whatsapp":
            return """
Por favor, forneça um identificador válido:

📋 *CPF* (11 dígitos)
📱 *Telefone* (10 ou 11 dígitos)  
🚗 *Placa do veículo*
🔢 *Número da ordem de serviço*
"""
        else:
            return """
        Por favor, forneça um identificador válido:
        
        📋 **CPF** (11 dígitos)
        📱 **Telefone** (10 ou 11 dígitos)
        🚗 **Placa do veículo**
        🔢 **Número da ordem de serviço**
        """
    
    client_data = get_client_data(tipo, valor)
    
    if not client_data.get('sucesso'):
        if session_data.platform == "whatsapp":
            return f"""
❌ *Não encontrei informações* com o {tipo} fornecido.

*Você pode tentar:*
• Verificar se digitou corretamente
• Usar outro identificador  
• Entrar em contato: *0800-727-2327*
"""
        else:
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
    
    if session_data.platform == "whatsapp":
        # Versão simplificada para WhatsApp
        status_text = get_whatsapp_status_text(client_data)
        
        return f"""
👋 *Olá {nome}!* Encontrei suas informações.

{status_text}

📋 *Resumo:*
• *Ordem:* {dados.get('ordem', 'N/A')}
• *Serviço:* {dados.get('tipo_servico', 'N/A')}
• *Veículo:* {dados.get('veiculo', {}).get('modelo', 'N/A')} ({dados.get('veiculo', {}).get('ano', 'N/A')})
• *Placa:* {dados.get('veiculo', {}).get('placa', 'N/A')}

💬 Como posso ajudar?
Digite *ajuda* para ver opções.
"""
    else:
        # Versão completa para web com HTML
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
            session_manager._remove_session(session_id)
        
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
        "sessions": {
            "web": len([s for s in session_manager.sessions.values() if s.platform == "web"]),
            "whatsapp": len([s for s in session_manager.sessions.values() if s.platform == "whatsapp"]),
            "total": len(session_manager.sessions)
        },
        "cache_items": len(cache.cache),
        "twilio_enabled": twilio_handler.is_enabled(),
        "config": {
            "use_real_api": config.USE_REAL_API,
            "openai_configured": bool(config.OPENAI_API_KEY)
        }
    })

@app.route('/whatsapp/status')
def whatsapp_status():
    """Endpoint para verificar status do WhatsApp"""
    if not twilio_handler.is_enabled():
        return jsonify({
            "enabled": False,
            "error": "Twilio não configurado - verifique TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN"
        }), 400
    
    return jsonify({
        "enabled": True,
        "whatsapp_number": config.TWILIO_WHATSAPP_NUMBER,
        "active_sessions": len([s for s in session_manager.sessions.values() if s.platform == "whatsapp"]),
        "webhook_url": request.url_root + "whatsapp/webhook"
    })

# ===== TRATAMENTO DE ERROS =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    logger.info("🚀 CarGlass Assistant v2.0 + Twilio WhatsApp iniciando...")
    logger.info(f"Modo API: {'REAL' if config.USE_REAL_API else 'SIMULAÇÃO'}")
    logger.info(f"OpenAI: {'CONFIGURADO' if config.OPENAI_API_KEY else 'FALLBACK'}")
    logger.info(f"Twilio WhatsApp: {'HABILITADO' if twilio_handler.is_enabled() else 'DESABILITADO'}")
    
    if twilio_handler.is_enabled():
        logger.info(f"📱 WhatsApp número: {config.TWILIO_WHATSAPP_NUMBER}")
        logger.info(f"🔗 Webhook URL: http://localhost:5000/whatsapp/webhook (configure no Twilio)")
    else:
        logger.warning("⚠️ Para habilitar WhatsApp, configure as variáveis:")
        logger.warning("   TWILIO_ACCOUNT_SID=ACxxxxx")
        logger.warning("   TWILIO_AUTH_TOKEN=xxxxx")
        logger.warning("   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886")
    
    app.run(debug=config.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
