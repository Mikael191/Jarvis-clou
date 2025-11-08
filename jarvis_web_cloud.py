"""
Jarvis AI - Servidor Web Cloud (Render/Heroku)
Backend Flask otimizado para hospedagem gratuita sem microfone
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import re
import requests
import json
import os
import psutil
import platform
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jarvis_secret_key_2024')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuração da API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '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')

def clean_text(text):
    """Remove asteriscos e markdown"""
    if not text:
        return text
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_groq_response(question):
    """Obtém resposta usando Groq API"""
    try:
        if not GROQ_API_KEY:
            return None
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system",
                    "content": "Você é o Jarvis, um assistente virtual inteligente e prestativo. Responda sempre em português brasileiro de forma clara e concisa. NUNCA use asteriscos (*) ou markdown na resposta, apenas texto puro."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content'].strip()
                text = re.sub(r'\*+', '', text)
                text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)
                return text
            
    except Exception as e:
        print(f"Erro Groq API: {e}")
    
    return None

def smart_response(question):
    """Respostas inteligentes baseadas em padrões"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite']):
        hora = datetime.now().hour
        if hora < 12:
            return "Bom dia! Como posso ajudá-lo hoje?"
        elif hora < 18:
            return "Boa tarde! Em que posso ser útil?"
        else:
            return "Boa noite! Como posso ajudá-lo?"
    
    if any(word in question_lower for word in ['que horas', 'hora', 'horário']):
        hora = datetime.now().strftime("%H:%M")
        return f"São exatamente {hora}."
    
    if any(word in question_lower for word in ['que dia', 'data', 'hoje']):
        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        agora = datetime.now()
        data = f"{agora.day} de {meses[agora.month - 1]} de {agora.year}"
        return f"Hoje é {data}."
    
    if any(word in question_lower for word in ['quem é você', 'seu nome', 'você é', 'quem você']):
        return "Eu sou o Jarvis, seu assistente virtual pessoal. Estou hospedado na nuvem e disponível 24/7 para ajudá-lo!"
    
    if any(word in question_lower for word in ['como você está', 'tudo bem', 'status']):
        return "Estou funcionando perfeitamente na nuvem, senhor. Online 24/7 e pronto para executar qualquer comando!"
    
    if any(word in question_lower for word in ['obrigado', 'obrigada', 'valeu', 'agradeço']):
        return "De nada! Estou sempre à disposição para ajudá-lo."
    
    return "Entendi sua pergunta. Pode reformular de outra forma ou ser mais específico?"

@app.route('/')
def index():
    """Página principal"""
    return render_template('index_cloud.html')

@app.route('/health')
def health():
    """Health check para Render"""
    return jsonify({"status": "healthy", "service": "Jarvis AI"}), 200

@socketio.on('connect')
def handle_connect():
    """Cliente conectado"""
    emit('status', {'message': 'Conectado ao Jarvis Cloud - Online 24/7!', 'type': 'success'})

@socketio.on('disconnect')
def handle_disconnect():
    """Cliente desconectado"""
    print('Cliente desconectado')

@socketio.on('question')
def handle_question(data):
    """Processa pergunta via texto"""
    question = data.get('text', '')
    if question:
        process_question(question)

def process_question(question):
    """Processa pergunta do usuário"""
    if not question or not question.strip():
        return
    
    question_lower = question.lower().strip()
    
    if any(word in question_lower for word in ['sair', 'encerrar', 'desligar', 'tchau', 'até logo']):
        response = "Até logo! Estarei aqui 24/7 quando precisar de mim novamente."
        socketio.emit('jarvis_speech', {'text': response})
        return
    
    try:
        socketio.emit('processing', {'status': True})
        
        # Tenta obter resposta da IA
        response = get_groq_response(question)
        
        if not response:
            response = smart_response(question)
        
        if response:
            clean_response = clean_text(response)
            if clean_response:
                socketio.emit('jarvis_speech', {'text': clean_response})
            else:
                socketio.emit('error', {'message': 'Resposta vazia recebida'})
        else:
            socketio.emit('error', {'message': 'Não foi possível processar sua pergunta'})
            
    except Exception as e:
        error_msg = f'Erro ao processar: {str(e)}'
        socketio.emit('error', {'message': error_msg})
        print(f"Erro ao processar pergunta: {e}")
    finally:
        socketio.emit('processing', {'status': False})

@socketio.on('get_system_info')
def handle_system_info():
    """Retorna informações do sistema"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        mem = psutil.virtual_memory()
        mem_total = mem.total / (1024**3)
        mem_used = mem.used / (1024**3)
        mem_percent = mem.percent
        
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)
        disk_free = disk.free / (1024**3)
        disk_percent = disk.percent
        
        net = psutil.net_io_counters()
        sent_mb = net.bytes_sent / (1024**2)
        recv_mb = net.bytes_recv / (1024**2)
        
        info = {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count
            },
            'memory': {
                'total': mem_total,
                'used': mem_used,
                'percent': mem_percent
            },
            'disk': {
                'total': disk_total,
                'free': disk_free,
                'percent': disk_percent
            },
            'network': {
                'sent': sent_mb,
                'received': recv_mb
            },
            'os': {
                'system': platform.system(),
                'release': platform.release(),
                'processor': 'Cloud Server',
                'python': platform.python_version()
            }
        }
        
        emit('system_info', info)
    except Exception as e:
        emit('error', {'message': f'Erro ao obter info do sistema: {e}'})

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("JARVIS AI - Cloud Server")
    print("=" * 50)
    print(f"Porta: {PORT}")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
