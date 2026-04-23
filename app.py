import streamlit as st
import base64
import time
import os
from gtts import gTTS
from google import genai

# --- 1. CONFIGURACIÓN DE LLAVES Y MODELOS ---
# Intentamos obtener ambas llaves de los Secrets de Streamlit
api_keys = [
    st.secrets.get("GEMINI_API_KEY"),
    st.secrets.get("GEMINI_API_KEY_2")
]
api_keys = [k for k in api_keys if k] # Filtramos solo las que existan

if not api_keys:
    st.error("No se encontraron API Keys en los Secrets de Streamlit.")
    st.stop()

# Selección de API Key activa
if "api_index" not in st.session_state:
    st.session_state.api_index = 0

# Lista de modelos en orden de preferencia (Estrategia 2026)
MODELOS = [
    "gemini-2.0-flash",       # El más potente
    "gemini-2.0-flash-lite",  # El más económico y rápido
    "gemini-1.5-flash",       # El todoterreno
    "gemini-1.5-flash-8b"     # El de mayor cuota
]

if "modelo_activo" not in st.session_state:
    st.session_state.modelo_activo = MODELOS[0]

# --- 2. INICIALIZACIÓN DEL CLIENTE ---
def inicializar_cliente():
    key_actual = api_keys[st.session_state.api_index]
    return genai.Client(
        api_key=key_actual,
        http_options={'api_version': 'v1beta'} # Clave para evitar el 404
    )

if "client" not in st.session_state:
    st.session_state.client = inicializar_cliente()

# --- 3. FUNCIÓN DE LLAMADA CON FALLBACK Y ROTACIÓN ---
def llamar_gemini(prompt, contexto):
    contenido = f"{contexto}\nAlumno: {prompt}"
    
    # Intentamos con cada modelo de la lista
    for modelo in MODELOS:
        try:
            response = st.session_state.client.models.generate_content(
                model=modelo,
                contents=contenido
            )
            st.session_state.modelo_activo = modelo
            return response.text
            
        except Exception as e:
            err = str(e).lower()
            # Si se agotó la cuota (429), intentamos cambiar de API Key
            if "429" in err and len(api_keys) > 1:
                st.session_state.api_index = (st.session_state.api_index + 1) % len(api_keys)
                st.session_state.client = inicializar_cliente()
                st.toast("🔄 Rotando a la segunda API Key por saturación...")
                # Reintentamos con la nueva llave y el mismo modelo
                try:
                    response = st.session_state.client.models.generate_content(model=modelo, contents=contenido)
                    return response.text
                except: pass
            
            # Si el modelo no existe (404), saltamos al siguiente en la lista
            if "404" in err:
                continue
            
    raise Exception("Todos los modelos y llaves están agotados por hoy.")

# --- 4. CACHÉ Y CONFIGURACIÓN DE PÁGINA ---
@st.cache_data(ttl=3600, show_spinner=False)
def respuesta_cacheada(p, c):
    return llamar_gemini(p, c)

st.set_page_config(page_title="Píxel - ISAP", page_icon="🤖", layout="wide")

# Estilos CSS
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
    </style>
    """, unsafe_allow_html=True)

# --- 5. LÓGICA DE IMAGEN Y VOZ ---
if "img_b64" not in st.session_state:
    ruta = "pixel_final_frontal.png"
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            st.session_state.img_b64 = base64.b64encode(f.read()).decode()
    else: st.session_state.img_b64 = ""

def render_pixel(texto=None, animar=False):
    img = st.session_state.img_b64
    if animar and texto:
        try:
            uid = int(time.time() * 1000)
            clean_txt = texto.replace("*", "").replace("_", "").replace("Píxel", "Píksel")
            tts = gTTS(text=clean_txt, lang='es', tld='com.ar')
            tts.save(f"v_{uid}.mp3")
            with open(f"v_{uid}.mp3", "rb") as f:
                aud = base64.b64encode(f.read()).decode()
            os.remove(f"v_{uid}.mp3")
            return f"""
                <div class="pixel-container" id="w-{uid}"><img src="data:image/png;base64,{img}" class="pixel-img hablando"></div>
                <audio autoplay onended="document.getElementById('w-{uid}').firstChild.classList.remove('hablando')">
                    <source src="data:audio/mp3;base64,{aud}" type="audio/mp3">
                </audio>
            """
        except: pass
    return f'<div class="pixel-container"><img src="data:image/png;base64,{img}" class="pixel-img"></div>'

# --- 6. INTERFAZ Y CHAT ---
st.markdown("<h2 style='text-align: center;'>🤖 Píxel: Tu Auxiliar</h2>", unsafe_allow_html=True)
st.caption(f"⚙️ Modo: `{st.session_state.modelo_activo}` | Llave: `{st.session_state.api_index + 1}`")

if "inicio" not in st.session_state: st.session_state.inicio = False
pixel_placeholder = st.empty()
texto_placeholder = st.empty()

if not st.session_state.inicio:
    pixel_placeholder.markdown(render_pixel(), unsafe_allow_html=True)
    if st.button("▶️ ACTIVAR PÍXEL"):
        st.session_state.inicio = True
        st.rerun()
else:
    if prompt := st.chat_input("Escribí tu consulta..."):
        status = st.status("🤖 Píxel trabajando...")
        try:
            contexto = "Sos Píxel, docente de TIC en Argentina. Responde socrático y breve."
            res = respuesta_cacheada(prompt.strip().lower(), contexto)
            status.update(label="¡Listo!", state="complete", expanded=False)
            pixel_placeholder.markdown(render_pixel(res, animar=True), unsafe_allow_html=True)
            texto_placeholder.info(res)
        except Exception as e:
            status.update(label="❌ Pausa", state="error", expanded=True)
            st.error(str(e))
                st.warning("🔧 El modelo no está disponible. Recargá la página.")
            elif "quota" in error_str.lower():
                st.warning("📊 Se agotó la cuota diaria. Intentá mañana o cambiá la API key.")
            else:
                st.warning("⚠️ Error desconocido — copiá el texto de arriba y compartilo.")
