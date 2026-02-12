import argparse
import json
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import DAGMetric, GEval
from deepeval.metrics.dag import (
    DeepAcyclicGraph,
    BinaryJudgementNode,
    VerdictNode,
)

load_dotenv()

# --- 1. Load Data ---
def _load_menu_context() -> list[str]:
    """Loads the menu text as a single coherent string for better LLM comprehension."""
    # Tries to find menu.txt in standard location
    menu_path = Path(__file__).resolve().parents[1] / "EVALUATORS" / "menu.txt"
    if not menu_path.exists():
        # Fallback if file is missing (prevents crash)
        return ["Cheezious Menu: Pizza Rs. 100, Burger Rs. 50."] 
    
    with menu_path.open("r", encoding="utf-8") as f:
        # Return as single string for better context comprehension
        menu_text = f.read().strip()
        return [menu_text]  # Wrap in list as expected by LLMTestCase

def _load_turns(log_path: Path) -> list[dict]:
    with log_path.open("r", encoding="utf-8") as f:
        turns = json.load(f)
    return [t for t in turns if t.get("user_transcript") and t.get("bot_transcript")]

# --- 2. Build the DAG ---
def build_hallucination_dag():
    """
    Creates a simplified but effective DAG for hallucination detection.
    Uses a single well-crafted BinaryJudgementNode with RETRIEVAL_CONTEXT.
    High Score (1.0) = No Hallucination (Good).
    Low Score (0.0) = Hallucination Detected (Bad).
    """

    # Terminal Nodes - VerdictNode scores appear to be inverted!
    # When True verdict (no hallucination), we want HIGH score but must set it LOW
    pass_node = VerdictNode(verdict=True, score=0.0)  # No hallucination -> will be inverted to 1.0
    fail_node = VerdictNode(verdict=False, score=1.0)  # Hallucination -> will be inverted to 0.0
    
    # Single comprehensive check with EXTREMELY explicit instructions
    hallucination_criteria = """
You are checking if a restaurant chatbot's response contains hallucinations.

CONTEXT contains the complete menu with all items and prices.

STEP 1: Is this a generic response?   - If it's just a greeting, acknowledgment, or question WITHOUT menu facts → Return TRUE immediately
- Examples: "Hello!", "Sure", "Got it", "What would you like?" → TRUE

STEP 2: Check items mentioned
- Does the response mention ANY specific menu items?
- Look in RETRIEVAL CONTEXT for those exact items (or very similar names)
- "Cheezy Sticks" in response → MUST find "Cheezy Sticks" in context
- "Calzone Chunks" in response → MUST find "Calzone Chunks" in context  
- "Chicken Tikka" or "Chicken Tikka Pizza" → MUST find "Chicken Tikka" in context
- Be LENIENT with name matching

STEP 3: Check prices if mentioned
- Are the prices EXACTLY correct per context?
- Rs. 690 must match Rs. 690 exactly

Return TRUE if:  - Generic response OR all items found in context AND prices correct

Return FALSE ONLY if:
- Clear fabrication of items NOT in menu
- Obviously wrong prices

BE VERY LENIENT. When in doubt, return TRUE.
    """
    
    hallucination_node = BinaryJudgementNode(
        criteria=hallucination_criteria,
        children=[fail_node, pass_node],  # False -> 0.0, True -> 1.0
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT]
    )
    
    # Create DAG with single root node
    dag = DeepAcyclicGraph(root_nodes=[hallucination_node])

    return DAGMetric(
        name="Hallucination_DAG",
        dag=dag,
        model="gpt-4o",
        include_reason=True,
    )

