import json
import os
from datetime import datetime
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    StartInterruptionFrame,
    TranscriptionFrame,
    TextFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame
)

class SessionObserver(BaseObserver):
    """
    Observer that tracks conversation turns, latencies, AND transcripts.
    Saves a complete JSON log of the conversation structure.
    """
    
    def __init__(self, filename="conversation_metrics.json"):
        super().__init__()
        
        # File Setup
        self.filename = filename
        self.turn_history = []
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Turn State
        self.turn_count = 1
        self.last_bot_stop_time = None 
        
        # Transcript Buffers
        self.user_text_buffer = []
        self.bot_text_buffer = [] 
        
        # Initialize First Turn
        self.current_turn = self._create_empty_turn(self.turn_count)

    def _create_empty_turn(self, turn_id):
        return {
            "turn_id": turn_id,
            "latency_from_last_turn": None,
            "user_start": None,
            "user_stop": None,
            "user_transcript": "",
            "bot_start": None,
            "bot_stop": None,
            "bot_transcript": "",
            "interrupted": False,
            "interruption_time": None
        }

    async def on_push_frame(self, data: FramePushed):
        # Convert nanoseconds to seconds
        time_sec = data.timestamp / 1_000_000_000
        frame = data.frame
        source = str(data.source) # Get source name (e.g., "LLM", "STT")

        
        # User Starts Speaking -> NEW TURN
        if isinstance(frame, UserStartedSpeakingFrame):
            # If previous turn was done, reset
            if self.current_turn["bot_stop"] is not None or self.current_turn["interrupted"]:
                self.turn_count += 1
                self.current_turn = self._create_empty_turn(self.turn_count)
                self.user_text_buffer = []  # Clear user buffer for new turn
                self.bot_text_buffer = []  # Clear bot buffer for new turn

            if self.current_turn["user_start"] is None:
                self.current_turn["user_start"] = time_sec
                self.user_text_buffer = []  # Reset buffer at the start of speaking
                
                # Calculate Latency
                if self.last_bot_stop_time is not None:
                    latency = time_sec - self.last_bot_stop_time
                    self.current_turn["latency_from_last_turn"] = round(latency, 4)
                else:
                    self.current_turn["latency_from_last_turn"] = 0.0

                print(f"\n🟢 [TURN {self.turn_count} OPENED]")

        # User Transcript (STT) -> Accumulate chunks
        elif isinstance(frame, TranscriptionFrame):
            if frame.text and frame.text.strip():
                self.user_text_buffer.append(frame.text.strip())
                self.current_turn["user_transcript"] = " ".join(self.user_text_buffer)

        # User Stops Speaking
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.current_turn["user_stop"] = time_sec
            if self.user_text_buffer:
                self.current_turn["user_transcript"] = " ".join(self.user_text_buffer)

        
        # Start of LLM Response -> Clear Buffer
        elif isinstance(frame, LLMFullResponseStartFrame):
            self.bot_text_buffer = []

        # LLM Text Chunk -> Append to Buffer
        elif isinstance(frame, TextFrame) and "LLM" in source:
            self.bot_text_buffer.append(frame.text)

        # End of LLM Response -> Save Buffer to Turn
        elif isinstance(frame, LLMFullResponseEndFrame):
            full_text = "".join(self.bot_text_buffer)
            self.current_turn["bot_transcript"] = full_text

        # Bot Starts Speaking (Audio)
        elif isinstance(frame, BotStartedSpeakingFrame):
            self.current_turn["bot_start"] = time_sec
            # Fallback: If we didn't get an EndFrame yet, update transcript from buffer now
            if not self.current_turn["bot_transcript"] and self.bot_text_buffer:
                self.current_turn["bot_transcript"] = "".join(self.bot_text_buffer)

        # Bot Stops Speaking (Normal End)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            if not self.current_turn["interrupted"] and self.current_turn["bot_stop"] is None:
                self.current_turn["bot_stop"] = time_sec
                self.last_bot_stop_time = time_sec
                
                # Finalize transcript in case more text came in
                if self.bot_text_buffer:
                     self.current_turn["bot_transcript"] = "".join(self.bot_text_buffer)
                
                self._finalize_turn(reason="Normal Completion")

        # Interruption (Abrupt End)
        elif isinstance(frame, StartInterruptionFrame):
            if not self.current_turn["interrupted"]:
                self.current_turn["interruption_time"] = time_sec
                self.current_turn["interrupted"] = True
                self.last_bot_stop_time = time_sec
                
                # Capture whatever text the bot managed to generate/speak
                if self.bot_text_buffer:
                     self.current_turn["bot_transcript"] = "".join(self.bot_text_buffer)
                
                self._finalize_turn(reason="Interrupted by User")

    def _finalize_turn(self, reason):
        """Prints summary and saves to file."""
        print(80 * "-")
        print(f"🏁 TURN {self.turn_count} SUMMARY | Status: {reason}")
        print(f"🗣️  User: {self.current_turn['user_transcript']}")
        print(f"🤖 Bot:  {self.current_turn['bot_transcript']}")
        print(f"⏱️  Latency: {self.current_turn['latency_from_last_turn']}s")
        print(80 * "-")
        
        self._save_to_json()

    def _save_to_json(self):
        """Appends current turn to history and writes to file."""
        self.turn_history.append(self.current_turn.copy())
        try:
            with open(self.filename, "w", encoding='utf-8') as f:
                json.dump(self.turn_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving metrics: {e}")