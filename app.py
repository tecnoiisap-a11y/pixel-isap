import streamlit as st
import base64
import time
import os
from gtts import gTTS
from google import genai

# --- 1. CONFIGURACIÓN ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Error: No se encontró la API KEY en los Secrets.")
    st.stop()

# Lista de modelos en orden de preferencia (fallback)
MODELOS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",  # el más permisivo en free tier
]

if "client" not in st.session_state:
    st.session_state.client = genai.Client(
        api_key=API_KEY,
        http_options={'api_version': 'v1'}
    )
if "modelo_activo" not in st.session_state:
    st.session_state.modelo_activo = MODELOS[0]

if "ultimo_request" not in st.session_state:
    st.session_state.ultimo_request = 0

# --- 2. FUNCIÓN CON RETRY + FALLBACK ---
def llamar_gemini(prompt, contexto, max_reintentos=3):
    """Llama a Gemini con retry exponencial y fallback de modelo."""
    
    # Cooldown mínimo entre requests (3 segundos)
    ahora = time.time()
    espera = ahora - st.session_state.ultimo_request
    if espera < 3:
        time.sleep(3 - espera)

    contenido = f"{contexto}\nAlumno: {prompt}"
    
    for modelo in MODELOS:
        for intento in range(max_reintentos):
            try:
                response = st.session_state.client.models.generate_content(
                    model=modelo,
                    contents=contenido
                )
                st.session_state.modelo_activo = modelo
                st.session_state.ultimo_request = time.time()
                return response.text
                
            except Exception as e:
                error_str = str(e)
                
                if "429" in error_str:
                    # Rate limit: espera exponencial y reintenta
                    espera_retry = (2 ** intento) * 5  # 5s, 10s, 20s
                    st.toast(f"⏳ Esperando {espera_retry}s antes de reintentar...")
                    time.sleep(espera_retry)
                    continue  # reintenta el mismo modelo
                    
                elif "404" in error_str:
                    # Modelo no disponible, pasa al siguiente
                    break  # sale del loop de reintentos y prueba otro modelo
                    
                else:
                    raise e  # error desconocido, lo propagamos
        
    raise Exception("Todos los modelos están saturados. Intentá en unos minutos.")

# --- 3. CACHÉ DE RESPUESTAS ---
@st.cache_data(ttl=3600, show_spinner=False)
def respuesta_cacheada(prompt_normalizado, contexto):
    """Cachea respuestas idénticas por 1 hora para no gastar cuota."""
    return llamar_gemini(prompt_normalizado, contexto)

# --- 4. ESTILOS CSS ---
st.set_page_config(page_title="Píxel - ISAP", page_icon="🤖", layout="wide")
st.markdown("""
    <style>
    .main .block-container { display: flex; flex-direction: column; align-items: center; padding-top: 1.5rem !important; }
    .pixel-container { display: flex; justify-content: center; width: 100%; margin-bottom: 15px; }
    .pixel-img { height: 310px !important; width: auto !important; border-radius: 20px; }
    @keyframes pulso {
        0% { transform: scale(1); filter: brightness(1); }
        50% { transform: scale(1.03); filter: brightness(1.1) drop-shadow(0 0 15px #38aecc); }
        100% { transform: scale(1); filter: brightness(1); }
    }
    .hablando { animation: pulso 0.6s infinite ease-in-out; border: 4px solid #38aecc !important; }
    .stButton > button { width: 100%; background: linear-gradient(to right, #1e3799, #38aecc) !important; color: white !important; border-radius: 50px !important; font-weight: bold !important; height: 55px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. CARGA DE IMAGEN ---
if "img_b64" not in st.session_state:
    ruta_img = "pixel_final_frontal.png"
    if os.path.exists(ruta_img):
        with open(ruta_img, "rb") as f:
            st.session_state.img_b64 = base64.b64encode(f.read()).decode()
    else:
        st.session_state.img_b64 = ""

# --- 6. FUNCIÓN RENDER ---
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
                <div class="pixel-container" id="wrp-{uid}"><img src="data:image/png;base64,{img}" class="pixel-img hablando"></div>
                <audio autoplay id="aud-{uid}"><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>
                <script>
                    var audio = document.getElementById('aud-{uid}');
                    audio.play().catch(e => console.log("Audio bloqueado"));
                    audio.onended = function() {{
                        document.getElementById('wrp-{uid}').innerHTML = '<img src="data:image/png;base64,{img}" class="pixel-img">';
                    }};
                </script>
            """
        except: pass
    return f'<div class="pixel-container"><img src="data:image/png;base64,{img}" class="pixel-img"></div>'

# --- 7. INTERFAZ ---
st.markdown("<h2 style='text-align: center;'>🤖 Píxel: Tu Auxiliar</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ISAP N° 8090 - Orán</p>", unsafe_allow_html=True)

# Muestra el modelo activo (útil para debug)
st.caption(f"Modelo activo: `{st.session_state.modelo_activo}`")

with st.expander("🚀 GUÍA DE MISIONES (Para alumnos)"):
    st.markdown("""
    * **Misión Detective:** *"Píxel, analicemos un lápiz con los 3 pilares."*
    * **Misión Duelo:** *"Píxel, ¿quién gana el duelo: un tenedor o una tablet?"*
    * **Misión Necesidad:** *"Píxel, ¿la ropa de marca es una necesidad primaria?"*
    """)

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
        saludo = "¡Hola! Soy Píxel. Elegí una misión o preguntame algo sobre Tecnología."
        pixel_placeholder.markdown(render_pixel(saludo, animar=True), unsafe_allow_html=True)
        texto_placeholder.info(saludo)
        st.session_state.saludo_dado = True
    else:
        pixel_placeholder.markdown(render_pixel(), unsafe_allow_html=True)

# --- 8. LÓGICA DE CHAT ---
CONTEXTO = (
    "Sos Píxel, un asistente pedagógico experto en Tecnología para alumnos de 12 a 14 años. "
    "Tu estilo es socrático: no des la respuesta servida, hacé preguntas que guíen al alumno "
    "a pensar. Usá un lenguaje cercano, amable y motivador. "
    "Respondé siempre en menos de 150 palabras para no gastar recursos."  # <-- límite de tokens ayuda
)

if st.session_state.inicio:
    if prompt := st.chat_input("Escribí tu consulta aquí..."):
        texto_placeholder.empty()
        
        # Normalizamos para el caché (minúsculas, sin espacios extra)
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
            
            # DIAGNÓSTICO COMPLETO - mostramos todo para saber qué pasa
            st.error(f"🔍 Error completo: {error_str}")
            st.code(error_str)  # lo muestra en un bloque copiable
            
            if "429" in error_str or "saturados" in error_str:
                st.warning("😅 Píxel necesita un descanso. Esperá 1-2 minutos y volvé a intentar.")
            elif "404" in error_str:
                st.warning("🔧 El modelo no está disponible. Recargá la página.")
            elif "quota" in error_str.lower():
                st.warning("📊 Se agotó la cuota diaria. Intentá mañana o cambiá la API key.")
            else:
                st.warning("⚠️ Error desconocido — copiá el texto de arriba y compartilo.")
