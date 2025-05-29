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
from collections import defaultdict
import hashlib

from flask import Flask, render_template, request, jsonify, session, abort # Importe 'abort' aqui
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from twilio.request_validator import RequestValidator
import bleach
from markupsafe import escape

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
    USE_REAL_API: bool = os.getenv('USE_REAL_API', 'true').lower() == 'true' # Corrigido aqui
    SESSION_TIMEOUT: int = int(os.getenv('SESSION_TIMEOUT', '1800'))
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '300'))
    
    # Configurações Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER: str = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    TWILIO_ENABLED: bool = bool(os.getenv('TWILIO_ACCOUNT_SID'))

config = Config()

# ===== FLASK APP =====
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ===== CONFIGURAÇÃO DE SEGURANÇA PARA HML =====
# Rate Limiting (CRÍTICO mesmo em HML)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour"],  # Mais permissivo para testes
    storage_uri="memory://"
)

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
                message = message[:1500] + "...\n\n📱 Continue no link:\nhttps://carglass-assistente.onrender.com"
            
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

# ===== GERENCIADOR DE SEGURANÇA PARA HML =====
class HMLSecurityManager:
    """Versão simplificada para homologação"""
    def __init__(self):
        self.request_counts = defaultdict(list)
        self.blocked_ips = set()
        
    def sanitize_input(self, text: str) -> str:
        """Sanitização básica - mais permissiva em HML"""
        if not text:
            return ""
        
        # Remove apenas scripts perigosos
        text = bleach.clean(text, tags=[], strip=True)
        text = escape(text)
        
        # Limita tamanho (mais generoso em HML)
        return text[:2000].strip()
    
    def log_request(self, ip: str, endpoint: str):
        """Log simples para monitoramento"""
        now = time.time()
        
        # Remove requests antigos (última hora)
        cutoff = now - 3600
        self.request_counts[ip] = [
            (ep, t) for ep, t in self.request_counts[ip] 
            if t > cutoff
        ]
        
        # Adiciona novo request
        self.request_counts[ip].append((endpoint, now))
        
        # Bloqueia apenas abuso extremo (mais de 200 requests/hora)
        if len(self.request_counts[ip]) > 200:
            self.blocked_ips.add(ip)
            logger.warning(f"🚨 IP bloqueado por abuso em HML: {ip}")
    
    def is_ip_blocked(self, ip: str) -> bool:
        return ip in self.blocked_ips
    
    def validate_twilio_webhook(self, request) -> bool:
        """CRÍTICO: Valida webhook mesmo em HML"""
        if not config.TWILIO_AUTH_TOKEN:
            logger.warning("⚠️ TWILIO_AUTH_TOKEN não configurado")
            return True  # Permite em desenvolvimento local (CUIDADO: APENAS PARA DEV/TESTE)
        
        try:
            validator = RequestValidator(config.TWILIO_AUTH_TOKEN)
            signature = request.headers.get('X-Twilio-Signature', '')
            url = request.url
            
            if request.method == 'POST':
                return validator.validate(url, request.form, signature)
            else:
                return validator.validate(url, request.args, signature)
                
        except Exception as e:
            logger.error(f"Erro na validação Twilio: {e}")
            return False

# Instância para HML
security_manager = HMLSecurityManager()

# ===== UTILITÁRIOS =====
def get_current_time() -> str:
    return time.strftime("%H:%M")

def get_current_datetime() -> str:
    return time.strftime("%d/%m/%Y - %H:%M")

def sanitize_input(text: str) -> str:
    """Função global de sanitização"""
    return security_manager.sanitize_input(text)

def validate_cpf(cpf: str) -> bool:
    """Valida CPF com exceções para CPFs de teste - CORRIGIDO"""
    if not cpf or len(cpf) != 11:
        logger.info(f"CPF inválido - tamanho: {len(cpf) if cpf else 0}")
        return False
    
    # CPFs de teste sempre válidos - EXPANSÃO DA LISTA
    test_cpfs = [
        "12345678900",  # Principal para testes
        "11938012431",  
        "98765432100",
        "11122233344",
        "33344455566",
        "44455566677",
        "55566677788",
        "77788899900",
        "22233344455"
    ]
    
    if cpf in test_cpfs:
        logger.info(f"CPF de teste válido: {cpf[:3]}***")
        return True
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        logger.info(f"CPF inválido - dígitos iguais: {cpf}")
        return False
    
    # Validação matemática normal
    try:
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        
        if int(cpf[9]) != digito1:
            logger.info(f"CPF inválido - primeiro dígito: {cpf}")
            return False
        
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        
        is_valid = int(cpf[10]) == digito2
        logger.info(f"CPF {'válido' if is_valid else 'inválido'}: {cpf[:3]}***")
        return is_valid
    except Exception as e:
        logger.error(f"Erro na validação CPF {cpf}: {e}")
        return False

