# 🍽️ Gerador de Comandas

Editor visual de comandas com QR Code ou Código de Barras, drag & drop, padrões salvos e geração de PDF em lote.

---

## ⚙️ Instalação (1 vez só)

### Requisitos
- Python 3.10 ou superior
- pip

### Passo a passo

**1. Abra o terminal na pasta do projeto**

**2. Instale as dependências:**
```bash
pip install -r requirements.txt
```

**3. (Opcional) Adicione fontes:**

Coloque arquivos `.ttf` na pasta `fonts/` para usar fontes personalizadas na geração do PDF.

---

## ▶️ Rodando o projeto

```bash
python main.py
```

Acesse no navegador: **http://localhost:8000**

---

## 🗂️ Estrutura do projeto

```
gerador-comandas/
│
├── main.py              ← Backend (FastAPI)
├── requirements.txt     ← Dependências Python
├── README.md
│
├── fonts/               ← Coloque suas fontes .ttf aqui
│   └── (vazio)
│
└── static/
    └── index.html       ← Frontend completo
```

---

## 🚀 Como usar

1. Acesse http://localhost:8000
2. Escolha **QR Code** ou **Código de Barras**
3. Configure o tamanho do canvas (em pixels)
4. Carregue o **template de fundo** (imagem PNG/JPG da sua comanda)
5. Adicione os elementos: código, número, texto, logo
6. Arraste e redimensione os elementos no canvas
7. Preencha o **Documento** (CNPJ ou CPF) no painel esquerdo
8. Clique em **👁 Preview** para ver como ficará o resultado real
9. Clique em **⬇ Gerar PDF** para baixar as comandas em lote

### Padrões
- Monte seu layout e clique em **🔖 Salvar padrão**
- Os padrões ficam salvos no navegador
- Na próxima vez, clique no padrão para carregar tudo automaticamente

---

## ❓ Dúvidas comuns

**Fontes não aparecem?**
→ Coloque arquivos `.ttf` na pasta `fonts/` e recarregue a página.

**Preview não funciona?**
→ Certifique-se de carregar um template de fundo (campo "Template de fundo" no painel esquerdo).

**Erro ao instalar?**
→ Tente `pip install --upgrade pip` e depois instale novamente.

---

## 📦 Dependências

| Pacote | Uso |
|--------|-----|
| FastAPI | Servidor web |
| Uvicorn | Servidor ASGI |
| Pillow | Processamento de imagem |
| qrcode | Geração de QR Code |
| python-barcode | Geração de código de barras (Code39) |
| python-multipart | Upload de arquivos |