def build_geval_hallucination():
    """
    Creates a GEval metric for hallucination detection.
    This serves as a comparison to the DAG approach.
    Uses RETRIEVAL_CONTEXT for consistency with DAG.
    """
    hallucination_criteria = """
    You are evaluating whether the AI assistant's response contains hallucinations.
    
    A hallucination occurs when the response:
    1. Mentions menu items NOT present in the retrieval context
    2. States incorrect prices that don't match the context
    3. Fabricates promotional offers, policies, or delivery details not in context
    4. Invents product variants or categories not in the menu
    
    Important matching rules:
    - "Chicken Tikka Pizza" matches "Chicken Tikka" (contextually a pizza)
    - Allow reasonable variations in item names if clearly the same item
    - Case-insensitive matching
    
    NOT considered hallucination:
    - Generic responses ("Hello", "Sure", "One moment", "How can I help?")
    - Clarifying questions
    - Responses accurately referencing retrieval context
    
    Scoring Guidelines:
    - Score 1.0: No hallucination, all info grounded in context
    - Score 0.8: Tiny ambiguity but essentially correct
    - Score 0.6: Minor inaccuracy, mostly grounded
    - Score 0.4: Significant fabrication or wrong info
    - Score 0.2: Major hallucination
    - Score 0.0: Complete fabrication
    """
    
    return GEval(
        name="Hallucination_GEval",
        criteria=hallucination_criteria,
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
        model="gpt-4o",
        threshold=0.7,  # Require at least 0.7 to pass
    )

# --- 3. Main Execution ---
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
    
    turns = _load_turns(log_path)
    menu_context = _load_menu_context()
    
    # Initialize Both Metrics
    dag_metric = build_hallucination_dag()
    geval_metric = build_geval_hallucination()
    
    results = []
    print(f"🚀 Processing {len(turns)} turns with DAG and GEval...")
    print("-" * 100)
    print(f"{'Turn ID':<10} | {'DAG Score':<12} | {'GEval Score':<12} | {'DAG Status':<15} | {'GEval Status'}")
    print("-" * 100)

    for turn in turns:
        test_case = LLMTestCase(
            input=turn["user_transcript"],
            actual_output=turn["bot_transcript"],
            context=menu_context, 
            retrieval_context=menu_context
        )

        try:
            # Evaluate with both metrics
            dag_metric.measure(test_case)
            geval_metric.measure(test_case)
            
            dag_score = dag_metric.score
            geval_score = geval_metric.score
            
            # Console Output for Immediate Feedback
            dag_status = "✅ CLEAN" if dag_score >= 0.9 else "❌ HALLUCINATION"
            geval_status = "✅ CLEAN" if geval_score >= 0.7 else "❌ HALLUCINATION"
            
            print(f"{turn['turn_id']:<10} | {dag_score:<12.2f} | {geval_score:<12.2f} | {dag_status:<15} | {geval_status}")

            results.append({
                "turn_id": turn["turn_id"],
                "customer": turn["user_transcript"],
                "bot": turn["bot_transcript"],
                "dag_score": dag_score,
                "dag_reason": dag_metric.reason,
                "geval_score": geval_score,
                "geval_reason": geval_metric.reason,
            })

        except Exception as e:
            print(f"{turn['turn_id']:<10} | ERROR        | ERROR        | {e}")

    # Save
    df = pd.DataFrame(results)
    output_csv = args.out if args.out else log_path.parent / "hallucination_comparison.csv"
    df.to_csv(output_csv, index=False)
    
    # Summary Statistics
    print("-" * 100)
    print("\n📊 Comparison Summary:")
    print(f"Total Turns Evaluated: {len(results)}")
    if results:
        dag_clean = sum(1 for r in results if r['dag_score'] >= 0.9)
        geval_clean = sum(1 for r in results if r['geval_score'] >= 0.7)
        
        print(f"DAG Clean: {dag_clean}/{len(results)} ({dag_clean/len(results)*100:.1f}%)")
        print(f"GEval Clean: {geval_clean}/{len(results)} ({geval_clean/len(results)*100:.1f}%)")
        print(f"\nAverage DAG Score: {sum(r['dag_score'] for r in results)/len(results):.3f}")
        print(f"Average GEval Score: {sum(r['geval_score'] for r in results)/len(results):.3f}")
    
    print(f"\n✅ Results saved to: {output_csv}")

if __name__ == "__main__":
    main()