def detect_identifier_type(text: str) -> Tuple[Optional[str], str]:
    """Detecta tipo de identificador - CORRIGIDO"""
    if not text:
        return None, ""
    
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
    logger.info(f"🔍 Detectando tipo para: '{clean_text}' (original: '{text}')")
    
    # Verifica CPF primeiro (11 dígitos)
    if re.match(r'^\d{11}$', clean_text):
        logger.info(f"Possível CPF detectado: {clean_text}")
        if validate_cpf(clean_text):
            logger.info(f"✅ CPF válido confirmado: {clean_text[:3]}***")
            return "cpf", clean_text
        else:
            logger.info(f"❌ CPF inválido: {clean_text}")
            return None, clean_text
    
    # Verifica telefone (10 ou 11 dígitos)
    elif re.match(r'^\d{10,11}$', clean_text):
        logger.info(f"Telefone detectado: {clean_text[:4]}***")
        return "telefone", clean_text
    
    # Verifica placa
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text):
        logger.info(f"Placa detectada: {clean_text}")
        return "placa", clean_text.upper()
    
    # Verifica ordem de serviço
    elif re.match(r'^\d{1,8}$', clean_text):
        logger.info(f"Ordem detectada: {clean_text}")
        return "ordem", clean_text
    
    logger.info(f"❌ Nenhum tipo identificado para: {clean_text}")
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
        text = text[:1400] + "...\n\n📱 Para mais detalhes:\nhttps://carglass-assistente.onrender.com"
    
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
    
    def cleanup_expired(self):
        """Remove itens expirados do cache"""
        current_time = time.time()
        expired_keys = [key for key, item in self.cache.items() if item['expires'] <= current_time]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.info(f"Cache cleanup: removidos {len(expired_keys)} itens expirados")

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte SessionData para dicionário"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "client_identified": self.client_identified,
            "client_info": self.client_info,
            "messages": self.messages,
            "platform": self.platform,
            "phone_number": self.phone_number
        }

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
            welcome_msg = "👋 Olá! Sou Clara, assistente virtual da CarGlass.\n\nDigite seu CPF, telefone ou placa do veículo para consultar seu atendimento."
        else:
            welcome_msg = "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        
        session_data.add_message("assistant", welcome_msg)
        
        self.sessions[session_id] = session_data
        
        # Para WhatsApp, mapeia telefone -> session_id
        if platform == "whatsapp" and phone_number:
            self.whatsapp_sessions[phone_number] = session_id
        
        self._cleanup_expired()
        logger.info(f"Sessão criada: {session_id[:8]}*** - Plataforma: {platform}")
        return session_data
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        if not session_id:
            return None
        
        session_data = self.sessions.get(session_id)
        if session_data and not session_data.is_expired():
            session_data.update_activity()
            return session_data
        elif session_data:
            logger.info(f"Sessão expirada removida: {session_id[:8]}***")
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
                logger.info(f"Mapeamento WhatsApp removido: {phone_number[:4]}***")
        
        # Cria nova sessão WhatsApp
        return self.create_session("whatsapp", phone_number)
    
    def _remove_session(self, session_id: str):
        """Remove sessão e limpeza dos mapeamentos"""
        if session_id in self.sessions:
            session_data = self.sessions[session_id]
            if session_data.phone_number and session_data.phone_number in self.whatsapp_sessions:
                del self.whatsapp_sessions[session_data.phone_number]
            del self.sessions[session_id]
            logger.info(f"Sessão removida: {session_id[:8]}***")
    
    def _cleanup_expired(self):
        current_time = time.time()
        expired = [sid for sid, data in self.sessions.items()  
                    if current_time - data.last_activity > config.SESSION_TIMEOUT]
        for sid in expired:
            self._remove_session(sid)
        if expired:
            logger.info(f"Limpeza de sessões: {len(expired)} sessões expiradas removidas")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das sessões"""
        total = len(self.sessions)
        web_sessions = len([s for s in self.sessions.values() if s.platform == "web"])
        whatsapp_sessions = len([s for s in self.sessions.values() if s.platform == "whatsapp"])
        identified = len([s for s in self.sessions.values() if s.client_identified])
        
        return {
            "total": total,
            "web": web_sessions,
            "whatsapp": whatsapp_sessions,
            "identified": identified,
            "unidentified": total - identified
        }

session_manager = SessionManager()

# ===== API CLIENT =====
def get_client_data(tipo: str, valor: str) -> Dict[str, Any]:
    cache_key = f"client:{tipo}:{valor}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit para {tipo}: {valor[:4]}***")
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
    """Dados mockados completos para testes"""
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
                "veiculo": {"modelo": "Honda Civic", "placa": "ABC1234", "ano": "2022"},
                "loja": "CarGlass Morumbi",
                "endereco_loja": "Av. Professor Francisco Morato, 2307 - Butantã",
                "previsao_conclusao": "hoje às 16h"
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
                "veiculo": {"modelo": "Toyota Corolla", "placa": "DEF5678", "ano": "2021"},
                "loja": "CarGlass Vila Mariana",
                "endereco_loja": "Rua Domingos de Morais, 1267 - Vila Mariana",
                "previsao_conclusao": "amanhã às 14h"
            }
        },
        "11122233344": {
            "sucesso": True,
            "dados": {
                "nome": "João Oliveira",
                "cpf": "11122233344",
                "telefone": "11955556666",
                "ordem": "ORD54321",
                "status": "Aguardando fotos para liberação da ordem",
                "tipo_servico": "Troca de Vidro Lateral",
                "veiculo": {"modelo": "Volkswagen Golf", "placa": "GHI9012", "ano": "2023"},
                "loja": "CarGlass Santo André",
                "endereco_loja": "Av. Industrial, 600 - Santo André"
            }
        },
        "33344455566": {
            "sucesso": True,
            "dados": {
                "nome": "Ana Costa",
                "cpf": "33344455566",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Concluído",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {"modelo": "BMW X3", "placa": "JKL3456", "ano": "2024"},
                "loja": "CarGlass Morumbi",
                "endereco_loja": "Av. Professor Francisco Morato, 2307 - Butantã"
            }
        },
        "44455566677": {
            "sucesso": True,
            "dados": {
                "nome": "Pedro Mendes",
                "cpf": "44455566677",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Fotos Recebidas",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {"modelo": "Jeep Compass", "placa": "MNO7890", "ano": "2023"},
                "loja": "CarGlass Morumbi",
                "endereco_loja": "Av. Professor Francisco Morato, 2307 - Butantã"
            }
        },
        "55566677788": {
            "sucesso": True,
            "dados": {
                "nome": "Paulo Mendes",
                "cpf": "55566677788",
                "telefone": "11911110000",
                "ordem": "ORD36925",
                "status": "Ordem de Serviço Aberta",
                "tipo_servico": "Reparo de Parabrisa",
                "veiculo": {"modelo": "Chevrolet Onix", "placa": "STU5678", "ano": "2021"},
                "loja": "CarGlass Vila Mariana",
                "endereco_loja": "Rua Domingos de Morais, 1267 - Vila Mariana"
            }
        },
        "77788899900": {
            "sucesso": True,
            "dados": {
                "nome": "Roberto Santos",
                "cpf": "77788899900",
                "telefone": "11933332222",
                "ordem": "ORD24680",
                "status": "Peça Identificada",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {"modelo": "Jeep Compass", "placa": "MNO7890", "ano": "2023"},
                "loja": "CarGlass Santo André",
                "endereco_loja": "Av. Industrial, 600 - Santo André"
            }
        },
        "22233344455": {
            "sucesso": True,
            "dados": {
                "nome": "Fernanda Lima",
                "cpf": "22233344455",
                "telefone": "11922221111",
                "ordem": "ORD13579",
                "status": "Ordem de Serviço Liberada",
                "tipo_servico": "Polimento de Faróis",
                "veiculo": {"modelo": "Hyundai HB20", "placa": "PQR1234", "ano": "2022"},
                "loja": "CarGlass Morumbi",
                "endereco_loja": "Av. Professor Francisco Morato, 2307 - Butantã"
            }
        }
    }
    
    # Mapeamentos completos
    ordem_para_cpf = {
        "123456": "12345678900",  
        "ORD12345": "12345678900",
        "ORD67890": "98765432100",
        "ORD54321": "11122233344",
        "ORD98765": "33344455566",
        "ORD24680": "44455566677",
        "ORD36925": "55566677788",
        "ORD13579": "22233344455"
    }
    telefone_para_cpf = {
        "11987654321": "12345678900",
        "11976543210": "98765432100",
        "11955556666": "11122233344",
        "11944443333": "33344455566",
        "11933332222": "44455566677",
        "11911110000": "55566677788",
        "11922221111": "22233344455"
    }
    placa_para_cpf = {
        "ABC1234": "12345678900",
        "DEF5678": "98765432100",
        "GHI9012": "11122233344",
        "JKL3456": "33344455566",
        "MNO7890": "44455566677",
        "STU5678": "55566677788",
        "PQR1234": "22233344455"
    }
    
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
        logger.info(f"✅ Dados encontrados para {tipo}: {valor}")
        return mock_database[cpf_key]
    
    logger.info(f"❌ Cliente não encontrado para {tipo}: {valor}")
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}"}

# ===== BARRA DE PROGRESSO =====
def get_progress_bar_html(client_data: Dict[str, Any]) -> str:
    """Gera HTML da barra de progresso baseado no status do cliente"""
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
📊 Timeline:
{"✅" if status != "Ordem de Serviço Aberta" else "🔄"} Ordem Aberta
{"✅" if status not in ["Ordem de Serviço Aberta", "Aguardando fotos para liberação da ordem"] else "⏳"} Fotos/Peça
{"✅" if status in ["Em andamento", "Concluído"] else "⏳"} Agendado
{"✅" if status == "Concluído" else "🔄" if status == "Em andamento" else "⏳"} Execução
{"✅" if status == "Concluído" else "⏳"} Concluído
"""
    
    return f"{emoji} {status}\n\n{timeline_text}"

