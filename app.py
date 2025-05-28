"""
Aplicação principal do Assistente Virtual CarGlass - Versão 2.1
Melhorada com IA conversacional e dados simulados detalhados
CÓDIGO COMPLETO COM TODAS AS FUNCIONALIDADES
"""
import os
import logging
import traceback
import time
import uuid
import random
import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    
    # Configurações Twilio (apenas para SMS ou voz, se aplicável, não WhatsApp)
    TWILIO_ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_GENERIC_NUMBER: str = os.getenv('TWILIO_GENERIC_NUMBER', '') # Um número genérico para Twilio, se houver
    TWILIO_ENABLED: bool = bool(os.getenv('TWILIO_ACCOUNT_SID'))

config = Config()

# ===== DADOS SIMULADOS DETALHADOS =====
LOJAS_CARGLASS = {
    "SP001": {
        "nome": "CarGlass Morumbi",
        "endereco": "Av. Professor Francisco Morato, 2307",
        "bairro": "Butantã",
        "cidade": "São Paulo",
        "telefone": "(11) 3719-2800",
        "horario": "Segunda a Sexta: 8h às 18h, Sábado: 8h às 12h"
    },
    "SP002": {
        "nome": "CarGlass Vila Mariana", 
        "endereco": "Rua Domingos de Morais, 1267",
        "bairro": "Vila Mariana",
        "cidade": "São Paulo",
        "telefone": "(11) 5574-1200",
        "horario": "Segunda a Sexta: 8h às 18h, Sábado: 8h às 12h"
    },
    "SP003": {
        "nome": "CarGlass Santo André",
        "endereco": "Av. Industrial, 600",
        "bairro": "Centro",
        "cidade": "Santo André", 
        "telefone": "(11) 4433-5500",
        "horario": "Segunda a Sexta: 8h às 18h"
    },
    "SP004": {
        "nome": "CarGlass Alphaville",
        "endereco": "Al. Rio Negro, 585",
        "bairro": "Alphaville",
        "cidade": "Barueri",
        "telefone": "(11) 4191-8800",
        "horario": "Segunda a Sexta: 8h às 18h"
    }
}

