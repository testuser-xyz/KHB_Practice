###VAD:
Voice activity detection
determines when someone is speaking versus when they are silent

###STT:
Speech to txt
converts audio to text

###LLM:
Large language model
Takes text input generates response

###TTS:
Text to speech
converts text response to audio

###WEBRTC:
Web Real-Time Communication
an open-source project and set of APIs that enables real-time audio, video, and data exchange directly between web browsers and apps

###prebuilt fe
uv add pipecat-ai-small-webrtc-prebuilt

---
## COMPLETE PARAMETER REFERENCE FOR BOT.PY COMPONENTS

### 1. SmallWebRTCTransport Parameters

```python
SmallWebRTCTransport(
    webrtc_connection,  # Required: WebRTC connection object from runner_args
    params,             # Optional: TransportParams instance (see below)
    name=None,          # Optional: Name for the transport instance
    input_name=None,    # Optional: Name for input processor
    output_name=None    # Optional: Name for output processor
)
```

---

### 2. TransportParams - All Available Parameters

```python
TransportParams(
    # AUDIO OUTPUT
    audio_out_enabled=False,              # Enable audio output streaming
    audio_out_sample_rate=None,           # Output sample rate in Hz (int or None)
    audio_out_channels=1,                 # Number of output channels (1 or 2)
    audio_out_bitrate=96000,              # Output bitrate in bits/sec
    audio_out_10ms_chunks=4,              # Number of 10ms chunks to buffer
    audio_out_mixer=None,                 # BaseAudioMixer instance or dict mapping
    audio_out_destinations=[],            # List of output destination IDs
    audio_out_end_silence_secs=2,         # Silence duration after EndFrame (0 for none)
    
    # AUDIO INPUT
    audio_in_enabled=False,               # Enable audio input streaming
    audio_in_sample_rate=None,            # Input sample rate in Hz (int or None)
    audio_in_channels=1,                  # Number of input channels (1 or 2)
    audio_in_filter=None,                 # BaseAudioFilter instance for filtering
    audio_in_stream_on_start=True,        # Start streaming immediately
    audio_in_passthrough=True,            # Pass input frames downstream
    
    # VIDEO INPUT
    video_in_enabled=False,               # Enable video input
    
    # VIDEO OUTPUT
    video_out_enabled=False,              # Enable video output streaming
    video_out_is_live=False,              # Enable real-time video output
    video_out_width=1024,                 # Video width in pixels
    video_out_height=768,                 # Video height in pixels
    video_out_bitrate=800000,             # Video bitrate in bits/sec
    video_out_framerate=30,               # Video framerate (FPS)
    video_out_color_format="RGB",         # Color format string ("RGB", "BGR", etc.)
    video_out_destinations=[],            # List of video destination IDs
    
    # DEPRECATED CAMERA PARAMETERS (use video_* instead)
    camera_in_enabled=False,              # DEPRECATED: Use video_in_enabled
    camera_out_enabled=False,             # DEPRECATED: Use video_out_enabled
    camera_out_is_live=False,             # DEPRECATED: Use video_out_is_live
    camera_out_width=1024,                # DEPRECATED: Use video_out_width
    camera_out_height=768,                # DEPRECATED: Use video_out_height
    camera_out_bitrate=800000,            # DEPRECATED: Use video_out_bitrate
    camera_out_framerate=30,              # DEPRECATED: Use video_out_framerate
    camera_out_color_format="RGB",        # DEPRECATED: Use video_out_color_format
    
    # VAD (Voice Activity Detection)
    vad_enabled=False,                    # DEPRECATED: Use audio_in_enabled + vad_analyzer
    vad_audio_passthrough=False,          # DEPRECATED: Use audio_in_passthrough
    vad_analyzer=None,                    # VADAnalyzer instance (e.g., SileroVADAnalyzer)
    
    # TURN ANALYZER
    turn_analyzer=None                    # BaseTurnAnalyzer for conversation management
)
```

#### Important Notes for TransportParams:
- Set `audio_in_enabled=True` to capture user microphone
- Set `audio_out_enabled=True` to send bot speech to user
- `vad_analyzer` requires a VADAnalyzer instance (like SileroVADAnalyzer)
- Sample rates typically: 8000, 16000, 24000, or 48000 Hz

---

### 3. SileroVADAnalyzer Parameters

```python
SileroVADAnalyzer(
    sample_rate=None,   # Optional: int (8000 or 16000 Hz), set later if None
    params=None         # Optional: VADParams instance (see below)
)
```

---

### 4. VADParams - Voice Activity Detection Configuration

```python
VADParams(
    confidence=0.7,     # Minimum confidence threshold (0.0 to 1.0)
    start_secs=0.2,     # Duration before confirming voice start (seconds)
    stop_secs=0.8,      # Duration before confirming voice stop (seconds)
    min_volume=0.6      # Minimum audio volume threshold (0.0 to 1.0)
)
```

#### VAD Parameter Details:
- **confidence**: Higher = more strict voice detection (default 0.7)
- **start_secs**: How long to wait before saying "user started speaking"
- **stop_secs**: How long of silence before saying "user stopped speaking"
- **min_volume**: Filters out very quiet audio below this threshold

