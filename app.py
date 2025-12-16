import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import time
from datetime import datetime
from typing import Optional, List, Dict
from PIL import Image

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
# Load favicon
try:
    favicon = Image.open("favicon.jpg")
except:
    favicon = "🎓"

st.set_page_config(
    page_title="ProfeBot - SPAN1001 Tutor",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI with floating message history
def get_custom_css(dark_mode: bool = False):
    if dark_mode:
        bg_color = "#0d1117"
        secondary_bg = "#161b22"
        text_color = "#f0f6fc"
        text_secondary = "#8b949e"
        panel_bg = "rgba(22, 27, 34, 0.92)"
        panel_border = "rgba(48, 54, 61, 0.8)"
        item_bg = "rgba(33, 38, 45, 0.9)"
        item_hover = "rgba(48, 54, 61, 0.95)"
        title_border = "#58a6ff"
        accent_color = "#58a6ff"
        accent_gradient = "linear-gradient(135deg, #58a6ff 0%, #a371f7 100%)"
        sidebar_bg = "#161b22"
        header_bg = "#0d1117"
        input_bg = "#21262d"
        border_color = "#30363d"
    else:
        bg_color = "#ffffff"
        secondary_bg = "#f6f8fa"
        text_color = "#24292f"
        text_secondary = "#57606a"
        panel_bg = "rgba(255, 255, 255, 0.92)"
        panel_border = "rgba(208, 215, 222, 0.8)"
        item_bg = "rgba(246, 248, 250, 0.9)"
        item_hover = "rgba(234, 238, 242, 0.95)"
        title_border = "#2da44e"
        accent_color = "#2da44e"
        accent_gradient = "linear-gradient(135deg, #2da44e 0%, #1a7f37 100%)"
        sidebar_bg = "#f6f8fa"
        header_bg = "#ffffff"
        input_bg = "#f6f8fa"
        border_color = "#d0d7de"
    
    return f"""
<style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=WDXL+Lubrifont+TC&display=swap');
    
    /* ===== GLOBAL DARK MODE STYLES ===== */
    {'html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {' if dark_mode else ''}
        {'background-color: ' + bg_color + ' !important;' if dark_mode else ''}
        {'color: ' + text_color + ' !important;' if dark_mode else ''}
    {'}' if dark_mode else ''}
    
    /* ===== SIDEBAR COMPLETE STYLING ===== */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {sidebar_bg} !important;
        padding-top: 0.5rem !important;
    }}
    
    [data-testid="stSidebar"] .block-container {{
        padding: 0.5rem 1rem !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
        margin-bottom: 0.3rem !important;
    }}
    
    [data-testid="stSidebar"] hr {{
        margin: 0.5rem 0 !important;
    }}
    
    [data-testid="stSidebar"] * {{
        color: {text_color} !important;
    }}
    
    /* Sidebar title with green text */
    .sidebar-title {{
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }}
    
    .sidebar-title-text {{
        color: {accent_color} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {{
        color: {text_secondary} !important;
    }}
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: {text_color} !important;
        {'background: ' + accent_gradient + ';' if dark_mode else ''}
        {'-webkit-background-clip: text;' if dark_mode else ''}
        {'-webkit-text-fill-color: transparent;' if dark_mode else ''}
        {'background-clip: text;' if dark_mode else ''}
    }}
    
    /* ===== HEADER / TOP BAR ===== */
    header, [data-testid="stHeader"] {{
        background-color: {header_bg} !important;
        border-bottom: 1px solid {border_color} !important;
    }}
    
    /* Fixed header title in Streamlit header bar */
    [data-testid="stHeader"]::before {{
        content: 'ProfeBot: SPAN1001 Interactive Tutor';
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        font-family: 'WDXL Lubrifont TC', sans-serif !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        background: {accent_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        z-index: 1000;
        white-space: nowrap;
    }}
    
    /* History item clickable */
    .history-item {{
        padding: 12px;
        margin: 8px 0;
        background: {item_bg};
        border-left: 3px solid {accent_color};
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.85rem;
    }}
    
    .history-item:hover {{
        background: {item_hover};
        transform: translateX(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,{'0.3' if dark_mode else '0.1'});
        border-left-color: {'#a371f7' if dark_mode else '#1a7f37'};
    }}
    
    .history-item:active {{
        transform: translateX(-5px) scale(0.98);
    }}
    
    /* ===== MAIN CONTENT AREA ===== */
    .main, [data-testid="stMain"] {{
        background-color: {bg_color} !important;
    }}
    
    .main .block-container {{
        padding-right: 320px;
        padding-top: 1rem;
        max-width: calc(100% - 300px);
        margin-right: 20px;
        background-color: {bg_color} !important;
    }}
    
    /* All text in main area */
    .main p, .main span, .main div {{
        color: {text_color} !important;
    }}
    
    .main .stCaption, .main small {{
        color: {text_secondary} !important;
    }}
    
    /* ===== CUSTOM TITLE STYLING ===== */
    .custom-title {{
        font-family: 'WDXL Lubrifont TC', sans-serif !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: {accent_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
        text-shadow: {'0 0 30px rgba(88, 166, 255, 0.3)' if dark_mode else 'none'};
    }}
    
    .custom-subtitle {{
        color: {text_secondary} !important;
        font-size: 1rem;
        margin-top: -10px;
    }}
    
    /* ===== FLOATING MESSAGE HISTORY PANEL ===== */
    .message-history-panel {{
        position: fixed;
        right: 20px;
        top: 80px;
        width: 280px;
        max-height: calc(100vh - 120px);
        min-height: 80px;
        height: auto;
        background: {panel_bg};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {panel_border};
        border-radius: 16px;
        padding: 15px;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0,0,0,{'0.4' if dark_mode else '0.12'});
        z-index: 999;
        transition: all 0.3s ease;
    }}
    
    .message-history-panel::-webkit-scrollbar {{
        width: 6px;
    }}
    
    .message-history-panel::-webkit-scrollbar-track {{
        background: transparent;
        border-radius: 10px;
    }}
    
    .message-history-panel::-webkit-scrollbar-thumb {{
        background: {border_color};
        border-radius: 10px;
    }}
    
    .message-history-panel::-webkit-scrollbar-thumb:hover {{
        background: {accent_color};
    }}
    
    .history-item-time {{
        font-size: 0.7rem;
        color: {text_secondary};
        margin-bottom: 4px;
    }}
    
    .history-item-text {{
        color: {text_color};
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    .history-panel-title {{
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid {title_border};
        color: {text_color};
        {'background: ' + accent_gradient + ';' if dark_mode else ''}
        {'-webkit-background-clip: text;' if dark_mode else ''}
        {'-webkit-text-fill-color: transparent;' if dark_mode else ''}
    }}
    
    .history-count {{
        font-size: 0.75rem;
        color: {text_secondary};
        font-weight: normal;
        {'-webkit-text-fill-color: ' + text_secondary + ';' if dark_mode else ''}
    }}
    
    /* ===== CHAT MESSAGES ===== */
    .stChatMessage {{
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        scroll-margin-top: 100px;
        background-color: {secondary_bg} !important;
        border: 1px solid {border_color};
    }}
    
    .stChatMessage p, .stChatMessage span, .stChatMessage div,
    .stChatMessage li, .stChatMessage strong, .stChatMessage em {{
        color: {text_color} !important;
    }}
    
    /* Force all markdown text in chat to be visible */
    [data-testid="stChatMessage"] * {{
        color: {text_color} !important;
    }}
    
    [data-testid="stChatMessage"] code {{
        background-color: {input_bg} !important;
        color: {accent_color} !important;
    }}
    
    /* ===== INPUT FIELDS ===== */
    .stTextInput input, [data-testid="stChatInput"] textarea {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
    }}
    
    /* ===== SELECTBOX STYLING ===== */
    .stSelectbox > div > div {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    
    .stSelectbox [data-baseweb="select"] {{
        background-color: {input_bg} !important;
    }}
    
    .stSelectbox [data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}
    
    .stSelectbox [data-baseweb="select"] span {{
        color: {text_color} !important;
    }}
    
    /* Dropdown menu */
    [data-baseweb="popover"] {{
        background-color: {secondary_bg} !important;
    }}
    
    [data-baseweb="popover"] li {{
        background-color: {secondary_bg} !important;
        color: {text_color} !important;
    }}
    
    [data-baseweb="popover"] li:hover {{
        background-color: {item_hover} !important;
    }}
    
    .stTextInput input:focus, [data-testid="stChatInput"] textarea:focus {{
        border-color: {accent_color} !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
    }}
    
    /* ===== BUTTONS ===== */
    .stButton button {{
        width: 100%;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        background-color: {secondary_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    
    .stButton button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,{'0.3' if dark_mode else '0.15'});
        border-color: {accent_color} !important;
        background-color: {item_hover} !important;
    }}
    
    .stButton button[kind="primary"] {{
        background: {accent_gradient} !important;
        border: none !important;
        color: white !important;
    }}
    
    /* Primary button text must be white */
    .stButton button[kind="primary"] span,
    .stButton button[kind="primary"] p,
    .stButton button[kind="primary"] div {{
        color: white !important;
    }}
    
    /* Quick action buttons */
    .quick-action-btn button {{
        height: 45px !important;
        font-weight: 500;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.5rem !important;
    }}
    
    /* ===== STATUS INDICATORS ===== */
    .status-badge {{
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.25rem;
    }}
    
    .status-success {{
        background-color: {'rgba(46, 160, 67, 0.2)' if dark_mode else '#d4edda'};
        color: {'#3fb950' if dark_mode else '#155724'};
        border: 1px solid {'#238636' if dark_mode else '#155724'};
    }}
    
    .status-error {{
        background-color: {'rgba(248, 81, 73, 0.2)' if dark_mode else '#f8d7da'};
        color: {'#f85149' if dark_mode else '#721c24'};
        border: 1px solid {'#da3633' if dark_mode else '#721c24'};
    }}
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border-radius: 8px !important;
        border: 1px solid {border_color} !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        background-color: {item_hover} !important;
        border-color: {accent_color} !important;
    }}
    
    .streamlit-expanderHeader p, .streamlit-expanderHeader span {{
        color: {text_color} !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: {secondary_bg} !important;
        border: 1px solid {border_color} !important;
        border-top: none !important;
    }}
    
    .streamlit-expanderContent p, .streamlit-expanderContent span,
    .streamlit-expanderContent div, .streamlit-expanderContent label {{
        color: {text_color} !important;
    }}
    
    /* Expander content captions */
    .streamlit-expanderContent .stCaption {{
        color: {text_secondary} !important;
    }}
    
    /* ===== DIVIDERS ===== */
    hr {{
        border-color: {border_color} !important;
    }}
    
    /* ===== METRICS ===== */
    [data-testid="stMetricValue"] {{
        color: {accent_color} !important;
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {text_secondary} !important;
    }}
    
    /* Empty state */
    .empty-history {{
        text-align: center;
        color: {text_secondary};
        font-size: 0.85rem;
        padding: 20px;
        font-style: italic;
    }}
    
    /* Loading animation */
    .loading-text {{
        animation: pulse 1.5s ease-in-out infinite;
    }}
    
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}
    
    /* Department link styling */
    .dept-link {{
        text-align: center;
        padding: 15px;
        margin-top: 10px;
        background: {item_bg};
        border-radius: 8px;
        border: 1px solid {border_color};
    }}
    
    .dept-link a {{
        color: {accent_color} !important;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
    }}
    
    .dept-link a:hover {{
        text-decoration: underline;
        {'filter: brightness(1.2);' if dark_mode else ''}
    }}
    
    /* ===== FOOTER ===== */
    footer {{
        background-color: {bg_color} !important;
    }}
    
    footer, footer * {{
        color: {text_secondary} !important;
    }}
</style>
"""

# API Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# Language configurations
LANGUAGE_OPTIONS = {
    "English": "English",
    "繁體中文 (Cantonese)": "Cantonese",
    "普通话 (Mandarin)": "Mandarin",
    "Other / Otro": "custom"
}

# ==========================================
# SECRET KEYS MANAGEMENT
# ==========================================
def load_secrets() -> Dict[str, str]:
    """Load secrets with fallback for local testing."""
    try:
        return {
            "NOTION_TOKEN": st.secrets["NOTION_TOKEN"],
            "DATABASE_ID": st.secrets["DATABASE_ID"],
            "HKU_API_KEY": st.secrets["HKU_API_KEY"]
        }
    except (FileNotFoundError, KeyError) as e:
        st.sidebar.error("⚠️ Missing secrets configuration")
        return {
            "NOTION_TOKEN": "your_notion_token_here",
            "DATABASE_ID": "your_database_id_here",
            "HKU_API_KEY": "your_hku_api_key_here"
        }

secrets = load_secrets()
NOTION_TOKEN = secrets["NOTION_TOKEN"]
DATABASE_ID = secrets["DATABASE_ID"]
HKU_API_KEY = secrets["HKU_API_KEY"]

DEPLOYMENT_ID = "DeepSeek-V3"
HKU_ENDPOINT = "https://api.hku.hk/deepseek/models/chat/completions"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def make_request_with_retry(
    method: str,
    url: str,
    headers: dict,
    json_payload: Optional[dict] = None,
    params: Optional[dict] = None,
    max_retries: int = MAX_RETRIES
) -> Optional[requests.Response]:
    """Make HTTP request with automatic retry logic for transient errors."""
    for attempt in range(max_retries):
        try:
            if method.upper() == "POST":
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=json_payload, 
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [502, 503, 504]:
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            
            return response
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                st.error(f"⏱️ Request timeout after {max_retries} attempts")
                return None
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                st.error(f"🔌 Connection error after {max_retries} attempts")
                return None
                
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    return None

def generate_thread_title(first_message: str) -> str:
    """Generate a short title from the first user message."""
    clean_msg = first_message.strip()
    if len(clean_msg) > 30:
        return clean_msg[:30] + "..."
    return clean_msg

def get_language_instruction(language: str, custom_language: str = "") -> str:
    """Get language-specific instruction for the prompt."""
    if language == "English":
        return "All grammatical explanations, feedback, and answers to administrative questions MUST be in ENGLISH."
    elif language == "Cantonese":
        return "All grammatical explanations, feedback, and answers to administrative questions MUST be in CANTONESE (繁體中文 - 粵語)."
    elif language == "Mandarin":
        return "All grammatical explanations, feedback, and answers to administrative questions MUST be in MANDARIN (普通话 - 简体中文)."
    elif language == "custom" and custom_language:
        return f"All grammatical explanations, feedback, and answers to administrative questions MUST be in {custom_language.upper()}."
    else:
        return "All grammatical explanations, feedback, and answers to administrative questions MUST be in ENGLISH."

# ==========================================
# NOTION CONNECTION WITH CACHING
# ==========================================
@st.cache_data(ttl=3600)
def get_weekly_content() -> str:
    """Fetch active content from Notion database with caching."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "filter": {"property": "Activo", "checkbox": {"equals": True}}
    }

    response = make_request_with_retry("POST", url, headers, json_payload=payload)
    
    if not response:
        return "❌ Failed to connect to Notion after multiple attempts."
    
    if response.status_code != 200:
        return f"❌ Notion API Error ({response.status_code}): {response.text[:200]}"
    
    try:
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return "⚠️ No active units found in database."

        full_context = ""
        for page in results:
            props = page["properties"]
            
            def get_text(col_name: str) -> str:
                if col_name == "Nombre":
                    items = props.get("Nombre", {}).get("title", [])
                else:
                    items = props.get(col_name, {}).get("rich_text", [])
                return " ".join([item.get("text", {}).get("content", "") for item in items])

            name = get_text("Nombre")
            lexicon = get_text("Léxico")
            grammar = get_text("Gramática")
            communication = get_text("Comunicación")
            exercises = get_text("Ejercicios")

            full_context += f"""
=== UNIT: {name} ===
[VOCABULARY]: {lexicon}
[GRAMMAR]: {grammar}
[COMMUNICATION]: {communication}
[APPROVED EXERCISES]: {exercises}
==============================
"""
        return full_context
        
    except Exception as e:
        return f"❌ Error parsing Notion data: {str(e)}"

# ==========================================
# AI CONNECTION
# ==========================================
def get_ai_response(user_message: str, notion_context: str, language: str, custom_language: str = "") -> str:
    """Get AI response from HKU API with error handling."""
    
    language_instruction = get_language_instruction(language, custom_language)
    
    system_prompt = f"""
[ROLE AND PROFILE]
You are "ProfeBot", the official Spanish Tutor for SPAN1001 at the University of Hong Kong (HKU).
Your students are adults, intelligent, and multilingual (English, Mandarin, Cantonese).
Your tone is: Academic yet approachable, encouraging, patient, and clear.

[STRICT LANGUAGE PROTOCOL]
1. **EXPLANATIONS IN STUDENT'S PREFERRED LANGUAGE**: {language_instruction}
   - If a student writes in Chinese (Traditional/Simplified), understand it but respond/explain in their PREFERRED LANGUAGE.
2. **EXAMPLES IN SPANISH**: When providing examples of usage, vocabulary lists, or correct phrasing, use SPANISH.

[CONTENT SACRED RULES]
1. THE "ACTIVE CONTENT" IS YOUR BIBLE:
   - You are STRICTLY FORBIDDEN from using vocabulary, verb tenses, or grammar rules that do not appear in the "ACTIVE CONTENT" list below.
   - If the student asks about something advanced (e.g., "fui" - past tense), congratulate their curiosity but explain IN THEIR PREFERRED LANGUAGE that it belongs to future levels and rephrase using ONLY what they know now.

[TASK GENERATION SYSTEM]
When the user requests a TASK (CMD_TASKS), follow this protocol:
1. **First, ASK the student** which type of task they want:
   - **Reading Task**: Create a 200-word text using ONLY vocabulary and grammar from the selected unit. Then provide 8 multiple choice comprehension questions.
   - **Conversation Task**: Generate simple conversation questions strictly controlled by the unit's grammar and vocabulary.
   - **Grammar & Vocabulary Task**: Design an exercise based on the [APPROVED EXERCISES] in the database for that unit.
2. **Ask which unit** they want to practice.
3. **Wait for their response** before creating the task.

[QUIZ GENERATION LOGIC]
When the user requests a QUIZ (CMD_QUIZ):
1. **First, ASK the student** what topic or vocabulary they want to practice.
2. **IMPORTANT**: When you provide quiz questions, do NOT include the answers.
3. Wait for the student to submit their answers.
4. Only AFTER they respond, provide detailed feedback on each answer.

[EXERCISE GENERATION LOGIC]
- When the user asks for an exercise or practice:
  1. **PRIORITY 1**: Check the `[APPROVED EXERCISES]` section in the content below. If there are exercises there, USE THEM.
  2. **PRIORITY 2**: If NO exercises are listed there (or they are exhausted), generate a meaningful "Fill-in-the-blanks" or "Multiple Choice" exercise based STRICTLY on the vocabulary list.
  3. **QUALITY CONTROL**: AVOID trivial questions (e.g., "Is 'Hola' written with H?"). Create communicative context (e.g., "Complete the dialogue between A and B").

[EXPLAIN MORE COMMAND]
When the user requests CMD_EXPLAIN_MORE:
- Elaborate on the topic you were just discussing.
- Go slightly deeper, provide additional context, examples, or nuances.
- Keep explanations appropriate to the student's level (beginner).
- Do not introduce advanced grammar or vocabulary outside the active content.

[DYNAMIC FOLLOW-UP SYSTEM]
Do not just say goodbye. Your goal is to keep the conversation going.
At the very end of your response, you MUST generate exactly 3 suggested follow-up questions for the student.
- These questions must be relevant to what you just explained and intersect with the course topics.
- Format them EXACTLY like this (starting with ///):
  /// Tell me more about [Related Topic]
  /// Give me a quiz about [Current Topic]
  /// How do I use [Word] in a sentence?

--- ACTIVE CONTENT ---
{notion_context}
"""

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": HKU_API_KEY
    }
    
    payload = {
        "model": DEPLOYMENT_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 1000,
        "temperature": 0.4
    }

    response = make_request_with_retry(
        "POST", 
        HKU_ENDPOINT, 
        headers, 
        json_payload=payload,
        params={"deployment-id": DEPLOYMENT_ID}
    )
    
    if not response:
        return "❌ Failed to connect to AI service. Please try again later."
    
    if response.status_code == 200:
        try:
            return response.json()['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            return f"❌ Unexpected API response format: {str(e)}"
    else:
        return f"❌ HKU API Error ({response.status_code}): {response.text[:200]}"

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
def initialize_session_state():
    """Initialize all session state variables."""
    if "contexto" not in st.session_state:
        st.session_state.contexto = None
        st.session_state.context_loaded = False
        st.session_state.last_sync = None
    
    # Thread management
    if "threads" not in st.session_state:
        st.session_state.threads = {}
        st.session_state.current_thread_id = "default"
        st.session_state.thread_counter = 0
        
        st.session_state.threads["default"] = {
            "title": "New Conversation",
            "messages": [{
                "role": "assistant", 
                "content": "¡Hola! 👋 I am **ProfeBot**, your SPAN1001 tutor. Ask me about Spanish grammar, vocabulary, or the course!"
            }],
            "created_at": datetime.now(),
            "suggestions": []
        }
    
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    
    if "preferred_language" not in st.session_state:
        st.session_state.preferred_language = "English"
    
    if "custom_language" not in st.session_state:
        st.session_state.custom_language = ""
    
    if "selected_message_index" not in st.session_state:
        st.session_state.selected_message_index = None
    
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

initialize_session_state()

# Apply custom CSS based on dark mode
st.markdown(get_custom_css(st.session_state.dark_mode), unsafe_allow_html=True)

# ==========================================
# THREAD MANAGEMENT FUNCTIONS
# ==========================================
def create_new_thread():
    """Create a new conversation thread."""
    st.session_state.thread_counter += 1
    new_thread_id = f"thread_{st.session_state.thread_counter}"
    
    st.session_state.threads[new_thread_id] = {
        "title": f"New Conversation {st.session_state.thread_counter}",
        "messages": [{
            "role": "assistant", 
            "content": "¡Hola! 👋 I am **ProfeBot**. What would you like to learn today?"
        }],
        "created_at": datetime.now(),
        "suggestions": []
    }
    
    st.session_state.current_thread_id = new_thread_id

def switch_thread(thread_id: str):
    """Switch to a different conversation thread."""
    st.session_state.current_thread_id = thread_id
    st.session_state.selected_message_index = None

def delete_thread(thread_id: str):
    """Delete a conversation thread."""
    if thread_id in st.session_state.threads and len(st.session_state.threads) > 1:
        del st.session_state.threads[thread_id]
        if st.session_state.current_thread_id == thread_id:
            st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]

def get_current_thread():
    """Get the current active thread."""
    return st.session_state.threads[st.session_state.current_thread_id]

def update_thread_title(thread_id: str, first_user_message: str):
    """Update thread title based on first user message."""
    if st.session_state.threads[thread_id]["title"].startswith("New Conversation"):
        st.session_state.threads[thread_id]["title"] = generate_thread_title(first_user_message)

def get_user_messages_with_time():
    """Get all user messages from current thread with timestamps."""
    from datetime import timedelta
    current_thread = get_current_thread()
    user_messages = []
    
    for idx, msg in enumerate(current_thread["messages"]):
        if msg["role"] == "user":
            # Estimate time based on message order
            time_estimate = current_thread["created_at"] + timedelta(seconds=idx * 30)
            user_messages.append({
                "index": idx,
                "content": msg["content"],
                "time": time_estimate
            })
    
    return user_messages

# ==========================================
# LOAD NOTION CONTENT ON FIRST RUN
# ==========================================
if not st.session_state.context_loaded:
    with st.spinner('🔄 Syncing with course database...'):
        st.session_state.contexto = get_weekly_content()
        st.session_state.context_loaded = True
        st.session_state.last_sync = datetime.now()
        
        if "❌" not in st.session_state.contexto:
            st.success("✅ Course content loaded successfully!")
        else:
            st.error("⚠️ Error loading course content. Some features may be limited.")

# ==========================================
# CORE PROCESSING FUNCTION
# ==========================================
def process_user_input(user_text: str):
    """Process user input and get AI response."""
    if not user_text or user_text.strip() == "":
        return
    
    if not st.session_state.contexto:
        st.error("⚠️ Course content not loaded. Please refresh the page.")
        return
    
    current_thread = get_current_thread()
    
    # Update thread title if this is first user message
    user_message_count = sum(1 for m in current_thread["messages"] if m["role"] == "user")
    if user_message_count == 0:
        update_thread_title(st.session_state.current_thread_id, user_text)
    
    # Add user message
    current_thread["messages"].append({"role": "user", "content": user_text})
    st.session_state.message_count += 1
    
    # Get AI response
    with st.spinner("🤔 Thinking..."):
        raw_response = get_ai_response(
            user_text, 
            st.session_state.contexto,
            st.session_state.preferred_language,
            st.session_state.custom_language
        )
        
        # Extract suggestions
        suggestions = re.findall(r'///\s*(.*)', raw_response)
        suggestions = [s.strip() for s in suggestions if s.strip()][:3]
        current_thread["suggestions"] = suggestions
        
        # Clean response
        clean_response = re.sub(r'///.*', '', raw_response).strip()
    
    # Add AI message
    current_thread["messages"].append({"role": "assistant", "content": clean_response})
    st.session_state.message_count += 1

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown('<p class="sidebar-title">🎓 <span class="sidebar-title-text">ProfeBot Control</span></p>', unsafe_allow_html=True)
    
    # Thread History
    st.subheader("💬 Conversations")
    
    for thread_id, thread_data in sorted(
        st.session_state.threads.items(), 
        key=lambda x: x[1]["created_at"], 
        reverse=True
    ):
        is_active = thread_id == st.session_state.current_thread_id
        
        col_btn, col_del = st.columns([4, 1])
        
        with col_btn:
            if st.button(
                f"{'📌 ' if is_active else '💭 '}{thread_data['title'][:20]}",
                key=f"thread_btn_{thread_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                if thread_id != st.session_state.current_thread_id:
                    switch_thread(thread_id)
                    st.rerun()
        
        with col_del:
            if len(st.session_state.threads) > 1:
                if st.button("🗑️", key=f"del_{thread_id}", help="Delete"):
                    delete_thread(thread_id)
                    st.rerun()
    
    st.caption(f"{len(st.session_state.threads)} conversation(s)")
    
    st.divider()
    
    # Actions
    st.subheader("🔧 Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            with st.spinner("Refreshing..."):
                get_weekly_content.clear()
                st.session_state.contexto = get_weekly_content()
                st.session_state.last_sync = datetime.now()
                st.rerun()
    
    with col2:
        if st.button("➕ New", use_container_width=True):
            create_new_thread()
            st.rerun()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        current_thread = get_current_thread()
        current_thread["messages"] = [{
            "role": "assistant", 
            "content": "¡Hola! 👋 Chat cleared!"
        }]
        current_thread["suggestions"] = []
        st.session_state.selected_message_index = None
        st.rerun()
    
    st.divider()
    
    # SETTINGS (includes status, language, night mode)
    with st.expander("⚙️ Settings", expanded=False):
        # Status indicators
        st.markdown("**📊 Status**")
        if st.session_state.context_loaded:
            if "❌" not in st.session_state.contexto:
                st.markdown('<div class="status-badge status-success">✓ Connected</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-badge status-error">✗ Error</div>', unsafe_allow_html=True)
        
        if st.session_state.last_sync:
            st.caption(f"Last sync: {st.session_state.last_sync.strftime('%H:%M:%S')}")
        
        st.caption(f"Total messages: {st.session_state.message_count}")
        
        st.divider()
        
        # Language
        st.markdown("**🌐 Language**")
        
        selected_lang = st.selectbox(
            "Explanation Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            index=0,
            key="lang_selector",
            label_visibility="collapsed"
        )
        
        st.session_state.preferred_language = LANGUAGE_OPTIONS[selected_lang]
        
        if st.session_state.preferred_language == "custom":
            custom_lang_input = st.text_input(
                "Your language:",
                value=st.session_state.custom_language,
                placeholder="Français, Deutsch, 日本語",
                key="custom_lang_input"
            )
            st.session_state.custom_language = custom_lang_input
        
        st.divider()
        
        # Night Mode Toggle
        st.markdown("**🌙 Appearance**")
        dark_mode_label = "Switch to Day Mode" if st.session_state.dark_mode else "Switch to Night Mode"
        if st.button(dark_mode_label, use_container_width=True, key="dark_mode_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
        
        st.divider()
        st.caption(f"Model: {DEPLOYMENT_ID}")
        st.caption(f"Temp: 0.4 | Tokens: 1000")
    
    # About
    with st.expander("ℹ️ About"):
        st.markdown("""
        **ProfeBot** - AI Spanish Tutor
        
        **Features:**
        - 📚 Context-aware
        - 🎯 Personalized exercises
        - 💬 Interactive
        - 🌐 Multilingual
        
        ---
        Made with ❤️ for SPAN1001
        Powered by DeepSeek-V3
        """)
    
    # Department Link
    st.markdown("""
    <div class="dept-link">
        <a href="https://spanish.hku.hk/" target="_blank">🏛️ HKU Spanish Department</a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FLOATING MESSAGE HISTORY PANEL
# ==========================================
user_messages = get_user_messages_with_time()

# Build history HTML with proper escaping
history_items_html = []
if user_messages:
    for msg_data in user_messages:  # Oldest first, newest at bottom
        # Escape HTML characters in message content
        msg_content = msg_data["content"][:80]
        msg_content = msg_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")
        msg_preview = msg_content + "..." if len(msg_data["content"]) > 80 else msg_content
        time_str = msg_data["time"].strftime("%H:%M")
        idx = msg_data["index"]
        
        history_items_html.append(f'''<div class="history-item" data-idx="{idx}"><div class="history-item-time">🕐 {time_str}</div><div class="history-item-text">{msg_preview}</div></div>''')

history_content = "".join(history_items_html) if history_items_html else '<div class="empty-history">No messages yet.<br>Start chatting!</div>'

# Get dark mode state for styling
is_dark = st.session_state.get('dark_mode', False)
panel_bg = "rgba(22, 27, 34, 0.92)" if is_dark else "rgba(255, 255, 255, 0.92)"
history_text_color = "#f0f6fc" if is_dark else "#24292f"
history_text_secondary = "#8b949e" if is_dark else "#57606a"
history_border_color = "#30363d" if is_dark else "#d0d7de"
history_item_bg = "rgba(33, 38, 45, 0.9)" if is_dark else "rgba(246, 248, 250, 0.9)"
history_item_hover = "rgba(48, 54, 61, 0.95)" if is_dark else "rgba(234, 238, 242, 0.95)"
history_accent_color = "#58a6ff" if is_dark else "#2da44e"

# HTML for the panel (will be rendered with st.markdown)
history_panel_html = f'''
<div class="message-history-panel" style="
    position: fixed;
    right: 20px;
    top: 80px;
    width: 280px;
    max-height: calc(100vh - 120px);
    min-height: 80px;
    background: {panel_bg};
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid {history_border_color};
    border-radius: 16px;
    padding: 15px;
    overflow-y: auto;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    z-index: 999;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
">
    <div style="font-size: 1rem; font-weight: 600; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid {history_accent_color}; color: {history_text_color};">
        📝 Your Messages <span style="font-size: 0.75rem; color: {history_text_secondary}; font-weight: normal;">({len(user_messages)})</span>
    </div>
    {history_content}
</div>
<style>
    .message-history-panel .history-item {{
        padding: 12px;
        margin: 8px 0;
        background: {history_item_bg};
        border-left: 3px solid {history_accent_color};
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.85rem;
    }}
    .message-history-panel .history-item:hover {{
        background: {history_item_hover};
        transform: translateX(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}
    .message-history-panel .history-item-time {{
        font-size: 0.7rem;
        color: {history_text_secondary};
        margin-bottom: 4px;
    }}
    .message-history-panel .history-item-text {{
        color: {history_text_color};
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .message-history-panel .empty-history {{
        text-align: center;
        color: {history_text_secondary};
        font-size: 0.85rem;
        padding: 20px;
        font-style: italic;
    }}
</style>
'''

# ==========================================
# MAIN CHAT INTERFACE
# ==========================================
# Get current thread
current_thread = get_current_thread()

# Display chat history with IDs for navigation
for idx, message in enumerate(current_thread["messages"]):
    tipo = "user" if message["role"] == "user" else "assistant"
    
    # Add anchor ID for user messages with scroll margin
    if tipo == "user":
        st.markdown(f'<div id="msg_{idx}" style="scroll-margin-top: 100px;"></div>', unsafe_allow_html=True)
    
    with st.chat_message(tipo):
        clean_text = re.sub(r'///.*', '', message["content"]).strip()
        st.markdown(clean_text)

# Dynamic suggestion buttons
if current_thread["suggestions"] and len(current_thread["messages"]) > 1:
    st.divider()
    st.caption("💡 **Suggested follow-ups:**")
    cols = st.columns(len(current_thread["suggestions"]))
    for i, suggestion in enumerate(current_thread["suggestions"]):
        if i < 3:
            with cols[i]:
                if st.button(
                    suggestion, 
                    key=f"sugg_{st.session_state.current_thread_id}_{st.session_state.message_count}_{i}",
                    use_container_width=True
                ):
                    process_user_input(suggestion)
                    st.rerun()

# Quick action buttons
st.divider()
st.caption("⚡ **Quick Actions:**")

c0, c1, c2, c3, c4 = st.columns(5)

with c0:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("📋 Tasks!", use_container_width=True, key="qa_tasks"): 
        process_user_input("""CMD_TASKS: I want to do a practice task. Please respond in my preferred language (as set in my language preferences) and ask me which type of task I'd like to do:

1. **Reading Task** - A 250-word text with paragraph structure, using simple connectors, with 8 multiple choice comprehension questions
2. **Conversation Task** - Simple conversation questions to practice speaking. Instructions should be in my preferred language.
3. **Grammar & Vocabulary Task** - Exercises based on the activity bank. Instructions should be in my preferred language.

Also ask me which unit I want to practice. Wait for my response before creating the task.""")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c1:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("📝 Quiz", use_container_width=True, key="qa_quiz"): 
        process_user_input("""CMD_QUIZ: I want to take a quiz. Please ask me what topic or vocabulary I want to practice from the active units. 

IMPORTANT: When you give me the quiz questions, do NOT provide the answers. Wait for me to respond with my answers first, then give me feedback on each one.""")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("➕ Examples", use_container_width=True, key="qa_examples"): 
        process_user_input("CMD_EXAMPLES: Give me 3 examples using active vocabulary.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("🧐 Explain more", use_container_width=True, key="qa_explain"): 
        process_user_input("CMD_EXPLAIN_MORE: Please elaborate a bit more on what we were just discussing. Go slightly deeper into the topic, provide additional context or examples, but keep it at my level.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("💬 Roleplay", use_container_width=True, key="qa_roleplay"): 
        process_user_input("CMD_ROLEPLAY: Let's start a short conversation.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Type your question here... (any language)", key="main_chat_input"):
    process_user_input(prompt)
    st.rerun()

# Inject floating message history panel
st.markdown(history_panel_html, unsafe_allow_html=True)

# Inject JavaScript for click handlers using components.html
scroll_js = f'''
<script>
(function() {{
    function setupHistoryClickHandlers() {{
        var items = window.parent.document.querySelectorAll('.message-history-panel .history-item');
        items.forEach(function(item) {{
            if (!item.hasAttribute('data-click-setup')) {{
                item.setAttribute('data-click-setup', 'true');
                item.addEventListener('click', function() {{
                    var idx = this.getAttribute('data-idx');
                    var targetId = 'msg_' + idx;
                    var target = window.parent.document.getElementById(targetId);
                    if (target) {{
                        target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        target.style.transition = 'background-color 0.3s';
                        target.style.backgroundColor = 'rgba(88, 166, 255, 0.4)';
                        target.style.borderRadius = '8px';
                        target.style.padding = '10px';
                        setTimeout(function() {{
                            target.style.backgroundColor = 'transparent';
                        }}, 2000);
                    }}
                }});
            }}
        }});
    }}
    // Run multiple times to ensure it catches the elements
    setTimeout(setupHistoryClickHandlers, 100);
    setTimeout(setupHistoryClickHandlers, 500);
    setTimeout(setupHistoryClickHandlers, 1000);
}})();
</script>
'''
components.html(scroll_js, height=0, scrolling=False)
