import os
#access env variables
from dotenv import load_dotenv
#loads env variables from .env
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
#pipecat services to support stt, llm, tts

from pipecat.pipeline.pipeline import Pipeline
#connect services in a pipeline
from pipecat.pipeline.runner import PipelineRunner
# executes the pipeline asynchronously
from pipecat.pipeline.task import PipelineParams, PipelineTask
#wraps pipeline into a task with params
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
#manages conversation history
from pipecat.audio.vad.silero import SileroVADAnalyzer
#voice activation detection, detects speech and silence
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
#handles real time audio streaming
from pipecat.transports.base_transport import TransportParams
#configurations 
from pipecat.runner.types import RunnerArguments
#contains webrtc connection details


load_dotenv()

async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,    #contains webrtc connection details
        params=TransportParams(
            audio_in_enabled=True,      #captures user microphone input
            audio_out_enabled=True,     #sends bot speech back to user
            vad_analyzer=SileroVADAnalyzer(),   
        )
    )

    # stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    stt = GroqSTTService(api_key=os.getenv("GROQ_API_KEY"), model="whisper-large-v3")
    llm = GroqLLMService(api_key=os.getenv("GROQ_API_KEY"), model="llama-3.1-8b-instant")
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22"
    )

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),  #add user message to context
        llm,
        tts,
        transport.output(),     #send bot speech back to user
        context_aggregator.assistant()
    ])

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()