def get_mock_data_enhanced(tipo: str, valor: str) -> Dict[str, Any]:
    """Dados simulados com informações detalhadas para respostas conversacionais"""
    
    # Gera datas simuladas (serviço para hoje + 1-3 dias)
    hoje = datetime.now()
    data_servico = hoje + timedelta(days=random.randint(1, 3))
    data_servico_str = data_servico.strftime("%d/%m/%Y")
    
    # Seleciona loja aleatória
    loja_id = random.choice(list(LOJAS_CARGLASS.keys()))
    loja_info = LOJAS_CARGLASS[loja_id]
    
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
                "veiculo": {
                    "modelo": "Honda Civic",
                    "placa": "ABC1234", 
                    "ano": "2022",
                    "cor": "Prata"
                },
                "loja": loja_info,
                "loja_id": loja_id,
                "data_agendamento": data_servico_str,
                "horario_agendamento": "14:00",
                "tecnico_responsavel": "José Santos",
                "tempo_estimado": "2 horas",
                "observacoes": "Parabrisa com trinca extensa no lado direito",
                "valor_servico": "R$ 680,00",
                "forma_pagamento": "Seguro - Porto Seguro"
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
                "veiculo": {
                    "modelo": "Toyota Corolla",
                    "placa": "DEF5678",
                    "ano": "2021",
                    "cor": "Branco"
                },
                "loja": LOJAS_CARGLASS["SP002"],
                "loja_id": "SP002",
                "data_agendamento": (hoje + timedelta(days=1)).strftime("%d/%m/%Y"),
                "horario_agendamento": "09:30",
                "tecnico_responsavel": "Ana Paula Costa",
                "tempo_estimado": "1 hora",
                "observacoes": "Pequena trinca no canto inferior esquerdo",
                "valor_servico": "R$ 280,00",
                "forma_pagamento": "Cartão de crédito"
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
                "veiculo": {
                    "modelo": "Volkswagen Golf",
                    "placa": "GHI9012",
                    "ano": "2023",
                    "cor": "Azul"
                },
                "loja": LOJAS_CARGLASS["SP001"],
                "loja_id": "SP001", 
                "data_agendamento": "A definir após análise",
                "horario_agendamento": "A definir",
                "tecnico_responsavel": "A definir",
                "tempo_estimado": "3 horas",
                "observacoes": "Vidro lateral traseiro direito danificado",
                "valor_servico": "R$ 420,00",
                "forma_pagamento": "Seguro - Bradesco"
            }
        },
        "44455566677": {
            "sucesso": True,
            "dados": {
                "nome": "Ana Souza", 
                "cpf": "44455566677",
                "telefone": "11944443333",
                "ordem": "ORD98765",
                "status": "Concluído",
                "tipo_servico": "Calibração ADAS",
                "veiculo": {
                    "modelo": "Jeep Compass",
                    "placa": "JKL3456",
                    "ano": "2024",
                    "cor": "Vermelho"
                },
                "loja": LOJAS_CARGLASS["SP003"],
                "loja_id": "SP003",
                "data_agendamento": (hoje - timedelta(days=2)).strftime("%d/%m/%Y"),
                "horario_agendamento": "15:00",
                "tecnico_responsavel": "Roberto Lima",
                "tempo_estimado": "4 horas",
                "observacoes": "Calibração completa dos sistemas ADAS após troca de parabrisa",
                "valor_servico": "R$ 850,00", 
                "forma_pagamento": "Dinheiro",
                "data_conclusao": (hoje - timedelta(days=1)).strftime("%d/%m/%Y %H:%M"),
                "garantia_ate": (hoje + timedelta(days=365)).strftime("%d/%m/%Y")
            }
        }
    }
    
    # Mapeamentos para diferentes tipos de consulta
    ordem_para_cpf = {
        "123456": "12345678900",
        "ORD12345": "12345678900",
        "67890": "98765432100", 
        "ORD67890": "98765432100",
        "54321": "11122233344",
        "ORD54321": "11122233344"
    }
    
    telefone_para_cpf = {
        "11987654321": "12345678900",
        "11976543210": "98765432100", 
        "11955556666": "11122233344"
    }
    
    placa_para_cpf = {
        "ABC1234": "12345678900",
        "DEF5678": "98765432100",
        "GHI9012": "11122233344"
    }
    
    # Determina qual CPF usar baseado no tipo de consulta
    cpf_key = None
    if tipo == "cpf" and valor in mock_database:
        cpf_key = valor
    elif tipo == "ordem" and valor in ordem_para_cpf:
        cpf_key = ordem_para_cpf[valor]
    elif tipo == "telefone" and valor in telefone_para_cpf:
        cpf_key = telefone_para_cpf[valor]
    elif tipo == "placa" and valor in placa_para_cpf:
        cpf_key = placa_para_cpf[valor]
    
    if cpf_key and cpf_key in mock_database:
        return mock_database[cpf_key]
    
    return {"sucesso": False, "mensagem": f"Cliente não encontrado para {tipo}: {valor}"}

