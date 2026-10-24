#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "[*] Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
fi

# Ensure dependencies are installed
echo "[*] Verificando dependências..."
.venv/bin/pip install -q -r requirements.txt

echo "=========================================================="
echo "  🚗 Confere Placa Web - Servidor Iniciado"
echo "  Acesse no navegador: http://localhost:8000"
echo "  Usuário inicial: admin | Senha: exibida abaixo no primeiro início"
echo "=========================================================="

# Start FastAPI server via uvicorn
exec .venv/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload
