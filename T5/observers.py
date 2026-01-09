import json
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    StartInterruptionFrame
)

class LatencyObserver(BaseObserver):
    """
    Observer that tracks conversation turns, calculates latency, 
    and saves the metrics to a JSON file.
    """
    
    def __init__(self, filename="conversation_metrics.json"):
        super().__init__()
        
        # --- NEW: File Saving Setup ---
        self.filename = filename
        self.turn_history = [] # Stores all completed turns
        
        # --- Existing Logic Setup ---
        self.turn_count = 1
        self.last_bot_stop_time = None 
        self.current_turn = self._create_empty_turn(self.turn_count)

    def _create_empty_turn(self, turn_id):
        return {
            "turn_id": turn_id,
            "latency_bot_to_user": None,
            "user_start": None,
            "user_stop": None,
            "bot_start": None,
            "bot_stop": None,
            "interrupted": False,
            "interruption_time": None
        }

    async def on_push_frame(self, data: FramePushed):
        time_sec = data.timestamp / 1_000_000_000
        frame = data.frame

        # 1. USER STARTS (Start of new turn)
        if isinstance(frame, UserStartedSpeakingFrame):
            if self.current_turn["bot_stop"] is not None or self.current_turn["interrupted"]:
                self.turn_count += 1
                self.current_turn = self._create_empty_turn(self.turn_count)

            if self.current_turn["user_start"] is None:
                self.current_turn["user_start"] = time_sec
                
                # Calculate Latency
                if self.last_bot_stop_time is not None:
                    latency = time_sec - self.last_bot_stop_time
                    self.current_turn["latency_bot_to_user"] = round(latency, 4)
                else:
                    self.current_turn["latency_bot_to_user"] = 0.0

                print(f"\n🟢 [TURN {self.turn_count} OPENED]")

        # 2. USER STOPS
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.current_turn["user_stop"] = time_sec

        # 3. BOT STARTS
        elif isinstance(frame, BotStartedSpeakingFrame):
            self.current_turn["bot_start"] = time_sec

        # 4. BOT STOPS (Normal End)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            if not self.current_turn["interrupted"] and self.current_turn["bot_stop"] is None:
                self.current_turn["bot_stop"] = time_sec
                self.last_bot_stop_time = time_sec
                self._finalize_turn(reason="Normal Completion")

        # 5. INTERRUPTION (Abrupt End)
        elif isinstance(frame, StartInterruptionFrame):
            if not self.current_turn["interrupted"]:
                self.current_turn["interruption_time"] = time_sec
                self.current_turn["interrupted"] = True
                self.last_bot_stop_time = time_sec
                self._finalize_turn(reason="Interrupted by User")

    def _finalize_turn(self, reason):
        """Prints summary and saves to file."""
        # 1. Print to Console (Existing Logic)
        print(80 * "-")
        print(f"🏁 TURN {self.turn_count} SUMMARY | Status: {reason}")
        print(f"⏱️  Latency: {self.current_turn['latency_bot_to_user']}s")
        print(json.dumps(self.current_turn, indent=2))
        print(80 * "-")
        
        # 2. Save to JSON File (New Feature)
        self._save_to_json()

    def _save_to_json(self):
        """Appends current turn to history and writes to file."""
        # Add a copy of the current turn to history
        self.turn_history.append(self.current_turn.copy())
        
        try:
            with open(self.filename, "w") as f:
                json.dump(self.turn_history, f, indent=2)
            print(f"💾 Metrics saved to {self.filename}")
        except Exception as e:
            print(f"⚠️ Error saving metrics: {e}")