┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
│                   (Browser/Mic)                             │
│                   (Customer Role)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ WebRTC Audio Stream
┌─────────────────────────────────────────────────────────────┐
│              SmallWebRTCTransport                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ VAD (Silero) + Smart Turn Analyzer                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Audio Chunks
┌─────────────────────────────────────────────────────────────┐
│                    GroqSTTService                           │
│               (Whisper Large V3)                            │
│            [audio_passthrough=True]                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ TranscriptionFrame
┌─────────────────────────────────────────────────────────────┐
│              LLMUserContextAggregator                       │
│         (Adds user message to context)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ LLMMessagesFrame
┌─────────────────────────────────────────────────────────────┐
│                  GroqLLMService                             │
│              (Llama 3.1 8B Instant)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ System Prompt: Customer AI Logic                     │  │
│  │ - Acts as customer calling restaurant                │  │
│  │ - Responds to restaurant assistant                   │  │
│  │ - Places orders naturally                            │  │
│  │ - Asks questions and confirms orders                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ TextFrame (streaming)
┌─────────────────────────────────────────────────────────────┐
│                CartesiaTTSService                           │
│          (Neural Voice Synthesis)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ AudioRawFrame
┌─────────────────────────────────────────────────────────────┐
│              SmallWebRTCTransport Output                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ WebRTC Audio Stream
┌─────────────────────────────────────────────────────────────┐
│              AudioBufferProcessor                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Captures & Records Audio:                            │  │
│  │ - Full conversation (mono mix)                       │  │
│  │ - Separate user & bot tracks                         │  │
│  │ - Individual turns (user & bot)                      │  │
│  │ - Audio analysis & metrics                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMAssistantContextAggregator                  │
│        (Saves bot response to context)                      │
└─────────────────────────────────────────────────────────────┘

AUDIO BUFFER EVENT FLOW:
═══════════════════════

1. on_audio_data
   └─> Triggered when recording stops
   └─> Saves: full_conversation_mono.wav
   └─> Contains: User + Bot audio mixed in temporal sequence

2. on_track_audio_data
   └─> Triggered when recording stops
   └─> Saves: user_track_full.wav (all user audio)
   └─> Saves: bot_track_full.wav (all bot audio)
   └─> Analyzes: User/Bot audio ratio

3. on_user_turn_audio_data
   └─> Triggered after each user turn ends
   └─> Saves: user_turn_001.wav, user_turn_002.wav, etc.
   └─> Analyzes: Volume, duration, engagement metrics

4. on_bot_turn_audio_data
   └─> Triggered after each bot turn ends
   └─> Saves: bot_turn_001.wav, bot_turn_002.wav, etc.
   └─> Analyzes: TTS quality, response time, voice consistency