# ===== RESPOSTAS CONVERSACIONAIS INTELIGENTES =====
def get_smart_ai_response(pergunta: str, cliente_info: Dict[str, Any], platform: str = "web") -> str:
    """
    Gera respostas conversacionais inteligentes baseadas no contexto do cliente
    """
    pergunta_lower = pergunta.lower()
    dados = cliente_info.get('dados', {})
    
    nome = dados.get('nome', 'Cliente')
    status = dados.get('status', '')
    servico = dados.get('tipo_servico', '')
    loja = dados.get('loja', {})
    veiculo = dados.get('veiculo', {})
    
    # Comandos especiais (adaptados para não mencionar WhatsApp)
    if pergunta_lower in ['status', 'situacao', 'situação']:
        return get_detailed_status_response(dados, platform)
    
    if pergunta_lower in ['ajuda', 'help', 'menu', 'opcoes', 'opções']:
        # Opções adaptadas para a web ou outros canais não-WhatsApp
        return """
🤖 *Comandos disponíveis:*

📋 *status* - Situação detalhada
📍 *loja* - Informações da loja
📅 *quando* - Data e horário
💰 *valor* - Informações de pagamento
🛡️ *garantia* - Informações de garantia
👥 *atendente* - Falar com pessoa
🔄 *reiniciar* - Nova consulta

💬 Ou faça sua pergunta!
"""
    
    # Respostas contextuais baseadas no status atual
    if "quando" in pergunta_lower or "data" in pergunta_lower or "horário" in pergunta_lower or "horario" in pergunta_lower:
        return get_scheduling_response(dados, platform)
    
    if "onde" in pergunta_lower or "loja" in pergunta_lower or "local" in pergunta_lower:
        return get_location_response(dados, platform)
    
    if "quanto" in pergunta_lower or "valor" in pergunta_lower or "preço" in pergunta_lower or "preco" in pergunta_lower:
        return get_pricing_response(dados, platform)
    
    if "garantia" in pergunta_lower:
        return get_warranty_response(dados, platform)
    
    if "status" in pergunta_lower or "situação" in pergunta_lower or "situacao" in pergunta_lower:
        return get_detailed_status_response(dados, platform)
    
    if "técnico" in pergunta_lower or "tecnico" in pergunta_lower or "responsável" in pergunta_lower:
        return get_technician_response(dados, platform)
    
    if "cancelar" in pergunta_lower:
        return get_cancellation_response(dados, platform)
    
    if "reagendar" in pergunta_lower or "mudar data" in pergunta_lower:
        return get_reschedule_response(dados, platform)
    
    if "atendente" in pergunta_lower or "pessoa" in pergunta_lower or "humano" in pergunta_lower:
        return get_human_contact_response(platform)
    
    # Resposta baseada no status atual - mais conversacional
    return get_status_contextual_response(dados, pergunta, platform)

def get_detailed_status_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta detalhada sobre o status atual"""
    status = dados.get('status', '')
    nome = dados.get('nome', 'Cliente')
    servico = dados.get('tipo_servico', '')
    loja = dados.get('loja', {})
    
    # Resposta otimizada para web/geral
    if status == "Em andamento":
        return f"""
🔧 Olá **{nome}**!

Seu serviço de **{servico}** está **em execução** neste momento!

📍 **Local:** {loja.get('nome', 'CarGlass')}
🏢 {loja.get('endereco', '')}, {loja.get('bairro', '')}

⏰ **Tempo estimado:** {dados.get('tempo_estimado', 'Em análise')}
👨‍🔧 **Técnico:** {dados.get('tecnico_responsavel', 'Equipe CarGlass')}

Seu veículo está em boas mãos! ✨
"""
    elif status == "Serviço agendado com sucesso":
        return f"""
📅 Olá **{nome}**!

Seu serviço de **{servico}** está **confirmado**!

📍 **Local:** {loja.get('nome', 'CarGlass')}
🏢 {loja.get('endereco', '')}, {loja.get('bairro', '')}

📅 **Data:** {dados.get('data_agendamento', 'A confirmar')}
⏰ **Horário:** {dados.get('horario_agendamento', 'A confirmar')}
👨‍🔧 **Técnico:** {dados.get('tecnico_responsavel', 'A definir')}

Chegue 15 minutos antes! ⏰
"""
    elif status == "Aguardando fotos para liberação da ordem":
        return f"""
📷 Olá **{nome}**!

Precisamos de **fotos do seu veículo** para liberar seu serviço de **{servico}**.

📱 **Envie as fotos por e-mail:** fotos@carglass.com.br

📋 **Fotos necessárias:**
• Dano principal (close)
• Visão geral do vidro
• Documento do veículo

Após recebermos, agendaremos rapidamente! 🚀
"""
    elif status == "Concluído":
        return f"""
✅ Olá **{nome}**!

Seu serviço de **{servico}** foi **concluído com sucesso**!

📅 **Finalizado em:** {dados.get('data_conclusao', 'Recentemente')}
🛡️ **Garantia até:** {dados.get('garantia_ate', '12 meses')}
⭐ **Qualidade CarGlass certificada!**

