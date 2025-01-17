<div>
<h2>Junte-se ao nosso servidor Discord!</h2>

<a href="https://discord.gg/762358903354687548"><img src="http://invidget.switchblade.xyz/762358903354687548?language=pt" style="width: 400px;"/></a>
</div>

![Logo da Empresa](static/site1.png)

# Sem Segredos Bot

Um chatbot interativo usando a API Gemini do Google.

## Funcionalidades

- Chat interativo com o modelo Gemini gratuito
- Suporte a criação de diferentes personalidades
- Sistema de histórico de conversas
- Interface web amigável

<img src="static/screenshot.jpg" alt="Screenshot do Projeto" width="800"/>

## Configuração

1. Abra o terminal do Windows:

2. Clone o repositório:
  ```bash
  git clone https://github.com/diogopzlopes/sem_segredos_bot.git
  cd sem_segredos_bot
  ```

3. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   ```

   - Para ativar no Windows:
     ```bash
     venv\Scripts\activate
     ```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Pegue sua chave api em https://aistudio.google.com/app/apikey
```bash
Crie e copie sua chave api (modelo usado no projeto é gratuito)
```

6. Renomear o arquivo .env.example para .env - Botão direito, editar com bloco de notas, adicione sua chave api e salve:
```
GEMINI_API_KEY=sua_api_key_aqui
```

7. Execute a aplicação - No terminal digite:
```bash
python app.py
```

8. Acesse o bot no navegador:
```
http://localhost:5000
```
