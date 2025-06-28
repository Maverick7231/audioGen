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


# --- Configuration ---
HINDI_VOICE_MALE = "hi-IN-MadhurNeural"
HINDI_VOICE_FEMALE = "hi-IN-SwaraNeural"
OUTPUT_DIR = "generated_audio"
LOG_SHEET_NAME = "logs"  

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
async def generate_audio(text, voice, output_filename, rate="+0%", pitch="+0Hz"):
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    final_output_path = Path(OUTPUT_DIR) / output_filename
    
    try:
        communicate = Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(final_output_path))
        return final_output_path
    except Exception as e:
        st.error(f"Error during audio generation: {e}")
        return None

# --- Main App ---
def main_app():
    st.title("Hindi Text-to-Speech Generator")
    st.markdown("Convert Hindi text to natural sounding speech")
    
    VOICES = {
        "Female (Swara)": HINDI_VOICE_FEMALE,
        "Male (Madhur)": HINDI_VOICE_MALE
    }

    # Single form definition
    with st.form("tts_form"):
        text = st.text_area("Enter Hindi Text", height=200, 
                          value='''अब शिक्षा बनेगी आपकी ताक़त, क्योंकि आपका भविष्य है हमारी प्राथमिकता!

जी हाँ! विजय मेमोरियल हायर सेकेंडरी स्कूल, रजाखेड़ी मकरोनिया सागर, मध्यप्रदेश में
एक ऐसा विद्यालय जो देता है शिक्षा, संस्कार और संपूर्ण विकास का वातावरण।''')
        
        # Voice selection using the VOICES dictionary
        voice_name = st.selectbox("Select Voice", list(VOICES.keys()))
        voice = VOICES[voice_name]  # Gets the actual voice ID
        
        col1, col2 = st.columns(2)
        with col1:
            rate = st.selectbox("Speed", ["+0%", "+10%", "+20%", "-10%", "-20%"])
        with col2:
            pitch = st.selectbox("Pitch", ["+0Hz", "+10Hz", "+20Hz", "-10Hz", "-20Hz"])
        
        filename = st.text_input("Output filename (without extension)", "output")
        
        submitted = st.form_submit_button("Generate Audio")
    
    # with st.form("tts_form"):
    #     text = st.text_area("Enter Hindi Text", height=200)
    #     voice = st.selectbox("Select Voice", list(VOICES.keys()))
    #     filename = st.text_input("Output Filename", "output")
    #     submitted = st.form_submit_button("Generate Audio")

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
        # with st.spinner("Generating..."):
        #     output_path = asyncio.run(
        #         generate_audio(
        #             text=text,
        #             voice=VOICES[voice],
        #             output_filename=f"{filename}.mp3"
        #         )
        #     )
        
        # if output_path:
        #     log_request(
        #         st.session_state.current_user,
        #         voice,
        #         text,
        #         f"{filename}.mp3"
        #     )
        #     st.success("Done! Audio generated and logged.")
        #     st.audio(str(output_path))

        if output_path and output_path.exists():
            log_request(
                st.session_state.current_user,
                voice,
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
