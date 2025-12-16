import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import time
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from PIL import Image
from pathlib import Path
from collections import Counter

# ==========================================
# LOGGING CONFIGURATION
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
# Paths
BASE_DIR = Path(__file__).parent
STYLES_DIR = BASE_DIR / "styles"
DATA_DIR = BASE_DIR / "data"
THREADS_FILE = DATA_DIR / "threads.json"
ANALYTICS_FILE = DATA_DIR / "analytics.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

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

# ==========================================
# CSS LOADING FROM FILES
# ==========================================
def load_css_from_file(dark_mode: bool = False) -> str:
    """Load CSS from external file based on theme."""
    css_file = STYLES_DIR / ("dark.css" if dark_mode else "light.css")
    try:
        with open(css_file, "r", encoding="utf-8") as f:
            css_content = f.read()
            logger.info(f"Loaded CSS from {css_file}")
            return f"<style>{css_content}</style>"
    except FileNotFoundError:
        logger.warning(f"CSS file not found: {css_file}, using fallback")
        return get_fallback_css(dark_mode)

def get_fallback_css(dark_mode: bool = False) -> str:
    """Minimal fallback CSS if files not found."""
    bg = "#0d1117" if dark_mode else "#ffffff"
    text = "#f0f6fc" if dark_mode else "#24292f"
    return f"""
    <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
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
            logger.warning("No active units found in Notion database")
            return "⚠️ No active units found in database."

        full_context = ""
        for page in results:
            props = page.get("properties", {})
            
            def get_text_safe(col_name: str) -> str:
                """Safely extract text from Notion properties with validation."""
                try:
                    if col_name == "Nombre":
                        prop_data = props.get("Nombre", {})
                        items = prop_data.get("title", []) if prop_data else []
                    else:
                        prop_data = props.get(col_name, {})
                        items = prop_data.get("rich_text", []) if prop_data else []
                    
                    if not items:
                        logger.debug(f"No content found for column: {col_name}")
                        return ""
                    
                    texts = []
                    for item in items:
                        if isinstance(item, dict):
                            text_content = item.get("text", {})
                            if isinstance(text_content, dict):
                                content = text_content.get("content", "")
                                if content:
                                    texts.append(content)
                    return " ".join(texts)
                except Exception as e:
                    logger.error(f"Error extracting text from {col_name}: {e}")
                    return ""

            name = get_text_safe("Nombre")
            lexicon = get_text_safe("Léxico")
            grammar = get_text_safe("Gramática")
            communication = get_text_safe("Comunicación")
            exercises = get_text_safe("Ejercicios")

            if name:  # Only add unit if it has a name
                full_context += f"""
