import os
import wave
from datetime import datetime
from dotenv import load_dotenv
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
# from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
# # from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
# from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
# from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver as LatencyObserver
# from pipecat.observers.loggers.debug_log_observer import DebugLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import RunnerArguments

from prompts import get_system_instruction
from observers import LatencyObserver

load_dotenv()

async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        )
    )

    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3",
        audio_passthrough=True
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant"
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE"),
    )

    system_instruction = get_system_instruction()

    messages = [{"role": "system", "content": system_instruction}]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "Recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    # Create AudioBufferProcessor
    audiobuffer = AudioBufferProcessor(
        num_channels=1,
        buffer_size=0,
    )
    
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        audiobuffer,
        context_aggregator.assistant(),
    ])

    # Setup event handlers
    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        """Save audio when recording stops."""
        if len(audio) == 0:
            return
        
        os.makedirs("Recordings", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Recordings/audio_{timestamp}.wav"
        
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)
        
        print(f"✅ Audio saved: {filename}")

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Start recording when client connects."""
        await audiobuffer.start_recording()
        print("🎙️ Recording started")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Stop recording when client disconnects - this triggers on_audio_data."""
        await audiobuffer.stop_recording()
        print("🛑 Recording stopped")
    
    observer=LatencyObserver(filename=os.path.join(audio_dir, "conversation_metrics.json"))
    task = PipelineTask(
        pipeline=pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            observers=[observer],
        )
    )

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()