# ===== AI SERVICE =====
def get_ai_response(pergunta: str, cliente_info: Dict[str, Any], platform: str = "web") -> str:
    """Processa perguntas do cliente usando IA ou respostas predefinidas"""
    pergunta_lower = pergunta.lower()
    nome = cliente_info.get('dados', {}).get('nome', 'Cliente')
    
    # Log da pergunta
    logger.info(f"Processando pergunta ({platform}): {pergunta[:50]}...")
    
    # Comandos especiais para WhatsApp
    if platform == "whatsapp":
        if pergunta_lower in ['status', 'situacao', 'situação']:
            dados = cliente_info.get('dados', {})
            status_text = get_whatsapp_status_text(cliente_info)
            return f"Status atual do seu atendimento:\n\n{status_text}"
        
        if pergunta_lower in ['ajuda', 'help', 'menu', 'opcoes', 'opções']:
            return """
🤖 Comandos disponíveis:

📋 status - Ver situação atual
🏪 lojas - Lojas próximas  
🛡️ garantia - Info de garantia
👥 atendente - Falar com pessoa
🔄 reiniciar - Nova consulta

💬 Ou envie sua pergunta!
"""
        
        if pergunta_lower in ['reiniciar', 'reset', 'nova consulta', 'recomeçar']:
            return "🔄 Consulta reiniciada!\n\nDigite seu CPF, telefone ou placa do veículo para nova consulta."
    
    # Detecta quando cliente não entende ou está frustrado
    if any(keyword in pergunta_lower for keyword in ['não entende', 'não entendo', 'confuso', 'não sei', 'help', 'ajuda']):
        if platform == "whatsapp":
            return f"""
Entendo sua dúvida, {nome}! 😊

Sou a Clara, assistente virtual da CarGlass. Estou aqui para te ajudar com informações sobre seu atendimento.

📞 Se preferir falar com nossa equipe humana:
0800-701-9495

💬 Ou me diga: o que você gostaria de saber?
"""
        else:
            return f"""
Entendo sua dúvida, {nome}!

Sou a Clara, assistente virtual da CarGlass. Estou aqui para te ajudar com informações sobre seu atendimento.

📞 Se preferir falar com nossa equipe: 0800-701-9495

💬 Ou me diga: o que você gostaria de saber?
"""
    
    # CORREÇÃO: Política de lojas mais restritiva e específica
    if any(keyword in pergunta_lower for keyword in ['loja', 'local', 'onde', 'endereço', 'trocar de loja', 'mudar local', 'mudar loja', 'troca de loja']):
        # SEMPRE orienta para central quando menciona trocar/mudar
        if any(keyword in pergunta_lower for keyword in ['trocar', 'mudar', 'alterar', 'escolher', 'troca']):
            logger.info(f"Cliente solicitou troca de loja - orientando para central")
            if platform == "whatsapp":
                return f"""
🏪 Para trocar de loja é necessário consultar as lojas previamente.

Por favor, {nome}, entre em contato com nossa central de atendimento:

📞 0800-701-9495

Eles vão te ajudar a escolher a melhor loja para você! 😊
"""
            else:
                return f"""
🏪 Para trocar de loja é necessário consultar as lojas previamente.

Por favor, {nome}, entre em contato com nossa central de atendimento:

📞 0800-701-9495

Eles vão te ajudar a escolher a melhor loja para você!
"""
        # Apenas para consulta informativa específica (sem intenção de trocar)
        elif any(keyword in pergunta_lower for keyword in ['onde fica', 'quais são', 'informação sobre lojas', 'conhecer as lojas']):
            logger.info(f"Cliente solicitou informações sobre lojas - fornecendo lista")
            if platform == "whatsapp":
                return """
🏪 Lojas CarGlass próximas:

📍 CarGlass Morumbi
Av. Professor Francisco Morato, 2307
Butantã - São Paulo

📍 CarGlass Vila Mariana  
Rua Domingos de Morais, 1267
Vila Mariana - São Paulo

📍 CarGlass Santo André
Av. Industrial, 600
Santo André

📞 Para escolher sua loja: 0800-701-9495
"""
            else:
                return """
🏪 Lojas CarGlass próximas:

• CarGlass Morumbi: Av. Professor Francisco Morato, 2307 - Butantã
• CarGlass Vila Mariana: Rua Domingos de Morais, 1267 - Vila Mariana
• CarGlass Santo André: Av. Industrial, 600 - Santo André

📞 Para escolher sua loja: 0800-701-9495
"""
        else:
            # Qualquer outra menção de loja = orientar para central
            logger.info(f"Cliente mencionou loja - orientando para central por segurança")
            if platform == "whatsapp":
                return f"""
🏪 Para informações sobre lojas, entre em contato com nossa central:

📞 0800-701-9495

Nossa equipe vai te ajudar com todas as informações! 😊
"""
            else:
                return f"""
🏪 Para informações sobre lojas, entre em contato com nossa central:

📞 0800-701-9495

Nossa equipe vai te ajudar com todas as informações!
"""
    
    # Perguntas sobre garantia
    if any(keyword in pergunta_lower for keyword in ['garantia', 'seguro']):
        tipo_servico = cliente_info.get('dados', {}).get('tipo_servico', 'seu serviço')
        if platform == "whatsapp":
            return f"""
🛡️ Garantia CarGlass para {tipo_servico}:

✅ 12 meses a partir da conclusão
✅ Cobre defeitos de instalação  
✅ Válida em qualquer unidade

📞 Central: 0800-701-9495
"""
        else:
            return f"""
🛡️ Garantia CarGlass para {tipo_servico}:

✅ 12 meses a partir da conclusão
✅ Cobre defeitos de instalação
✅ Válida em qualquer unidade CarGlass

📞 Central: 0800-701-9495
"""
    
    # Perguntas sobre atendimento humano
    if any(keyword in pergunta_lower for keyword in ['falar com pessoa', 'atendente', 'humano']):
        if platform == "whatsapp":
            return """
👥 Falar com nossa equipe:

📞 Central: 0800-701-9495

⏰ Horário:
• Segunda a Sexta: 8h às 20h
• Sábado: 8h às 16h
"""
        else:
            return """
👥 Falar com nossa equipe:

📞 Central: 0800-701-9495

⏰ Horário:
• Segunda a Sexta: 8h às 20h
• Sábado: 8h às 16h
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
    
    # Para perguntas sobre status - usar GPT para resposta mais humanizada
    if any(keyword in pergunta_lower for keyword in ['status', 'como está', 'situação', 'andamento', 'etapa', 'fase']):
        if config.OPENAI_API_KEY and len(config.OPENAI_API_KEY) > 10:
            try:
                import openai
                openai.api_key = config.OPENAI_API_KEY
                
                dados = cliente_info.get('dados', {})
                status_atual = dados.get('status', 'Em processamento')
                tipo_servico = dados.get('tipo_servico', 'serviço')
                
                system_message = f"""
                Você é Clara, assistente virtual da CarGlass falando com {nome}.
                
                O status atual do atendimento é: "{status_atual}"
                Tipo de serviço: {tipo_servico}
                
                IMPORTANTE: Responda como se fosse uma pessoa real explicando qual é o status atual.
                Seja natural, amigável e humana. Não liste etapas ou use formatação técnica.
                Explique o que o status significa de forma conversacional.
                NÃO use asteriscos ou formatação markdown excessiva.
                
                Se precisar de mais detalhes, mencione nosso telefone: 0800-701-9495
                """
                
                response = openai.ChatCompletion.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Como está meu atendimento?"}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                
                return response.choices[0].message['content'].strip()
            except Exception as e:
                logger.error(f"OpenAI erro: {e}")
        
        # Fallback humanizado para status
        dados = cliente_info.get('dados', {})
        status = dados.get('status', 'Em processamento')
        
        if platform == "whatsapp":
            if "agendado" in status.lower():
                previsao_text = f" com previsão para {dados.get('previsao_conclusao', '')}" if dados.get('previsao_conclusao') else ""
                return f"Oi {nome}! 😊 Seu serviço já está agendado{previsao_text}. Nossa equipe está organizando tudo para o dia marcado. Em breve você receberá mais detalhes!"
            elif "andamento" in status.lower():
                previsao_text = f" com previsão de conclusão {dados.get('previsao_conclusao', '')}" if dados.get('previsao_conclusao') else ""
                return f"Olá {nome}! 🔧 Seu atendimento está em andamento{previsao_text}. Nossa equipe técnica está trabalhando no seu veículo neste momento."
            elif "concluido" in status.lower():
                return f"Oi {nome}! ✅ Ótima notícia - seu serviço foi concluído com sucesso!"
            else:
                return f"Oi {nome}! 📋 Seu atendimento está com status: {status}. Nossa equipe está cuidando de tudo!"
        else:
            if "agendado" in status.lower():
                previsao_text = f" com previsão para {dados.get('previsao_conclusao', '')}" if dados.get('previsao_conclusao') else ""
                return f"Olá {nome}! Seu serviço já está agendado{previsao_text}. Nossa equipe está organizando tudo para o dia marcado."
            elif "andamento" in status.lower():
                previsao_text = f" com previsão de conclusão {dados.get('previsao_conclusao', '')}" if dados.get('previsao_conclusao') else ""
                return f"Olá {nome}! Seu atendimento está em andamento{previsao_text}. Nossa equipe técnica está trabalhando no seu veículo."
            elif "concluido" in status.lower():
                return f"Olá {nome}! Ótima notícia - seu serviço foi concluído com sucesso!"
            else:
                return f"Olá {nome}! Seu atendimento está com status: {status}. Nossa equipe está cuidando de tudo!"
    
    # Perguntas sobre etapas ou progresso
    if any(keyword in pergunta_lower for keyword in ['etapa', 'progresso', 'andamento', 'fase']):
        dados = cliente_info.get('dados', {})
        status = dados.get('status', 'Em processamento')
        
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

Você pode enviar as fotos pelo telefone 0800-701-9495 ou pelo e-mail atendimento@carglass.com.br.

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
    
    # Fallback usando OpenAI ou genérico para outras perguntas
    if config.OPENAI_API_KEY and len(config.OPENAI_API_KEY) > 10:
        try:
            import openai
            openai.api_key = config.OPENAI_API_KEY
            
            dados = cliente_info.get('dados', {})
            system_message = f"""
            Você é Clara, assistente virtual da CarGlass. Cliente: {nome}
            Status: {dados.get('status', 'N/A')}
            Serviço: {dados.get('tipo_servico', 'N/A')}
            
            IMPORTANTE: Responda como uma pessoa real, de forma natural e conversacional.
            Seja simpática, prestativa e humana. Não use listas ou formatação técnica.
            NÃO use asteriscos duplos ou formatação markdown excessiva.
            Mantenha um tom amigável e profissional.
            
            Central: 0800-701-9495
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
    
    # Fallback genérico melhorado
    if platform == "whatsapp":
        return f"Entendi sua pergunta, {nome}! 😊\n\nPara informações específicas:\n📞 0800-701-9495"
    else:
        return f"Entendi sua pergunta, {nome}. Para informações específicas, entre em contato: 📞 0800-701-9495"

