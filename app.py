import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import base64
import time
import os

# --- 1. CONFIGURACIÓN SEGURA ---
import os

# Si está en la nube (Streamlit Cloud) usa Secrets, si está en tu PC usa tu clave directa
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = "AIzaSyCXU9qFWGYvVoDzfTuR7FbHQ1eei1AoHNo" # Poné tu clave acá para probar local

genai.configure(api_key=API_KEY)
def obtener_modelo_valido():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return m.name
    except: pass
    return "gemini-1.5-flash"

if "modelo_activo" not in st.session_state:
    st.session_state.modelo_activo = obtener_modelo_valido()

st.set_page_config(page_title="Píxel - ISAP", page_icon="🤖", layout="wide")

# --- 2. ESTILOS CSS ---
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

# --- 3. CARGA DE IMAGEN ---
# --- 3. CARGA DE IMAGEN ---
if "img_b64" not in st.session_state:
    # Solo el nombre del archivo, sin carpetas
    ruta_img = "pixel_final_frontal.png" 
    if os.path.exists(ruta_img):
        with open(ruta_img, "rb") as f:
            st.session_state.img_b64 = base64.b64encode(f.read()).decode()
    else: 
        st.session_state.img_b64 = "" # Si no la encuentra, no rompe la app
# --- 4. FUNCIÓN RENDER (VOZ LIMPIA) ---
def render_pixel(texto=None, animar=False):
    uid = int(time.time() * 1000)
    img = st.session_state.img_b64
    if animar and texto:
        try:
            # Limpiamos el texto para que la voz no lea asteriscos ni tildes deletreadas
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

# --- 5. INTERFAZ Y GUÍA DE MISIONES ---
st.markdown("<h2 style='text-align: center;'>🤖 Píxel: Tu Auxiliar</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ISAP N° 8090 - Orán</p>", unsafe_allow_html=True)

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

# --- 6. LÓGICA DE CHAT SOCRÁTICO ---
if st.session_state.inicio:
    if prompt := st.chat_input("Escribí tu consulta aquí..."):
        texto_placeholder.empty()
        
        contexto = (
            "Sos Píxel, profesor de Tecnología del ISAP en Orán. "
            "ORDEN: 1. Responde directo usando el Módulo 1. "
            "2. Relaciona con los 3 Pilares (Humano, Problema, Objeto). "
            "3. Termina con un desafío o pregunta para el alumno. "
            "Usa voseo argentino, máximo 30 palabras."
        )
        try:
            with st.spinner("🤖 Píxel pensando..."):
                # Intentamos con el modelo Pro que es el más estable en la red
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(f"{contexto}\n Alumno: {prompt}")
                
                # Si la respuesta está vacía o bloqueada
                if not response.text:
                    respuesta = "Che, no puedo responder eso. ¡Preguntame algo de tecnología!"
                else:
                    respuesta = response.text
                
                pixel_placeholder.markdown(render_pixel(respuesta, animar=True), unsafe_allow_html=True)
                texto_placeholder.info(f"Píxel: {respuesta}")