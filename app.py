from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
import google.generativeai as genai
from dotenv import load_dotenv
import os
import base64
from PIL import Image
import io
from datetime import datetime
import json
from pathlib import Path
import webbrowser
import logging
from abc import ABC, abstractmethod
from mistralai import Mistral

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Tente carregar variáveis de ambiente do arquivo .env
try:
    load_dotenv()
except Exception as e:
    print(f"Erro ao carregar o arquivo .env: {e}")

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.urandom(24)  # Necessário para usar sessions

# Obter a chave da API do ambiente
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    print("A chave da API não foi encontrada. Verifique o arquivo .env.")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-pro')

# Criar constantes para os arquivos de dados
DATA_DIR = Path("data")
AGENTS_FILE = DATA_DIR / "agents.json"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"

# Garantir que o diretório de dados existe
DATA_DIR.mkdir(exist_ok=True)

print("Pasta static existe:", os.path.exists('static'))
print("Imagem existe:", os.path.exists('static/site1.png'))

def load_agents():
    if AGENTS_FILE.exists():
        with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Agente padrão se arquivo não existir
    default_agents = {
        'default': {
            'name': 'Padrão',
            'instruction': '',
            'created_at': datetime.now().strftime("%d/%m/%Y %H:%M")
        }
    }
    # Criar arquivo com agente padrão
    with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_agents, f, ensure_ascii=False, indent=4)
    return default_agents

def save_agents(agents):
    with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)

def load_conversations():
    if CONVERSATIONS_FILE.exists():
        with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Criar arquivo vazio se não existir
    empty_conversations = {}
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(empty_conversations, f, ensure_ascii=False, indent=4)
    return empty_conversations

def save_conversations(conversations):
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

# Modificar a função get_agents para usar o arquivo
def get_agents():
    return load_agents()

# Classe base para modelos de IA
class AIModel(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

# Implementação do modelo Gemini
class GeminiModel(AIModel):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.debug("Gemini inicializado com modelo: gemini-2.0-flash-exp")
    
    def generate_response(self, prompt: str, image_data: str = None, history=None) -> str:
        try:
            logger.debug(f"Gerando resposta Gemini para prompt: {prompt[:100]}...")
            
            if image_data:
                logger.debug("Processando imagem...")
                try:
                    # Processar a imagem
                    if ',' in image_data:
                        image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    messages = []
                    if history:
                        for msg in history:
                            messages.append(msg['parts'])
                    
                    messages.append(prompt)
                    messages.append(image)
                    
                    response = self.model.generate_content(messages)
                    return response.text
                except Exception as img_error:
                    logger.error(f"Erro ao processar imagem: {str(img_error)}")
                    raise
            
            # Se não houver imagem, usar o modelo com histórico
            conversation = ""
            if history:
                for msg in history:
                    prefix = "Human: " if msg["role"] == "user" else "Assistant: "
                    conversation += f"{prefix}{msg['parts']}\n"
            
            conversation += f"Human: {prompt}\nAssistant:"
            
            logger.debug(f"Enviando conversa completa: {conversation[:200]}...")
            response = self.model.generate_content(conversation)
            return response.text
        except Exception as e:
            logger.error(f"Erro no Gemini: {str(e)}")
            raise
    
    def get_name(self) -> str:
        return "Gemini 2.0"

# Implementação do modelo Mistral
class MistralModel(AIModel):
    def __init__(self, api_key: str):
        self.client = Mistral(api_key=api_key)
        self.model = "pixtral-12b-2409"
        logger.debug(f"Mistral inicializado com modelo: {self.model}")
    
    def generate_response(self, prompt: str, image_data: str = None, history=None) -> str:
        try:
            logger.debug(f"Gerando resposta Mistral para prompt: {prompt[:100]}...")
            
            messages = []
            
            # Adicionar system prompt apenas se vier da instrução do agente
            if prompt.startswith("System:"):
                system_msg, user_msg = prompt.split("\n\n", 1)
                messages.append({
                    "role": "system",
                    "content": system_msg.replace("System:", "").strip()
                })
                prompt = user_msg
            
            # Adicionar histórico de mensagens
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        messages.append({
                            "role": "user",
                            "content": msg["parts"]
                        })
                    else:
                        messages.append({
                            "role": "assistant",
                            "content": msg["parts"]
                        })
            
            # Adicionar mensagem atual
            if image_data:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": image_data}
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": prompt
                })

            logger.debug(f"Enviando mensagens para Mistral: {messages}")
            
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            
            logger.debug("Resposta recebida do Mistral")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro detalhado no Mistral: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def get_name(self) -> str:
        return "Mistral (Pixtral-12B)"

# Dicionário global para armazenar os modelos disponíveis
AI_MODELS = {}

# Função para inicializar os modelos disponíveis
def initialize_ai_models():
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            AI_MODELS['gemini'] = GeminiModel(gemini_key)
            logger.info("Modelo Gemini inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar Gemini: {str(e)}")
    
    try:
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            AI_MODELS['mistral'] = MistralModel(mistral_key)
            logger.info("Modelo Mistral inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar Mistral: {str(e)}")

@app.route('/')
def home():
    logger.debug("Iniciando rota principal")
    conversations = load_conversations()
    current_chat_id = session.get('current_chat_id')
    
    if not current_chat_id or current_chat_id not in conversations:
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversations[chat_id] = {
            'title': 'Nova Conversa',
            'history': [],
            'created_at': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'model': 'gemini'  # Modelo padrão
        }
        save_conversations(conversations)
        session['current_chat_id'] = chat_id
        current_chat_id = chat_id
    
    return render_template(
        'chatbot.html',
        conversations=conversations,
        current_chat_id=current_chat_id,
        chat_history=conversations.get(current_chat_id, {}).get('history', []),
        agents=get_agents(),
        available_models=AI_MODELS  # Passando os modelos disponíveis para o template
    )

