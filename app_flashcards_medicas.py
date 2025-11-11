import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from pptx import Presentation
import pandas as pd
import io
import google.generativeai as genai
import json

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Med-Flash AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS VISUALES (Según tu prompt) ---
# Paleta: #F5A6C1 (Rosa), #E0E0E0 (Gris claro), #4A4A4A (Gris oscuro), #FFFFFF (Blanco)
st.markdown("""
<style>
/* Paleta de Colores */
:root {
    --color-principal: #F5A6C1;
    --color-principal-hover: #E08BAA; /* Rosa más oscuro */
    --gris-claro: #E0E0E0;
    --gris-oscuro: #4A4A4A;
    --blanco: #FFFFFF;
    --verde-correcto: #28a745;
    --amarillo-parcial: #ffc107;
    --rojo-incorrecto: #dc3545;
}

/* Fondo de la app */
.main {
    background-color: #F8F9FA; /* Un gris muy sutil */
}

/* Botones Redondeados */
.stButton>button {
    border-radius: 20px !important;
    background-color: var(--color-principal) !important;
    color: var(--blanco) !important;
    border: none !important;
    padding: 10px 20px !important;
    font-weight: bold !important;
}
.stButton>button:hover {
    background-color: var(--color-principal-hover) !important;
    color: var(--blanco) !important;
}

/* Estilo de Tarjetas (Flashcards) */
.flashcard {
    background-color: var(--blanco);
    border: 2px solid var(--gris-claro);
    border-radius: 15px;
    padding: 25px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    min-height: 250px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

/* Títulos */
h1, h2 {
    color: var(--gris-oscuro);
}

/* Verificación Médica Colores */
.verif-correcto { color: var(--verde-correcto); border-left: 5px solid var(--verde-correcto); padding-left: 10px; }
.verif-parcial { color: var(--amarillo-parcial); border-left: 5px solid var(--amarillo-parcial); padding-left: 10px; }
.verif-incorrecto { color: var(--rojo-incorrecto); border-left: 5px solid var(--rojo-incorrecto); padding-left: 10px; }

</style>
""", unsafe_allow_html=True)

# --- Funciones de Extracción (Placeholders) ---
# (Aquí iría la lógica completa de Tika, PyMuPDF, etc.)

def extraer_texto_pdf(file_stream):
    try:
        doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()
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
if 'current_exam' not in st.session_state: # Renombrado de 'current_flashcard'
    st.session_state.current_exam = None
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'user_answer' not in st.session_state:
    st.session_state.user_answer = None
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False
if 'exam_results' not in st.session_state:
    st.session_state.exam_results = []