---

### 5. GroqSTTService Parameters (Speech-to-Text)

```python
GroqSTTService(
    api_key,                              # Required: Groq API key (string)
    model="whisper-large-v3-turbo",       # Model name (string)
    base_url="https://api.groq.com/openai/v1",  # API endpoint
    language=Language.EN,                 # Language enum (Language.EN, Language.ES, etc.)
    prompt=None,                          # Optional: Text to guide model's style (string)
    temperature=None,                     # Optional: Sampling temperature 0.0-1.0 (float)
    **kwargs                              # Additional BaseWhisperSTTService args
)
```

#### Available Groq Whisper Models:
- `whisper-large-v3-turbo` (default, fastest)
- `whisper-large-v3`

---

### 6. GroqLLMService Parameters (Language Model)

```python
GroqLLMService(
    api_key,                              # Required: Groq API key (string)
    model="llama-3.3-70b-versatile",      # Model name (string)
    base_url="https://api.groq.com/openai/v1",  # API endpoint
    **kwargs                              # Additional OpenAILLMService parameters
)
```

#### Available Groq LLM Models:
- `llama-3.3-70b-versatile` (default)
- `llama-3.1-8b-instant`
- `llama-3.1-70b-versatile`
- `gemma2-9b-it`
- `mixtral-8x7b-32768`

#### Additional OpenAI-Compatible kwargs:
```python
temperature=0.7,           # Sampling temperature (0.0-2.0)
max_tokens=None,           # Max tokens to generate (int or None)
top_p=1.0,                 # Nucleus sampling parameter
frequency_penalty=0.0,     # Penalty for repeated tokens (-2.0 to 2.0)
presence_penalty=0.0,      # Penalty for new topics (-2.0 to 2.0)
seed=None                  # Random seed for reproducibility (int or None)
```

---

### 7. CartesiaTTSService Parameters (Text-to-Speech)

```python
CartesiaTTSService(
    api_key,                              # Required: Cartesia API key (string)
    voice_id,                             # Required: Voice ID (string)
    cartesia_version="2025-04-16",        # API version string
    url="wss://api.cartesia.ai/tts/websocket",  # WebSocket URL
    model="sonic-3",                      # TTS model name
    sample_rate=None,                     # Audio sample rate (int or None)
    encoding="pcm_s16le",                 # Audio encoding format
    container="raw",                      # Audio container format
    params=None,                          # Optional: CartesiaTTSService.InputParams
    text_aggregator=None,                 # Optional: BaseTextAggregator instance
    aggregate_sentences=True,             # Whether to aggregate sentences
    **kwargs                              # Additional TTSService parameters
)
```

#### CartesiaTTSService.InputParams:
```python
CartesiaTTSService.InputParams(
    language=Language.EN,                 # Language enum
    speed=None,                           # Literal["slow", "normal", "fast"] (deprecated)
    emotion=[],                           # List[str] of emotions (deprecated)
    generation_config=None                # GenerationConfig for Sonic-3 (see below)
)
```

#### GenerationConfig (Sonic-3 Models):
```python
GenerationConfig(
    volume=None,    # Volume multiplier: 0.5 to 2.0 (float, default 1.0)
    speed=None,     # Speed multiplier: 0.6 to 1.5 (float, default 1.0)
    emotion=None    # Single emotion string (e.g., "neutral", "excited", "sad")
)
```

#### Available Cartesia Emotions (60+ options):
```
Primary: neutral, angry, excited, content, sad, scared
Happy: happy, enthusiastic, elated, euphoric, triumphant
Surprise: amazed, surprised, curious
Social: flirtatious, joking/comedic, grateful, affectionate, sympathetic
Calm: peaceful, serene, calm, trust, contemplative
Anger: mad, outraged, frustrated, agitated, threatened
Disgust: disgusted, contempt, envious, sarcastic, ironic
Sad: dejected, melancholic, disappointed, hurt, guilty, rejected, nostalgic
Tired: bored, tired, resigned
Anxiety: anxious, panicked, alarmed, hesitant, insecure, confused
Other: anticipation, mysterious, proud, confident, distant, skeptical, 
       determined, apologetic, wistful
```

#### Voice ID Examples:
```
79a125e8-cd45-4c13-8a67-188112f4dd22  # Example voice
# Get more voice IDs from Cartesia dashboard: https://play.cartesia.ai/
```

---

### 8. PipelineParams - Pipeline Execution Configuration

```python
PipelineParams(
    allow_interruptions=True,             # Enable user interruptions (barge-in)
    audio_in_sample_rate=16000,           # Input sample rate in Hz
    audio_out_sample_rate=24000,          # Output sample rate in Hz
    enable_heartbeats=False,              # Enable heartbeat monitoring
    enable_metrics=False,                 # Enable metrics collection
    enable_usage_metrics=False,           # Enable usage metrics
    heartbeats_period_secs=1.0,           # Period between heartbeats
    interruption_strategies=[],           # List[BaseInterruptionStrategy]
    observers=[],                         # DEPRECATED: Use PipelineTask observers arg
    report_only_initial_ttfb=False,       # Report only first time-to-first-byte
    send_initial_empty_metrics=False,     # Send empty metrics on start
    start_metadata={}                     # Dict[str, Any] for metadata
)
```

