import os
import asyncio
from pathlib import Path
import streamlit as st
from edge_tts import Communicate
import hashlib
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pytz
import requests
import json


# --- Configuration ---
HINDI_VOICE_MALE = "hi-IN-MadhurNeural"
HINDI_VOICE_FEMALE = "hi-IN-SwaraNeural"
OUTPUT_DIR = "generated_audio"
LOG_SHEET_NAME = "logs"  

# English voices with different accents
ENGLISH_VOICES = {
    "American Male (Eric)": "en-US-EricNeural",
    "American Female (Jenny)": "en-US-JennyNeural",
    "Spanish Male (Alvaro)": "es-ES-AlvaroNeural",
    "Spanish Female (Elvira)": "es-ES-ElviraNeural",
    "Mexican Male (Jorge)": "es-MX-JorgeNeural",
    "Mexican Female (Dalia)": "es-MX-DaliaNeural"
}

def groq_chat_tab():
    st.header("AI Assistant")
    
    # Get API key from root level of secrets
    groq_api_key = "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"
    
    if not groq_api_key:
        st.warning("Please set GROQ_API_KEY in secrets or environment variables")
        return
    
    # Model selection
    model = st.selectbox(
        "Select Model",
        ["mixtral-8x7b-32768", "llama2-70b-4096"],
        index=0
    )
    
    # Chat interface
    if "groq_messages" not in st.session_state:
        st.session_state.groq_messages = []
    
    # Display chat messages
    for message in st.session_state.groq_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input for new messages
    if prompt := st.chat_input("Ask Groq AI anything..."):
        # Add user message to chat history
        st.session_state.groq_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": st.session_state.groq_messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        # Show loading spinner while waiting for response
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                
                # Get AI response
                ai_response = response.json()["choices"][0]["message"]["content"]
                
                # Add AI response to chat history
                st.session_state.groq_messages.append({"role": "assistant", "content": ai_response})
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
                    
            except Exception as e:
                st.error(f"Error calling Groq API: {str(e)}")

# --- Google Sheets Setup ---
def get_google_sheet():
    """Authenticate and return the Google Sheet"""
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["GCP_CREDS"], scope)
    client = gspread.authorize(creds)
    return client.open(LOG_SHEET_NAME).sheet1

def log_request(username, voice, input_text, output_filename):
    """Log request to Google Sheets"""
    sheet = get_google_sheet()

    # Get current time in IST
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_now = datetime.datetime.now(ist_timezone)
    
    response = sheet.append_row([
        ist_now.strftime("%Y-%m-%d %H:%M:%S"),  # IST-formatted time
        username,
        get_client_ip(),
        voice,
        input_text[:100],
        output_filename
    ])
    print(f"Response from Google Sheets: {response}")

    # Check if the append was actually successful
    if isinstance(response, dict) and response.get('updates', {}).get('updatedRows', 0) > 0:
        st.sidebar.success("Request logged successfully")
    else:
        st.sidebar.warning("Logged but may not have saved")

# --- IP Detection ---
def get_client_ip():
    """Get client IP address (works for Streamlit Sharing)"""
    try:
        ctx = st.runtime.get_instance().script_run_ctx
        if ctx is not None:
            return ctx.remote_ip
    except:
        return "unknown"

