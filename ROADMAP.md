# 🗺️ Roadmap do Projeto — Gerador de Comandas

## Estratégia de desenvolvimento

> **Fase atual: Desenvolvimento local em Python**
> Rodar localmente, ajustar, validar — depois subir para produção online.

---

## ✅ Fase 1 — Base local (CONCLUÍDA)

- [x] Editor visual com drag & drop no navegador
- [x] Escolha exclusiva entre QR Code ou Código de Barras
- [x] Arrastar e redimensionar elementos no canvas
- [x] Adicionar: QR Code, Código de Barras, Texto livre, Número da comanda, Logo/imagem
- [x] Painel de propriedades (posição, tamanho, rotação, cor, fonte, alinhamento)
- [x] Salvar e carregar padrões de layout (persistidos no navegador)
- [x] Preview real da comanda (renderizado pelo backend Python/Pillow)
- [x] Geração de PDF em lote (N a M comandas)
- [x] Download em PDF ou ZIP
- [x] Backend FastAPI + Pillow + qrcode + python-barcode
- [x] Suporte a fontes TTF customizadas (pasta `fonts/`)

---

## 🔧 Fase 2 — Ajustes e melhorias (EM ANDAMENTO)

> Rodar localmente, testar com templates reais, listar o que precisa mudar.

### Funcionalidades a ajustar / adicionar
- [ ] _anotar aqui o que for surgindo durante os testes_
- [ ] _ex: ajuste fino de posicionamento_
- [ ] _ex: novo tipo de elemento_
- [ ] _ex: melhoria visual no editor_

### Bugs encontrados
- [ ] _anotar aqui_

---

## 🚀 Fase 3 — Deploy online (PLANEJADO)

> Após validação local completa, subir para acesso via link no navegador.

### Plataforma escolhida
- [ ] **Railway** (recomendado — gratuito, fácil, suporta FastAPI)
- [ ] Render
- [ ] Fly.io
- [ ] VPS próprio

### Checklist antes do deploy
- [ ] Testar geração de PDF com templates reais
- [ ] Validar QR Codes gerados com leitor real
- [ ] Validar Código de Barras com leitor de PDV
- [ ] Revisar limite de comandas por lote
- [ ] Adicionar autenticação básica (opcional)
- [ ] Configurar variáveis de ambiente
- [ ] Testar em diferentes navegadores (Chrome, Firefox, Edge)

### O que muda no deploy
- Padrões salvos passam do `localStorage` do navegador para banco de dados (SQLite ou PostgreSQL)
- Templates e logos enviados ficam em storage (local ou S3)
- URL pública em vez de `localhost:8000`

---

## 🏃 Como rodar localmente agora

```bash
# 1. Entrar na pasta do projeto
cd gerador-comandas

# 2. Instalar dependências (só na primeira vez)
pip install -r requirements.txt

# 3. Rodar
python main.py

# 4. Acessar no navegador
http://localhost:8000
```

---

## 📁 Estrutura do projeto

```
gerador-comandas/
│
├── main.py              ← Backend Python (FastAPI + Pillow)
├── requirements.txt     ← Dependências
├── README.md            ← Instruções de instalação
├── ROADMAP.md           ← Este arquivo
│
├── fonts/               ← Fontes .ttf customizadas
│   └── (coloque seus .ttf aqui)
│
└── static/
    └── index.html       ← Frontend completo (editor visual)
```

---

## 🧰 Stack técnica

| Camada | Tecnologia | Motivo |
|--------|-----------|--------|
| Backend | Python + FastAPI | Rápido, leve, fácil de manter |
| Imagem | Pillow | Mesma lib do projeto original |
| QR Code | qrcode[pil] | Mesma lib do projeto original |
| Barcode | python-barcode | Mesma lib do projeto original |
| Frontend | HTML + JS puro | Sem dependências, roda em qualquer browser |
| Padrões (local) | localStorage | Simples, funciona offline |
| Padrões (produção) | SQLite / PostgreSQL | A definir no deploy |

---

_Atualizado em: início do desenvolvimento — Fase 1 concluída_