#### Key Pipeline Parameters:
- **allow_interruptions**: If True, user can speak while bot is talking
- **audio_in_sample_rate**: Must match your STT service requirements
- **audio_out_sample_rate**: Must match your TTS service output
- **interruption_strategies**: Custom interruption behavior handlers

---

### 9. PipelineRunner Parameters

```python
PipelineRunner(
    handle_sigint=False  # Whether to handle SIGINT (Ctrl+C) signals
)
```

---

### 10. OpenAILLMContext Parameters

```python
OpenAILLMContext(
    messages,           # Required: List of message dicts with 'role' and 'content'
    tools=None,         # Optional: List of function calling tools
    tool_choice=None    # Optional: Control tool selection ("auto", "none", etc.)
)
```

#### Message Format:
```python
messages = [
    {"role": "system", "content": "System prompt"},
    {"role": "user", "content": "User message"},
    {"role": "assistant", "content": "Bot response"}
]
```

---

## EXAMPLE CONFIGURATIONS

### Minimal Voice Bot (Current Usage):
```python
transport = SmallWebRTCTransport(
    webrtc_connection=runner_args.webrtc_connection,
    params=TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer()
    )
)
```

### Advanced Voice Bot with Custom VAD:
```python
vad = SileroVADAnalyzer(
    sample_rate=16000,
    params=VADParams(
        confidence=0.8,      # Stricter voice detection
        start_secs=0.1,      # Quick response to speech
        stop_secs=1.0,       # Wait 1 sec before stopping
        min_volume=0.5       # Allow quieter speech
    )
)

transport = SmallWebRTCTransport(
    webrtc_connection=runner_args.webrtc_connection,
    params=TransportParams(
        audio_in_enabled=True,
        audio_in_sample_rate=16000,
        audio_in_passthrough=True,
        audio_out_enabled=True,
        audio_out_sample_rate=24000,
        vad_analyzer=vad
    )
)
```

### Emotional TTS with Speed Control:
```python
tts = CartesiaTTSService(
    api_key=os.getenv("CARTESIA_API_KEY"),
    voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",
    params=CartesiaTTSService.InputParams(
        language=Language.EN,
        generation_config=GenerationConfig(
            volume=1.2,        # 20% louder
            speed=1.1,         # 10% faster
            emotion="excited"  # Excited tone
        )
    )
)
```

### LLM with Custom Parameters:
```python
llm = GroqLLMService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-70b-versatile",
    temperature=0.9,           # More creative
    max_tokens=500,            # Limit response length
    top_p=0.95,                # Nucleus sampling
    frequency_penalty=0.3,     # Reduce repetition
    presence_penalty=0.2       # Encourage new topics
)
```

### Pipeline with Interruptions Disabled:
```python
task = PipelineTask(
    pipeline,
    params=PipelineParams(
        allow_interruptions=False,    # User cannot interrupt bot
        audio_in_sample_rate=16000,
        audio_out_sample_rate=24000,
        enable_metrics=True           # Track performance
    )
)
```

---

## PARAMETER VALIDATION RULES

### Sample Rates:
- SileroVAD: Only 8000 or 16000 Hz
- Common rates: 8000, 16000, 24000, 44100, 48000 Hz
- Input/output rates can differ (automatic resampling)

### Volume/Speed Ranges:
- Cartesia volume: 0.5 to 2.0
- Cartesia speed: 0.6 to 1.5
- VAD confidence: 0.0 to 1.0
- VAD min_volume: 0.0 to 1.0

### API Keys Required:
- GROQ_API_KEY: For GroqSTTService and GroqLLMService
- CARTESIA_API_KEY: For CartesiaTTSService
- DEEPGRAM_API_KEY: If using DeepgramSTTService (commented out)

---

## COMMON PATTERNS

### Enable Video Streaming:
```python
params = TransportParams(
    audio_in_enabled=True,
    audio_out_enabled=True,
    video_in_enabled=True,         # Add video input
    video_out_enabled=True,        # Add video output
    video_out_width=1280,
    video_out_height=720,
    video_out_framerate=30,
    vad_analyzer=SileroVADAnalyzer()
)
```

### Multiple Audio Destinations:
```python
params = TransportParams(
    audio_out_enabled=True,
    audio_out_destinations=["main", "recording", "monitor"],
    vad_analyzer=SileroVADAnalyzer()
)
```

### Custom Audio Processing:
```python
from pipecat.audio.filters.base_audio_filter import BaseAudioFilter

params = TransportParams(
    audio_in_enabled=True,
    audio_in_filter=MyCustomFilter(),  # Your filter implementation
    vad_analyzer=SileroVADAnalyzer()
)
```



OSI Layers, TCP IP Layers
Transport, application layers