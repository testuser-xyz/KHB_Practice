import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.runner.types import RunnerArguments
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport,
    TransportParams,
)
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter

from pipecat_flows import (
    FlowArgs,
    FlowManager,
    FlowsFunctionSchema,
    NodeConfig,
)

load_dotenv()

# -----------------------------
# Flow Nodes
# -----------------------------

def create_greeting_node() -> NodeConfig:
    return NodeConfig(
        name="greeting",
        role_messages=[
            {
                "role": "system",
                "content": (
                    "You are an inquisitive child. "
                    "Use very simple language. "
                    "Ask one short question. "
                    "Do not call any functions."
                ),
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Say hello and ask the user's favorite color.",
            }
        ],
        post_actions=[
            {
                "type": "tts_say",
                "text": "Hello world. What is your favorite color?",
            }
        ],
        next_node="collect_color",
    )


def create_collect_color_node() -> NodeConfig:
    record_favorite_color_func = FlowsFunctionSchema(
        name="record_favorite_color_func",
        description="Record the user's favorite color.",
        required=["color"],
        handler=record_favorite_color_and_end,
        properties={
            "color": {"type": "string"}
        },
    )

    return NodeConfig(
        name="collect_color",
        role_messages=[
            {
                "role": "system",
                "content": (
                    "The user will say their favorite color. "
                    "Extract the color and call record_favorite_color_func. "
                    "You must call the function."
                ),
            }
        ],
        functions=[record_favorite_color_func],
    )


def create_end_node() -> NodeConfig:
    return NodeConfig(
        name="end",
        task_messages=[
            {
                "role": "system",
                "content": "Thank the user and end the conversation.",
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )


# -----------------------------
# Function Handler
# -----------------------------

async def record_favorite_color_and_end(
    args: FlowArgs,
    flow_manager: FlowManager,
) -> tuple[str, NodeConfig]:
    color = args["color"]
    print(f"✅ Favorite color recorded: {color}")
    return color, create_end_node()


# -----------------------------
# Bot Setup
# -----------------------------

async def bot(runner_args: RunnerArguments):

    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3",
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant",
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE"),
        text_filters=[MarkdownTextFilter()],
    )

    context = LLMContext()
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
        ),
    )

    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        await flow_manager.initialize(create_greeting_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


# -----------------------------
# Entrypoint
# -----------------------------

if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
