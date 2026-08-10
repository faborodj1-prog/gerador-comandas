"""
Gerador de Comandas - Backend FastAPI
Rode com: python main.py
Acesse:   http://localhost:8000
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
import qrcode
import base64
import re
import io
import zipfile
import os
import json
from barcode import Code39, Code128
from barcode.writer import ImageWriter
import uvicorn
import gc

# ── Limite de tamanho por parte no upload (multipart) ────────────────
# Versões recentes do Starlette (>=0.40) impõem um limite de 1 MB por parte
# do formulário, rejeitando fundos/logos grandes com "Part exceeded maximum
# size of 1024KB". Elevamos esse limite para 25 MB. O frontend já comprime as
# imagens; isto é uma rede de segurança para o preview/geração nunca travar.
try:
    import inspect
    import starlette.formparsers as _fp
    if "max_part_size" in inspect.signature(_fp.MultiPartParser.__init__).parameters:
        _mpp_init_orig = _fp.MultiPartParser.__init__
        def _mpp_init_patch(self, *args, **kwargs):
            kwargs["max_part_size"] = 25 * 1024 * 1024   # 25 MB
            _mpp_init_orig(self, *args, **kwargs)
        _fp.MultiPartParser.__init__ = _mpp_init_patch
except Exception:
    pass

app = FastAPI(title="Gerador de Comandas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("fonts", exist_ok=True)
app.mount("/fonts-preview", StaticFiles(directory="fonts"), name="fonts-preview")


@app.get("/")
def index():
    # no-cache: garante que cada deploy chegue ao usuário sem hard refresh
    return FileResponse(
        "static/index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ── Fontes curadas na pasta fonts/ (baixadas via baixar_fontes.py) ──────────
# Estas são a fonte PRIMÁRIA — independentes de SO, sempre disponíveis.
_FONTES_LOCAL = [
    # Impacto / destaque — muito usadas em cardápios e comandas
    ("Anton (Impacto)",           "fonts/Anton-Regular.ttf"),
    ("Bebas Neue",                "fonts/BebasNeue-Regular.ttf"),
    # Sans-serif moderna — leitura limpa
    ("Inter Bold",                "fonts/Inter-Bold.ttf"),
    ("Inter Regular",             "fonts/Inter-Regular.ttf"),
    ("Roboto Bold",               "fonts/Roboto-Bold.ttf"),
    ("Roboto Regular",            "fonts/Roboto-Regular.ttf"),
    ("Open Sans Bold",            "fonts/OpenSans-Bold.ttf"),
    ("Open Sans Regular",         "fonts/OpenSans-Regular.ttf"),
    ("Montserrat Bold",           "fonts/Montserrat-Bold.ttf"),
    ("Montserrat Regular",        "fonts/Montserrat-Regular.ttf"),
    ("Oswald Bold",               "fonts/Oswald-Bold.ttf"),
    ("Oswald Regular",            "fonts/Oswald-Regular.ttf"),
    ("Lato Bold",                 "fonts/Lato-Bold.ttf"),
    ("Lato Regular",              "fonts/Lato-Regular.ttf"),
    ("Source Sans Pro Bold",      "fonts/SourceSansPro-Bold.ttf"),
    ("Source Sans Pro Regular",   "fonts/SourceSansPro-Regular.ttf"),
    ("Ubuntu Bold",               "fonts/Ubuntu-Bold.ttf"),
    ("Ubuntu Regular",            "fonts/Ubuntu-Regular.ttf"),
    # Serif — elegante / tradicional
    ("Playfair Display Bold",     "fonts/PlayfairDisplay-Bold.ttf"),
    ("Playfair Display Regular",  "fonts/PlayfairDisplay-Regular.ttf"),
    # Casual / manuscrito
    ("Pacifico",                  "fonts/Pacifico-Regular.ttf"),
]

# ── Fontes do sistema operacional (fallback se a local não existir) ──────────
_FONTES_SISTEMA = [
    # Windows
    ("Impact",                "C:/Windows/Fonts/impact.ttf"),
    ("Arial Black",           "C:/Windows/Fonts/ariblk.ttf"),
    ("Arial Bold",            "C:/Windows/Fonts/arialbd.ttf"),
    ("Arial",                 "C:/Windows/Fonts/arial.ttf"),
    ("Calibri Bold",          "C:/Windows/Fonts/calibrib.ttf"),
    ("Calibri",               "C:/Windows/Fonts/calibri.ttf"),
    ("Tahoma Bold",           "C:/Windows/Fonts/tahomabd.ttf"),
    ("Tahoma",                "C:/Windows/Fonts/tahoma.ttf"),
    ("Trebuchet MS Bold",     "C:/Windows/Fonts/trebucbd.ttf"),
    ("Trebuchet MS",          "C:/Windows/Fonts/trebuc.ttf"),
    ("Verdana Bold",          "C:/Windows/Fonts/verdanab.ttf"),
    ("Verdana",               "C:/Windows/Fonts/verdana.ttf"),
    ("Segoe UI Bold",         "C:/Windows/Fonts/segoeuib.ttf"),
    ("Segoe UI",              "C:/Windows/Fonts/segoeui.ttf"),
    ("Georgia Bold",          "C:/Windows/Fonts/georgiab.ttf"),
    ("Georgia",               "C:/Windows/Fonts/georgia.ttf"),
    ("Times New Roman Bold",  "C:/Windows/Fonts/timesbd.ttf"),
    ("Times New Roman",       "C:/Windows/Fonts/times.ttf"),
    ("Comic Sans MS",         "C:/Windows/Fonts/comic.ttf"),
    # Linux / Mac
    ("DejaVu Sans Bold",      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("DejaVu Sans",           "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("Liberation Sans Bold",  "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("Liberation Sans",       "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
]


@app.get("/fontes")
def listar_fontes():
    """
    Prioridade:
      1. Fontes curadas em fonts/ (_FONTES_LOCAL) → grupo 'sistema' no frontend
      2. Fontes do SO como fallback                → mesmo grupo 'sistema'
      3. Arquivos .ttf adicionados pelo usuário     → grupo 'usuario'
    """
    pasta = "fonts"
    fontes_sistema: dict = {}
    fontes_usuario: dict = {}
    nomes_sistema: set   = set()   # controla duplicatas

    # 1. Fontes curadas na pasta fonts/ (fonte primária)
    for nome, caminho in _FONTES_LOCAL:
        if os.path.exists(caminho):
            fontes_sistema[nome] = caminho
            nomes_sistema.add(os.path.abspath(caminho))

    # 2. Fontes do SO como complemento/fallback
    for nome, caminho in _FONTES_SISTEMA:
        if os.path.exists(caminho) and nome not in fontes_sistema:
            fontes_sistema[nome] = caminho
            nomes_sistema.add(os.path.abspath(caminho))

    # 3. Arquivos .ttf extras adicionados manualmente pelo usuário
    if os.path.isdir(pasta):
        for arq in sorted(os.listdir(pasta)):
            if not arq.lower().endswith(".ttf") or arq.startswith("_"):
                continue
            caminho = os.path.join(pasta, arq)
            if os.path.abspath(caminho) in nomes_sistema:
                continue   # já listada como fonte do sistema
            try:
                f    = ImageFont.truetype(caminho, 10)
                nome = " ".join(f.getname())
            except Exception:
                nome = os.path.splitext(arq)[0]
            fontes_usuario[nome] = caminho

    todas = {**fontes_sistema, **fontes_usuario}
    return {"fontes": todas, "usuario": fontes_usuario, "sistema": fontes_sistema}


def _validar_documento_qr(cfg: dict) -> None:
    """Garante que o documento esteja preenchido corretamente quando tipo_codigo == 'qr'."""
    if cfg.get("tipo_codigo") != "qr":
        return
    nums     = re.sub(r"\D", "", cfg.get("documento", "").strip())
    tipo_doc = cfg.get("tipo_doc", "CNPJ").upper()
    needed   = 14 if tipo_doc == "CNPJ" else 11
    if len(nums) != needed:
        raise HTTPException(
            status_code=400,
            detail=f"DOCUMENTO_INVALIDO:{tipo_doc}:{needed}"
        )


@app.post("/preview")
async def preview(
    template: UploadFile = File(...),
    layout: str = Form(...),
    numero: int = Form(1),
):
    try:
        cfg = json.loads(layout)
        _validar_documento_qr(cfg)
        img_bytes = await template.read()
        background = Image.open(io.BytesIO(img_bytes))
        resultado = renderizar_comanda(background, numero, cfg)
        buf = io.BytesIO()
        resultado.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Layout inválido: {e}")
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ── Presets de qualidade ────────────────────────────────────────────
# dpi       → resolução da imagem gerada
# ram_pag   → RAM estimada por página 400x600 (MB)
# lote_max  → máximo de páginas por lote nesse preset (target ~500MB RAM)
QUALIDADE_PRESETS = {
    "alta":   {"dpi": 300, "label": "Alta (300 DPI) — impressão profissional",  "ram_pag": 6.7, "lote_max": 20},
    "media":  {"dpi": 200, "label": "Média (200 DPI) — impressão padrão",       "ram_pag": 3.0, "lote_max": 20},
    "normal": {"dpi": 150, "label": "Normal (150 DPI) — impressão doméstica",   "ram_pag": 1.7, "lote_max": 20},
    "baixa":  {"dpi": 96,  "label": "Rápida (96 DPI) — tela / PDF digital",     "ram_pag": 0.7, "lote_max": 20},
}

@app.get("/ping")
def ping():
    return {"ok": True}


@app.get("/qualidade-presets")
def get_presets():
    """Retorna presets de qualidade disponíveis para o frontend."""
    return {"presets": QUALIDADE_PRESETS, "padrao": "alta"}


@app.post("/gerar-pdf")
async def gerar_pdf(
    template: UploadFile = File(...),
    layout: str = Form(...),
    inicio: int = Form(1),
    fim: int = Form(10),
    formato: str = Form("pdf"),
    qualidade: str = Form("alta"),
):
    preset = QUALIDADE_PRESETS.get(qualidade, QUALIDADE_PRESETS["alta"])
    dpi    = preset["dpi"]
    limite = preset["lote_max"]
    total  = fim - inicio + 1

    if total <= 0:
        raise HTTPException(status_code=400, detail="Número final deve ser maior que o inicial.")

    try:
        _validar_documento_qr(json.loads(layout))
    except json.JSONDecodeError:
        pass  # erro de JSON será capturado adiante

    if total > limite:
        raise HTTPException(
            status_code=400,
            detail=f"LIMITE_EXCEDIDO:{total}:{limite}:{qualidade}"
        )

    try:
        cfg = json.loads(layout)
        img_bytes = await template.read()
        background = Image.open(io.BytesIO(img_bytes))
        escala_pdf = dpi / 96.0

        # ── Geração com baixo uso de RAM ──────────────────────────────
        # Salva página por página no buffer — não acumula todas na memória
        pdf_buf = io.BytesIO()
        primeira = True
        paginas_extras = []

        for num in range(inicio, fim + 1):
            img = renderizar_comanda(background, num, cfg, escala=escala_pdf)
            if not img:
                continue
            img_rgb = img.convert("RGB")
            del img  # libera RGBA imediatamente após converter
            if primeira:
                primeira_img = img_rgb
                primeira = False
            else:
                paginas_extras.append(img_rgb)

        if primeira:  # nenhuma imagem gerada
            raise HTTPException(status_code=400, detail="Nenhuma imagem gerada.")

        primeira_img.save(
            pdf_buf, format="PDF", save_all=True,
            append_images=paginas_extras,
            resolution=dpi,
        )
        # Libera memória imediatamente após salvar
        del paginas_extras
        del primeira_img
        pdf_buf.seek(0)
        gc.collect()   # força limpeza antes de retornar

        nome_base = f"comandas_{inicio}_a_{fim}"

        if formato == "zip":
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{nome_base}.pdf", pdf_buf.getvalue())
            zip_buf.seek(0)
            return StreamingResponse(
                zip_buf,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={nome_base}.zip"}
            )

        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={nome_base}.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ── Remoção de fundo por cor (PIL) ──────────────────────────────────
@app.post("/remover-fundo-cor")
async def remover_fundo_cor(
    imagem: UploadFile = File(...),
    cor: str = Form("#ffffff"),
    tolerancia: int = Form(30),
    substituir: str = Form("transparent"),  # "transparent" ou cor hex ex: "#cc0000"
):
    try:
        img_bytes = await imagem.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        r_t, g_t, b_t = _hex_to_rgb(cor)
        limiar = tolerancia * 2.55
        usar_subst = substituir != "transparent"
        rs, gs, bs  = _hex_to_rgb(substituir) if usar_subst else (0, 0, 0)
        pixels = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r - r_t) ** 2 + (g - g_t) ** 2 + (b - b_t) ** 2) ** 0.5
                if dist <= limiar:
                    pixels[x, y] = (rs, gs, bs, 255) if usar_subst else (r, g, b, 0)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# ── Remoção de fundo por IA (rembg) ─────────────────────────────────
@app.post("/remover-fundo-ia")
async def remover_fundo_ia(imagem: UploadFile = File(...)):
    try:
        from rembg import remove as rembg_remove
    except ImportError:
        raise HTTPException(status_code=503, detail="REMBG_NAO_INSTALADO")
    try:
        img_bytes = await imagem.read()
        result = rembg_remove(img_bytes)
        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ── Funções de renderização ──────────────────────────────────────────

def _fonte_embutida_path():
    """Retorna uma fonte TTF padrão — prioriza fontes já na pasta fonts/."""
    pasta = "fonts"
    os.makedirs(pasta, exist_ok=True)

    # Prioridade 1: fontes curadas já baixadas
    for candidata in ["Roboto-Bold.ttf", "OpenSans-Bold.ttf", "Inter-Bold.ttf",
                      "Lato-Bold.ttf", "Ubuntu-Bold.ttf"]:
        caminho = os.path.join(pasta, candidata)
        if os.path.exists(caminho):
            return caminho

    # Prioridade 2: _embutida.ttf (copiada do sistema em execuções anteriores)
    caminho = os.path.join(pasta, "_embutida.ttf")
    if os.path.exists(caminho):
        return caminho

    # Prioridade 3: copia do SO
    # Tenta copiar do sistema primeiro
    fontes_sistema = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
    ]
    import shutil
    for f in fontes_sistema:
        if os.path.exists(f):
            try:
                shutil.copy(f, caminho)
                return caminho
            except Exception:
                continue
    return None

_FONTE_EMBUTIDA = None
_FONTE_CACHE: dict = {}
_FONTE_CACHE_MAX = 30   # evita cache ilimitado em produção

def carregar_fonte(caminho, tamanho):
    global _FONTE_EMBUTIDA

    chave = (caminho or '', tamanho)
    if chave in _FONTE_CACHE:
        return _FONTE_CACHE[chave]

    # Remove entrada mais antiga se o cache estiver cheio
    if len(_FONTE_CACHE) >= _FONTE_CACHE_MAX:
        _FONTE_CACHE.pop(next(iter(_FONTE_CACHE)))

    fonte = None

    # 1. Tenta TTF do usuário
    if caminho and os.path.exists(caminho):
        try:
            fonte = ImageFont.truetype(caminho, tamanho)
        except Exception:
            pass

    # 2. Tenta fonte embutida (copiada do sistema na primeira chamada)
    if fonte is None:
        if _FONTE_EMBUTIDA is None:
            _FONTE_EMBUTIDA = _fonte_embutida_path()
        if _FONTE_EMBUTIDA and os.path.exists(_FONTE_EMBUTIDA):
            try:
                fonte = ImageFont.truetype(_FONTE_EMBUTIDA, tamanho)
            except Exception:
                pass

    # 3. Fallback PIL com tamanho (funciona no Pillow >= 10)
    if fonte is None:
        try:
            fonte = ImageFont.load_default(size=tamanho)
        except TypeError:
            fonte = ImageFont.load_default()

    _FONTE_CACHE[chave] = fonte
    return fonte


def aplicar_mascara(documento, tipo):
    nums = re.sub(r"\D", "", documento)
    if tipo == "CNPJ" and len(nums) == 14:
        return f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:14]}:"
    if tipo == "CPF" and len(nums) == 11:
        return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:11]}:"
    return nums + ":"


# ── Presets para QR imagem standalone ───────────────────────────
QR_IMG_PRESETS = {
    "baixa":  {"px": 400,  "label": "Baixa (400 px)",   "lote_max": 500},
    "media":  {"px": 800,  "label": "Média (800 px)",   "lote_max": 300},
    "alta":   {"px": 1200, "label": "Alta (1200 px)",   "lote_max": 150},
    "maxima": {"px": 2000, "label": "Máxima (2000 px)", "lote_max": 80},
}

@app.get("/qr-img-presets")
def get_qr_img_presets():
    return {"presets": QR_IMG_PRESETS, "padrao": "alta"}


@app.post("/preview-qr-img")
async def preview_qr_img(
    numero: int = Form(1),
    documento: str = Form(""),
    tipo_doc: str = Form("CNPJ"),
    cfg_sistema_json: str = Form("{}"),
):
    """Gera um único QR Code em JPEG para preview no modal."""
    nums_doc = re.sub(r"\D", "", documento.strip())
    needed   = 14 if tipo_doc.upper() == "CNPJ" else 11
    if len(nums_doc) != needed:
        raise HTTPException(status_code=400, detail=f"DOCUMENTO_INVALIDO:{tipo_doc.upper()}:{needed}")
    try:
        cfg_sistema = json.loads(cfg_sistema_json)
        dado_base   = aplicar_mascara(documento, tipo_doc)
        img         = _gerar_qr_imagem(numero, dado_base, 400, cfg_sistema)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True, subsampling=0)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gerar-qr-zip")
async def gerar_qr_zip(
    inicio: int = Form(1),
    fim: int = Form(10),
    documento: str = Form(""),
    tipo_doc: str = Form("CNPJ"),
    tamanho_px: int = Form(1200),
    qualidade_jpg: int = Form(95),
    cfg_sistema_json: str = Form("{}"),
):
    total = fim - inicio + 1
    if total <= 0:
        raise HTTPException(status_code=400, detail="Nº final deve ser maior que o inicial.")
    if total > 500:
        raise HTTPException(status_code=400, detail=f"LIMITE_EXCEDIDO:{total}:500")

    # Trava: documento obrigatório para QR Code
    nums_doc = re.sub(r"\D", "", documento.strip())
    needed   = 14 if tipo_doc.upper() == "CNPJ" else 11
    if len(nums_doc) != needed:
        raise HTTPException(
            status_code=400,
            detail=f"DOCUMENTO_INVALIDO:{tipo_doc.upper()}:{needed}"
        )

    try:
        cfg_sistema = json.loads(cfg_sistema_json)
        dado_base   = aplicar_mascara(documento, tipo_doc)
        padding     = len(str(fim))

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for num in range(inicio, fim + 1):
                img = _gerar_qr_imagem(num, dado_base, tamanho_px, cfg_sistema)
                img_buf = io.BytesIO()
                img.save(img_buf, format="JPEG", quality=qualidade_jpg, optimize=True, subsampling=0)
                img_buf.seek(0)
                zf.writestr(f"{str(num).zfill(padding)}.jpg", img_buf.getvalue())

        zip_buf.seek(0)
        nome = f"qrcodes_{inicio}_a_{fim}.zip"
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={nome}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


def _gerar_qr_imagem(numero: int, dado_base: str, tamanho_px: int, cfg_sistema: dict) -> "Image.Image":
    """QR Code standalone de alta qualidade — sem resize, gerado nativamente no tamanho alvo."""
    if dado_base and dado_base.strip(":"):
        texto = f"{dado_base}{numero}"
        encoded = base64.b64encode(texto.encode()).decode()
        conteudo = f"https://pediucomeu.com.br/autoatendimento/{encoded}"
    else:
        conteudo = str(numero)

    correcao   = _CORRECAO_MAP.get(cfg_sistema.get("qr_correcao", "H"), qrcode.constants.ERROR_CORRECT_H)
    cor_modulo = cfg_sistema.get("qr_cor_modulo", "#000000")
    border     = 4   # módulos de margem branca (padrão ISO)

    # Estima o tamanho do QR em módulos para calcular box_size ideal
    qr_probe = qrcode.QRCode(version=None, error_correction=correcao, box_size=1, border=0)
    qr_probe.add_data(conteudo)
    qr_probe.make(fit=True)
    modulos = qr_probe.modules_count + border * 2

    box_size = max(4, tamanho_px // modulos)

    qr = qrcode.QRCode(version=None, error_correction=correcao, box_size=box_size, border=border)
    qr.add_data(conteudo)
    qr.make(fit=True)
    img = qr.make_image(fill_color=cor_modulo, back_color="white").convert("RGB")

    # Ajuste fino para o tamanho exato (NEAREST mantém módulos nítidos)
    img = img.resize((tamanho_px, tamanho_px), Image.Resampling.NEAREST)
    return img


_CORRECAO_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


def gerar_qr(numero, dado_base, tamanho, rotacao, cfg_sistema=None):
    tamanho = max(tamanho, 50)
    cfg = cfg_sistema or {}

    if dado_base and dado_base.strip(":"):
        texto = f"{dado_base}{numero}"
        encoded = base64.b64encode(texto.encode()).decode()
        conteudo = f"https://pediucomeu.com.br/autoatendimento/{encoded}"
    else:
        conteudo = str(numero)

    correcao = _CORRECAO_MAP.get(cfg.get("qr_correcao", "M"), qrcode.constants.ERROR_CORRECT_M)
    cor_modulo = cfg.get("qr_cor_modulo", "#000000")
    fundo_raw  = cfg.get("qr_fundo", "#ffffff")
    back_color = (0, 0, 0, 0) if fundo_raw == "transparent" else fundo_raw

    qr = qrcode.QRCode(version=None, error_correction=correcao, box_size=10, border=2)
    qr.add_data(conteudo)
    qr.make(fit=True)
    img = qr.make_image(fill_color=cor_modulo, back_color=back_color).convert("RGBA")
    img = img.resize((tamanho, tamanho), Image.Resampling.LANCZOS)
    if rotacao:
        img = img.rotate(rotacao, expand=True)
    return img


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def gerar_barcode(numero, prefixo, largura, altura, corte_v, corte_e, corte_d, rotacao, cfg_sistema=None):
    cfg = cfg_sistema or {}
    codigo = f"{prefixo}{str(numero).zfill(4)}"
    writer = ImageWriter()
    writer.set_options({
        "module_width": 0.7,
        "module_height": altura / 10,
        "quiet_zone": 2.0,
        "font_size": 0,
        "text_distance": 0,
        "write_text": False,
    })
    # Code128 codifica EXATAMENTE o prefixo digitado (suporta todo o ASCII).
    # Fallback para Code39 apenas se algo falhar.
    try:
        obj = Code128(codigo, writer=writer)
    except Exception:
        obj = Code39(codigo, writer=writer, add_checksum=False)
    buf = io.BytesIO()
    obj.write(buf)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    rw, rh = img.size
    ct = int(rh * (1 - corte_v / 100))
    ce = int(rw * corte_e / 100)
    cd = int(rw * (1 - corte_d / 100))
    img = img.crop((ce, 0, cd, ct)).resize((largura, altura), Image.Resampling.NEAREST)

    # Recolorir se necessário
    cor_barra  = cfg.get("bc_cor_modulo", "#000000")
    fundo_bc   = cfg.get("bc_fundo", "#ffffff")
    if cor_barra != "#000000" or fundo_bc != "#ffffff":
        rm, gm, bm = _hex_to_rgb(cor_barra)
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if r < 128:                           # pixel escuro → cor da barra
                    pixels[x, y] = (rm, gm, bm, 255)
                else:                                 # pixel claro → fundo
                    if fundo_bc == "transparent":
                        pixels[x, y] = (255, 255, 255, 0)
                    elif fundo_bc != "#ffffff":
                        rf, gf, bf = _hex_to_rgb(fundo_bc)
                        pixels[x, y] = (rf, gf, bf, 255)

    if rotacao:
        img = img.rotate(rotacao, expand=True)
    return img


def colar_texto_quebrado(draw, imagem, texto_str, fonte, x, y, w, h, cor, rotacao, align="center"):
    """Renderiza texto com quebra automática de linha, centrado no elemento."""
    if not texto_str:
        return

    # ── Quebrar em linhas que caibam na largura ──────────────────
    palavras = texto_str.split()
    linhas = []
    linha_atual = []

    for palavra in palavras:
        teste = " ".join(linha_atual + [palavra])
        try:
            bx = draw.textbbox((0, 0), teste, font=fonte)
            largura_teste = bx[2] - bx[0]
        except Exception:
            largura_teste = len(teste) * (fonte.size if hasattr(fonte, "size") else 12)

        if largura_teste <= w or not linha_atual:
            linha_atual.append(palavra)
        else:
            linhas.append(" ".join(linha_atual))
            linha_atual = [palavra]

    if linha_atual:
        linhas.append(" ".join(linha_atual))

    if not linhas:
        return

    # ── Medir altura de uma linha ────────────────────────────────
    try:
        b0 = draw.textbbox((0, 0), linhas[0], font=fonte)
        line_h = max(1, b0[3] - b0[1])
    except Exception:
        line_h = fonte.size if hasattr(fonte, "size") else 14

    espaco = int(line_h * 0.25)
    total_h = len(linhas) * line_h + max(0, len(linhas) - 1) * espaco

    # ── Posição Y inicial (centralizado verticalmente) ───────────
    start_y = y + max(0, (h - total_h) // 2)

    # ── Renderizar cada linha ────────────────────────────────────
    for i, linha in enumerate(linhas):
        ly = start_y + i * (line_h + espaco)
        cy_linha = ly + line_h // 2

        try:
            bl = draw.textbbox((0, 0), linha, font=fonte)
            tw = bl[2] - bl[0]
        except Exception:
            tw = len(linha) * (line_h // 2)

        if align == "left":
            cx_linha = x + tw // 2
        elif align == "right":
            cx_linha = x + w - tw // 2
        else:
            cx_linha = x + w // 2

        colar_texto(draw, imagem, linha, fonte, cx_linha, int(cy_linha), cor, rotacao)


def colar_texto(draw, imagem, texto_str, fonte, cx, cy, cor, rotacao):
    bbox = draw.textbbox((0, 0), texto_str, font=fonte)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    if rotacao == 0:
        draw.text((cx - tw // 2, cy - th // 2), texto_str, font=fonte, fill=cor)
    else:
        tmp = Image.new("RGBA", (max(tw, 1), max(th, 1)), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tmp)
        dt.text((-bbox[0], -bbox[1]), texto_str, font=fonte, fill=cor)
        tmp = tmp.rotate(rotacao, expand=True)
        rw, rh = tmp.size
        imagem.paste(tmp, (cx - rw // 2, cy - rh // 2), tmp)


def renderizar_comanda(background, numero, cfg, escala: float = 1.0):
    """
    escala: multiplicador de resolução.
      1.0 = tamanho do canvas (preview rápido)
      auto = calculado para atingir DPI_ALVO na geração de PDF
    """
    tipo = cfg.get("tipo_codigo", "qr")
    elementos = cfg.get("elementos", [])
    documento = cfg.get("documento", "")
    tipo_doc = cfg.get("tipo_doc", "CNPJ")
    canvas_w = cfg.get("canvas_w", 400)
    canvas_h = cfg.get("canvas_h", 600)
    fonte_path = cfg.get("fonte_path", "")

    bg_color_hex = cfg.get("bg_color", "#ffffff")
    bg_mode = cfg.get("bg_mode", "cor")

    # Se modo cor: cria imagem no tamanho canvas * escala (alta resolução)
    if bg_mode == "cor" or background is None:
        out_w = max(1, int(canvas_w * escala))
        out_h = max(1, int(canvas_h * escala))
        bg = Image.new("RGBA", (out_w, out_h), bg_color_hex)
    else:
        bg = background.copy().convert("RGBA")
        if escala != 1.0:
            out_w = max(1, int(bg.width * escala))
            out_h = max(1, int(bg.height * escala))
            bg = bg.resize((out_w, out_h), Image.Resampling.LANCZOS)

    bg_w, bg_h = bg.size
    sx = bg_w / max(canvas_w, 1)
    sy = bg_h / max(canvas_h, 1)

    draw = ImageDraw.Draw(bg)
    dado_base = aplicar_mascara(documento, tipo_doc) if tipo == "qr" else ""
    cfg_sistema = cfg.get("config_sistema", {})

    # Ordenar por z-index
    for el in sorted(elementos, key=lambda e: e.get("z", 0)):
        el_type = el.get("type")
        x = int(el.get("x", 0) * sx)
        y = int(el.get("y", 0) * sy)
        w = max(int(el.get("w", 100) * sx), 1)
        h = max(int(el.get("h", 100) * sy), 1)
        rot = el.get("rot", 0)

        if el_type == "qr" and tipo == "qr":
            qr_img = gerar_qr(numero, dado_base, min(w, h), rot, cfg_sistema)
            bg.paste(qr_img, (x, y), qr_img)

        elif el_type == "barcode" and tipo == "barcode":
            prefixo = cfg.get("bc_prefixo", "/")
            cortev = el.get("bc_cortev", 27)
            cortee = el.get("bc_cortee", 8)
            corted = el.get("bc_corted", 8)
            bc = gerar_barcode(numero, prefixo, w, h, cortev, cortee, corted, rot, cfg_sistema).convert("RGBA")
            bg.paste(bc, (x, y), bc)

        elif el_type in ("text", "number"):
            # Para barcode: número formatado com zeros à esquerda (ex: 0001)
            if el_type == "number":
                if tipo == "barcode":
                    texto = str(numero).zfill(4)
                else:
                    texto = str(numero)
            else:
                texto = el.get("text", "")
            if not texto:
                continue

            # Fonte: fs em pixels do canvas, escalado proporcionalmente ao template
            fs_original = el.get("fs", 18)
            # Escala pelo fator médio entre largura e altura do template vs canvas
            fs = max(8, int(fs_original * ((sx + sy) / 2)))
            # SEMPRE usar carregar_fonte — garante TTF real com tamanho correto
            fonte = carregar_fonte(fonte_path, fs)
            cor = el.get("color", "#000000")
            align = el.get("align", "center")

            if el_type == "text":
                # Texto livre: quebra automática de linha
                colar_texto_quebrado(draw, bg, texto, fonte, x, y, w, h, cor, rot, align)
            else:
                # Número da comanda: linha única centralizada
                cx = x + w // 2
                cy = y + h // 2
                try:
                    bbox = draw.textbbox((0, 0), texto, font=fonte)
                    tw   = bbox[2] - bbox[0]
                except Exception:
                    tw = fs * len(texto) // 2
                if align == "left":
                    cx = x + tw // 2
                elif align == "right":
                    cx = x + w - tw // 2
                colar_texto(draw, bg, texto, fonte, cx, cy, cor, rot)

        elif el_type == "logo":
            src = el.get("src", "")
            if src.startswith("data:"):
                try:
                    _, b64data = src.split(",", 1)
                    logo = Image.open(io.BytesIO(base64.b64decode(b64data))).convert("RGBA")
                    logo = logo.resize((w, h), Image.Resampling.LANCZOS)
                    if rot:
                        logo = logo.rotate(rot, expand=True)
                    bg.paste(logo, (x, y), logo)
                except Exception:
                    pass

    return bg.convert("RGB")


if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    os.makedirs("fonts", exist_ok=True)
    port = int(os.environ.get("PORT", 8000))
    dev  = os.environ.get("RENDER") is None  # reload só localmente
    print("\n✅  Gerador de Comandas iniciando...")
    print(f"🌐  Acesse: http://localhost:{port}\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=dev)