@app.route('/new_chat', methods=['POST'])
def new_chat():
    logger.debug("Criando novo chat")
    chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conversations = load_conversations()
    conversations[chat_id] = {
        'title': 'Nova Conversa',
        'history': [],
        'created_at': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    save_conversations(conversations)
    session['current_chat_id'] = chat_id
    logger.debug(f"Novo chat criado: {chat_id}")
    return jsonify({'success': True, 'chat_id': chat_id})

@app.route('/switch_chat/<chat_id>')
def switch_chat(chat_id):
    conversations = load_conversations()
    if chat_id in conversations:
        session['current_chat_id'] = chat_id
        return jsonify({
            'success': True,
            'history': conversations[chat_id]['history']
        })
    return jsonify({'success': False}), 404

@app.route('/rename_chat/<chat_id>', methods=['POST'])
def rename_chat(chat_id):
    new_title = request.json.get('title')
    conversations = load_conversations()
    if chat_id in conversations:
        conversations[chat_id]['title'] = new_title
        save_conversations(conversations)
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/delete_chat/<chat_id>', methods=['POST'])
def delete_chat(chat_id):
    conversations = load_conversations()
    if chat_id in conversations:
        del conversations[chat_id]
        save_conversations(conversations)
        if session.get('current_chat_id') == chat_id:
            session['current_chat_id'] = next(iter(conversations)) if conversations else None
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/agents')
def agents():
    return render_template('agents.html', agents=get_agents())

@app.route('/agent/new', methods=['POST'])
def new_agent():
    data = request.json
    agent_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    agents = load_agents()
    agents[agent_id] = {
        'name': data.get('name', 'Novo Agente'),
        'instruction': data.get('instruction', ''),
        'created_at': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    save_agents(agents)
    return jsonify({'success': True, 'agent_id': agent_id})

@app.route('/agent/edit/<agent_id>', methods=['POST'])
def edit_agent(agent_id):
    data = request.json
    agents = load_agents()
    if agent_id in agents:
        agents[agent_id]['name'] = data.get('name', agents[agent_id]['name'])
        agents[agent_id]['instruction'] = data.get('instruction', agents[agent_id]['instruction'])
        save_agents(agents)
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/agent/delete/<agent_id>', methods=['POST'])
def delete_agent(agent_id):
    agents = load_agents()
    if agent_id in agents and agent_id != 'default':
        del agents[agent_id]
        save_agents(agents)
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        logger.debug("Iniciando processamento da mensagem")
        data = request.json
        user_message = data.get('message', '')
        image_data = data.get('image')
        agent_id = data.get('agent_id', 'default')
        model_id = data.get('model_id', 'gemini')
        current_chat_id = session.get('current_chat_id')
        
        logger.debug(f"Mensagem recebida: {user_message}")
        logger.debug(f"Modelo selecionado: {model_id}")
        logger.debug(f"Imagem presente: {'Sim' if image_data else 'Não'}")
        
        if model_id not in AI_MODELS:
            return jsonify({'error': 'Modelo de IA não disponível'}), 400

        selected_model = AI_MODELS[model_id]
        
        # Carregar histórico da conversa atual
        conversations = load_conversations()
        current_chat = conversations.get(current_chat_id, {
            'title': 'Nova Conversa',
            'history': [],
            'model': model_id
        })
        
        history = current_chat.get('history', [])
        
        # Se for a primeira mensagem, renomear o chat automaticamente
        if not history:
            # Pegar as 4 primeiras palavras (ou menos se a mensagem for mais curta)
            words = user_message.split()[:4]
            auto_title = ' '.join(words)
            if len(auto_title) > 30:  # Limitar o tamanho do título
                auto_title = auto_title[:27] + '...'
            current_chat['title'] = auto_title
        
        agents = get_agents()
        agent = agents.get(agent_id, agents['default'])
        system_instruction = agent.get('instruction', '')
        
        prompt = f"{system_instruction}\n\n{user_message}" if system_instruction else user_message
        
        try:
            response_text = selected_model.generate_response(prompt, image_data, history)
            
            # Atualizar histórico
            history.append({
                "role": "user",
                "parts": user_message,
                "has_image": bool(image_data)
            })
            history.append({
                "role": "model",
                "parts": response_text
            })
            
            current_chat['history'] = history
            conversations[current_chat_id] = current_chat
            save_conversations(conversations)

            return jsonify({
                'response': response_text,
                'history': history,
                'model': model_id,
                'title': current_chat['title']  # Retornar o título para atualizar a interface
            })

        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo: {str(e)}")
            return jsonify({
                'error': 'Erro ao gerar resposta',
                'details': str(e)
            }), 500

    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        return jsonify({
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500

@app.route('/test_static')
def test_static():
    static_files = os.listdir('static')
    return jsonify({
        'static_exists': os.path.exists('static'),
        'files_in_static': static_files
    })

@app.route('/available_models')
def available_models():
    return jsonify({
        'models': [
            {'id': model_id, 'name': model.get_name()} 
            for model_id, model in AI_MODELS.items()
        ]
    })

if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask...")
    logger.info(f"API Key presente: {'Sim' if api_key else 'Não'}")
    initialize_ai_models()
    
    # Abrir o navegador apenas se não estiver sendo executado pelo reloader
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        webbrowser.open('http://127.0.0.1:5000/')
    
    try:
        app.run(debug=True)
    except Exception as e:
        logger.error(f"Erro ao iniciar aplicação: {str(e)}")