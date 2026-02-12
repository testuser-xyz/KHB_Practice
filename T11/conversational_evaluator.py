import argparse
import json
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from deepeval.test_case import ConversationalTestCase, Turn
from deepeval.test_case.conversational_test_case import TurnParams
from deepeval.metrics import ConversationalDAGMetric, ConversationalGEval
from deepeval.metrics.conversational_dag import (
    ConversationalBinaryJudgementNode,
    ConversationalVerdictNode,
)
from deepeval.metrics.dag import DeepAcyclicGraph

load_dotenv()

# --- 1. Load Data ---
def _load_menu_context() -> list[str]:
    """Loads the menu text."""
    menu_path = Path(__file__).resolve().parents[1] / "EVALUATORS" / "menu.txt"
    if not menu_path.exists():
        return ["Cheezious Menu: Pizza Rs. 100, Burger Rs. 50."] 
    
    with menu_path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def _load_conversation(log_path: Path) -> list[dict]:
    """Loads the full conversation from the log file."""
    with log_path.open("r", encoding="utf-8") as f:
        turns = json.load(f)
    return [t for t in turns if t.get("user_transcript") and t.get("bot_transcript")]

# --- 2. Build Conversational DAG ---
def build_conversational_hallucination_dag():
    """
    Creates a Conversational DAG for hallucination detection.
    Evaluates the entire conversation with a single comprehensive judgment.
    """

    # Terminal Nodes
    pass_verdict = ConversationalVerdictNode(verdict=True, score=1.0)
    fail_verdict = ConversationalVerdictNode(verdict=False, score=0.0)
    
    # Single comprehensive conversational hallucination check
    conversational_hallucination_criteria = """
    You are evaluating an entire conversation for hallucinations.
    You will analyze the conversation turns  to check if the assistant (bot) hallucinates.
    The conversation context contains menu information that the bot should reference.
    
    Evaluate these aspects across the ENTIRE conversation:
    
    1. MENU GROUNDEDNESS: Are all menu items, prices, sizes mentioned by the bot accurate?
    2. CROSS-TURN CONSISTENCY: Does the bot provide consistent information across turns?
    3. CONVERSATION MEMORY: Does the bot accurately reference earlier conversation points?
    4. FABRICATION: Does the bot invent offers, policies, or conversation context?
    
    Return TRUE if ALL of these conditions are met:
    - Every menu item mentioned by assistant exists in menu context
    - All prices quoted by assistant are accurate
    - Bot maintains consistent information (no contradictions between turns)
    - Bot doesn't fabricate what customer said
    - No invented promotional offers or policies
    - Generic greetings/acknowledgments are acceptable
    
    Return FALSE if ANY of these occur:
    - Any bot turn mentions incorrect items/prices
    - Bot contradicts itself across turns (different prices for same item)
    - Bot hallucinates customer preferences or statements
    - Bot fabricates menu options or policies
    - Inconsistent availability claims across turns
    
    Note: Evaluate only the assistant's responses for hallucinations.
    """
    
    hallucination_node = ConversationalBinaryJudgementNode(
        criteria=conversational_hallucination_criteria,
        children=[fail_verdict, pass_verdict],  # False -> Hallucination, True -> Clean
        evaluation_params=[TurnParams.CONTENT]
    )
    
    # Create DAG with single root node
    dag = DeepAcyclicGraph(root_nodes=[hallucination_node])

    return ConversationalDAGMetric(
        name="Conversational_Hallucination_DAG",
        dag=dag,
        model="gpt-4o",
        include_reason=True,
    )

# --- 3. Build Conversational GEval ---
def build_conversational_geval_hallucination():
    """
    Creates a Conversational GEval metric for hallucination detection.
    Evaluates the entire conversation holistically.
    """
    hallucination_criteria = """
    You are evaluating whether the bot hallucinates across an entire conversation.
    
    Consider these aspects:
    
    1. MENU ACCURACY:
       - Does the bot mention only items/prices from the menu context?
       - Are all quoted prices correct throughout the conversation?
    
    2. INTERNAL CONSISTENCY:
       - Does the bot contradict itself across turns?
       - Are repeated queries answered consistently?
    
    3. CONVERSATION MEMORY:
       - Does the bot accurately reference earlier turns?
       - Does it fabricate customer statements/preferences?
    
    4. FABRICATION DETECTION:
       - Does the bot invent promotional offers?
       - Does it create non-existent menu options?
       - Does it fabricate policies or capabilities?
    
    Scoring Guidelines:
    - Score 1.0: Perfect - No hallucinations, fully grounded, internally consistent
    - Score 0.8: Minor - One small inaccuracy but generally reliable
    - Score 0.5: Moderate - Multiple inaccuracies or one significant hallucination
    - Score 0.2: Severe - Frequent hallucinations or critical misinformation
    - Score 0.0: Critical - Pervasive hallucinations throughout conversation
    
    Note: Generic greetings and small talk are not hallucinations.
    """
    
    return ConversationalGEval(
        name="Conversational_Hallucination_GEval",
        criteria=hallucination_criteria,
        evaluation_params=[TurnParams.CONTENT],
        model="gpt-4o",
        threshold=0.7,
    )

