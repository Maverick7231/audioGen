import os
import asyncio
from pathlib import Path
import streamlit as st
from edge_tts import Communicate
import asyncio

# Define the Hindi voices
HINDI_VOICE_MALE = "hi-IN-MadhurNeural"
HINDI_VOICE_FEMALE = "hi-IN-SwaraNeural"
OUTPUT_DIR = "generated_audio"

async def generate_audio(text, voice, output_filename, rate="+0%", pitch="+0Hz"):
    """Generate audio file from text using edge-tts"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    final_output_path = Path(OUTPUT_DIR) / output_filename
    
    try:
        communicate = Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(final_output_path))
        return final_output_path
    except Exception as e:
        st.error(f"Error during audio generation: {e}")
        return None

def main():
    st.title("Hindi Text-to-Speech Generator")
    st.markdown("Convert Hindi text to natural sounding speech")
    
    # Define voices with clear labels
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
            st.success("Audio generated successfully!")
            
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

# User database (in production, use a real database)
USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "name": "Administrator"
    },
    "user": {
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "name": "Regular User"
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
        main_app()  # Your existing TTS app function