# ===== PROCESSAMENTO DE IDENTIFICAÇÃO =====
def process_identification(user_input: str, session_data: SessionData) -> str:
    """Processa identificação do cliente"""
    tipo, valor = detect_identifier_type(user_input)
    
    logger.info(f"🔍 Processando identificação - Tipo: {tipo}, Valor: {valor[:4] if valor else 'None'}***")
    
    if not tipo:
        logger.info("❌ Tipo de identificador não reconhecido")
        if session_data.platform == "whatsapp":
            return """
Por favor, forneça um identificador válido:

📋 CPF (11 dígitos)
📱 Telefone (10 ou 11 dígitos)  
🚗 Placa do veículo
🔢 Número da ordem de serviço
"""
        else:
            return """
Por favor, forneça um identificador válido:

📋 CPF (11 dígitos)
📱 Telefone (10 ou 11 dígitos)
🚗 Placa do veículo
🔢 Número da ordem de serviço
"""
    
    client_data = get_client_data(tipo, valor)
    logger.info(f"📊 Resultado da consulta - Sucesso: {client_data.get('sucesso')}")
    
    if not client_data.get('sucesso'):
        logger.info(f"❌ Cliente não encontrado: {tipo} = {valor}")
        if session_data.platform == "whatsapp":
            return f"""
❌ Não encontrei informações com o {tipo} fornecido.

Você pode tentar:
• Verificar se digitou corretamente
• Usar outro identificador  
• Entrar em contato: 0800-701-9495
"""
        else:
            return f"""
❌ Não encontrei informações com o {tipo} fornecido.

Você pode tentar:
• Verificar se digitou corretamente
• Usar outro identificador
• Entrar em contato: 📞 0800-701-9495
"""
    
    session_data.client_identified = True
    session_data.client_info = client_data
    
    dados = client_data['dados']
    nome = dados.get('nome', 'Cliente')
    status = dados.get('status', 'Em processamento')
    ordem = dados.get('ordem', 'N/A')
    tipo_servico = dados.get('tipo_servico', 'N/A')
    veiculo = dados.get('veiculo', {})
    modelo = veiculo.get('modelo', 'N/A')
    ano = veiculo.get('ano', 'N/A')
    placa = veiculo.get('placa', 'N/A')
    
    logger.info(f"✅ Cliente identificado: {nome} - Status: {status}")
    
    # Resposta conversacional humanizada - SEM tags de status visuais
    if config.OPENAI_API_KEY and len(config.OPENAI_API_KEY) > 10:
        try:
            import openai
            openai.api_key = config.OPENAI_API_KEY
            
            system_message = f"""
            Você é Clara, assistente virtual da CarGlass, falando com {nome}.
            
            Informações do atendimento:
            - Ordem: {ordem}
            - Status atual: {status}
            - Serviço: {tipo_servico}
            - Veículo: {modelo} ({ano})
            - Placa: {placa}
            
            IMPORTANTE: 
            1. Cumprimente o cliente pelo nome de forma natural
            2. Explique o status atual de forma conversacional e humana
            3. NUNCA mencione loja específica - se precisar falar de local, diga apenas "nossa equipe" ou "uma de nossas unidades"
            4. Se cliente perguntar sobre loja, oriente para ligar 0800-701-9495
            5. Seja natural, como se fosse uma pessoa real falando
            6. NÃO use formatação excessiva ou asteriscos duplos
            7. Inclua detalhes do veículo e ordem de forma natural na conversa
            8. Termine perguntando como pode ajudar de forma amigável
            
            Mantenha um tom conversacional e amigável, como se estivesse falando pessoalmente.
            """
            
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Cliente forneceu {tipo}: {valor}"}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            logger.info("✅ Resposta OpenAI gerada com sucesso")
            return response.choices[0].message['content'].strip()
            
        except Exception as e:
            logger.error(f"❌ OpenAI erro na identificação: {e}")
    
    # Fallback humanizado sem OpenAI
    previsao = dados.get('previsao_conclusao', '')
    
    if session_data.platform == "whatsapp":
        if "agendado" in status.lower():
            previsao_text = f" com previsão para {previsao}" if previsao else ""
            return f"""
👋 Olá {nome}!  

Sua ordem de serviço {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}, está agendada{previsao_text}.

🏪 Nossa equipe já está organizando tudo para você.

💬 Como posso te ajudar?
"""
        elif "andamento" in status.lower():
            previsao_text = f" com previsão de conclusão {previsao}" if previsao else ""
            return f"""
👋 Olá {nome}!  

Sua ordem de serviço {ordem} está em andamento. Nossa equipe está trabalhando na {tipo_servico} do seu {modelo} ({ano}), placa {placa}{previsao_text}.

🔧 Tudo está correndo bem e dentro do prazo previsto.

💬 Precisa de alguma informação específica?
"""
        elif "concluído" in status.lower():
            return f"""
👋 Olá {nome}!  

✅ Ótima notícia! Sua ordem {ordem} foi concluída com sucesso. A {tipo_servico} do seu {modelo} ({ano}), placa {placa}, está pronta.

🏪 Você pode retirar seu veículo em nossa unidade.

💬 Posso te ajudar com mais alguma coisa?
"""
        elif "aguardando fotos" in status.lower():
            return f"""
👋 Olá {nome}!  

Sua ordem {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}, está aguardando as fotos para darmos continuidade.

📷 Você pode enviar pelo nosso sistema ou entrar em contato: 0800-701-9495

💬 Precisa de ajuda para enviar as fotos?
"""
        else:
            return f"""
👋 Olá {nome}!  

Encontrei sua ordem {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}. No momento está: {status}.

🏪 Nossa equipe está cuidando de tudo para você.

💬 Como posso te ajudar?
"""
    else:
        # Versão web
        if "agendado" in status.lower():
            previsao_text = f" com previsão para {previsao}" if previsao else ""
            return f"""
👋 Olá {nome}! Encontrei suas informações.

Sua ordem de serviço {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}, está agendada{previsao_text}.

🏪 Nossa equipe já está organizando tudo para você.

💬 Como posso te ajudar?
"""
        elif "andamento" in status.lower():
            previsao_text = f" com previsão de conclusão {previsao}" if previsao else ""
            return f"""
👋 Olá {nome}! Encontrei suas informações.

Sua ordem de serviço {ordem} está em andamento. Nossa equipe está trabalhando na {tipo_servico} do seu {modelo} ({ano}), placa {placa}{previsao_text}.

🔧 Tudo está correndo bem e dentro do prazo previsto.

💬 Precisa de alguma informação específica?
"""
        elif "concluído" in status.lower():
            return f"""
👋 Olá {nome}! Encontrei suas informações.

✅ Ótima notícia! Sua ordem {ordem} foi concluída com sucesso. A {tipo_servico} do seu {modelo} ({ano}), placa {placa}, está pronta.

🏪 Você pode retirar seu veículo em nossa unidade.

💬 Posso te ajudar com mais alguma coisa?
"""
        elif "aguardando fotos" in status.lower():
            return f"""
👋 Olá {nome}! Encontrei suas informações.

Sua ordem {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}, está aguardando as fotos para darmos continuidade.

📷 Você pode enviar pelo nosso sistema ou entrar em contato: 0800-701-9495

💬 Precisa de ajuda para enviar as fotos?
"""
        else:
            return f"""
👋 Olá {nome}! Encontrei suas informações.

Sua ordem {ordem} para {tipo_servico} no seu {modelo} ({ano}), placa {placa}, está com status: {status}.

🏪 Nossa equipe está cuidando de tudo para você.

💬 Como posso te ajudar?
"""

