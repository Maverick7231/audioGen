import streamlit as st
from pydub import AudioSegment
from pydub.utils import make_chunks
import os
import tempfile

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