Obrigado por confiar em nós! 🙏
"""
    else:
        return f"Seu serviço de **{servico}** está com status: **{status}**"

def get_scheduling_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre agendamento e horários"""
    data_agendamento = dados.get('data_agendamento', 'A definir')
    horario = dados.get('horario_agendamento', 'A definir')
    loja = dados.get('loja', {})
    
    if data_agendamento != "A definir":
        return f"""
📅 **Seu agendamento:**

🗓️ **Data:** {data_agendamento}
⏰ **Horário:** {horario}
📍 **Local:** {loja.get('nome', 'CarGlass')}

⏰ **Chegue 15 minutos antes!**
📞 **Para reagendar:** 0800-701-9495
"""
    else:
        return f"""
📅 **Agendamento pendente**

Assim que recebermos as informações necessárias, entraremos em contato para confirmar data e horário.

📞 **Para mais informações:** 0800-701-9495
"""

def get_location_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre localização da loja"""
    loja = dados.get('loja', {})
    
    if not loja:
        return "📍 Informações da loja serão confirmadas em breve. Central: **0800-701-9495**"
    
    return f"""
📍 **{loja.get('nome', 'CarGlass')}**

🏢 {loja.get('endereco', '')}
📍 {loja.get('bairro', '')}, {loja.get('cidade', '')}

📞 **Telefone:** {loja.get('telefone', '')}
⏰ **Horário:** {loja.get('horario', '')}

🚗 Estacionamento disponível
"""

def get_pricing_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre valores e pagamento"""
    valor = dados.get('valor_servico', 'A definir')
    pagamento = dados.get('forma_pagamento', 'A definir')
    
    return f"""
💰 **Informações de pagamento:**

💵 **Valor:** {valor}
💳 **Forma:** {pagamento}

**Aceitos:** Dinheiro, cartão, PIX, seguros
📞 **Dúvidas:** 0800-701-9495
"""

def get_warranty_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre garantia"""
    servico = dados.get('tipo_servico', '')
    
    return f"""
🛡️ **Garantia CarGlass para {servico}:**

⏰ **12 meses** a partir da conclusão
✅ Defeitos de instalação
✅ Problemas de vedação  
✅ Válida em qualquer unidade CarGlass

📞 **Central:** 0800-701-9495
"""

def get_technician_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre técnico responsável"""
    tecnico = dados.get('tecnico_responsavel', 'A designar')
    
    return f"👨‍🔧 **Técnico responsável:** {tecnico}\n\nNossa equipe é especializada e certificada CarGlass!"

def get_cancellation_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre cancelamento"""
    return f"""
❌ **Para cancelar seu serviço:**

📞 **Central:** 0800-701-9495

⏰ **Horário:** Segunda a Sexta: 8h às 18h

**Importante:** Cancelamentos com menos de 24h podem ter taxa.
"""

def get_reschedule_response(dados: Dict[str, Any], platform: str) -> str:
    """Resposta sobre reagendamento"""
    return f"""
🔄 **Para reagendar seu serviço:**

📞 **Central:** 0800-701-9495

⏰ **Horário:** Segunda a Sexta: 8h às 18h

**Reagendamentos são gratuitos!**
"""

def get_status_contextual_response(dados: Dict[str, Any], pergunta: str, platform: str) -> str:
    """Resposta contextual baseada no status e pergunta"""
    status = dados.get('status', '')
    nome = dados.get('nome', 'Cliente')
    servico = dados.get('tipo_servico', '')
    
    # Respostas inteligentes baseadas no contexto
    if "preocupado" in pergunta.lower() or "demorar" in pergunta.lower():
        return f"Entendo sua preocupação, {nome}! Seu {servico} está sendo feito com todo cuidado. Nossa equipe é especializada e seguimos rigorosos padrões de qualidade. Em breve estará pronto! 😊"
    
    # Resposta genérica inteligente
    return f"Olá {nome}! Seu {servico} está com status **{status}**. Como posso ajudar? Pergunte sobre horários, local, valores ou qualquer dúvida."

def get_human_contact_response(platform: str) -> str:
    """Resposta para contato humano"""
    return """
