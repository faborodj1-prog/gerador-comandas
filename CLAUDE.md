# CLAUDE.md

Guia do projeto para o Claude Code (e para humanos). Mantém registrado o que o
código não deixa óbvio.

## Visão geral

**Gerador de Comandas** — editor visual web para gerar comandas de restaurante
em lote, com QR Code ou código de barras, template de fundo, drag & drop e
exportação em PDF/ZIP.

- **Backend:** FastAPI + Pillow (`main.py`)
- **Frontend:** HTML/JS/CSS puro, arquivo único (`static/index.html`, ~3.900 linhas)
- **Deploy:** Render (plano free) — `render.yaml` + `build.sh`
- **Python fixado em 3.11.9** (`runtime.txt`) por compatibilidade com Pillow

## Como rodar

```bash
pip install -r requirements.txt
python main.py
```

Acessa em `http://localhost:8000`. A porta vem de `PORT` (env); `reload` só liga
localmente (desliga quando a env `RENDER` existe).

## Estrutura

```
main.py              ← Backend FastAPI (renderização com Pillow)
static/index.html    ← Frontend completo (editor, tudo inline)
baixar_fontes.py     ← Baixa as fontes .ttf faltantes (roda no build do Render)
fonts/               ← 21 fontes .ttf curadas, versionadas no repo
requirements.txt     ← Dependências (sem versão travada, usa >=)
render.yaml          ← Config de deploy do Render
build.sh             ← Build do Render: instala deps + baixa fontes
runtime.txt          ← Python 3.11.9
README.md            ← Instruções de instalação/uso
ROADMAP.md           ← Roadmap (DESATUALIZADO — ver "Pontos de atenção")
```

## Endpoints (main.py)

| Rota | Método | Função |
|------|--------|--------|
| `/` | GET | Serve o `index.html` |
| `/fontes` | GET | Lista fontes (curadas + SO + do usuário) |
| `/preview` | POST | Renderiza 1 comanda para preview (PNG) |
| `/gerar-pdf` | POST | Gera PDF/ZIP em lote |
| `/qualidade-presets` | GET | Presets de DPI para o PDF |
| `/qr-img-presets` | GET | Presets de tamanho para QR standalone |
| `/preview-qr-img` | POST | Preview de 1 QR Code (JPEG) |
| `/gerar-qr-zip` | POST | Gera N QR Codes em ZIP de imagens |
| `/remover-fundo-cor` | POST | Remove fundo por cor (Pillow) |
| `/remover-fundo-ia` | POST | Remove fundo por IA (`rembg`, opcional) |
| `/ping` | GET | Health check (warm-up do Render) |

## Regra de negócio central

O QR Code **não** contém o número cru. Ele embute uma URL de autoatendimento:

1. Documento (CNPJ/CPF) é mascarado — ex: `12.345.678/0001-99:` (`aplicar_mascara`)
2. Concatena com o número da comanda → `<doc-mascarado><numero>`
3. Codifica em **base64**
4. Monta: `https://pediucomeu.com.br/autoatendimento/<base64>`

Ver `gerar_qr` / `_gerar_qr_imagem` em `main.py`. Documento válido (14 dígitos
CNPJ / 11 CPF) é **obrigatório** para gerar QR — validado no backend
(`_validar_documento_qr`), não só no frontend.

O **código de barras** usa **Code128** (`gerar_barcode`), que codifica o prefixo
exatamente como digitado (`/`, `;`, `#`, etc). Fallback para Code39 se falhar.
Nota: leitores em layout US/ABNT2 podem converter `/` em `;` — há aviso no frontend.

## Restrições de ambiente (Render free)

O plano free tem **RAM limitada**, e boa parte do histórico do projeto é briga
com isso. Cuidados já implementados — **não remover sem entender o porquê**:

- PDF gerado **página por página**, com `del img` e `gc.collect()` entre páginas
  (`gerar_pdf`), para não acumular tudo na RAM.
- `lote_max` fixado em **20** por preset de qualidade (`QUALIDADE_PRESETS`).
- Cache de fontes limitado a 30 entradas (`_FONTE_CACHE_MAX`).
- Disco do Render free é **efêmero**: qualquer arquivo salvo em runtime some em
  reinícios/deploys. (Relevante para qualquer ideia de contador/persistência.)

## Convenções

- Código e comentários em **português (pt-BR)**.
- Mensagens de erro estruturadas por código, ex:
  `DOCUMENTO_INVALIDO:CNPJ:14`, `LIMITE_EXCEDIDO:<total>:<max>:<qualidade>` —
  o frontend faz o parse e mostra mensagem amigável.
- Commits: prefixo `feat:` / `fix:` / `refactor:` com descrição em português.
- Fontes são a fonte primária (`_FONTES_LOCAL`); SO é fallback (`_FONTES_SISTEMA`).

## Pontos de atenção / dívida técnica

- **ROADMAP.md está desatualizado**: diz que o deploy é "planejado" e sugere
  Railway, mas o projeto já roda no Render. Fase 2 com caixas vazias.
- **`requirements.txt` sem versões travadas** (`>=`): já causou quebra de deploy
  (Pillow/Python). Travar versões evitaria surpresas.
- **Loops pixel-a-pixel** em `remover_fundo_cor` e na recoloração de
  `gerar_barcode`: lentos para imagens grandes; NumPy resolveria.
- **`index.html` monolítico** (~3.900 linhas): CSS+HTML+JS num arquivo só.
- **CORS liberado** (`allow_origins=["*"]`) e **sem autenticação**: ok para uso
  interno; revisar antes de expor publicamente.
- **Sem testes automatizados e sem CI.**

## Estado atual (decisões tomadas)

- Manter o projeto **como está** por enquanto — sem novas features.
- Ideias discutidas, ainda **não implementadas**:
  - Contador de acessos (pendente decidir: simples/pode-zerar vs persistente;
    contar acessos vs pessoas únicas).
  - Possível migração de hospedagem (Railway = mais fácil, banco+cache inclusos;
    VPS Hostinger = mais barato em R$ e mais RAM, mas exige administração).
