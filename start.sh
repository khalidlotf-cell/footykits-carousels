#!/bin/bash

echo "🚀 Démarrage de Footykits Carousel Generator..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé. Installe Python depuis python.org"
    exit 1
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "📦 Installation des dépendances..."
pip install -r requirements.txt -q

# Create folders
mkdir -p uploads/category1 uploads/category2 generated

# Start app
echo ""
echo "✅ Tout est prêt !"
echo "👉 Ouvre http://localhost:8080 dans ton navigateur"
echo ""
python3 app.py