# --- 4. Main Execution ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    # Find Log File
    log_path = args.log
    if not log_path:
        recordings_dir = Path("Recordings")
        if not recordings_dir.exists():
            print("❌ 'Recordings' directory not found.")
            return
        json_files = sorted(recordings_dir.glob("**/conversation_metrics.json"), key=os.path.getmtime, reverse=True)
        if not json_files:
            print("❌ No conversation_metrics.json found.")
            return
        log_path = json_files[0]

    print(f"📂 Log File: {log_path}")
    
    turns_data = _load_conversation(log_path)
    menu_context = _load_menu_context()
    
    # Build Conversational Test Case using Turn objects
    # Each conversation turn has a user message and bot response
    conversation_turns = []
    for turn_data in turns_data:
        # Add user turn
        conversation_turns.append(
            Turn(
                role="user",
                content=turn_data["user_transcript"]
            )
        )
        # Add assistant turn
        conversation_turns.append(
            Turn(
                role="assistant",
                content=turn_data["bot_transcript"]
            )
        )
    
    conversational_test_case = ConversationalTestCase(
        turns=conversation_turns,
        context=menu_context
    )
    
    # Initialize Both Metrics
    dag_metric = build_conversational_hallucination_dag()
    geval_metric = build_conversational_geval_hallucination()
    
    print(f"🚀 Evaluating conversation with {len(turns_data)} turns using Conversational DAG and GEval...")
    print("-" * 80)
    
    results = {}
    
    try:
        # Evaluate with DAG
        print("📊 Running Conversational DAG...")
        dag_metric.measure(conversational_test_case)
        dag_score = dag_metric.score
        dag_reason = dag_metric.reason
        dag_status = "✅ CLEAN" if dag_score >= 0.9 else "❌ HALLUCINATION DETECTED"
        
        print(f"   DAG Score: {dag_score:.3f} - {dag_status}")
        
        # Evaluate with GEval
        print("📊 Running Conversational GEval...")
        geval_metric.measure(conversational_test_case)
        geval_score = geval_metric.score
        geval_reason = geval_metric.reason
        geval_status = "✅ CLEAN" if geval_score >= 0.7 else "❌ HALLUCINATION DETECTED"
        
        print(f"   GEval Score: {geval_score:.3f} - {geval_status}")
        
        results = {
            "conversation_id": log_path.stem,
            "total_turns": len(turns_data),
            "dag_score": dag_score,
            "dag_status": dag_status,
            "dag_reason": dag_reason,
            "geval_score": geval_score,
            "geval_status": geval_status,
            "geval_reason": geval_reason,
        }
        
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        results = {
            "conversation_id": log_path.stem,
            "total_turns": len(turns_data),
            "error": str(e)
        }
    
    # Save Results
    output_json = args.out if args.out else log_path.parent / "conversational_hallucination_scores.json"
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Also save as CSV for easy viewing
    df = pd.DataFrame([results])
    output_csv = output_json.with_suffix(".csv")
    df.to_csv(output_csv, index=False)
    
    print("-" * 80)
    print("\n📊 Evaluation Summary:")
    print(f"   Conversation: {results.get('conversation_id', 'N/A')}")
    print(f"   Total Turns: {results.get('total_turns', 0)}")
    dag_score = results.get('dag_score', 'N/A')
    geval_score = results.get('geval_score', 'N/A')
    dag_score_str = f"{dag_score:.3f}" if isinstance(dag_score, (int, float)) else dag_score
    geval_score_str = f"{geval_score:.3f}" if isinstance(geval_score, (int, float)) else geval_score
    print(f"   DAG Score: {dag_score_str} - {results.get('dag_status', 'N/A')}")
    print(f"   GEval Score: {geval_score_str} - {results.get('geval_status', 'N/A')}")
    print(f"\n✅ Results saved to:")
    print(f"   JSON: {output_json}")
    print(f"   CSV:  {output_csv}")

if __name__ == "__main__":
    main()
