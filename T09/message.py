import asyncio
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

from dotenv import load_dotenv

# Load .env
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists(): 
    load_dotenv(env_file)
    print(f"✅ Loaded .env from {env_file}")

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from groq import AsyncGroq

from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.observers.base_observer import BaseObserver, FrameProcessed, FramePushed
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection, IceServer

from pipecat_flows import FlowManager
from pipecat_flows.types import NodeConfig


# =============================================================================
# CONFIG
# =============================================================================

HOST = "0.0.0.0"
PORT = 7860
ice_servers = [IceServer(urls="stun:stun.l.google.com:19302")]


# =============================================================================
# OBJECTION NODES
# =============================================================================

# respond_immediately=False prevents double LLM responses when transitioning
# while main LLM is still responding. The context updates but waits for next user input.
# Set to True if you want immediate objection handling (but may cause overlapping responses).
OBJECTION_NODES: Dict[str, NodeConfig] = {
    "price_too_high": {
        "name": "objection_price",
        "task_messages": [{"role": "system", "content": "User thinks price is too high. Acknowledge, emphasize value, ask about their budget."}],
        "respond_immediately": False,
    },
    "bad_timing": {
        "name": "objection_timing",
        "task_messages": [{"role": "system", "content": "User says timing isn't right. Acknowledge, explore better timing, offer follow-up."}],
        "respond_immediately": False,
    },
    "need_to_think": {
        "name": "objection_think",
        "task_messages": [{"role": "system", "content": "User wants to think. Acknowledge, ask what concerns remain, suggest follow-up."}],
        "respond_immediately": False,
    },
    "competitor_mention": {
        "name": "objection_competitor",
        "task_messages": [{"role": "system", "content": "User mentioned competitor. Acknowledge professionally, highlight your differentiators."}],
        "respond_immediately": False,
    },
    "not_interested": {
        "name": "objection_interest",
        "task_messages": [{"role": "system", "content": "User not interested. Respect, ask one clarifying question, leave door open."}],
        "respond_immediately": False,
    },
}

INITIAL_NODE: NodeConfig = {
    "name": "greeting",
    "task_messages": [{"role": "system", "content": "You are a friendly sales rep. Greet warmly and ask how you can help. Keep it brief."}],
}


# =============================================================================
# CLASSIFIER STATE
# =============================================================================

@dataclass
class ClassifierState:
    pending_node: Optional[NodeConfig] = None
    total_objections: int = 0
    history: List[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# =============================================================================
# ASYNC CLASSIFIER (runs separately from main pipeline)
# =============================================================================

class AsyncClassifier:
    """Classifies objections using a separate LLM call, doesn't block main pipeline."""

    SYSTEM_PROMPT = """You detect customer objections in sales conversations.

If you detect an objection, respond with ONLY the objection type from this list:
- price_too_high
- bad_timing
- need_to_think
- competitor_mention
- not_interested

If no objection, respond with: none

Only respond with one word - the type or "none"."""

    def __init__(self, state: ClassifierState):
        self._state = state
        self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def classify_only(self, text: str) -> Optional[str]:
        """Classify text and return objection type (or None). Doesn't apply transition."""
        try:
            logger.debug(f"🔍 Classifier analyzing: {text[:50]}...")

            response = await self._client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Customer said: {text}"}
                ],
                max_tokens=20,
                temperature=0,
            )

            result = response.choices[0].message.content.strip().lower()
            logger.debug(f"🔍 Classifier result: {result}")

            if result != "none" and result in OBJECTION_NODES:
                # Update stats
                async with self._state.lock:
                    self._state.total_objections += 1
                    self._state.history.append({
                        "type": result,
                        "text": text[:100],
                        "timestamp": datetime.now().isoformat(),
                    })
                return result

            return None

        except Exception as e:
            logger.error(f"Classifier error: {e}")
            return None


# =============================================================================
# CLASSIFIER OBSERVER (listens for transcriptions, queues transitions)
# =============================================================================

