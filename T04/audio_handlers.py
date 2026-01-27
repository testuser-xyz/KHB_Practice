"""
Audio buffer event handlers for processing and saving conversation audio
"""
import os
import wave
import struct
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor


class AudioBufferHandlers:
    """
    Manages audio buffer event handlers for recording and analyzing conversation audio
    """
    
    def __init__(self, audio_dir: str):
        """
        Initialize audio buffer handlers
        
        Args:
            audio_dir: Directory path where audio files will be saved
        """
        self.audio_dir = audio_dir
        self.user_turn_counter = 0
        self.bot_turn_counter = 0
    
    def setup_handlers(self, audiobuffer: AudioBufferProcessor):
        """
        Register all event handlers with the AudioBufferProcessor
        
        Args:
            audiobuffer: AudioBufferProcessor instance to attach handlers to
        """
        # Event handler: Triggered when recording stops with merged audio
        @audiobuffer.event_handler("on_audio_data")
        async def on_audio_data(buffer, audio: bytes, sample_rate: int, num_channels: int):
            print(f"\n📼 [AUDIO] Merged audio captured | Sample rate: {sample_rate}Hz | Channels: {num_channels}")
            print(f"   Size: {len(audio)} bytes")
            
            # Save merged audio (stereo: user on one channel, bot on the other)
            if len(audio) > 0:
                filepath = os.path.join(self.audio_dir, "full_conversation_stereo.wav")
                with wave.open(filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                print(f"   ✅ Saved to: {filepath}")
                
                # Calculate duration
                duration_sec = len(audio) / (sample_rate * num_channels * 2)
                print(f"   ⏱️  Duration: {duration_sec:.2f} seconds")

        # Event handler: Provides separate user and bot audio tracks
        @audiobuffer.event_handler("on_track_audio_data")
        async def on_track_audio_data(buffer, user_audio: bytes, bot_audio: bytes, sample_rate: int, num_channels: int):
            print(f"\n🎤 [TRACK AUDIO] Separate tracks captured | Sample rate: {sample_rate}Hz")
            print(f"   User audio: {len(user_audio)} bytes | Bot audio: {len(bot_audio)} bytes")
            
            # Save user track (stereo)
            if len(user_audio) > 0:
                user_filepath = os.path.join(self.audio_dir, "user_track_full.wav")
                with wave.open(user_filepath, 'wb') as wf:
                    wf.setnchannels(2)  # Stereo
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(user_audio)
                user_duration = len(user_audio) / (sample_rate * 2)
                print(f"   👤 User track saved: {user_filepath} ({user_duration:.2f}s)")
            
            # Save bot track (2 stereo)
            if len(bot_audio) > 0:
                bot_filepath = os.path.join(self.audio_dir, "bot_track_full.wav")
                with wave.open(bot_filepath, 'wb') as wf:
                    wf.setnchannels(2)  # Stereo
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(bot_audio)
                bot_duration = len(bot_audio) / (sample_rate * 2)
                print(f"   🤖 Bot track saved: {bot_filepath} ({bot_duration:.2f}s)")
            
            # Analyze audio characteristics
            if len(user_audio) > 0 and len(bot_audio) > 0:
                user_to_bot_ratio = len(user_audio) / len(bot_audio)
                print(f"   📊 User/Bot audio ratio: {user_to_bot_ratio:.2f}")
                if user_to_bot_ratio > 2:
                    print(f"   ⚠️  User spoke significantly more than bot")
                elif user_to_bot_ratio < 0.5:
                    print(f"   ⚠️  Bot spoke significantly more than user")

        # Event handler: Triggered when user's speaking turn ends
        @audiobuffer.event_handler("on_user_turn_audio_data")
        async def on_user_turn_audio_data(buffer, audio: bytes, sample_rate: int, num_channels: int):
            self.user_turn_counter += 1
            
            print(f"\n👤 [USER TURN #{self.user_turn_counter}] Audio captured | Sample rate: {sample_rate}Hz | Size: {len(audio)} bytes")
            
            if len(audio) > 0:
                # Save individual user turn
                filename = f"user_turn_{self.user_turn_counter:03d}.wav"
                filepath = os.path.join(self.audio_dir, filename)
                
                with wave.open(filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                
                duration = len(audio) / (sample_rate * num_channels * 2)
                print(f"   ✅ Saved: {filename} ({duration:.2f}s)")
                
                # Basic audio analysis
                # Calculate simple volume indicator (RMS of audio samples)
                samples = struct.unpack(f'{len(audio)//2}h', audio)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                volume_percent = min(100, (rms / 32768) * 100 * 10)  # Normalize to percentage
                
                print(f"   🔊 Volume level: {volume_percent:.1f}%")
                if volume_percent < 5:
                    print(f"   ⚠️  Low volume detected - user may be speaking softly")
                elif volume_percent > 80:
                    print(f"   ⚠️  High volume - possible background noise or loud speech")
                
                # Engagement metrics
                if duration < 1:
                    print(f"   💬 Quick response (< 1s)")
                elif duration > 10:
                    print(f"   💬 Long utterance (> 10s) - user may have detailed question")

        # Event handler: Triggered when bot's speaking turn ends
        @audiobuffer.event_handler("on_bot_turn_audio_data")
        async def on_bot_turn_audio_data(buffer, audio: bytes, sample_rate: int, num_channels: int):
            self.bot_turn_counter += 1
            
            print(f"\n🤖 [BOT TURN #{self.bot_turn_counter}] Audio captured | Sample rate: {sample_rate}Hz | Size: {len(audio)} bytes")
            
            if len(audio) > 0:
                # Save individual bot turn
                filename = f"bot_turn_{self.bot_turn_counter:03d}.wav"
                filepath = os.path.join(self.audio_dir, filename)
                
                with wave.open(filepath, 'wb') as wf:
                    wf.setnchannels(num_channels)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                
                duration = len(audio) / (sample_rate * num_channels * 2)
                print(f"   ✅ Saved: {filename} ({duration:.2f}s)")
                
                # Quality checks
                samples = struct.unpack(f'{len(audio)//2}h', audio)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                volume_percent = min(100, (rms / 32768) * 100 * 10)
                
                print(f"   🔊 TTS output volume: {volume_percent:.1f}%")
                
                # Check for potential issues
                if rms < 100:
                    print(f"   ⚠️  Very low audio level - possible TTS issue")
                
                # Response time quality
                if duration < 2:
                    print(f"   ⚡ Quick response ({duration:.1f}s)")
                elif duration > 15:
                    print(f"   ⏳ Long response ({duration:.1f}s) - user may lose interest")
                
                # Voice consistency check (comparing to expected range)
                expected_rms_range = (1000, 5000)  # Typical TTS range
                if expected_rms_range[0] <= rms <= expected_rms_range[1]:
                    print(f"   ✓ Voice quality consistent")
                else:
                    print(f"   ⚠️  Voice quality outside expected range (RMS: {rms:.0f})")
