# -*- coding: utf-8 -*-
"""
Baixa fontes gratuitas (OFL/Apache) para a pasta fonts/.
Relevantes para o segmento de alimentacao / comandas.

Execute:  python baixar_fontes.py
"""
import urllib.request
import os
import sys

# Forcar UTF-8 no terminal Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PASTA = "fonts"

# Fontes via fontsource CDN (jsdelivr) — URLs estaveis e confiavéis
FONTES_CDN = [
    ("Anton-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/anton@latest/latin-400-normal.ttf"),
    ("BebasNeue-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/bebas-neue@latest/latin-400-normal.ttf"),
    ("Oswald-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/oswald@latest/latin-700-normal.ttf"),
    ("Oswald-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/oswald@latest/latin-400-normal.ttf"),
    ("Roboto-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/roboto@latest/latin-700-normal.ttf"),
    ("Roboto-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/roboto@latest/latin-400-normal.ttf"),
    ("OpenSans-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/open-sans@latest/latin-700-normal.ttf"),
    ("OpenSans-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/open-sans@latest/latin-400-normal.ttf"),
    ("Montserrat-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/montserrat@latest/latin-700-normal.ttf"),
    ("Montserrat-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/montserrat@latest/latin-400-normal.ttf"),
    ("Inter-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-700-normal.ttf"),
    ("Inter-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-400-normal.ttf"),
    ("PlayfairDisplay-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/playfair-display@latest/latin-700-normal.ttf"),
    ("PlayfairDisplay-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/playfair-display@latest/latin-400-normal.ttf"),
    ("SourceSansPro-Bold.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/source-sans-pro@latest/latin-700-normal.ttf"),
    ("SourceSansPro-Regular.ttf",
     "https://cdn.jsdelivr.net/fontsource/fonts/source-sans-pro@latest/latin-400-normal.ttf"),
]

# Fontes ja baixadas do GitHub (manter por compatibilidade)
FONTES_GH = [
    ("Lato-Bold.ttf",
     "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Bold.ttf"),
    ("Lato-Regular.ttf",
     "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf"),
    ("Pacifico-Regular.ttf",
     "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf"),
    ("Ubuntu-Bold.ttf",
     "https://github.com/google/fonts/raw/main/ufl/ubuntu/Ubuntu-Bold.ttf"),
    ("Ubuntu-Regular.ttf",
     "https://github.com/google/fonts/raw/main/ufl/ubuntu/Ubuntu-Regular.ttf"),
]

TODAS = FONTES_CDN + FONTES_GH

os.makedirs(PASTA, exist_ok=True)

ok = 0
erros = []

print(f"\nBaixando {len(TODAS)} fontes para '{PASTA}/'...\n")

for nome, url in TODAS:
    dest = os.path.join(PASTA, nome)
    if os.path.exists(dest):
        print(f"  [OK]  {nome} (ja existe)")
        ok += 1
        continue
    print(f"  [DL]  {nome} ...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            dados = resp.read()
            f.write(dados)
        print(f"OK ({len(dados)//1024} KB)")
        ok += 1
    except Exception as e:
        print(f"ERRO ({e})")
        erros.append(nome)

print(f"\n{'='*50}")
print(f"[RESULTADO] {ok}/{len(TODAS)} fontes prontas em '{PASTA}/'")
if erros:
    print(f"[ERRO] Falhas: {', '.join(erros)}")
else:
    print("[OK] Todas as fontes baixadas com sucesso!")
print("\nReinicie o servidor (python main.py) para que as fontes aparecam.")
