import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from pptx import Presentation
import pandas as pd
import io
import google.generativeai as genai
import json
import random 
import plotly.graph_objects as go 
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit_authenticator as stauth
import bcrypt
import yaml
from yaml.loader import SafeLoader
import time

# --- FRASES MOTIVACIONALES ---
STOIC_QUOTES = [
    "“El obstáculo es el camino.” — Marco Aurelio",
    "“La dificultad es lo que despierta al genio.” — Séneca",
    "“No es que tengamos poco tiempo, sino que perdemos mucho.” — Séneca",
    "“La excelencia es un hábito, no un acto.” — Aristóteles",
    "“Un gramo de práctica vale más que una tonelada de teoría.”",
    "“El éxito es la suma de pequeños esfuerzos repetidos día tras día.” — Robert Collier"
]

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Med-Flash AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed", 
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    /* Paleta de colores */
    :root {
        --primary-color: #F5A6C1; /* Rosa Principal */
        --secondary-color: #E0E0E0; /* Gris Claro */
        --text-color: #4A4A4A; /* Gris Oscuro */
        --bg-color: #FFFFFF; /* Blanco */
        --dark-bg: #1E1E1E; /* Fondo oscuro opcional */
        --dark-text: #F0F0F0; /* Texto claro opcional */
    }

    /* Estilo para tema oscuro (preferido por Streamlit) */
    body {
        background-color: var(--dark-bg);
        color: var(--dark-text);
    }
    
    /* Contenedor principal */
    .stApp {
        background-color: var(--dark-bg);
    }

    /* Barra lateral */
    [data-testid="stSidebar"] {
        background-color: #2F2F2F;
        border-right: 2px solid var(--primary-color);
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: transparent;
        color: var(--dark-text);
        border: 2px solid var(--primary-color);
        border-radius: 12px;
        width: 100%;
        margin-bottom: 10px;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: var(--primary-color);
        color: var(--text-color);
        border-color: var(--primary-color);
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: var(--dark-text) !important;
    }

    /* Botones principales */
    .stButton > button {
        background-color: var(--primary-color);
        color: var(--text-color);
        font-weight: bold;
        border-radius: 12px;
        padding: 10px 20px;
        border: none;
    }
    .stButton > button:hover {
        background-color: #F7BACF;
        color: var(--text-color);
    }
    
    /* Contenedor del Login centrado */
    [data-testid="stVerticalBlockBorderWrapper"][class*="st-emotion-cache-"] {
        max-width: 500px;
        margin: 0 auto; 
    }

    /* Estilo de Tarjetas (Flashcards) */
    .flashcard {
        background-color: #2F2F2F; 
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        border: 1px solid #4A4A4A;
        color: var(--dark-text); 
    }
    .flashcard h5 {
        color: var(--primary-color); 
        margin-bottom: 15px;
        font-size: 1.25rem;
    }

    /* Cajas de Alerta (Info, Success, Error) */
    [data-testid="stAlert"] {
        border-radius: 12px;
    }
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
        color: #000; 
    }

    /* Contenedores de Feedback */
    .feedback-correct {
        background-color: #2F2F2F;
        border: 2px solid #28a745; 
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        color: #F0F0F0;
    }
    .feedback-incorrect {
        background-color: #2F2F2F;
        border: 2px solid #dc3545; 
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        color: #F0F0F0;
    }
    .feedback-explanation {
        background-color: #2F2F2F;
        border: 2px solid #17a2b8; 
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        color: #F0F0F0;
    }

    /* Contenedor de "Doodle" */
    .doodle-container {
        width: 100%;
        height: 150px;
        background-color: var(--primary-color);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 20px;
        padding: 10px;
    }
    .doodle-container svg {
        max-width: 80%;
        max-height: 80%;
        fill: var(--text-color); 
    }
