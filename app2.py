import streamlit as st
from pydub import AudioSegment
from pydub.utils import make_chunks
import os
import tempfile
import hashlib
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Configuration ---
USERS = {
    "kamesh": {
        "password_hash": hashlib.sha256("nirvaan".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    },
    "ram": {
        "password_hash": hashlib.sha256("ram123".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    },
    "admin": {
        "password_hash": hashlib.sha256("9329283191".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    },
    "ankit": {
        "password_hash": hashlib.sha256("ankit123".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    },
    "sahil": {
        "password_hash": hashlib.sha256("blackDog".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    },
    "oladi": {
        "password_hash": hashlib.sha256("blender".encode()).hexdigest(),
        "name": "Administrator",
        "is_admin": True
    }
}

LOG_SHEET_NAME = "logs"  # Name of your Google Sheet

def get_google_sheet(sheet_index=0):
    """Authenticate and return the specific worksheet"""
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["GCP_CREDS"], scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open(LOG_SHEET_NAME)
        
        # Get all worksheets and select by index
        worksheets = spreadsheet.worksheets()
        if len(worksheets) > sheet_index:
            return worksheets[sheet_index]
        else:
            st.error(f"Sheet index {sheet_index} not found. Available sheets: {[ws.title for ws in worksheets]}")
            return None
    except Exception as e:
        st.error(f"Failed to access Google Sheets: {e}")
        return None

def log_usage(username, action, details=""):
    """Log user actions to first sheet (Sheet1)"""
    sheet = get_google_sheet(0)  # First sheet for usage logs
    if sheet:
        try:
            sheet.append_row([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                action,
                details
            ])
        except Exception as e:
            st.error(f"Failed to log usage: {e}")

def log_audio_processing(username, params, voice_file_name, bg_file_name):
    """Log audio processing details to second sheet (Sheet2)"""
    sheet = get_google_sheet(1)  # Second sheet for audio processing logs
    if sheet:
        try:
            sheet.append_row([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                voice_file_name,
                bg_file_name,
                str(params['chunk_size_ms']),
                str(params['duck_amount_db']),
                str(params['light_duck_db']),
                str(params['fade_ms']),
                str(params['bg_extension_ms']),
                str(params['loudness_threshold'])
            ])
        except Exception as e:
            st.error(f"Failed to log audio processing: {e}")

# --- Authentication ---
def login():
    """Login form with user/password validation"""
    def password_entered():
        if st.session_state.username in USERS:
            stored_hash = USERS[st.session_state.username]["password_hash"]
            input_hash = hashlib.sha256(st.session_state.password.encode()).hexdigest()
            if stored_hash == input_hash:
                st.session_state.logged_in = True
                st.session_state.current_user = st.session_state.username
                st.session_state.user_name = USERS[st.session_state.username]["name"]
                log_usage(st.session_state.username, "Login")
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
            st.form_submit_button("Login", on_click=password_entered)
        return False
    return True

def logout():
    """Logout button"""
    if st.sidebar.button("Logout"):
        log_usage(st.session_state.current_user, "Logout")
        st.session_state.logged_in = False
        st.experimental_rerun()



def duck_background_music(voiceover, background, output_path, params):
    """Modified ducking function with all parameters configurable"""
    # Extend voiceover with silence-free background continuation
    total_length = len(voiceover) + params['bg_extension_ms']
    if len(background) < total_length:
        background *= (total_length // len(background) + 1)
    background = background[:total_length]

    # Extend voiceover with silence
    voiceover += AudioSegment.silent(duration=params['bg_extension_ms'])

    # Chunk both audios
    voice_chunks = make_chunks(voiceover, params['chunk_size_ms'])
    bg_chunks = make_chunks(background, params['chunk_size_ms'])

    ducked_chunks = []
    
    for v_chunk, b_chunk in zip(voice_chunks, bg_chunks):
        v_db = v_chunk.dBFS
        
        # Duck background based on voice loudness
        if v_db > params['loudness_threshold']:
            b_chunk = b_chunk - params['duck_amount_db']
        else:
            b_chunk = b_chunk - params['light_duck_db']  # Configurable light ducking

        # Apply fade
        b_chunk = b_chunk.fade_in(params['fade_ms']).fade_out(params['fade_ms'])
        ducked_chunks.append(b_chunk)

    # Combine and export
    sum(ducked_chunks).overlay(voiceover).export(output_path, format="mp3", bitrate="192k")

def main():
    st.title("🎵 Audio Ducking Tool")
    st.markdown("Automatically lower background music when voiceover plays")

    # File uploaders
    col1, col2 = st.columns(2)
    with col1:
        voice_file = st.file_uploader("Upload Voiceover", type=["mp3", "wav"])
    with col2:
        bg_file = st.file_uploader("Upload Background Music", type=["mp3", "wav"])

    # Parameters - Sidebar
    with st.sidebar:
        st.header("Ducking Parameters")
        params = {
            'chunk_size_ms': st.slider("Chunk Size (ms)", 500, 2000, 1000),
            'duck_amount_db': st.slider("Duck Amount (dB)", 5, 30, 20),
            'light_duck_db': st.slider("Light Ducking (dB)", 0, 15, 10),
            'fade_ms': st.slider("Fade Duration (ms)", 10, 100, 30),
            'bg_extension_ms': st.slider("Background Extension (ms)", 1000, 5000, 3000),
            'loudness_threshold': st.slider("Voice Threshold (dBFS)", -50, -10, -30)
        }

    # Process button
    if st.button("Process Audio") and voice_file and bg_file:
        with st.spinner("Processing..."):
            # Create temp files
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp1, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp2, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp3:
                
                # Save uploads to temp files
                tmp1.write(voice_file.read())
                tmp2.write(bg_file.read())
                
                # Load audio
                voice = AudioSegment.from_file(tmp1.name)
                bg = AudioSegment.from_file(tmp2.name)
                
                # Process
                duck_background_music(voice, bg, tmp3.name, params)
                
                # Show result
                st.success("Processing complete!")
                st.audio(tmp3.name)
                
                # Download button
                with open(tmp3.name, "rb") as f:
                    st.download_button(
                        "Download Processed Audio",
                        f.read(),
                        file_name="ducked_audio.mp3",
                        mime="audio/mp3"
                    )
                
            # Clean up
            os.unlink(tmp1.name)
            os.unlink(tmp2.name)
            os.unlink(tmp3.name)

if __name__ == "__main__":
    main()
