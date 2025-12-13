import streamlit as st
import requests

# ==========================================
# 1. TUS CLAVES (¡RELLENA ESTO!)
# ==========================================

# Accessing keys securely from the cloud (or local secrets.toml)
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
    HKU_API_KEY = st.secrets["HKU_API_KEY"]
except FileNotFoundError:
    st.error("Secrets not found! Please create a .streamlit/secrets.toml file locally or set up Secrets in Streamlit Cloud.")
    st.stop()

# El nombre del modelo (según tus capturas es este)
DEPLOYMENT_ID = "DeepSeek-V3" 

# La dirección web exacta para DeepSeek en HKU
HKU_ENDPOINT = "https://api.hku.hk/deepseek/models/chat/completions"

# ==========================================
# 2. NOTION CONNECTION (CONTENT LOADER)
# ==========================================
def get_weekly_content():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Only fetch rows where "Activo" checkbox is checked
    payload = {
        "filter": {
            "property": "Activo",
            "checkbox": {
                "equals": True
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return f"Notion Error ({response.status_code}): {response.text}"
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return "No active units found in Notion. Please check the 'Activo' column."

        full_context = ""
        for page in results:
            props = page["properties"]
            
            # Helper to extract clean text from Notion columns
            def get_text(col_name):
                # Title column is special
                if col_name == "Nombre":
                    items = props.get("Nombre", {}).get("title", [])
                else:
                    items = props.get(col_name, {}).get("rich_text", [])
                
                return " ".join([item.get("text", {}).get("content", "") for item in items])

            name = get_text("Nombre") or "Untitled"
            lexicon = get_text("Léxico")
            grammar = get_text("Gramática")
            communication = get_text("Comunicación")

            full_context += f"""
            === ACTIVE UNIT: {name} ===
            [VOCABULARY]: {lexicon}
            [GRAMMAR RULES]: {grammar}
            [COMMUNICATION/INFO]: {communication}
            ==============================
            """
        
        return full_context

    except Exception as e:
        return f"Notion Connection Error: {e}"

# ==========================================
# 3. AI CONNECTION (HKU GATEWAY)
# ==========================================
def get_ai_response(user_message, notion_context):
    
    # --- THE SUPER PROMPT (UPDATED & FULL) ---
    system_prompt = f"""
    [ROL Y PERFIL]
    Eres "ProfeBot", el tutor oficial de Español SPAN1001 de la Universidad de Hong Kong (HKU).
    Tus alumnos son adultos universitarios, inteligentes y multilingües (Inglés, Mandarín, Cantonés).
    Tu tono es: Académico pero cercano, motivador, paciente y claro.

    [REGLAS SAGRADAS DE CONTENIDO]
    1. LA BIBLIA ES EL CONTENIDO ACTIVO:
       - Tienes terminantemente PROHIBIDO usar vocabulario, tiempos verbales o reglas gramaticales que no aparezcan en la lista de "CONTENIDO ACTIVO" de abajo.
       - Si el alumno pregunta por algo avanzado (ej: "fui", "comeré"), felicítalo por su curiosidad, pero dile en Inglés que eso pertenece a niveles futuros y enséñale la alternativa correcta usando SOLO lo que sabe hoy.

    2. IDIOMAS:
       - Tus explicaciones gramaticales deben ser siempre en INGLÉS para evitar confusiones.
       - Los ejemplos deben ser en ESPAÑOL.
       - Si el alumno te habla en Chino (Tradicional/Simplificado), responde explicando en Inglés.

    3. ESTILO DE ENSEÑANZA ADULTO:
       - Usa ejemplos universitarios (campus, cafetería, estudios, viajes, compañeros de piso). Evita ejemplos infantiles.
       - Si das una explicación, SIEMPRE acompáñala de 3 ejemplos prácticos en español basados en el vocabulario permitido.

    [GESTIÓN DEL FLUJO Y OPCIONES]
    No te despidas simplemente. Tu objetivo es mantener al alumno practicando.
    Al final de CADA respuesta, debes proponer 3 caminos a seguir, variando la redacción para no ser repetitivo.

    Elige siempre 3 de estas opciones según lo que acabéis de hablar:
    A) "Generar Ejercicio": Crear un ejercicio de huecos (fill-in-the-blanks) o selección múltiple.
    B) "Más Ejemplos": Dar 5 frases nuevas usando la gramática explicada.
    C) "Profundizar": Explicar el "por qué" de la regla con más detalle o contrastar con el inglés.
    D) "Conversar": Iniciar un roleplay corto (ej: en la tienda, en la clase).
    E) "Lectura": Generar un párrafo breve de comprensión lectora.

    IMPORTANTE (COMANDOS DE BOTONES):
    Si el alumno escribe "BUTTON_EXERCISE", genera un ejercicio inmediatamente.
    Si el alumno escribe "BUTTON_EXAMPLES", genera solo ejemplos adicionales.
    Si el alumno escribe "BUTTON_EXPLAIN", amplía la explicación teórica en inglés.
    Si el alumno escribe "BUTTON_CONVERSATION", inicia un roleplay.

    --- CONTENIDO ACTIVO DE ESTA SEMANA (FROM NOTION) ---
    {notion_context}
    """

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": HKU_API_KEY
    }
    
    params = {"deployment-id": DEPLOYMENT_ID}
    
    payload = {
        "model": DEPLOYMENT_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 1000,
        "temperature": 0.5 
    }

    try:
        response = requests.post(HKU_ENDPOINT, headers=headers, params=params, json=payload)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"HKU API Error ({response.status_code}): {response.text}"
            
    except Exception as e:
        return f"Connection Error: {e}"

# ==========================================
# 4. USER INTERFACE (STREAMLIT) - NOW IN ENGLISH
# ==========================================
st.set_page_config(page_title="ProfeBot HKU", page_icon="🎓")

st.title("🎓 ProfeBot: SPAN1001 Tutor")
st.caption("AI Tutor connected to Notion Syllabus & DeepSeek (HKU)")

# Initialize Context
if "contexto" not in st.session_state:
    with st.spinner('Syncing with Notion Syllabus...'):
        st.session_state.contexto = get_weekly_content()
        if "Error" not in st.session_state.contexto:
            st.success("✅ Course data loaded successfully.")
        else:
            st.error(st.session_state.contexto)

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "¡Hola! I am ProfeBot. How can I help you with your Spanish or the course details today?"
    })

