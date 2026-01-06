import os
from dotenv import load_dotenv
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver as LatencyObserver
from pipecat.observers.loggers.debug_log_observer import DebugLogObserver
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
from pipecat.frames.frames import LLMRunFrame, StartInterruptionFrame, UserStoppedSpeakingFrame
import pytz
from datetime import datetime
from prompts import get_system_instruction, get_greeting_prompt
from audio_handlers import AudioBufferHandlers


load_dotenv()
async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabledd=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        )
    )

    stt = GroqSTTService(
                    api_key=os.getenv("GROQ_API_KEY"),
                    model="whisper-large-v3",
                    audio_passthrough=True #for audio buffering
                    )
    llm = GroqLLMService(
                    api_key=os.getenv("GROQ_API_KEY"),
                    model="llama-3.1-8b-instant"
                    )
    tts = CartesiaTTSService(
                    api_key=os.getenv("CARTESIA_API_KEY"),
                    voice_id=os.getenv("CARTESIA_VOICE")
                    )
    
    tz=pytz.timezone("Asia/Karachi")
    current_time=datetime.now(tz)
    day = current_time.strftime("%A")
    date =current_time.strftime("%Y-%m-%d")
    time = current_time.strftime("%I:%M %p")

    system_instruction = get_system_instruction(day, date, time)

    messages = [{"role": "system", "content": system_instruction}]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "audio_recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    audio_handlers = AudioBufferHandlers(audio_dir)


    audiobuffer = AudioBufferProcessor(
        sample_rate=None,
        num_channels=1,
        buffer_size=0,
        enable_turn_audio=False
    )

    audio_handlers.setup_handlers(audiobuffer)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        audiobuffer,
        context_aggregator.assistant()
    ])


    @transport.event_handler('on_client_connected')
    async def handle_client_connected(transport: SmallWebRTCTransport,  client):
        print("Client connected:")
        await audiobuffer.start_recording()
        if current_time.hour < 12:
            time_context = "It's morning time."
        elif 12 <= current_time.hour < 17:
            time_context = "It's afternoon."
        else:
            time_context = "It's evening."
        
        greeting_prompt = get_greeting_prompt(time_context)
        messages.append({"role": "system", "content": greeting_prompt})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler('on_client_disconnected')
    async def handle_client_disconnected(transport: SmallWebRTCTransport, client):
        print("Client disconnected:")
        await audiobuffer.stop_recording()
        await task.cancel()

    task = PipelineTask(
        pipeline=pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            observers=[
                LLMLogObserver(),
                TranscriptionLogObserver(),
                TurnTrackingObserver(),
                LatencyObserver(),
                DebugLogObserver(frame_types=[StartInterruptionFrame, UserStoppedSpeakingFrame])
            ]
        )
    )

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()