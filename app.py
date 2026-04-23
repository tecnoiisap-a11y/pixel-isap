import streamlit as st
import base64
import time
import os
from gtts import gTTS
from google import genai

# --- 1. CONFIGURACIÓN INICIAL (DEBE IR PRIMERO) ---
st.set_page_config(page_title="Píxel - ISAP", page_icon="🤖", layout="wide")

# --- 2. GESTIÓN DE API KEYS Y CLIENTE ---
api_keys = [
    st.secrets.get("GEMINI_API_KEY"),
    st.secrets.get("GEMINI_API_KEY_2")
]
api_keys = [k for k in api_keys if k]

if not api_keys:
    st.error("Error: No se encontraron API Keys en los Secrets.")
    st.stop()

if "api_index" not in st.session_state:
    st.session_state.api_index = 0

MODELOS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b"
]

def inicializar_cliente():
    """Crea el cliente con la llave actual y la versión v1beta para evitar 404."""
    key_actual = api_keys[st.session_state.api_index]
    return genai.Client(
        api_key=key_actual,
        http_options={'api_version': 'v1beta'}
    )

if "client" not in st.session_state:
    st.session_state.client = inicializar_cliente()

if "modelo_activo" not in st.session_state:
    st.session_state.modelo_activo = MODELOS[0]

# --- 3. LÓGICA DE COMUNICACIÓN (FALLBACK) ---
def llamar_gemini(prompt, contexto):
    contenido = f"{contexto}\nAlumno: {prompt}"
    
    for modelo in MODELOS:
        try:
            response = st.session_state.client.models.generate_content(
                model=modelo,
                contents=contenido
            )
            st.session_state.modelo_activo = modelo
            return response.text
        except Exception as e:
            err_msg = str(e).lower()
            # Si es error de cuota (429) y tenemos otra llave, rotamos
            if "429" in err_msg and len(api_keys) > 1:
                st.session_state.api_index = (st.session_state.api_index + 1) % len(api_keys)
                st.session_state.client = inicializar_cliente()
                st.toast(f"🔄 Rotando a Llave {st.session_state.api_index + 1}...")
                try:
                    # Reintento rápido con la nueva llave
                    res = st.session_state.client.models.generate_content(model=modelo, contents=contenido)
                    return res.text
                except: pass
            
            # Si es error 404 o cualquier otro, probamos el siguiente modelo
            continue
            
    raise Exception("Todos los modelos están saturados. Reintentá en un minuto.")

@st.cache_data(ttl=3600, show_spinner=False)
def respuesta_cacheada(p, c):
    return llamar_gemini(p, c)

# --- 4. ESTILOS Y CARGA DE RECURSOS ---
st.markdown("""
    <style>
    .pixel-container { display: flex; justify-content: center; width: 100%; margin-bottom: 15px; }
    .pixel-img { height: 310px !important; width: auto !important; border-radius: 20px; }
    @keyframes pulso {
        0% { transform: scale(1); }
        50% { transform: scale(1.03); filter: brightness(1.1) drop-shadow(0 0 15px #38aecc); }
        100% { transform: scale(1); }
    }
    .hablando { animation: pulso 0.6s infinite ease-in-out; border: 4px solid #38aecc !important; }
    .stButton > button { width: 100%; background: linear-gradient(to right, #1e3799, #38aecc) !important; color: white !important; border-radius: 50px !important; font-weight: bold !important; height: 55px !important; }
    </style>
    """, unsafe_allow_html=True)

if "img_b64" not in st.session_state:
    ruta_img = "pixel_final_frontal.png"
    if os.path.exists(ruta_img):
        with open(ruta_img, "rb") as f:
            st.session_state.img_b64 = base64.b64encode(f.read()).decode()
    else:
        st.session_state.img_b64 = ""

# --- 5. FUNCIONES DE RENDERIZADO ---
def render_pixel(texto=None, animar=False):
    img = st.session_state.img_b64
    if animar and texto:
        try:
            uid = int(time.time() * 1000)
            clean_txt = texto.replace("**", "").replace("*", "").replace("_", "").replace("Píxel", "Píksel")
            tts = gTTS(text=clean_txt, lang='es', tld='com.ar')
            fname = f"v_{uid}.mp3"
            tts.save(fname)
            with open(fname, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            os.remove(fname)
            return f"""
                <div class="pixel-container" id="w-{uid}"><img src="data:image/png;base64,{img}" class="pixel-img hablando"></div>
                <audio autoplay onended="document.getElementById('w-{uid}').firstChild.classList.remove('hablando')">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
            """
        except: pass
    return f'<div class="pixel-container"><img src="data:image/png;base64,{img}" class="pixel-img"></div>'

# --- 6. INTERFAZ DE USUARIO ---
st.markdown("<h2 style='text-align: center;'>🤖 Píxel: Tu Auxiliar</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ISAP N° 8090 - Orán</p>", unsafe_allow_html=True)
st.caption(f"⚙️ Modelo: `{st.session_state.modelo_activo}` | Llave: `{st.session_state.api_index + 1}`")

if "inicio" not in st.session_state: st.session_state.inicio = False
if "saludo_dado" not in st.session_state: st.session_state.saludo_dado = False

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
        saludo = "¡Hola! Soy Píxel. ¿En qué misión tecnológica trabajamos hoy?"
        pixel_placeholder.markdown(render_pixel(saludo, animar=True), unsafe_allow_html=True)
        texto_placeholder.info(saludo)
        st.session_state.saludo_dado = True
    else:
        pixel_placeholder.markdown(render_pixel(), unsafe_allow_html=True)

# --- 7. LÓGICA DE CHAT ---
if st.session_state.inicio:
    if prompt := st.chat_input("Escribí tu consulta aquí..."):
        texto_placeholder.empty()
        prompt_norm = prompt.strip().lower()
        
        status = st.status("🤖 Píxel pensando...")
        try:
            contexto = "Sos Píxel, docente de TIC. Estilo socrático, breve y motivador."
            res = respuesta_cacheada(prompt_norm, contexto)
            status.update(label="¡Listo!", state="complete", expanded=False)
            
            pixel_placeholder.markdown(render_pixel(res, animar=True), unsafe_allow_html=True)
            texto_placeholder.info(f"Píxel: {res}")
        except Exception as e:
            status.update(label="❌ Aviso", state="error", expanded=True)
            st.error(str(e))