# Display Chat History
for message in st.session_state.messages:
    tipo = "user" if message["role"] == "user" else "assistant"
    with st.chat_message(tipo):
        st.markdown(message["content"])

# Button Logic Helper
def handle_button_click(hidden_command):
    # Add user message to history (hidden command)
    st.session_state.messages.append({"role": "user", "content": hidden_command})
    # Rerun to trigger AI response
    st.rerun()

# --- ACTION BUTTONS (English UI) ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📝 Practice"): handle_button_click("BUTTON_EXERCISE")
with col2:
    if st.button("➕ More Examples"): handle_button_click("BUTTON_EXAMPLES")
with col3:
    if st.button("🧐 Explain More"): handle_button_click("BUTTON_EXPLAIN")
with col4:
    if st.button("💬 Roleplay"): handle_button_click("BUTTON_CONVERSATION")

# Chat Input
if prompt := st.chat_input("Type here (English, Español, 中文)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("ProfeBot is thinking..."):
            ai_response = get_ai_response(prompt, st.session_state.contexto)
            st.markdown(ai_response)
    
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

# Sidebar for Admin
with st.sidebar:
    st.info("Instructor Panel")
    if st.button("🔄 Refresh Notion Data"):
        st.session_state.contexto = get_weekly_content()
        st.rerun()