</style>
""", unsafe_allow_html=True)

# --- Listas de Materias y Sistemas (Nuevas) ---
MATERIAS = [
    "Seleccionar Materia", "Anatomía", "Fisiología", "Bioquímica", "Histología", 
    "Embriología", "Microbiología", "Parasitología", "Farmacología", 
    "Patología", "Semiología", "Medicina Interna", "Pediatría", "Neurología", "Cirugía", "Ginecología/Obstetricia", "Otra"
]

SISTEMAS = [
    "Seleccionar Sistema", "General", "Cardiovascular", "Respiratorio", "Nervioso Central", 
    "Nervioso Periférico", "Digestivo", "Renal (Urinario)", "Musculoesquelético", 
    "Endocrino", "Hematológico", "Inmunológico", "Tegumentario", "Reproductivo", "Otro"
]
# --- Funciones de Extracción ---
def extraer_texto_pdf(file_stream):
    try:
        doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()
        doc.close()
        return texto
    except Exception as e:
        return f"Error al procesar PDF: {e}"

def extraer_texto_pptx(file_stream):
    try:
        prs = Presentation(file_stream)
        texto = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texto += shape.text + "\n"
        return texto
    except Exception as e:
        return f"Error al procesar PPTX: {e}"

# --- Estado de Sesión ---
if 'page' not in st.session_state:
    st.session_state.page = "Cargar Contenido"
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None
if 'current_exam' not in st.session_state:
    st.session_state.current_exam = None
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'user_answer' not in st.session_state:
    st.session_state.user_answer = None
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False
if 'exam_results' not in st.session_state:
    st.session_state.exam_results = []
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
if "user_level" not in st.session_state:
    st.session_state.user_level = "Nivel 1 (Novato)"
if "materia_actual" not in st.session_state: # Nuevo
    st.session_state.materia_actual = MATERIAS[0]
if "sistema_actual" not in st.session_state: # Nuevo
    st.session_state.sistema_actual = SISTEMAS[0]

# --- Funciones de API (Gemini y Firestore) ---

@st.cache_resource
def init_firebase():
    try:
        if "FIREBASE_SERVICE_ACCOUNT" not in st.secrets:
            st.error("Secret de Firebase no encontrado.")
            return None
        
        cred_json = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        cred = credentials.Certificate(cred_json)
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            
        return firestore.client()
    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        return None

db = init_firebase()

def check_api_key():
    if "GOOGLE_API_KEY" not in st.secrets:
        return False
    if not st.secrets["GOOGLE_API_KEY"]:
        return False
    return True

api_key_disponible = check_api_key()
gemini_model = None
if api_key_disponible:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-09-2025")
    except Exception as e:
        st.error(f"Error al configurar Gemini: {e}")
        api_key_disponible = False

# --- Funciones de Base de Datos (Firestore) ---

def get_all_users_credentials():
    """Obtiene todos los usuarios para configurar el autenticador."""
    if not db: return {}
    try:
        users_ref = db.collection('usuarios')
        docs = users_ref.stream()
        usernames_dict = {}
        for doc in docs:
            data = doc.to_dict()
            usernames_dict[doc.id] = {
                'email': data.get('email', ''),
                'name': data.get('name', doc.id),
                'password': data.get('password', '')
            }
        if not usernames_dict: # Si no hay usuarios, creamos uno por defecto (admin)
             # Hash de prueba para "123"
             default_hash = bcrypt.hashpw("123".encode(), bcrypt.gensalt()).decode()
             usernames_dict['drdavid'] = {'email': 'david@medflash.ai', 'name': 'Dr. David', 'password': default_hash}
        
        return {'usernames': usernames_dict}
    except Exception as e:
        st.error(f"Error cargando usuarios: {e}")
        return {}

def register_new_user(name, email, username, password):
    """Registra un nuevo estudiante en Firestore."""
    if not db: return False
    try:
        # Verificar si ya existe
        doc_ref = db.collection('usuarios').document(username)
        if doc_ref.get().exists:
            return "exists"
        
        # Hashear password
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Guardar datos iniciales (Nivel 1)
        doc_ref.set({
            'name': name,
            'email': email,
            'password': hashed_pw,
            'level': "Nivel 1 (Novato)",
            'xp': 0
        })
        return "success"
    except Exception as e:
        return str(e)

def get_user_progress(username):
    """Obtiene el nivel y XP del estudiante."""
    if not db: return "Nivel 1 (Novato)", 0
    try:
        doc = db.collection('usuarios').document(username).get()
        if doc.exists:
            data = doc.to_dict()
            return data.get('level', "Nivel 1 (Novato)"), data.get('xp', 0)
    except:
        pass
    return "Nivel 1 (Novato)", 0

def update_user_level(username, passed_exam):
    """Actualiza el nivel del estudiante según su desempeño."""
    if not db: return
    try:
        doc_ref = db.collection('usuarios').document(username)
        doc = doc_ref.get()
        if not doc.exists: return
        
        data = doc.to_dict()
        current_level = data.get('level', "Nivel 1 (Novato)")
        current_xp = data.get('xp', 0)
        
        # Lógica de niveles
        levels_order = ["Nivel 1 (Novato)", "Nivel 2 (Estudiante)", "Nivel 3 (Interno)", "Nivel 4 (Residente)", "Nivel 5 (Especialista)"]
        
        new_level = current_level
        msg = ""
        
        if passed_exam:
            current_xp += 10
            # Subir nivel si tiene suficiente XP (lógica simple por ahora)
            # O simplemente subir si pasa el examen con nota alta
            try:
                current_idx = levels_order.index(current_level)
                if current_idx < len(levels_order) - 1:
                    new_level = levels_order[current_idx + 1]
                    msg = f"¡Has subido de nivel! Ahora eres: {new_level} 🌟"
            except:
                pass
        else:
            # Si falla, se mantiene o baja XP
             msg = "Sigue practicando para subir de nivel."

        doc_ref.update({
            'level': new_level,
            'xp': current_xp
        })
        return new_level, msg

    except Exception as e:
        st.error(f"Error actualizando nivel: {e}")
        return None, None

def get_user_decks(username):
    if not db or not username: return {}
    try:
        user_ref = db.collection('usuarios').document(username)
        decks_ref = user_ref.collection('mazos')
        decks = decks_ref.stream()
        user_decks = {}
        for deck in decks:
            user_decks[deck.id] = deck.to_dict()
            # Guardamos el diccionario completo, no solo las preguntas
        return user_decks
    except Exception as e:
        st.error(f"Error al cargar mazos: {e}")
        return {}

def save_user_deck(username, deck_name, deck_content, materia, sistema):
    if not db or not username: return False
    try:
        user_ref = db.collection('usuarios').document(username)
        deck_ref = user_ref.collection('mazos').document(deck_name)
        deck_ref.set({
            'preguntas': deck_content,
            'materia': materia,
            'sistema': sistema,
            'creado': firestore.SERVER_TIMESTAMP
        }) 
        return True
    except Exception as e:
        st.error(f"Error al guardar el mazo: {e}")
        return False

def delete_user_deck(username, deck_name):
    if not db or not username: return False
    try:
        user_ref = db.collection('usuarios').document(username)
        deck_ref = user_ref.collection('mazos').document(deck_name)
        deck_ref.delete()
        return True
    except Exception as e:
        st.error(f"Error al eliminar el mazo: {e}")
        return False

# --- CONFIGURACIÓN DE AUTENTICACIÓN ---
# Cargar usuarios desde Firestore
credentials_data = get_all_users_credentials()

config = {
    'credentials': credentials_data,
    'cookie': {
        'expiry_days': 30,
        'key': 'medflash_auth_key_12345', 
        'name': 'medflash_auth_cookie'
    },
    'preauthorized': {'emails': []}
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']['emails']
)

# --- INTERFAZ PRINCIPAL ---
if not st.session_state.get("authentication_status"):
    st.title("Med-Flash AI 🧬")
    
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse 📝"])
    
    with tab1:
        authenticator.login('main')
        
    with tab2:
        st.subheader("Crear nueva cuenta de estudiante")
        with st.form("register_form"):
            new_name = st.text_input("Nombre Completo")
            new_email = st.text_input("Correo Electrónico")
            new_user = st.text_input("Usuario")
            new_pass = st.text_input("Contraseña", type="password")
            new_pass2 = st.text_input("Repetir Contraseña", type="password")
            submit_reg = st.form_submit_button("Registrarme")
            
            if submit_reg:
                if new_pass != new_pass2:
                    st.error("Las contraseñas no coinciden.")
                elif len(new_pass) < 4:
                    st.error("La contraseña es muy corta.")
                elif not new_user or not new_name:
                    st.error("Por favor completa todos los campos.")
                else:
                    res = register_new_user(new_name, new_email, new_user, new_pass)
                    if res == "success":
                        st.success("¡Registro exitoso! Por favor ve a la pestaña 'Iniciar Sesión'.")
                        time.sleep(1)
                        st.rerun()
                    elif res == "exists":
                        st.error("Ese usuario ya existe. Prueba con otro.")
                    else:
                        st.error(f"Error en el registro: {res}")

# --- APP LOGUEADA ---
if st.session_state["authentication_status"]:
    
    # Datos del usuario actual
    username = st.session_state["username"]
    name = st.session_state["name"]
    
    # Cargar Nivel y Mazos
    if "user_level" not in st.session_state or st.session_state.get("last_user") != username:
        lvl, xp = get_user_progress(username)
        st.session_state.user_level = lvl
        st.session_state.user_xp = xp
        st.session_state.flashcard_library = get_user_decks(username)
        st.session_state.last_user = username

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.title("Med-Flash AI 🧬")
        st.markdown(f"Hola, **{name}** 👋")
        st.markdown(f"**Nivel:** {st.session_state.user_level}")
        
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.markdown("---")
        
        st.markdown(f"""
        <div class="doodle-container">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 3H5C3.89543 3 3 3.89543 3 5V19C3 20.1046 3.89543 21 5 21H19C20.1046 21 21 20.1046 21 19V5C21 3.89543 20.1046 3 19 3ZM19 5V19H5V5H19Z"></path>
                <path d="M17 7H7V17H17V7Z" fill="var(--primary-color)"></path>
                <path d="M12 8C10.6667 8 9.33333 9.33333 8 10C9.33333 10.6667 10.6667 12 12 12C13.3333 12 14.6667 10.6667 16 10C14.6667 9.33333 13.3333 8 12 8Z" fill="var(--text-color)"></path>
                <path d="M12 13C10.6667 13 9.33333 14.3333 8 15C9.33333 15.6667 10.6667 17 12 17C13.3333 17 14.6667 15.6667 16 15C14.6667 14.3333 13.3333 13 12 13Z" fill="var(--text-color)"></path>
                <path d="M12 10.5C11.1716 10.5 10.5 11.1716 10.5 12C10.5 12.8284 11.1716 13.5 12 13.5C12.8284 13.5 13.5 12.8284 13.5 12C13.5 11.1716 12.8284 10.5 12 10.5Z" fill="var(--primary-color)"></path>
            </svg>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("1. Cargar Contenido", use_container_width=True):
            st.session_state.page = "Cargar Contenido"
        if st.button("2. Verificación IA", use_container_width=True):
            st.session_state.page = "Verificación IA"
        if st.button("3. Generar Examen", use_container_width=True):
            st.session_state.page = "Generar Examen"
        if st.button("4. Estudiar y Progreso", use_container_width=True):
            st.session_state.page = "Mi Progreso"

    # 1. Carga de Contenido (MOVIMOS CATEGORIZACIÓN AQUÍ)
    if st.session_state.page == "Cargar Contenido":
        st.header("1. Define y Carga tu Contenido 📚")
        st.markdown("Primero, define la categoría médica para que la IA se enfoque correctamente.")
        
        col1, col2 = st.columns(2)
        with col1:
            # SELECCIÓN DE MATERIA (Guardada en session_state)
            st.session_state.materia_actual = st.selectbox("Materia:", options=MATERIAS, key="input_materia")
        with col2:
            # SELECCIÓN DE SISTEMA (Guardada en session_state)
            st.session_state.sistema_actual = st.selectbox("Sistema/Órgano:", options=SISTEMAS, key="input_sistema")

        st.markdown("---")

        if st.session_state.materia_actual == MATERIAS[0] or st.session_state.sistema_actual == SISTEMAS[0]:
            st.warning("Por favor, selecciona una Materia y un Sistema antes de subir un archivo.")
        else:
            st.success(f"Contexto de Estudio: **{st.session_state.materia_actual}** / **{st.session_state.sistema_actual}**")

            uploaded_file = st.file_uploader(
                "Sube archivos .pdf, .pptx, .txt, .md para analizar",
                type=["pdf", "pptx", "txt", "md"],
                accept_multiple_files=False,
            )
            
            if uploaded_file:
                file_type = uploaded_file.type
                texto_extraido = ""
                
                with st.spinner(f"Procesando {uploaded_file.name}..."):
                    try:
                        if file_type == "application/pdf":
                            texto_extraido = extraer_texto_pdf(uploaded_file)
                        elif file_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                            texto_extraido = extraer_texto_pptx(uploaded_file)
                        elif file_type in ["text/plain", "text/markdown"]:
                            texto_extraido = uploaded_file.read().decode("utf-8")
                        
                        st.session_state.extracted_content = texto_extraido
                        st.success("¡Archivo procesado con éxito!")
                        st.info(f"Se extrajeron {len(texto_extraido)} caracteres. Continúa con 'Verificación IA'.")
                        
                    except Exception as e:
                        st.error(f"Ocurrió un error al procesar el archivo: {e}")
                        st.session_state.extracted_content = None

        if st.session_state.extracted_content:
            st.subheader("Texto Extraído (Primeros 1000 caracteres):")
            st.text_area("", st.session_state.extracted_content[:1000] + "...", height=300)

    # 2. Verificación Médica
    elif st.session_state.page == "Verificación IA":
        st.header("2. Verificación Médica con IA 🔬")
        
        if not st.session_state.extracted_content:
            st.warning("Por favor, carga un archivo primero en la pestaña 'Cargar Contenido'.")
        elif st.session_state.materia_actual == MATERIAS[0]:
             st.warning("Por favor, define la Materia y el Sistema en la pestaña 'Cargar Contenido'.")
        else:
            st.subheader(f"Contexto: **{st.session_state.materia_actual}** / **{st.session_state.sistema_actual}**")
            st.text_area("Contenido a Verificar:", st.session_state.extracted_content, height=300, key="verif_content")
            
            if st.button("🔬 Analizar Precisión"):
                try:
                    prompt_parts = [
                        f"Rol: Eres un profesor de medicina en {st.session_state.materia_actual} y revisor científico experto.",
                        f"Contexto: {st.session_state.materia_actual} aplicada al sistema {st.session_state.sistema_actual}.",
                        f"Texto a revisar:\n---\n{st.session_state.extracted_content}\n---\n",
                        "Tu Tarea: Analiza el texto y evalúa su precisión científica, coherencia y claridad.",
                        "Marca los conceptos clave con un color/ícono:",
                        "🟢 Correcto y claro.",
                        "🟡 Parcialmente correcto (requiere aclaración).",
                        "🔴 Incorrecto o confuso.",
                        "Provee un resumen de tu análisis en formato Markdown.",
                        "Para puntos 🟡 y 🔴, provee una breve sugerencia o corrección con referencia a fuentes médicas estándar."
                    ]

                    with st.spinner("🧠 La IA está analizando la precisión..."):
                        response = gemini_model.generate_content(prompt_parts)
                        st.subheader("Resultados del Análisis de Gemini:")
                        st.markdown(response.text)

                except Exception as e:
                    st.error(f"Error al conectar con Gemini: {e}")

    # 3. Generador de Preguntas (ADAPTATIVO)
    elif st.session_state.page == "Generar Examen":
        st.header("3. Generar Mazo de Flashcards 🎓")
        st.markdown(f"**Nivel actual del estudiante:** {st.session_state.user_level}")
        
        if not st.session_state.extracted_content:
            st.warning("Por favor, carga un archivo primero en la pestaña 'Cargar Contenido'.")
        elif st.session_state.materia_actual == MATERIAS[0]:
             st.warning("Por favor, define la Materia y el Sistema en la pestaña 'Cargar Contenido'.")
        else:
            st.info(f"El examen será de **{st.session_state.materia_actual}** / **{st.session_state.sistema_actual}** y se adaptará a tu nivel.")

            deck_name = st.text_input("Nombre del Mazo (ej. Repaso Parcial 1):")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Dificultad:** Adaptativa ({st.session_state.user_level})")
            with col2:
                st.session_state.num_questions = st.number_input("Número de Preguntas:", min_value=1, max_value=10, value=5)
            
            if st.button("🚀 Generar Examen Adaptativo"):
                if not deck_name:
                    st.warning("Por favor, dale un nombre a tu mazo.")
                elif deck_name in st.session_state.flashcard_library:
                    st.error(f"Ya existe un mazo con el nombre '{deck_name}'.")
                else:
                    restart_exam()
                    try:
                        # PROMPT ADAPTATIVO MEJORADO
                        level_instruction = ""
                        if "Novato" in st.session_state.user_level or "Nivel 1" in st.session_state.user_level:
                            level_instruction = "El estudiante es Nivel NOVATO. Genera preguntas de conceptos BÁSICOS, definiciones fundamentales y anatomía simple. Evita casos clínicos complejos. Sé didáctico."
                        elif "Especialista" in st.session_state.user_level:
                            level_instruction = "El estudiante es NIVEL ESPECIALISTA. Genera preguntas de alta complejidad, casos clínicos con matices, fisiopatología avanzada y toma de decisiones."
                        else:
                            level_instruction = f"El estudiante está en {st.session_state.user_level}. Genera preguntas de dificultad INTERMEDIA/ALTA acorde a su progreso."

                        prompt_parts = [
                            f"Rol: Eres un profesor de medicina experto en {st.session_state.materia_actual} y tutor adaptativo.",
                            f"Contexto Médico: {st.session_state.materia_actual} aplicada al sistema {st.session_state.sistema_actual}.",
                            f"Instrucción de Nivel: {level_instruction}",
                            f"Texto base:\n---\n{st.session_state.extracted_content}\n---\n",
                            f"Genera {st.session_state.num_questions} preguntas de opción múltiple enfocadas en {st.session_state.materia_actual}/{st.session_state.sistema_actual}.",
                            "Formato de Respuesta: OBLIGATORIAMENTE una LISTA de objetos JSON válidos:",
                            """[{"pregunta": "...", "opciones": {"A": "...", "B": "...", "C": "...", "D": "..."}, "respuesta_correcta": "B", "explicacion": "..."}]"""
                        ]

                        with st.spinner(f"🧠 Generando preguntas de {st.session_state.materia_actual}/{st.session_state.sistema_actual} para {st.session_state.user_level}..."):
                            response = gemini_model.generate_content(prompt_parts)
                            clean_response = response.text.strip().replace('```json', '').replace('```', '')
                            preguntas_json_list = json.loads(clean_response)
                            
                            if save_user_deck(username, deck_name, preguntas_json_list, st.session_state.materia_actual, st.session_state.sistema_actual):
                                st.session_state.flashcard_library[deck_name] = preguntas_json_list
                                st.success(f"¡Mazo '{deck_name}' ({st.session_state.materia_actual}) creado y guardado!")
                                st.balloons()
                            else:
                                st.error("Error guardando en base de datos.")

                    except Exception as e:
                        st.error(f"Error generando examen: {e}")

    # 4. Estudiar y Progreso
    elif st.session_state.page == "Estudiar":
        if st.button("⬅️ Volver a mis mazos"):
            st.session_state.page = "Mi Progreso"
            restart_exam() 
            st.rerun()

        if st.session_state.current_exam:
            exam_data = st.session_state.current_exam # El diccionario completo del mazo
            exam = exam_data.get('preguntas', []) # Solo las preguntas
            
            idx = st.session_state.current_question_index
            
            if idx >= len(exam):
                st.header("¡Examen Completado! 🥳")
                
                correctas = sum(1 for r in st.session_state.exam_results if r['correcta'])
                total = len(exam)
                puntaje = (correctas / total) * 100 if total > 0 else 0
                
                # Lógica de Actualización de Nivel
                passed = puntaje >= 80
                new_lvl, msg = update_user_level(username, passed)
                if new_lvl:
                    st.session_state.user_level = new_lvl
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Tu Puntaje:", f"{puntaje:.0f}%", f"{correctas}/{total} correctas")
                with col2:
                    if passed:
                        st.success("¡Excelente desempeño! 🌟")
                        if msg: st.markdown(f"### {msg}")
                    elif puntaje < 40:
                        st.warning("Te sugerimos repasar conceptos básicos antes de avanzar.")
                    else:
                        st.info("Buen intento. Sigue practicando para subir de nivel.")

                labels = ['Correctas', 'Incorrectas']
                values = [correctas, total - correctas]
                colors = ['#28a745', '#dc3545'] 

                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3, marker_colors=colors)])
                fig.update_layout(title_text='Resumen', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#F0F0F0')
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Revisión Detallada:")
                for i, result in enumerate(st.session_state.exam_results):
                    q = exam[i]
                    if result['correcta']:
                        st.markdown(f"""<div class="feedback-correct">✅ <strong>{i+1}. Correcto</strong> ({result['seleccionada']})</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="feedback-incorrect">❌ <strong>{i+1}. Incorrecto</strong> (Tu: {result['seleccionada']} | Ok: {result['correcta_texto']})</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="feedback-explanation">🧠 {q['explicacion']}</div>""", unsafe_allow_html=True)
                
                if st.button("Volver a mis mazos", on_click=restart_exam, key="volver_final"):
                    st.session_state.page = "Mi Progreso"
                    st.rerun() 
            
            else:
                # Mostrar pregunta
                card = exam[idx]
                st.subheader(f"Pregunta {idx + 1} de {len(exam)}")
                st.markdown('<div class="flashcard">', unsafe_allow_html=True)
                st.markdown(f"<h5>{card['pregunta']}</h5>", unsafe_allow_html=True)
                opciones = list(card["opciones"].values())
                st.radio("Respuesta:", options=opciones, key=f"user_answer_{idx}", disabled=st.session_state.show_explanation)
                st.markdown('</div>', unsafe_allow_html=True) 
                
                if not st.session_state.show_explanation:
                    if st.button("Responder"):
                        sel = st.session_state.get(f"user_answer_{idx}") 
                        if sel: 
                            st.session_state.user_answer = sel 
                            st.session_state.show_explanation = True
                            
                            correct_ltr = card["respuesta_correcta"]
                            correct_txt = card["opciones"][correct_ltr]
                            es_correcta = (sel == correct_txt)
                            
                            st.session_state.exam_results.append({
                                'correcta': es_correcta,
                                'seleccionada': sel,
                                'correcta_texto': correct_txt
                            })
                            st.rerun() 
                        else:
                            st.warning("Selecciona una respuesta.")
                
                if st.session_state.show_explanation:
                    res = st.session_state.exam_results[idx]
                    if res['correcta']:
                        st.markdown(f"""<div class="feedback-correct">✅ ¡Correcto!</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="feedback-incorrect">❌ Incorrecto. Era: {res['correcta_texto']}</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="feedback-explanation">🧠 {card['explicacion']}</div>""", unsafe_allow_html=True)
                    st.button("Siguiente ➡️", on_click=go_to_next_question)

    elif st.session_state.page == "Mi Progreso":
        st.header("4. Estudiar y Progreso 🏆")
        st.subheader(f"Mis Mazos ({name})")
        st.caption(f"Nivel Actual: {st.session_state.user_level}")
        
        if not st.session_state.flashcard_library:
            st.session_state.flashcard_library = get_user_decks(username)

        if not st.session_state.flashcard_library:
            st.info("No hay mazos guardados. Ve a 'Generar Examen'.")
        else:
            
            # Mostrar la lista de mazos con sus etiquetas
            deck_options = []
            for name, data in st.session_state.flashcard_library.items():
                materia = data.get('materia', 'N/A')
                sistema = data.get('sistema', 'N/A')
                deck_options.append(f"[{materia}/{sistema}] - {name}")

            c1, c2 = st.columns([2, 1])
            with c1:
                sel_display = st.selectbox("Elige mazo:", options=deck_options)
                # Extraer el nombre real del mazo (lo que está después de ' - ')
                sel_deck_name = sel_display.split(' - ')[-1] if ' - ' in sel_display else sel_display
            
            with c2:
                if st.button("Iniciar 🚀", type="primary"):
                    if sel_deck_name: 
                        restart_exam()
                        # Cargamos el diccionario completo del mazo (que incluye preguntas, materia, sistema)
                        st.session_state.current_exam = st.session_state.flashcard_library[sel_deck_name]
                        st.session_state.page = "Estudiar"
                        st.rerun()
                if st.button("🗑️ Eliminar"):
                    if sel_deck_name: 
                        if delete_user_deck(username, sel_deck_name):
                            del st.session_state.flashcard_library[sel_deck_name]
                            st.success("Eliminado.")
                            st.rerun()

# Manejo de errores de login (fuera del bloque principal)
elif st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
elif st.session_state["authentication_status"] is None:
    pass # Esperando input en la pantalla de login
