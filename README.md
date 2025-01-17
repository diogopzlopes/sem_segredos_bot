# Sem Segredos Bot

Um chatbot interativo usando a API Gemini do Google.

## Configuração

1. Clone o repositório:
```bash
git clone https://github.com/diogopzlopes/sem_segredos_bot.git
cd sem_segredos_bot
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` na raiz do projeto e adicione sua API key do Google:
```
GEMINI_API_KEY=sua_api_key_aqui
```

4. Execute a aplicação:
```bash
python app.py
```

5. Acesse o bot no navegador:
```
http://localhost:5000
```

## Funcionalidades

- Chat interativo com o modelo Gemini
- Suporte a múltiplos agentes com diferentes personalidades
- Sistema de histórico de conversas
- Interface web amigável

## Observações

- Os arquivos de dados (agents.json e conversations.json) serão criados automaticamente na primeira execução
- Um agente padrão será criado automaticamente
- Todas as conversas são salvas localmente