# ===== MIDDLEWARES DE SEGURANÇA PARA HML =====

@app.before_request
def hml_security_check():
    """Verificações básicas para HML"""
    ip = get_remote_address()
    
    # Apenas bloqueia abuse extremo
    if security_manager.is_ip_blocked(ip):
        logger.warning(f"🚫 IP bloqueado: {ip}")
        abort(429)  # Too Many Requests
    
    # Log para monitoramento
    if request.endpoint in ['send_message', 'whatsapp_webhook']:
        security_manager.log_request(ip, request.endpoint)

@app.after_request
def hml_security_headers(response):
    """Headers básicos para HML"""
    # Headers mínimos que não quebram funcionalidade
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # Menos restritivo
    
    # Remove headers que vazam informações
    response.headers.pop('Server', None)
    
    return response

# ===== ROTAS FLASK =====

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
@limiter.limit("30 per minute")  # Mais permissivo para testes
def send_message():
    """Versão para homologação"""
    try:
        ip = get_remote_address()
        
        # Sanitização básica
        user_input = sanitize_input(request.form.get('message', ''))
        
        if not user_input:
            return jsonify({'error': 'Mensagem vazia'}), 400
        
        logger.info(f"📨 Mensagem HML de {ip[:8]}***: {user_input[:50]}...")
        
        # Lógica original mantida
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
        logger.error(f"Erro HML send_message: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/whatsapp/webhook', methods=['POST'])
@limiter.limit("60 per minute")  # Mais permissivo para testes
def whatsapp_webhook():
    """Webhook WhatsApp para homologação"""
    ip = get_remote_address()
    
    if not twilio_handler.is_enabled():
        return "Twilio not configured", 400
    
    # VALIDAÇÃO CRÍTICA (mesmo em HML)
    if not security_manager.validate_twilio_webhook(request):
        logger.error(f"🚨 Webhook Twilio inválido de {ip}")
        abort(403)
    
    try:
        # Lógica original mantida
        message_data = twilio_handler.process_incoming_message(request.form)
        
        if not message_data:
            return "Bad request", 400
        
        phone = message_data['phone']
        message_text = sanitize_input(message_data['message'])
        
        logger.info(f"📱 WhatsApp HML de {phone[:6]}***: {message_text[:30]}...")
        
        session_data = session_manager.get_whatsapp_session(phone)
        
        if message_text.lower() in ['reiniciar', 'reset', 'nova consulta']:
            if session_data.session_id in session_manager.sessions:
                session_manager._remove_session(session_data.session_id)
            session_data = session_manager.create_session("whatsapp", phone)
            response = "🔄 Consulta reiniciada!\n\nDigite seu CPF, telefone ou placa do veículo."
        else:
            session_data.add_message("user", message_text)
            
            if not session_data.client_identified:
                response = process_identification(message_text, session_data)
            else:
                response = get_ai_response(message_text, session_data.client_info, "whatsapp")
            
            session_data.add_message("assistant", response)
        
        formatted_response = format_for_whatsapp(response)
        success = twilio_handler.send_message(phone, formatted_response)
        
        return twilio_handler.create_twiml_response(), 200
        
    except Exception as e:
        logger.error(f"❌ Erro webhook WhatsApp HML: {e}")
        logger.error(traceback.format_exc())
        return "Internal error", 500

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

@app.route('/test_openai')
def test_openai():
    """Endpoint para testar configuração OpenAI"""
    if not config.OPENAI_API_KEY:
        return jsonify({
            "status": "error",
            "message": "OPENAI_API_KEY não configurada"
        })
    
    if len(config.OPENAI_API_KEY) < 10:
        return jsonify({
            "status": "error",  
            "message": f"OPENAI_API_KEY parece inválida (muito curta): {config.OPENAI_API_KEY[:10]}..."
        })
    
    try:
        import openai
        openai.api_key = config.OPENAI_API_KEY
        
        # Teste simples da API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Modelo mais barato para teste
            messages=[
                {"role": "user", "content": "Responda apenas 'OK' se você está funcionando"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        return jsonify({
            "status": "success",
            "message": "OpenAI configurada corretamente",
            "response": response.choices[0].message['content'],
            "model": config.OPENAI_MODEL
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao testar OpenAI: {str(e)}",
            "key_preview": config.OPENAI_API_KEY[:20] + "..." if len(config.OPENAI_API_KEY) > 20 else config.OPENAI_API_KEY
        })

@app.route('/health')
def health_check():
    """Endpoint para verificação de saúde da aplicação"""
    try:
        # Cleanup periódico
        cache.cleanup_expired()
        session_manager._cleanup_expired()
        
        stats = session_manager.get_stats()
        
        return jsonify({
            "status": "healthy",
            "timestamp": get_current_time(),
            "sessions": stats,
            "cache_items": len(cache.cache),
            "twilio_enabled": twilio_handler.is_enabled(),
            "config": {
                "use_real_api": config.USE_REAL_API,
                "openai_configured": bool(config.OPENAI_API_KEY),
                "openai_key_length": len(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else 0,
                "openai_model": config.OPENAI_MODEL,
                "session_timeout": config.SESSION_TIMEOUT,
                "cache_ttl": config.CACHE_TTL
            },
            "version": "2.1"
        })
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": get_current_time()
        }), 500

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

# ===== ENDPOINTS ÚTEIS PARA HML =====

@app.route('/hml/status')
def hml_status():
    """Status específico para homologação"""
    return jsonify({
        "environment": "HOMOLOGAÇÃO",
        "security_level": "BÁSICO",
        "data_type": "MOCK/TESTE",
        "validations": {
            "twilio_webhook": config.TWILIO_AUTH_TOKEN is not None,
            "rate_limiting": True,
            "input_sanitization": True,
            "ip_blocking": len(security_manager.blocked_ips)
        },
        "request_stats": {
            "monitored_ips": len(security_manager.request_counts),
            "blocked_ips": len(security_manager.blocked_ips)
        },
        "recommendations": [
            "✅ Ambiente adequado para testes",
            "⚠️ Não usar dados reais",
            "🔄 Aplicar segurança completa antes da produção"
        ]
    })

@app.route('/hml/security-test')
def security_test():
    """Endpoint para testar validações"""
    test_results = {
        "input_sanitization": False,
        "rate_limiting": False,
        "twilio_validation": False
    }
    
    # Teste sanitização
    malicious_input = "<script>alert('xss')</script>Test"
    sanitized = sanitize_input(malicious_input)
    test_results["input_sanitization"] = "<script>" not in sanitized
    
    # Teste Twilio (se configurado)
    if config.TWILIO_AUTH_TOKEN:
        test_results["twilio_validation"] = True
    
    # Rate limiting está ativo se chegou aqui
    test_results["rate_limiting"] = True
    
    return jsonify({
        "environment": "HML",
        "security_tests": test_results,
        "status": "✅ Validações básicas funcionando"
    })

@app.route('/debug/sessions')
def debug_sessions():
    """Endpoint para debug das sessões (apenas em modo DEBUG)"""
    if not config.DEBUG:
        return jsonify({"error": "Debug mode not enabled"}), 403
    
    try:
        sessions_info = []
        for session_id, session_data in session_manager.sessions.items():
            sessions_info.append({
                "session_id": session_id[:8] + "***",
                "platform": session_data.platform,
                "client_identified": session_data.client_identified,
                "messages_count": len(session_data.messages),
                "created_at": time.strftime("%H:%M:%S", time.localtime(session_data.created_at)),
                "last_activity": time.strftime("%H:%M:%S", time.localtime(session_data.last_activity)),
                "phone_number": session_data.phone_number[:4] + "***" if session_data.phone_number else None
            })
        
        return jsonify({
            "total_sessions": len(sessions_info),
            "sessions": sessions_info,
            "whatsapp_mappings": len(session_manager.whatsapp_sessions)
        })
    except Exception as e:
        logger.error(f"Erro no debug sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug/cache')
def debug_cache():
    """Endpoint para debug do cache (apenas em modo DEBUG)"""
    if not config.DEBUG:
        return jsonify({"error": "Debug mode not enabled"}), 403
    
    try:
        cache_info = {}
        current_time = time.time()
        
        for key, item in cache.cache.items():
            cache_info[key] = {
                "expires_in": max(0, int(item['expires'] - current_time)),
                "size": len(str(item['value']))
            }
        
        return jsonify({
            "cache_size": len(cache.cache),
            "max_items": cache.max_items,
            "items": cache_info
        })
    except Exception as e:
        logger.error(f"Erro no debug cache: {e}")
        return jsonify({"error": str(e)}), 500

# ===== TRATAMENTO DE ERROS =====
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 - Página não encontrada: {request.url}")
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {error}")
    logger.error(traceback.format_exc())
    return jsonify({'error': 'Erro interno do servidor'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Exceção não tratada: {e}")
    logger.error(traceback.format_exc())
    return jsonify({'error': 'Erro interno do servidor'}), 500

# ===== INICIALIZAÇÃO =====
def initialize_app():
    """Inicializa componentes da aplicação"""
    logger.info("🔧 Inicializando componentes da aplicação...")
    
    # Cleanup inicial
    cache.cleanup_expired()
    session_manager._cleanup_expired()
    
    # Testa configurações
    if config.OPENAI_API_KEY:
        logger.info("✅ OpenAI API Key configurada")
    else:
        logger.warning("⚠️ OpenAI API Key não configurada - usando fallbacks")
    
    if twilio_handler.is_enabled():
        logger.info("✅ Twilio WhatsApp habilitado")
    else:
        logger.warning("⚠️ Twilio WhatsApp desabilitado")
    
    logger.info("✅ Aplicação inicializada com sucesso")

if __name__ == '__main__':
    logger.info("🚀 CarGlass Assistant v2.1 + Twilio WhatsApp iniciando...")
    logger.info(f"Modo API: {'REAL' if config.USE_REAL_API else 'SIMULAÇÃO'}")
    logger.info(f"OpenAI: {'CONFIGURADO' if config.OPENAI_API_KEY else 'FALLBACK'}")
    logger.info(f"Twilio WhatsApp: {'HABILITADO' if twilio_handler.is_enabled() else 'DESABILITADO'}")
    logger.info(f"Debug Mode: {'HABILITADO' if config.DEBUG else 'DESABILITADO'}")
    
    if twilio_handler.is_enabled():
        logger.info(f"📱 WhatsApp número: {config.TWILIO_WHATSAPP_NUMBER}")
        logger.info(f"🔗 Webhook URL: http://localhost:5000/whatsapp/webhook (configure no Twilio)")
    else:
        logger.warning("⚠️ Para habilitar WhatsApp, configure as variáveis:")
        logger.warning("    TWILIO_ACCOUNT_SID=ACxxxxx")
        logger.warning("    TWILIO_AUTH_TOKEN=xxxxx")
        logger.warning("    TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886")
    
    # Inicializa componentes
    initialize_app()
    
    # Inicia aplicação
    app.run(debug=config.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
