@echo off
echo Iniciando o Sem Segredos Bot...

:: Verificar se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado! Por favor, instale o Python 3.x
    pause
    exit
)

:: Verificar se a pasta venv existe, se não, criar
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)

:: Ativar o ambiente virtual
call venv\Scripts\activate

:: Instalar dependências se requirements.txt existir
if exist requirements.txt (
    echo Instalando/atualizando dependencias...
    pip install -r requirements.txt
)

:: Iniciar o servidor em segundo plano
start /B python app.py

:: Aguardar alguns segundos para o servidor iniciar
timeout /t 3 /nobreak

:: Abrir o navegador
start http://127.0.0.1:5000

echo Servidor iniciado! Acesse http://127.0.0.1:5000
echo Para encerrar, feche esta janela.
pause 