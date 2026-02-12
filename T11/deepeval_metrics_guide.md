# DeepEval Metrics Guide (T11)

This guide explains how the three DeepEval metrics are computed in this project and how they are used in T11. It aligns with the DeepEval “Getting Started” flow and the current implementation in this workspace.

Official docs: https://deepeval.com/docs/getting-started

---

## 1) What we evaluate
For each conversation turn, we evaluate the assistant’s response using the menu as the ground-truth context.

Inputs used in each test case:
- **input**: the user’s transcript (customer speech)
- **actual_output**: the bot’s transcript (assistant speech)
- **context**: the menu lines (ground truth)
- **retrieval_context**: the same menu lines (ground truth)

In code, this is created using:
- `LLMTestCase(input=user_text, actual_output=bot_text, context=menu_context, retrieval_context=menu_context)`

---

## 2) Metrics used (3)
The evaluator uses exactly the same three metrics as the DeepEval example in EVALUATORS/brain_trust.py:

### A) HallucinationMetric
**Purpose:** Checks if the assistant invents items or prices that are not supported by the menu context.

**How it’s computed in this project:**
- The metric compares the response to the provided `context` and `retrieval_context` (menu lines).
- If the response introduces items/prices not grounded in the menu, the score decreases.
- A higher score means fewer hallucinations.

### B) FaithfulnessMetric
**Purpose:** Checks if the assistant’s statements are factually consistent with the menu context.

**How it’s computed in this project:**
- The metric validates that claims made by the assistant align with the menu context.
- If the assistant contradicts the menu (wrong prices, wrong item names), the score decreases.
- A higher score means more accurate, faithful responses.

### C) AnswerRelevancyMetric
**Purpose:** Checks if the assistant’s response is relevant to the user’s question or request.

**How it’s computed in this project:**
- The metric evaluates whether the response addresses the user’s input.
- If the response ignores the question or drifts off topic, the score decreases.
- A higher score means the response is more relevant.

---

## 4) G-eval Metric (Custom Criteria Evaluator)

### Purpose
G-eval is a flexible, LLM-based evaluation metric that can measure **custom criteria** defined by the user. Unlike fixed metrics that measure specific properties, G-eval allows you to define any evaluation criteria you want the LLM to judge against.

### How it's computed in this project
In T11, G-eval evaluates whether the assistant's response is properly grounded in the menu context:
- **Criteria**: "Determine if the assistant's response is grounded in the provided menu context and accurately reflects available items, prices, and options. Check that no unsupported items or incorrect information is presented."
- **Parameters used**: `ACTUAL_OUTPUT` (bot response) and `CONTEXT` (menu lines)
- The metric checks that the response aligns with the menu without introducing unsupported items or prices.
- A higher score means better grounding in the menu context.

### Configuration
- `GEval(name="Menu Grounding", criteria="...", evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.CONTEXT], threshold=0.5, model="gpt-4o", include_reason=True)`

---

## 5) Scoring and thresholds
In this project:
- Each metric returns a **score** in the range **0 to 1**.
- The evaluator sets a **threshold of 0.5** for all four metrics (including G-eval).
- `include_reason=True` is enabled, so each metric outputs a **reason** string explaining the score.

---

## 6) Where the metrics are configured
In T11, the metrics are initialized as follows:
- `HallucinationMetric(threshold=0.5, model="gpt-4o", include_reason=True)`
- `FaithfulnessMetric(threshold=0.5, model="gpt-4o", include_reason=True)`
- `AnswerRelevancyMetric(threshold=0.5, model="gpt-4o", include_reason=True)`
- `GEval(name="Menu Grounding", criteria="...", evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.CONTEXT], threshold=0.5, model="gpt-4o", include_reason=True)`

The reasons are stored into separate columns in the output CSV.

---

## 7) Output columns (CSV)
The evaluator writes a CSV with these columns:
- `turn_id`
- `customer_speech`
- `assistant_speech`
- `hallucination_score`, `hallucination_reason`
- `faithfulness_score`, `faithfulness_reason`
- `relevance_score`, `relevance_reason`
- `geval_score`, `geval_reason`

---

## 8) How to run the evaluator
From T11:
- Run: `python evaluator.py`
- It will auto-pick the most recent conversation log in Recordings/.
- It saves the CSV next to that log.

---

## 9) Notes
- These metrics are LLM-based evaluators, so results can vary slightly across runs.
- The menu context is the single source of truth for all grounding checks.
- G-eval provides a flexible, custom evaluation criteria that complements the fixed metrics.
- If you change the menu, re-run the evaluator to reflect the updates.
