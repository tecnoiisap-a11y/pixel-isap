import streamlit as st
import base64
import time
import os
from gtts import gTTS
from openai import OpenAI

# ============================================================
# 1. CONFIGURACIÓN — OPENROUTER PRINCIPAL + GEMINI FALLBACK
# ============================================================

# Cargamos OpenRouter (principal)
try:
    OPENROUTER_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    OPENROUTER_KEY = None

# Cargamos Gemini como fallback
GEMINI_KEYS = []
for nombre_key in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
    try:
        GEMINI_KEYS.append(st.secrets[nombre_key])
    except Exception:
        pass

if not OPENROUTER_KEY and len(GEMINI_KEYS) == 0:
    st.error("❌ Error: No se encontró ninguna API KEY en los Secrets.")
    st.stop()

# Cliente OpenRouter
if "openrouter_client" not in st.session_state and OPENROUTER_KEY:
    st.session_state.openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_KEY,
    )

MODELOS_OPENROUTER = [
    "openrouter/auto",          # ← router automático gratuito
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# Gemini como fallback
if "gemini_clientes" not in st.session_state and len(GEMINI_KEYS) > 0:
    from google import genai
    st.session_state.gemini_clientes = [
        genai.Client(api_key=k, http_options={'api_version': 'v1beta'})
        for k in GEMINI_KEYS
    ]

MODELOS_GEMINI = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-preview-04-17",
    "gemini-1.5-flash-latest",
]

if "modelo_activo" not in st.session_state:
    st.session_state.modelo_activo = MODELOS_OPENROUTER[0]
if "ultimo_request" not in st.session_state:
    st.session_state.ultimo_request = 0
if "gemini_key_index" not in st.session_state:
    st.session_state.gemini_key_index = 0
if "proveedor_activo" not in st.session_state:
    st.session_state.proveedor_activo = "OpenRouter"