class ClassifierObserver(BaseObserver):
    """Observer that forwards transcriptions to classifier and handles transitions."""

    def __init__(self, classifier: AsyncClassifier):
        super().__init__()
        self._classifier = classifier
        self._llm_speaking = False
        self._pending_node: Optional[NodeConfig] = None

    def set_flow_manager(self, fm: FlowManager):
        """Set flow manager for applying transitions."""
        self._flow_manager = fm

    async def on_push_frame(self, data: FramePushed):
        """Called when a frame is pushed through the pipeline."""
        frame = data.frame
        frame_type = type(frame).__name__

        # Track LLM speaking state
        if frame_type == "LLMFullResponseStartFrame":
            self._llm_speaking = True
            logger.debug("🎤 LLM started speaking")

        elif frame_type == "LLMFullResponseEndFrame":
            self._llm_speaking = False
            logger.debug("🎤 LLM finished speaking")

            # Apply pending transition after LLM finishes
            if self._pending_node and hasattr(self, '_flow_manager'):
                node = self._pending_node
                self._pending_node = None
                logger.info(f"⏰ Applying queued transition → {node.get('name')}")
                await self._flow_manager.set_node_from_config(node)
                logger.success(f"✅ Now at: {self._flow_manager.current_node}")

        # Forward transcriptions to classifier
        elif frame_type == "TranscriptionFrame":
            text = getattr(frame, 'text', '')
            if text.strip():
                asyncio.create_task(self._classify_and_queue(text))

    async def _classify_and_queue(self, text: str):
        """Classify and queue transition (don't apply immediately)."""
        try:
            result = await self._classifier.classify_only(text)
            if result:
                logger.warning(f"🚨 OBJECTION: {result} - queuing transition")
                node = OBJECTION_NODES.get(result)
                if node:
                    if self._llm_speaking:
                        # Queue for later
                        self._pending_node = node
                        logger.info(f"⏸️ Transition queued (LLM speaking)")
                    elif hasattr(self, '_flow_manager'):
                        # Apply immediately
                        logger.info(f"⚡ Applying transition immediately")
                        await self._flow_manager.set_node_from_config(node)
                        logger.success(f"✅ Now at: {self._flow_manager.current_node}")
        except Exception as e:
            logger.error(f"Classification error: {e}")

    async def on_process_frame(self, data: FrameProcessed):
        """Not used - we use on_push_frame instead."""
        pass


# =============================================================================
# BOT RUNNER
# =============================================================================

async def bot(runner_args):
    """Run bot with parallel classifier."""
    logger.info("🤖 Starting bot with parallel classifier")
    
    connection = runner_args.webrtc_connection
    classifier_state = ClassifierState()

    try:
        # Services
        llm = GroqLLMService(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
        )

        stt = GroqSTTService(
            api_key=os.getenv("GROQ_API_KEY"),
            model="whisper-large-v3"
        )
        
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id=os.getenv("CARTESIA_VOICE"),
        )

        # Transport
        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            )
        )

        # Classifier (separate from main pipeline)
        classifier = AsyncClassifier(classifier_state)
        classifier_observer = ClassifierObserver(classifier)

        # Context and aggregators
        context = LLMContext(
            messages=[{"role": "system", "content": "You are a helpful sales assistant."}]
        )
        user_aggregator = LLMUserResponseAggregator()
        assistant_aggregator = LLMAssistantResponseAggregator()

        # Simple pipeline - no custom processors needed
        pipeline = Pipeline([
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            assistant_aggregator,
            transport.output(),
        ])

        task = PipelineTask(pipeline)

        # Add classifier observer to task
        task.add_observer(classifier_observer)

        # FlowManager
        flow_manager = FlowManager(
            task=task,
            llm=llm,
            context_aggregator=user_aggregator,
        )
        # Wire up observer with flow manager (not the classifier!)
        classifier_observer.set_flow_manager(flow_manager)

        @transport.event_handler("on_client_connected")
        async def on_connected(transport, client):
            logger.success("👤 Client connected!")
            await flow_manager.initialize(INITIAL_NODE)
            logger.info(f"🎯 Flow at: {flow_manager.current_node}")

        @transport.event_handler("on_client_disconnected")
        async def on_disconnected(transport, client):
            logger.info("👤 Client disconnected")
            logger.info(f"📊 Stats: {classifier_state.total_objections} objections")

        runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
        await runner.run(task)

    except Exception as e:
        logger.exception(f"Bot error: {e}")


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()