# --- TTS Functions ---
async def generate_audio(text, voice, output_filename, rate=0, pitch=0):
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    final_output_path = Path(OUTPUT_DIR) / output_filename
    
    # try:
    # Convert integer inputs to percentage/Hz values
    rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
    pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
    
    communicate = Communicate(text=text, voice=voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(str(final_output_path))
    return final_output_path
    # except Exception as e:
    #     st.error(f"Error during audio generation: {e}")
    #     return None

def main_app():
    tab1, tab2 = st.tabs(["Text-to-Speech", "AI Chat"])
    
    with tab1:
        st.title("Multilingual Text-to-Speech Generator")
        st.markdown("Convert text to natural sounding speech in multiple languages")

    
        HINDI_VOICES = {
            "Female (Swara)": HINDI_VOICE_FEMALE,
            "Male (Madhur)": HINDI_VOICE_MALE
        }
    
        # Combine all voice options
        ALL_VOICES = {
            **HINDI_VOICES,
            **ENGLISH_VOICES
        }
    
        # Single form definition
        with st.form("tts_form"):
            text = st.text_area("Enter Text", height=200, 
                              value=''' Hello! This is a sample text for testing the TTS functionality.
                              You can enter any text here to generate audio.''')
            
            # Voice selection
            voice_name = st.selectbox("Select Voice", list(ALL_VOICES.keys()))
            voice = ALL_VOICES[voice_name]  # Gets the actual voice ID
            
            col1, col2 = st.columns(2)
            with col1:
                rate = st.number_input("Speed Adjustment (-100 to 100)", 
                                      min_value=-100, max_value=100, value=0, step=1,
                                      help="Positive values increase speed, negative values decrease")
            with col2:
                pitch = st.number_input("Pitch Adjustment (-100 to 100)", 
                                       min_value=-100, max_value=100, value=0, step=1,
                                       help="Positive values increase pitch, negative values decrease")
            
            filename = st.text_input("Output filename (without extension)", "output")
            
            submitted = st.form_submit_button("Generate Audio")
    
        if submitted:
            if not text.strip():
                st.warning("Please enter some text")
                return
                
            with st.spinner("Generating audio..."):
                output_path = asyncio.run(
                    generate_audio(
                        text=text,
                        voice=voice,
                        output_filename=f"{filename}.mp3",
                        rate=rate,
                        pitch=pitch
                    )
                )          
    
            if output_path and output_path.exists():
                log_request(
                    st.session_state.current_user,
                    voice_name,  # Log the display name rather than the voice ID
                    text,
                    f"{filename}.mp3"
                )
                st.success("Audio generated successfully and logged!")
                
                # Display audio player
                audio_file = open(output_path, 'rb')
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/mp3')
                
                # Download button
                st.download_button(
                    label="Download MP3",
                    data=audio_bytes,
                    file_name=f"{filename}.mp3",
                    mime="audio/mp3"
                )
        

    with tab2:
        groq_chat_tab()

# # --- Main App ---
# def main_app():
#     st.title("Multilingual Text-to-Speech Generator")
#     st.markdown("Convert text to natural sounding speech in multiple languages")
    
#     HINDI_VOICES = {
#         "Female (Swara)": HINDI_VOICE_FEMALE,
#         "Male (Madhur)": HINDI_VOICE_MALE
#     }

#     # Combine all voice options
#     ALL_VOICES = {
#         **HINDI_VOICES,
#         **ENGLISH_VOICES
#     }

#     # Single form definition
#     with st.form("tts_form"):
#         text = st.text_area("Enter Text", height=200, 
#                           value=''' Hello! This is a sample text for testing the TTS functionality.
#                           You can enter any text here to generate audio.''')
        
#         # Voice selection
#         voice_name = st.selectbox("Select Voice", list(ALL_VOICES.keys()))
#         voice = ALL_VOICES[voice_name]  # Gets the actual voice ID
        
#         col1, col2 = st.columns(2)
#         with col1:
#             rate = st.number_input("Speed Adjustment (-100 to 100)", 
#                                   min_value=-100, max_value=100, value=0, step=1,
#                                   help="Positive values increase speed, negative values decrease")
#         with col2:
#             pitch = st.number_input("Pitch Adjustment (-100 to 100)", 
#                                    min_value=-100, max_value=100, value=0, step=1,
#                                    help="Positive values increase pitch, negative values decrease")
        
#         filename = st.text_input("Output filename (without extension)", "output")
        
#         submitted = st.form_submit_button("Generate Audio")

#     if submitted:
#         if not text.strip():
#             st.warning("Please enter some text")
#             return
            
#         with st.spinner("Generating audio..."):
#             output_path = asyncio.run(
#                 generate_audio(
#                     text=text,
#                     voice=voice,
#                     output_filename=f"{filename}.mp3",
#                     rate=rate,
#                     pitch=pitch
#                 )
#             )          

#         if output_path and output_path.exists():
#             log_request(
#                 st.session_state.current_user,
#                 voice_name,  # Log the display name rather than the voice ID
#                 text,
#                 f"{filename}.mp3"
#             )
#             st.success("Audio generated successfully and logged!")
            
#             # Display audio player
#             audio_file = open(output_path, 'rb')
#             audio_bytes = audio_file.read()
#             st.audio(audio_bytes, format='audio/mp3')
            
#             # Download button
#             st.download_button(
#                 label="Download MP3",
#                 data=audio_bytes,
#                 file_name=f"{filename}.mp3",
#                 mime="audio/mp3"
#             )

# --- Authentication ---
USERS = {
    "kamesh": {
        "password_hash": hashlib.sha256("nirvaan".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "ram": {
        "password_hash": hashlib.sha256("ram123".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "admin": {
        "password_hash": hashlib.sha256("9329283191".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "ankit": {
        "password_hash": hashlib.sha256("ankit123".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "sahil": {
        "password_hash": hashlib.sha256("blackDog".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "oladi": {
        "password_hash": hashlib.sha256("blender".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "ntwist": {
        "password_hash": hashlib.sha256("ntwist123".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    },
    "faal": {
        "password_hash": hashlib.sha256("faal".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True  # Added this field
    }
}

def login():
    """Login form with user/password validation"""
    def login_clicked():
        if st.session_state.username in USERS:
            stored_hash = USERS[st.session_state.username]["password_hash"]
            input_hash = hashlib.sha256(st.session_state.password.encode()).hexdigest()
            if stored_hash == input_hash:
                st.session_state.logged_in = True
                st.session_state.current_user = st.session_state.username
                st.session_state.user_name = USERS[st.session_state.username]["name"]
            else:
                st.error("Invalid password")
        else:
            st.error("User not found")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Login")
        with st.form("login_form"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Login", on_click=login_clicked)
        return False
    return True


def logout():
    """Logout button"""
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()



if __name__ == "__main__":
    if login():
        st.sidebar.title(f"Welcome, {st.session_state.user_name}")
        logout()
        main_app()
