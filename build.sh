#!/usr/bin/env bash
# build.sh — executado pelo Render antes de iniciar o servidor
set -e

echo "==> Instalando dependencias Python..."
pip install -r requirements.txt

echo "==> Verificando fontes..."
mkdir -p fonts

# Baixa fontes faltantes (caso nao estejam no repositorio)
python baixar_fontes.py

echo "==> Build concluido."
