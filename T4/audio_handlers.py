import os
import wave #used for saving audio files
import struct #used for handling binary data
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

class AudioBufferHandlers:
    def __init__(self, audio_dir: str):
        self.audio_dir = audio_dir
        self.user_turn_counter = 0
        self.bot_turn_counter = 0

    def setup_handlers(self, audiobuffer: AudioBufferProcessor):
        @audiobuffer.event_handler("on_audio_data")
        async def on_audio_data(buffer, audio:bytes, sample_rate:int, num_channels:int):
            if len(audio)>0:
                filepath = os.path.join(self.audio_dir, "full_conversation_mono.wav")
                with wave.open(filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
        
        @audiobuffer.event_handler("on_track_audio_data")
        async def on_track_audio_data(buffer, user_audio:bytes, bot_audio:bytes, sample_rate:int, num_channels:int):
            if len(user_audio)>0:
                user_filepath = os.path.join(self.audio_dir, "user_track_full.wav")
                with wave.open(user_filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(sample_rate)
                    wf.writeframes(user_audio)
            
            if len(bot_audio)>0:
                bot_filepath = os.path.join(self.audio_dir, "bot_track_full.wav")
                with wave.open(bot_filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(sample_rate)
                    wf.writeframes(bot_audio)
        
        @audiobuffer.event_handler("on_user_turn_audio_data")
        async def on_user_turn_audio_data(buffer, audio:bytes, sample_rate:int, num_channels:int):
            self.user_turn_counter += 1
            print(f'Total user turns recorded: {self.user_turn_counter}')

        @audiobuffer.event_handler("on_bot_turn_audio_data")
        async def on_bot_turn_audio_data(buffer, audio:bytes, sample_rate:int, num_channels:int):
            self.bot_turn_counter += 1
            print(f'Total bot turns recorded: {self.bot_turn_counter}')