import json
import os
from datetime import datetime
from pipecat.observers.base_observer import BaseObserver, FramePushed
# We import TranscriptionFrame to ensure we capture the EXACT text
from pipecat.frames.frames import TranscriptionFrame, TextFrame, Frame, LLMFullResponseStartFrame, LLMFullResponseEndFrame
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver
from pipecat.observers.base_observer import BaseObserver, FramePushed
# Import the specific frames we need to detect Start/End of turns

class JsonLatencyObserver(UserBotLatencyLogObserver):
    def __init__(self, output_filepath: str):

        super().__init__()
        self.output_filepath = output_filepath
        self.captured_latencies = [] 
        
        self.log_data = {
            "session_start": datetime.now().isoformat(),
            "latency_events": [],
            "summary": None
        }
        self._save_json()

    def _save_json(self):
        """Helper to write current state to disk"""
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving latency JSON: {e}")

    def _log_latency(self, latency: float):
        super()._log_latency(latency)
        
        self.captured_latencies.append(latency)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "latency_seconds": round(latency, 4),
            "message": f"LATENCY FROM USER STOPPED SPEAKING TO BOT STARTED SPEAKING: {latency:.3f}s"
        }
        
        self.log_data["latency_events"].append(entry)
        self._save_json()

    def _log_summary(self):
        super()._log_summary()

        if not self.captured_latencies:
            return

        avg_lat = sum(self.captured_latencies) / len(self.captured_latencies)
        min_lat = min(self.captured_latencies)
        max_lat = max(self.captured_latencies)

        self.log_data["summary"] = {
            "timestamp": datetime.now().isoformat(),
            "count": len(self.captured_latencies),
            "average_seconds": round(avg_lat, 4),
            "min_seconds": round(min_lat, 4),
            "max_seconds": round(max_lat, 4)
        }
        self._save_json()


class JsonTranscriptionObserver(BaseObserver):
    def __init__(self, output_filepath: str):
        super().__init__()
        self.output_filepath = output_filepath
        self.bot_text_buffer = []
        
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        
        self.log_data = {
            "session_start": datetime.now().isoformat(),
            "conversation": []
        }
        self._save_json()

    def _save_json(self):
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _append_log(self, role, text):
        if not text.strip(): return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role, 
            "text": text.strip()
        }
        print(f"📝 [LOG] {role.upper()}: {text}") 
        self.log_data["conversation"].append(entry)
        self._save_json()

    async def on_push_frame(self, *args, **kwargs):
        source = None
        frame = None

        if len(args) > 0:
            if isinstance(args[0], FramePushed):
                frame = args[0].frame
                source = args[0].source
            else:
                source = args[0] 
                for arg in args:
                    if isinstance(arg, Frame):
                        frame = arg
                        break
        
        if not frame: return

        src_name = str(source) if source else ""

        # --- LOGIC WITH SOURCE FILTERING ---

        if isinstance(frame, TranscriptionFrame):
            if "STT" in src_name:
                self._append_log("user", frame.text)

        elif "LLM" in src_name and "Aggregator" not in src_name:
            
            if isinstance(frame, LLMFullResponseStartFrame):
                self.bot_text_buffer = []

            elif isinstance(frame, TextFrame):
                self.bot_text_buffer.append(frame.text)

            elif isinstance(frame, LLMFullResponseEndFrame):
                full_sentence = "".join(self.bot_text_buffer)
                self._append_log("assistant", full_sentence)
                self.bot_text_buffer = []

        return