# ============================================================
# 2. ESTILOS CSS
# ============================================================
st.set_page_config(page_title="Píxel - ISAP", page_icon="🤖", layout="wide")
st.markdown("""
    <style>
    .main .block-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 1.5rem !important;
    }
    .pixel-container {
        display: flex;
        justify-content: center;
        width: 100%;
        margin-bottom: 15px;
    }
    .pixel-img {
        height: 310px !important;
        width: auto !important;
        border-radius: 20px;
    }
    @keyframes pulso {
        0%   { transform: scale(1);    filter: brightness(1); }
        50%  { transform: scale(1.03); filter: brightness(1.1) drop-shadow(0 0 15px #38aecc); }
        100% { transform: scale(1);    filter: brightness(1); }
    }
    .hablando {
        animation: pulso 0.6s infinite ease-in-out;
        border: 4px solid #38aecc !important;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(to right, #1e3799, #38aecc) !important;
        color: white !important;
        border-radius: 50px !important;
        font-weight: bold !important;
        height: 55px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# 3. CARGA DE IMAGEN
# ============================================================
if "img_b64" not in st.session_state:
    ruta_img = "pixel_final_frontal.png"
    if os.path.exists(ruta_img):
        with open(ruta_img, "rb") as f:
            st.session_state.img_b64 = base64.b64encode(f.read()).decode()
    else:
        st.session_state.img_b64 = ""

# ============================================================
# 4. FUNCIÓN RENDER (VOZ + ANIMACIÓN)
# ============================================================
def render_pixel(texto=None, animar=False):
    uid = int(time.time() * 1000)
    img = st.session_state.img_b64
    if animar and texto:
        try:
            texto_voz = texto.replace("**", "").replace("*", "").replace("_", "")
            texto_voz = texto_voz.replace("Píxel", "Píksel")
            tts = gTTS(text=texto_voz, lang='es', tld='com.ar')
            fname = f"v_{uid}.mp3"
            tts.save(fname)
            with open(fname, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            os.remove(fname)
            return f"""
                <div class="pixel-container" id="wrp-{uid}">
                    <img src="data:image/png;base64,{img}" class="pixel-img hablando">
                </div>
                <audio autoplay id="aud-{uid}">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
                <script>
                    var audio = document.getElementById('aud-{uid}');
                    audio.play().catch(e => console.log("Audio bloqueado"));
                    audio.onended = function() {{
                        document.getElementById('wrp-{uid}').innerHTML =
                            '<img src="data:image/png;base64,{img}" class="pixel-img">';
                    }};
                </script>
            """
        except:
            pass
    return f'<div class="pixel-container"><img src="data:image/png;base64,{img}" class="pixel-img"></div>'

# ============================================================
# 5. FUNCIONES DE LLAMADA A LA API
# ============================================================
def llamar_openrouter(prompt, contexto):
    modelos = [
        "openrouter/auto",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-12b-it:free",
    ]
    for modelo in modelos:
        try:
            response = st.session_state.openrouter_client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": contexto},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
            )
            st.session_state.modelo_activo = modelo
            st.session_state.proveedor_activo = "OpenRouter"
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "429" in error_str:
                continue
            else:
                raise e
    raise Exception("OPENROUTER_AGOTADO")

def llamar_gemini(prompt, contexto):
    """Llama a Gemini como fallback."""
    if not hasattr(st.session_state, 'gemini_clientes') or len(st.session_state.gemini_clientes) == 0:
        raise Exception("GEMINI_NO_DISPONIBLE")

    contenido = f"{contexto}\nAlumno: {prompt}"
    errores_log = []
    num_keys = len(st.session_state.gemini_clientes)

    for modelo in MODELOS_GEMINI:
        for ki in range(num_keys):
            key_idx = (st.session_state.gemini_key_index + ki) % num_keys
            cliente = st.session_state.gemini_clientes[key_idx]
            try:
                response = cliente.models.generate_content(
                    model=modelo,
                    contents=contenido
                )
                st.session_state.gemini_key_index = key_idx
                st.session_state.modelo_activo = modelo
                st.session_state.proveedor_activo = "Gemini"
                return response.text
            except Exception as e:
                error_str = str(e)
                errores_log.append(f"[key{key_idx+1}][{modelo}]: {error_str[:100]}")
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    continue
                elif "404" in error_str or "NOT_FOUND" in error_str:
                    break
                else:
                    break

    raise Exception("TODAS_AGOTADAS:\n" + "\n".join(errores_log))

def llamar_ia(prompt, contexto):
    """Intenta OpenRouter primero, luego Gemini como fallback."""
    # Cooldown de 2 segundos
    ahora = time.time()
    espera = ahora - st.session_state.ultimo_request
    if espera < 2:
        time.sleep(2 - espera)

    try:
        if OPENROUTER_KEY and "openrouter_client" in st.session_state:
            resultado = llamar_openrouter(prompt, contexto)
            st.session_state.ultimo_request = time.time()
            return resultado
    except Exception as e:
        if "OPENROUTER_AGOTADO" not in str(e):
            raise e
        # OpenRouter agotado, caemos a Gemini

    # Fallback a Gemini
    resultado = llamar_gemini(prompt, contexto)
    st.session_state.ultimo_request = time.time()
    return resultado

# ============================================================
# 6. CACHÉ DE RESPUESTAS
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def respuesta_cacheada(prompt_normalizado, contexto):
    return llamar_ia(prompt_normalizado, contexto)

# ============================================================
# 7. INTERFAZ PRINCIPAL
# ============================================================
st.markdown("<h2 style='text-align: center;'>🤖 Píxel: Tu Auxiliar</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ISAP N° 8090 - Orán</p>", unsafe_allow_html=True)

# Info de estado
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.caption(f"🧠 Modelo: `{st.session_state.modelo_activo}`")
with col_info2:
    st.caption(f"⚡ Proveedor: `{st.session_state.proveedor_activo}`")
with col_info3:
    keys_total = (1 if OPENROUTER_KEY else 0) + len(GEMINI_KEYS)
    st.caption(f"🔑 Keys cargadas: `{keys_total}`")

with st.expander("🚀 GUÍA DE MISIONES (Para alumnos)"):
    st.markdown("""
    * **Misión Detective:** *"Píxel, analicemos un lápiz con los 3 pilares."*
    * **Misión Duelo:** *"Píxel, ¿quién gana el duelo: un tenedor o una tablet?"*
    * **Misión Necesidad:** *"Píxel, ¿la ropa de marca es una necesidad primaria?"*
    """)

if "inicio" not in st.session_state:
    st.session_state.inicio = False
if "saludo_dado" not in st.session_state:
    st.session_state.saludo_dado = False

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    pixel_placeholder = st.empty()
    texto_placeholder = st.empty()

if not st.session_state.inicio:
    pixel_placeholder.markdown(render_pixel(), unsafe_allow_html=True)
    if st.button("▶️ ACTIVAR PÍXEL"):
        st.session_state.inicio = True
        st.rerun()
else:
    if not st.session_state.saludo_dado:
        saludo = "¡Hola! Soy Píxel. Elegí una misión o preguntame algo sobre Tecnología."
        pixel_placeholder.markdown(render_pixel(saludo, animar=True), unsafe_allow_html=True)
        texto_placeholder.info(saludo)
        st.session_state.saludo_dado = True
    else:
        pixel_placeholder.markdown(render_pixel(), unsafe_allow_html=True)

# ============================================================
# 8. LÓGICA DE CHAT SOCRÁTICO
# ============================================================
CONTEXTO = (
    "Sos Píxel, un asistente pedagógico experto en Tecnología para alumnos de 12 a 14 años. "
    "Tu estilo es socrático: no des la respuesta servida, hacé preguntas que guíen al alumno "
    "a pensar. Usá un lenguaje cercano, amable y motivador. "
    "Respondé siempre en menos de 120 palabras para ser claro y conciso."
)

if st.session_state.inicio:
    if prompt := st.chat_input("Escribí tu consulta aquí..."):
        texto_placeholder.empty()
        prompt_normalizado = prompt.strip().lower()

        status = st.status("🤖 Píxel está pensando...")
        try:
            respuesta = respuesta_cacheada(prompt_normalizado, CONTEXTO)
            status.update(label="¡Listo!", state="complete", expanded=False)
            pixel_placeholder.markdown(render_pixel(respuesta, animar=True), unsafe_allow_html=True)
            texto_placeholder.info(f"Píxel: {respuesta}")

        except Exception as e:
            status.update(label="❌ Algo pasó", state="error", expanded=True)
            error_str = str(e)
            st.code(error_str)  # <-- agregá esta línea para ver el error real

            if "TODAS_AGOTADAS" in error_str:
                st.error("🔴 Todos los servicios están agotados por hoy.")
                st.warning("⏰ La cuota de Gemini se resetea a las **21:00 hs Argentina**. OpenRouter se resetea cada minuto.")
                st.info("💡 Esperá 1-2 minutos y volvé a intentar — OpenRouter debería recuperarse solo.")
            elif "429" in error_str:
                st.warning("⏳ Demasiadas consultas seguidas. Esperá 1 minuto e intentá de nuevo.")
            elif "404" in error_str:
                st.warning("🔧 Modelo no disponible. Recargá la página.")
            else:
                st.error(f"⚠️ Error inesperado: {error_str}")
