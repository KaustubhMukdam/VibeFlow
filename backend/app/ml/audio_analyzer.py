import os
import uuid
import librosa
import numpy as np
from pydub import AudioSegment
import json

class AudioAnalyzer:
    def __init__(self):
        self.sr = 22050  # Default sample rate for feature extraction
        
    def _convert_to_wav_if_needed(self, file_path: str) -> str:
        """Convert non-wav files to a temp wav file for librosa via pydub"""
        if file_path.lower().endswith('.wav'):
            return file_path
            
        temp_path = f"temp_{uuid.uuid4().hex}.wav"
        try:
            audio = AudioSegment.from_file(file_path)
            audio.export(temp_path, format="wav")
            return temp_path
        except Exception as e:
            print(f"Error converting {file_path}: {e}")
            raise

    def analyze(self, file_path: str) -> dict:
        temp_wav = None
        try:
            # 1. Conversion
            process_path = self._convert_to_wav_if_needed(file_path)
            if process_path != file_path:
                temp_wav = process_path
            
            # 2. Load with librosa
            y, sr = librosa.load(process_path, sr=self.sr)
            
            # 3. Extract Features
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=6) # 7 bands total
            
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            tempo = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
            
            rms = librosa.feature.rms(y=y)
            zcr = librosa.feature.zero_crossing_rate(y=y)
            
            # Summarize (mean and std)
            mfcc_vector = np.concatenate((np.mean(mfcc, axis=1), np.std(mfcc, axis=1))).tolist()
            chroma_vector = np.concatenate((np.mean(chroma, axis=1), np.std(chroma, axis=1))).tolist()
            contrast_vector = np.concatenate((np.mean(contrast, axis=1), np.std(contrast, axis=1))).tolist()
            
            energy_val = float(np.mean(rms))
            zcr_val = float(np.mean(zcr))
            
            # Very basic proxy for valence (brightness / harmony proxy)
            # A real valence model is better, but this suffices for the MVP proxy
            valence_proxy = float(np.mean(chroma) * energy_val)
            
            # Construct unified embedding
            full_vector = np.concatenate([
                mfcc_vector, 
                chroma_vector, 
                contrast_vector, 
                [tempo / 200.0], # Normalize approx
                [energy_val * 10], 
                [zcr_val * 10], 
                [valence_proxy * 10]
            ])
            # L2 normalizations
            norm = np.linalg.norm(full_vector)
            if norm > 0:
                full_vector = full_vector / norm
            
            return {
                "mfcc_vector": json.dumps(mfcc_vector),
                "chroma_vector": json.dumps(chroma_vector),
                "contrast_vector": json.dumps(contrast_vector),
                "tempo": tempo,
                "energy": energy_val,
                "zcr": zcr_val,
                "valence_proxy": valence_proxy,
                "full_vector": json.dumps(full_vector.tolist())
            }
            
        finally:
            if temp_wav and os.path.exists(temp_wav):
                os.remove(temp_wav)
