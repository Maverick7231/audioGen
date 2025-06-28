import os
import asyncio
from pathlib import Path
import streamlit as st
from edge_tts import Communicate

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
    
    # Input form
    with st.form("tts_form"):
        text = st.text_area("Enter Hindi Text", height=200, 
                          value='''अब शिक्षा बनेगी आपकी ताक़त, क्योंकि आपका भविष्य है हमारी प्राथमिकता!

जी हाँ! विजय मेमोरियल हायर सेकेंडरी स्कूल, रजाखेड़ी मकरोनिया सागर, मध्यप्रदेश में
एक ऐसा विद्यालय जो देता है शिक्षा, संस्कार और संपूर्ण विकास का वातावरण।''')
        
        voice = st.selectbox("Select Voice", 
                           [HINDI_VOICE_FEMALE, HINDI_VOICE_MALE],
                           format_func=lambda x: "Female" if "Female" in x else "Male")
        
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

if __name__ == "__main__":
    main()
