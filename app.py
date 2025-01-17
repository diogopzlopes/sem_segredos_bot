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

model = genai.GenerativeModel("gemini-2.0-flash-exp")

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

@app.route('/')
def home():
    conversations = load_conversations()
    current_chat_id = session.get('current_chat_id')
    
    if not conversations:
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversations[chat_id] = {
            'title': 'Nova Conversa',
            'history': [],
            'created_at': datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        save_conversations(conversations)
        session['current_chat_id'] = chat_id
    
    return render_template(
        'chatbot.html',
        conversations=conversations,
        current_chat_id=current_chat_id,
        chat_history=conversations.get(current_chat_id, {}).get('history', []) if current_chat_id else [],
        agents=get_agents()
    )

@app.route('/new_chat', methods=['POST'])
def new_chat():
    chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conversations = load_conversations()
    conversations[chat_id] = {
        'title': 'Nova Conversa',
        'history': [],
        'created_at': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    save_conversations(conversations)
    session['current_chat_id'] = chat_id
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
    data = request.json
    user_message = data.get('message', '')
    image_data = data.get('image')
    current_chat_id = session.get('current_chat_id')
    agent_id = data.get('agent_id', 'default')
    
    if not current_chat_id:
        return jsonify({'error': 'No active chat'}), 400

    try:
        conversations = load_conversations()
        current_chat = conversations.get(current_chat_id)
        history = current_chat.get('history', [])
        
        # Obter a instrução do sistema do agente selecionado
        agents = get_agents()
        agent = agents.get(agent_id, agents['default'])
        system_instruction = agent['instruction']

        # Construir o contexto completo
        if image_data:
            # Para imagens, usamos uma abordagem mais simples
            messages = []
            if system_instruction:
                messages.append(system_instruction)
            messages.append(user_message)
            
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            messages.append(image)
            
            response = model.generate_content(messages)
        else:
            # Para texto, construímos um prompt mais estruturado
            conversation = ""
            if system_instruction:
                conversation += f"System: {system_instruction}\n\n"
            
            # Adicionar histórico anterior
            for msg in history:
                prefix = "Human: " if msg["role"] == "user" else "Assistant: "
                conversation += f"{prefix}{msg['parts']}\n"
            
            # Adicionar mensagem atual
            conversation += f"Human: {user_message}\nAssistant:"
            
            response = model.generate_content(conversation)
        
        # Atualizar histórico
        history.append({
            "role": "user",
            "parts": user_message
        })
        history.append({
            "role": "model",
            "parts": response.text
        })
        
        # Atualizar título se for primeira mensagem
        if len(history) == 2:
            current_chat['title'] = user_message[:30] + '...' if len(user_message) > 30 else user_message
        
        current_chat['history'] = history
        conversations[current_chat_id] = current_chat
        save_conversations(conversations)

        return jsonify({
            'response': response.text,
            'history': history
        })

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({
            'response': 'Desculpe, ocorreu um erro ao processar sua mensagem.',
            'error': str(e)
        }), 500

@app.route('/test_static')
def test_static():
    static_files = os.listdir('static')
    return jsonify({
        'static_exists': os.path.exists('static'),
        'files_in_static': static_files
    })

if __name__ == '__main__':
    app.run(debug=True)