=== UNIT: {name} ===
[VOCABULARY]: {lexicon or 'No vocabulary listed'}
[GRAMMAR]: {grammar or 'No grammar listed'}
[COMMUNICATION]: {communication or 'No communication topics listed'}
[APPROVED EXERCISES]: {exercises or 'No exercises listed'}
==============================
"""
                logger.info(f"Loaded unit: {name}")
        
        if not full_context:
            return "⚠️ No valid units found in database."
            
        return full_context
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return f"❌ Error parsing Notion response: Invalid JSON"
    except Exception as e:
        logger.error(f"Error parsing Notion data: {e}")
        return f"❌ Error parsing Notion data: {str(e)}"

# ==========================================
# AI CONNECTION
# ==========================================
def get_ai_response(user_message: str, notion_context: str, language: str, custom_language: str = "", conversation_history: List[Dict] = None) -> str:
    """Get AI response from HKU API with error handling and conversation history.
    
    Args:
        user_message: The current user message
        notion_context: The course content from Notion
        language: Preferred language for explanations
        custom_language: Custom language if 'Other' selected
        conversation_history: List of previous messages in the conversation
    """
    
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
    
    # Build messages array with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (limit to last 10 messages to manage context window)
    if conversation_history:
        # Filter out the suggestions from messages for cleaner context
        for msg in conversation_history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Clean out the /// suggestions from assistant messages
            if role == "assistant":
                import re
                content = re.sub(r'///.*', '', content).strip()
            if content:
                messages.append({"role": role, "content": content})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    logger.info(f"Sending {len(messages)} messages to AI (including system prompt)")
    
    payload = {
        "model": DEPLOYMENT_ID,
        "messages": messages,
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

# ==========================================
# PERSISTENCE FUNCTIONS
# ==========================================
def save_threads_to_file():
    """Save all threads to a local JSON file."""
    try:
        threads_data = {}
        for thread_id, thread in st.session_state.threads.items():
            threads_data[thread_id] = {
                "title": thread["title"],
                "messages": thread["messages"],
                "created_at": thread["created_at"].isoformat(),
                "suggestions": thread.get("suggestions", [])
            }
        
        with open(THREADS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "threads": threads_data,
                "current_thread_id": st.session_state.current_thread_id,
                "thread_counter": st.session_state.thread_counter,
                "message_count": st.session_state.message_count,
                "dark_mode": st.session_state.dark_mode,
                "preferred_language": st.session_state.preferred_language,
                "custom_language": st.session_state.custom_language
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(threads_data)} threads to {THREADS_FILE}")
    except Exception as e:
        logger.error(f"Error saving threads: {e}")

def load_threads_from_file():
    """Load threads from local JSON file."""
    try:
        if THREADS_FILE.exists():
            with open(THREADS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Restore threads
            threads = {}
            for thread_id, thread_data in data.get("threads", {}).items():
                threads[thread_id] = {
                    "title": thread_data["title"],
                    "messages": thread_data["messages"],
                    "created_at": datetime.fromisoformat(thread_data["created_at"]),
                    "suggestions": thread_data.get("suggestions", [])
                }
            
            if threads:
                st.session_state.threads = threads
                st.session_state.current_thread_id = data.get("current_thread_id", list(threads.keys())[0])
                st.session_state.thread_counter = data.get("thread_counter", len(threads))
                st.session_state.message_count = data.get("message_count", 0)
                st.session_state.dark_mode = data.get("dark_mode", False)
                st.session_state.preferred_language = data.get("preferred_language", "English")
                st.session_state.custom_language = data.get("custom_language", "")
                logger.info(f"Loaded {len(threads)} threads from {THREADS_FILE}")
                return True
    except Exception as e:
        logger.error(f"Error loading threads: {e}")
    return False

initialize_session_state()

# Try to load saved threads
if "threads_loaded" not in st.session_state:
    load_threads_from_file()
    st.session_state.threads_loaded = True

# Apply custom CSS - try external files first, fallback to inline
try:
    st.markdown(load_css_from_file(st.session_state.dark_mode), unsafe_allow_html=True)
except:
    st.markdown(get_fallback_css(st.session_state.dark_mode), unsafe_allow_html=True)

# ==========================================
# EXPORT FUNCTIONS
# ==========================================
def export_conversation_txt(messages: list) -> str:
    """Export conversation to TXT format."""
    current_thread = get_current_thread()
    lines = []
    lines.append(f"ProfeBot Conversation Export")
    lines.append(f"Title: {current_thread['title']}")
    lines.append(f"Date: {current_thread['created_at'].strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Language: {st.session_state.preferred_language}")
    lines.append("=" * 50)
    lines.append("")
    
    for msg in messages:
        role = "🧑 Student" if msg["role"] == "user" else "🤖 ProfeBot"
        # Clean out suggestion markers
        content = re.sub(r'///.*', '', msg["content"]).strip()
        lines.append(f"{role}:")
        lines.append(content)
        lines.append("")
    
    lines.append("=" * 50)
    lines.append(f"Exported from ProfeBot - SPAN1001 Tutor")
    lines.append(f"Total messages: {len(messages)}")
    
    return "\n".join(lines)

def export_conversation_md(messages: list) -> str:
    """Export conversation to Markdown format."""
    current_thread = get_current_thread()
    lines = []
    lines.append(f"# ProfeBot Conversation")
    lines.append(f"**Title:** {current_thread['title']}")
    lines.append(f"**Date:** {current_thread['created_at'].strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Language:** {st.session_state.preferred_language}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for msg in messages:
        if msg["role"] == "user":
            lines.append(f"### 🧑 Student")
        else:
            lines.append(f"### 🤖 ProfeBot")
        # Clean out suggestion markers
        content = re.sub(r'///.*', '', msg["content"]).strip()
        lines.append(content)
        lines.append("")
    
    lines.append("---")
    lines.append(f"*Exported from ProfeBot - SPAN1001 Tutor | {len(messages)} messages*")
    
    return "\n".join(lines)

# ==========================================
# ANALYTICS FUNCTIONS
# ==========================================
def load_analytics() -> Dict:
    """Load analytics data from file."""
    try:
        if ANALYTICS_FILE.exists():
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading analytics: {e}")
    return {
        "total_messages": 0,
        "total_sessions": 0,
        "questions_by_topic": {},
        "questions_by_unit": {},
        "daily_usage": {},
        "response_times": [],
        "popular_quick_actions": {}
    }

def save_analytics(analytics: Dict):
    """Save analytics data to file."""
    try:
        with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        logger.info("Analytics saved")
    except Exception as e:
        logger.error(f"Error saving analytics: {e}")

def track_message(user_message: str, response_time: float = 0):
    """Track a user message for analytics."""
    analytics = load_analytics()
    
    # Update total messages
    analytics["total_messages"] = analytics.get("total_messages", 0) + 1
    
    # Track daily usage
    today = datetime.now().strftime("%Y-%m-%d")
    if "daily_usage" not in analytics:
        analytics["daily_usage"] = {}
    analytics["daily_usage"][today] = analytics["daily_usage"].get(today, 0) + 1
    
    # Track response time (keep last 100)
    if response_time > 0:
        if "response_times" not in analytics:
            analytics["response_times"] = []
        analytics["response_times"].append(response_time)
        analytics["response_times"] = analytics["response_times"][-100:]
    
    # Detect topic keywords
    topics = {
        "grammar": ["gramática", "grammar", "verb", "conjugat", "tense"],
        "vocabulary": ["vocabulario", "vocabulary", "word", "palabra", "meaning"],
        "pronunciation": ["pronuncia", "sound", "accent"],
        "culture": ["cultura", "culture", "spain", "españa", "mexico"],
        "exercises": ["ejercicio", "exercise", "practice", "quiz", "task"]
    }
    
    message_lower = user_message.lower()
    for topic, keywords in topics.items():
        if any(kw in message_lower for kw in keywords):
            if "questions_by_topic" not in analytics:
                analytics["questions_by_topic"] = {}
            analytics["questions_by_topic"][topic] = analytics["questions_by_topic"].get(topic, 0) + 1
    
    # Detect unit references
    for i in range(1, 15):
        if f"unit {i}" in message_lower or f"unidad {i}" in message_lower:
            if "questions_by_unit" not in analytics:
                analytics["questions_by_unit"] = {}
            unit_key = f"Unit {i}"
            analytics["questions_by_unit"][unit_key] = analytics["questions_by_unit"].get(unit_key, 0) + 1
    
    save_analytics(analytics)

def track_quick_action(action_name: str):
    """Track quick action button usage."""
    analytics = load_analytics()
    if "popular_quick_actions" not in analytics:
        analytics["popular_quick_actions"] = {}
    analytics["popular_quick_actions"][action_name] = analytics["popular_quick_actions"].get(action_name, 0) + 1
    save_analytics(analytics)

def get_analytics_summary() -> Dict:
    """Get a summary of analytics for display."""
    analytics = load_analytics()
    
    # Calculate average response time
    response_times = analytics.get("response_times", [])
    avg_response = sum(response_times) / len(response_times) if response_times else 0
    
    # Get top topics
    topics = analytics.get("questions_by_topic", {})
    top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Get usage last 7 days
    daily = analytics.get("daily_usage", {})
    today = datetime.now()
    last_7_days = 0
    for i in range(7):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        last_7_days += daily.get(day, 0)
    
    return {
        "total_messages": analytics.get("total_messages", 0),
        "total_sessions": analytics.get("total_sessions", 1),
        "avg_response_time": round(avg_response, 2),
        "top_topics": top_topics,
        "messages_last_7_days": last_7_days,
        "popular_actions": sorted(
            analytics.get("popular_quick_actions", {}).items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
    }

# Track session on first load (after analytics functions are defined)
if "session_tracked" not in st.session_state:
    st.session_state.session_tracked = True
    _analytics = load_analytics()
    _analytics["total_sessions"] = _analytics.get("total_sessions", 0) + 1
    save_analytics(_analytics)

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
    save_threads_to_file()  # Persist new thread

def switch_thread(thread_id: str):
    """Switch to a different conversation thread."""
    st.session_state.current_thread_id = thread_id
    st.session_state.selected_message_index = None
    save_threads_to_file()  # Persist current thread change

def delete_thread(thread_id: str):
    """Delete a conversation thread."""
    if thread_id in st.session_state.threads and len(st.session_state.threads) > 1:
        del st.session_state.threads[thread_id]
        if st.session_state.current_thread_id == thread_id:
            st.session_state.current_thread_id = list(st.session_state.threads.keys())[0]
        save_threads_to_file()  # Persist deletion

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
def process_user_input(user_text: str, quick_action: str = None):
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
    
    # Track quick action if provided
    if quick_action:
        track_quick_action(quick_action)
    
    # Get AI response with conversation history
    start_time = time.time()
    with st.spinner("🤔 Thinking..."):
        # Get messages before adding the current one (for history)
        history_messages = current_thread["messages"][:-1]  # Exclude the just-added user message
        
        raw_response = get_ai_response(
            user_text, 
            st.session_state.contexto,
            st.session_state.preferred_language,
            st.session_state.custom_language,
            conversation_history=history_messages
        )
        
        # Extract suggestions
        suggestions = re.findall(r'///\s*(.*)', raw_response)
        suggestions = [s.strip() for s in suggestions if s.strip()][:3]
        current_thread["suggestions"] = suggestions
        
        # Clean response
        clean_response = re.sub(r'///.*', '', raw_response).strip()
    
    response_time = time.time() - start_time
    
    # Add AI message
    current_thread["messages"].append({"role": "assistant", "content": clean_response})
    st.session_state.message_count += 1
    
    # Track analytics
    track_message(user_text, response_time)
    
    # Save threads after each interaction
    save_threads_to_file()

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
        save_threads_to_file()  # Persist cleared chat
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
            save_threads_to_file()  # Persist preference
            st.rerun()
        
        st.divider()
        st.caption(f"Model: {DEPLOYMENT_ID}")
        st.caption(f"Temp: 0.4 | Tokens: 1000")
    
    # Export Conversations
    with st.expander("📥 Export Chat", expanded=False):
        st.markdown("**Download conversation**")
        current_thread = get_current_thread()
        
        # Export as TXT
        txt_content = export_conversation_txt(current_thread["messages"])
        st.download_button(
            label="📄 Download TXT",
            data=txt_content,
            file_name=f"profebot_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        # Export as Markdown
        md_content = export_conversation_md(current_thread["messages"])
        st.download_button(
            label="📝 Download Markdown",
            data=md_content,
            file_name=f"profebot_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    # Analytics / Usage Stats
    with st.expander("📊 Usage Stats", expanded=False):
        analytics = get_analytics_summary()
        
        st.markdown("**📈 Your Statistics**")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("Messages", analytics["total_messages"])
        with col_stat2:
            st.metric("Sessions", analytics["total_sessions"])
        
        st.metric("Avg Response", f"{analytics['avg_response_time']:.1f}s")
        
        if analytics["top_topics"]:
            st.markdown("**🎯 Top Topics**")
            for topic, count in analytics["top_topics"][:5]:
                st.caption(f"• {topic}: {count}")
        
        if analytics["popular_actions"]:
            st.markdown("**⚡ Popular Actions**")
            for action, count in analytics["popular_actions"][:3]:
                st.caption(f"• {action}: {count}")
    
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

Also ask me which unit I want to practice. Wait for my response before creating the task.""", quick_action="Tasks")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c1:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("📝 Quiz", use_container_width=True, key="qa_quiz"): 
        process_user_input("""CMD_QUIZ: I want to take a quiz. Please ask me what topic or vocabulary I want to practice from the active units. 

IMPORTANT: When you give me the quiz questions, do NOT provide the answers. Wait for me to respond with my answers first, then give me feedback on each one.""", quick_action="Quiz")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("➕ Examples", use_container_width=True, key="qa_examples"): 
        process_user_input("CMD_EXAMPLES: Give me 3 examples using active vocabulary.", quick_action="Examples")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("🧐 Explain more", use_container_width=True, key="qa_explain"): 
        process_user_input("CMD_EXPLAIN_MORE: Please elaborate a bit more on what we were just discussing. Go slightly deeper into the topic, provide additional context or examples, but keep it at my level.", quick_action="Explain More")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="quick-action-btn">', unsafe_allow_html=True)
    if st.button("💬 Roleplay", use_container_width=True, key="qa_roleplay"): 
        process_user_input("CMD_ROLEPLAY: Let's start a short conversation.", quick_action="Roleplay")
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
