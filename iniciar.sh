#!/usr/bin/env bash
# Script para iniciar o MediaFinder no Linux (Regata OS / openSUSE / Ubuntu / Fedora)

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Garante display do ambiente gráfico
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Detecta automaticamente autorização X11 se necessário
if [ -z "$XAUTHORITY" ] || [ ! -f "$XAUTHORITY" ]; then
    LATEST_XAUTH=$(ls -t /tmp/xauth_* 2>/dev/null | head -n 1)
    if [ -n "$LATEST_XAUTH" ] && [ -r "$LATEST_XAUTH" ]; then
        export XAUTHORITY="$LATEST_XAUTH"
    fi
fi

# Prioriza o ambiente virtual local .venv se existir
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Erro: Python 3 não foi encontrado no sistema."
    exit 1
fi

echo "🚀 Iniciando o MediaFinder..."
exec "$PYTHON_BIN" "$DIR/main.py" "$@"