# --- BARRA LATERAL (Navegación) ---
with st.sidebar:
    st.title("🧠 Med-Flash AI")
    st.markdown("Tu asistente de estudio médico con IA.")
    
    # Usamos st.radio para la navegación principal
    page = st.radio(
        "Navegación",
        ["Cargar Contenido", "Verificación IA", "Generar Examen", "Mi Progreso"],
        label_visibility="collapsed"
    )
    st.session_state.page = page
    
    st.markdown("---")
    # Placeholder para icono "doodle"
    st.image("https://placehold.co/250x150/F5A6C1/FFFFFF?text=Icono+Médico+Doodle", use_column_width=True)
    st.markdown(f"<p style='color:var(--gris-oscuro); text-align: center;'>¡Hola Dr. David!</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    # Campo para la API Key de Gemini
    api_key = st.text_input("Google AI API Key", type="password", help="Obtén tu API Key de Google AI Studio.")
    st.session_state.api_key = api_key


# --- CUERPO PRINCIPAL DE LA APP ---

# 1. Carga de Contenido
if st.session_state.page == "Cargar Contenido":
    st.header("1. Cargar Contenido 📤")
    st.markdown("Sube tu material de estudio. Extraeremos el texto y las imágenes automáticamente.")

    uploaded_file = st.file_uploader(
        "Sube archivos .pdf, .pptx, .jpg, .png, .txt, .csv, .xlsx",
        type=["pdf", "pptx", "jpg", "png", "txt", "csv", "xlsx"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        st.info(f"Procesando archivo: `{uploaded_file.name}`...")
        
        # Lógica de extracción
        content = None
        if uploaded_file.type == "application/pdf":
            content = extraer_texto_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            content = extraer_texto_pptx(uploaded_file)
        elif uploaded_file.type in ["image/jpeg", "image/png"]:
            img = Image.open(uploaded_file)
            st.image(img, caption="Imagen cargada. (La extracción de texto de imagen (OCR) se implementará aquí).")
            content = "[Placeholder: Texto extraído de imagen con OCR]"
        elif uploaded_file.type == "text/plain":
            content = str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            df = pd.read_csv(uploaded_file) if uploaded_file.type == "text/csv" else pd.read_excel(uploaded_file)
            st.dataframe(df.head())
            content = df.to_string()
            
        if content:
            st.session_state.extracted_content = content
            st.success("¡Contenido extraído! Puedes ir a 'Verificación IA' o 'Generar Examen'.")
            with st.expander("Ver texto extraído (primeros 1000 caracteres)"):
                st.text_area("Texto", value=content[:1000]+"...", height=300, disabled=True)

# 2. Verificación Médica
elif st.session_state.page == "Verificación IA":
    st.header("2. Verificación Médica con IA 🔬")
    st.markdown("Analizamos la precisión científica de tu contenido.")

    if not st.session_state.extracted_content:
        st.warning("Por favor, carga un archivo primero en la sección 'Cargar Contenido'.")
    elif not st.session_state.api_key:
        st.warning("Por favor, introduce tu Google AI API Key en la barra lateral para continuar.")
    else:
        st.text_area("Contenido a Verificar", value=st.session_state.extracted_content, height=250, disabled=True)
        
        if st.button("🔬 Analizar Precisión"):
            # --- CONEXIÓN REAL A GEMINI API ---
            try:
                genai.configure(api_key=st.session_state.api_key)
                
                # Configuración del modelo
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 2048,
                }
                model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-09-2025",
                                              generation_config=generation_config)
                
                # Creación del Prompt (Instrucción)
                prompt_parts = [
                    "Rol: Eres un experto en educación médica y un revisor científico riguroso.",
                    "Contexto: El siguiente texto fue extraído del material de estudio de un estudiante de medicina.",
                    f"Texto a Analizar:\n---\n{st.session_state.extracted_content}\n---\n",
                    "Tu Tarea: Analiza el texto. Para cada concepto clave o afirmación principal, evalúa su precisión científica y claridad.",
                    "Formato de Respuesta: Responde en viñetas (Markdown). Marca cada punto como:",
                    "🟢 Correcto: [Concepto] - [Breve análisis de por qué es correcto].",
                    "🟡 Parcialmente Correcto: [Concepto] - [Aclaración necesaria].",
                    "🔴 Incorrecto: [Concepto] - [Corrección clara y concisa].",
                    "Para puntos 🟡 y 🔴, provee una breve sugerencia o corrección con referencia a fuentes médicas estándar (ej. Harrison, ILAE, etc.)."
                ]

                with st.spinner("🧠 La IA está analizando la precisión..."):
                    # Generar contenido
                    response = model.generate_content(prompt_parts)
                    
                    st.subheader("Resultados del Análisis de Gemini:")
                    st.markdown(response.text)

            except Exception as e:
                st.error(f"Error al contactar la API de Gemini: {e}")
                st.error("Asegúrate de que la API Key sea correcta y tenga permisos.")
            
            # --- El contenido simulado de abajo ya no se usa ---
            # st.markdown("""
            # <div class="verif-correcto">...</div>
            # ...
            # """, unsafe_allow_html=True)

# 3. Generador de Preguntas
elif st.session_state.page == "Generar Examen":
    st.header("3. Generar Examen Tipo USMLE/MIR 🎓")
    st.markdown("Generamos preguntas basadas en tu material de estudio.")

    if not st.session_state.extracted_content:
        st.warning("Por favor, carga un archivo primero para generar preguntas sobre él.")
    elif not st.session_state.api_key:
        st.warning("Por favor, introduce tu Google AI API Key en la barra lateral para continuar.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.difficulty = st.selectbox("Nivel de Dificultad:", ["Automático (Adaptativo)", "Fácil", "Medio", "Difícil"])
        with col2:
            st.session_state.subject = st.selectbox("Tipo de Materia:", ["Materias Básicas (Anatomía, Fisio...)", "Materias Clínicas (Neuro, Pediatría...)"])
        with col3:
            st.session_state.num_questions = st.number_input("Número de Preguntas:", min_value=1, max_value=10, value=5)

        
        if st.button("🚀 Generar Examen"):
            # Limpiar el examen anterior
            st.session_state.current_exam = None
            st.session_state.current_question_index = 0
            st.session_state.user_answer = None
            st.session_state.show_explanation = False
            st.session_state.exam_results = []
            
            # --- CONEXIÓN REAL A GEMINI API para MÚLTIPLES PREGUNTAS ---
            try:
                genai.configure(api_key=st.session_state.api_key)
                model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-09-2025")
                
                # Prompt para generar MÚLTIPLES preguntas en formato JSON
                prompt_parts = [
                    "Rol: Eres un profesor de medicina experto en crear preguntas de examen tipo USMLE/MIR.",
                    f"Contexto del Estudiante: Nivel {st.session_state.difficulty}, Materia {st.session_state.subject}.",
                    f"Texto base (Material de estudio):\n---\n{st.session_state.extracted_content}\n---\n",
                    f"Tu Tarea: Genera {st.session_state.num_questions} preguntas de opción múltiple (4 opciones) basadas *únicamente* en el texto base.",
                    "Las preguntas deben ser claras, concisas y relevantes al estilo de examen médico.",
                    "Formato de Respuesta: Responde OBLIGATORIAMENTE en formato JSON. La estructura debe ser una LISTA de objetos:",
                    """
                    [
                      {
                        "pregunta": "El texto completo de la pregunta 1...",
                        "opciones": {
                          "A": "Texto de la opción A",
                          "B": "Texto de la opción B",
                          "C": "Texto de la opción C",
                          "D": "Texto de la opción D"
                        },
                        "respuesta_correcta": "B",
                        "explicacion": "Una breve pero completa explicación médica..."
                      },
                      {
                        "pregunta": "El texto completo de la pregunta 2...",
                        "opciones": { ... },
                        "respuesta_correcta": "A",
                        "explicacion": "..."
                      }
                    ]
                    """
                ]

                with st.spinner(f"🧠 Gemini está creando tu examen de {st.session_state.num_questions} preguntas..."):
                    response = model.generate_content(prompt_parts)
                    
                    # Limpiar la respuesta de Gemini (a veces añade '```json\n' al inicio y '```' al final)
                    clean_response = response.text.strip().replace('```json', '').replace('```', '')
                    
                    # Parsear el JSON
                    preguntas_json_list = json.loads(clean_response)
                    st.session_state.current_exam = preguntas_json_list

            except Exception as e:
                st.error(f"Error al generar el examen con Gemini: {e}")
                st.error("Asegúrate de que la API Key sea correcta y el modelo JSON haya funcionado.")
                st.error(f"Respuesta recibida (para depuración): {response.text if 'response' in locals() else 'No response'}")

    # --- Lógica para mostrar el examen (pregunta por pregunta) ---
    if st.session_state.current_exam:
        
        exam = st.session_state.current_exam
        idx = st.session_state.current_question_index
        
        # Verificar si el examen ha terminado
        if idx >= len(exam):
            st.header("¡Examen Completado! 🥳")
            
            # Calcular puntaje
            correctas = sum(1 for r in st.session_state.exam_results if r['correcta'])
            total = len(exam)
            puntaje = (correctas / total) * 100
            
            st.metric("Tu Puntaje:", f"{puntaje:.0f}%", f"{correctas} de {total} correctas")
            
            st.subheader("Resumen de tus respuestas:")
            for i, result in enumerate(st.session_state.exam_results):
                if result['correcta']:
                    st.success(f"**Pregunta {i+1}:** Correcta. (Seleccionaste: {result['seleccionada']})")
                else:
                    st.error(f"**Pregunta {i+1}:** Incorrecta. (Seleccionaste: {result['seleccionada']}, Correcta: {result['correcta_texto']})")
            
            if st.button("Volver a intentar"):
                st.session_state.current_exam = None
                st.rerun() # Recargar la página
        
        else:
            # Mostrar la pregunta actual
            card = exam[idx]
            st.subheader(f"Tu Examen: Pregunta {idx + 1} de {len(exam)}")
            
            st.markdown('<div class="flashcard">', unsafe_allow_html=True)
            st.markdown(f"<h5>{card['pregunta']}</h5>", unsafe_allow_html=True)
            
            opciones = list(card["opciones"].values())
            
            st.radio("Selecciona tu respuesta:", 
                     options=opciones,
                     key="user_answer",
                     index=None,
                     disabled=st.session_state.show_explanation # Deshabilitar opciones después de responder
                     )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Botón de Responder (solo si no se ha respondido)
            if not st.session_state.show_explanation:
                if st.button("Responder y ver explicación"):
                    if st.session_state.user_answer:
                        st.session_state.show_explanation = True
                        
                        # Lógica de evaluación
                        user_ans_text = st.session_state.user_answer
                        correct_ans_letter = card["respuesta_correcta"]
                        correct_ans_text = card["opciones"][correct_ans_letter]
                        
                        es_correcta = (user_ans_text == correct_ans_text)
                        
                        # Guardar resultado
                        st.session_state.exam_results.append({
                            'correcta': es_correcta,
                            'seleccionada': user_ans_text,
                            'correcta_texto': correct_ans_text
                        })
                        
                        if es_correcta:
                            st.success(f"¡Correcto! La respuesta es {correct_ans_letter}: {correct_ans_text}")
                        else:
                            st.error(f"Respuesta incorrecta. Seleccionaste: '{user_ans_text}'.")
                            st.info(f"La respuesta correcta era {correct_ans_letter}: {correct_ans_text}")
                        
                        st.subheader("Explicación:")
                        st.info(card["explicacion"])
                        st.rerun() # Volver a cargar para mostrar el botón "Siguiente"
                    else:
                        st.warning("Por favor, selecciona una respuesta antes de continuar.")
            
            # Botón de Siguiente Pregunta (solo si ya se respondió)
            if st.session_state.show_explanation:
                if st.button("Siguiente Pregunta ➡️"):
                    st.session_state.current_question_index += 1
                    st.session_state.user_answer = None
                    st.session_state.show_explanation = False
                    st.rerun() # Cargar la siguiente pregunta

# 4. Progreso y Gamificación
elif st.session_state.page == "Mi Progreso":
    st.header("4. Mi Progreso y Gamificación 🏆")
    st.markdown("Tu avance, niveles e insignias.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Nivel Actual:")
        st.progress(70)
        st.markdown("<h4>Nivel: Intermedio 🩺</h4>", unsafe_allow_html=True)
        st.caption("¡Sigue así para alcanzar el Nivel Clínico!")
    
    with col2:
        st.subheader("Mis Insignias 🧬")
        st.markdown(
            "- 🧠 **Dominio en Neurofisiología**\n"
            "- 👶 **Fundamentos de Pediatría**\n"
            "- 🧪 **Maestro de Bioquímica** (Bloqueada)"
        )
        
    st.subheader("Resumen de Desempeño (Placeholder)")
    st.markdown("Aquí irían los gráficos de Plotly con tu desempeño por materia.")
    
    # Placeholder para gráfico
    chart_data = pd.DataFrame(
        {'Materia': ['Anatomía', 'Fisiología', 'Neurología', 'Pediatría'],
         'Puntaje': [85, 92, 78, 81]}
    )
    st.bar_chart(chart_data, x='Materia', y='Puntaje')

    st.markdown("---")
    st.subheader("Frase Motivacional:")
    st.info("Recuerda, la medicina se aprende un caso a la vez. ¡Sigue estudiando!")