👥 **Falar com nossa equipe:**

📞 **Central:** 0800-701-9495

⏰ **Horário:**
• Segunda a Sexta: 8h às 18h
• Sábado: 8h às 12h
"""

# ===== TWILIO HANDLER (APENAS GENÉRICO, SEM WHATSAPP) =====
class TwilioGenericHandler:
    def __init__(self):
        self.account_sid = config.TWILIO_ACCOUNT_SID
        self.auth_token = config.TWILIO_AUTH_TOKEN
        self.generic_number = config.TWILIO_GENERIC_NUMBER
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio Generic handler inicializado com sucesso (sem WhatsApp)")
            except ImportError:
                logger.error("❌ Biblioteca Twilio não instalada. Execute: pip install twilio")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Twilio Generic: {e}")
        else:
            logger.warning("⚠️ Credenciais Twilio não configuradas - serviços Twilio desabilitados")
    
    def is_enabled(self) -> bool:
        return self.client is not None
    
    def send_message(self, to_number: str, message: str) -> bool:
        if not self.is_enabled():
            return False
        
        try:
            clean_number = re.sub(r'[^\d+]', '', to_number)
            if not clean_number.startswith('+'):
                if clean_number.startswith('55'):
                    clean_number = '+' + clean_number
                else:
                    clean_number = '+55' + clean_number
            
            # Aqui você enviaria um SMS, por exemplo, não WhatsApp
            message_instance = self.client.messages.create(
                body=message,
                from_=self.generic_number,
                to=clean_number
            )
            
            logger.info(f"✅ Mensagem Twilio genérica enviada: {message_instance.sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem Twilio genérica: {e}")
            return False

# Instância global do handler Twilio (agora genérico)
twilio_handler = TwilioGenericHandler()

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
        "11122233344",
        "44455566677"
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
    
    if re.match(r'^\d{11}$', clean_text): # CPF (11 dígitos numéricos)
        if validate_cpf(clean_text):
            return "cpf", clean_text
        else:
            return None, clean_text # CPF inválido
    elif re.match(r'^\d{10,11}$', clean_text): # Telefone (10 ou 11 dígitos numéricos)
        return "telefone", clean_text
    elif re.match(r'^[A-Za-z]{3}\d{4}$', clean_text) or re.match(r'^[A-Za-z]{3}\d[A-Za-z]\d{2}$', clean_text): # Placa (Mercosul ou antiga)
        return "placa", clean_text.upper()
    elif re.match(r'^\d{1,8}$', clean_text) or re.match(r'^(ORD)?\d+$', clean_text): # Ordem de serviço (até 8 dígitos numéricos, opcionalmente com "ORD")
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
    platform: str = "web" # Mantido como web, já que o WhatsApp não é usado diretamente
    phone_number: Optional[str] = None # Mantido para compatibilidade, mas não usado ativamente para WhatsApp
    
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
        # self.whatsapp_sessions = {} # Removido, pois não há sessões específicas de WhatsApp
    
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
        
        # Mensagem de boas-vindas sem menção ao WhatsApp
        welcome_msg = "Olá! Sou Clara, sua assistente virtual da CarGlass. Digite seu CPF, telefone ou placa do veículo para começarmos."
        
        session_data.add_message("assistant", welcome_msg)
        
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
            self._remove_session(session_id)
        
        return None
    
    # def get_whatsapp_session(self, phone_number: str) -> Optional[SessionData]: # Removido
    #     pass
    
    def _remove_session(self, session_id: str):
        if session_id in self.sessions:
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
        try:
            import requests
            api_urls = {
                "cpf": "http://fusion-hml.carglass.hml.local:3000/api/status/cpf/",
                "telefone": "http://fusion-hml.carglass.hml.local:3000/api/status/telefone/",
                "ordem": "http://fusion-hml.carglass.hml.local:3000/api/status/ordem/"
            }
            
            if tipo not in api_urls:
                logger.warning(f"Tipo '{tipo}' não suportado pelas APIs")
                return {"sucesso": False, "mensagem": f"Tipo '{tipo}' não suportado"}
            
            endpoint = f"{api_urls[tipo]}{valor}"
            logger.info(f"Consultando API CarGlass: {endpoint}")
            
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
    
    # Fallback para dados mockados melhorados
    logger.info("Usando dados simulados detalhados como fallback")
    mock_data = get_mock_data_enhanced(tipo, valor)
    cache.set(cache_key, mock_data, config.CACHE_TTL)
    return mock_data

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
    
    for i, step in enumerate(steps):
        if i < active_step:
            step["state"] = "completed"
        elif i == active_step:
            step["state"] = "active"
        elif i == active_step + 1 and active_step < len(steps) - 1:
            step["state"] = "next"
    
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
            response = get_smart_ai_response(user_input, session_data.client_info, session_data.platform)
        
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

# Removidas as rotas de webhook e status do WhatsApp
# @app.route('/whatsapp/status')
# def whatsapp_status():
#     pass

# @app.route('/whatsapp/webhook', methods=['POST'])
# def whatsapp_webhook():
#     pass

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
• Entrar em contato: **📞 0800-701-9495**
"""
    
    session_data.client_identified = True
    session_data.client_info = client_data
    
    dados = client_data['dados']
    nome = dados.get('nome', 'Cliente')
    status = dados.get('status', 'Em processamento')
    loja = dados.get('loja', {})
    
    # Resposta otimizada para a web (sem WhatsApp)
    status_class = "agendado" if "agendado" in status.lower() else "andamento"
    status_tag = f'<span class="status-tag {status_class}">{status}</span>'
    
    progress_bar = get_progress_bar_html(client_data)
    
    # Informação conversacional detalhada
    if status == "Em andamento":
        status_info = f"**🔧 Seu serviço de {dados.get('tipo_servico', '')} está sendo executado AGORA na {loja.get('nome', 'nossa loja')}!** O técnico {dados.get('tecnico_responsavel', 'responsável')} está trabalhando no seu {dados.get('veiculo', {}).get('modelo', 'veículo')}."
    elif status == "Serviço agendado com sucesso":
        status_info = f"**📅 Seu serviço está confirmado para {dados.get('data_agendamento', 'em breve')} às {dados.get('horario_agendamento', 'horário a definir')}** na {loja.get('nome', 'nossa loja')}. Chegue 15 minutos antes!"
    else:
        status_info = f"**Status atual:** {status}"
    
    return f"""
👋 **Olá {nome}!** Encontrei suas informações.

{status_info}

{progress_bar}

📋 **Resumo Completo:**
• **Ordem:** {dados.get('ordem', 'N/A')}
• **Serviço:** {dados.get('tipo_servico', 'N/A')}
• **Veículo:** {dados.get('veiculo', {}).get('modelo', 'N/A')} ({dados.get('veiculo', {}).get('ano', 'N/A')}) - {dados.get('veiculo', {}).get('cor', '')}
• **Placa:** {dados.get('veiculo', {}).get('placa', 'N/A')}
• **Local:** {loja.get('nome', 'A definir')}

💬 **Como posso ajudar?** Pergunte sobre horários, localização, valores, garantia ou qualquer dúvida!
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
            "total": len(session_manager.sessions)
        },
        "cache_items": len(cache.cache),
        "twilio_enabled": twilio_handler.is_enabled(),
        "config": {
            "use_real_api": config.USE_REAL_API,
            "openai_configured": bool(config.OPENAI_API_KEY)
        }
    })

if __name__ == '__main__':
    logger.info("🚀 CarGlass Assistant v2.1 - IA Conversacional iniciando...")
    logger.info(f"Modo API: {'REAL' if config.USE_REAL_API else 'SIMULAÇÃO'}")
    logger.info(f"OpenAI: {'CONFIGURADO' if config.OPENAI_API_KEY else 'FALLBACK'}")
    logger.info(f"Twilio Generic: {'HABILITADO' if twilio_handler.is_enabled() else 'DESABILITADO'}")
    logger.info("📞 Central CarGlass: 0800-701-9495")
    
    app.run(debug=config.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
