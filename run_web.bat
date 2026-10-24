@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Confere Placa Web - Inicializacao Windows
echo ==========================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Instale o Python 3 (https://www.python.org) e marque "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [*] Criando ambiente virtual (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

echo [*] Verificando dependencias...
call .venv\Scripts\pip.exe install -q -r requirements.txt

echo.
echo ==========================================================
echo   🚗 Confere Placa Web - Servidor Iniciado!
echo   Acesse no navegador: http://localhost:8000
echo   Usuario inicial: admin ^| Senha: exibida abaixo no primeiro inicio
echo ==========================================================
echo.

call .venv\Scripts\uvicorn.exe web.main:app --host 0.0.0.0 --port 8000 --reload
pause
