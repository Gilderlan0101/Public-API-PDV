#!/bin/bash

# A opção 'set -e' faz o script parar imediatamente se algum comando retornar erro.
# Isso evita que o servidor suba se houver erro de sintaxe na formatação.
set -e

#cho "🎨 [1/3] Executando Blue (Formatação)..."
# O ponto (.) indica para rodar na raiz/diretório atual recursivamente
blue .

#echo "🧹 [2/3] Executando Isort (Organização de Imports)..."
#isort .

#echo "🚀 [3/3] Iniciando Servidor (Main.py)..."
# Define explicitamente o ambiente como development para garantir
export ENVIRONMENT=development

# Executa o seu entrypoint
python3 Main.py
