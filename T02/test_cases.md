## 1. CONVERSATION FLOW TEST CASES

### TC-CF-01: Greeting & Onboarding (Breakfast Time)
**Initial Condition**: 
- Time: 09:00 AM (Breakfast hours: 7:00 AM - 11:30 AM)
- Client connects to bot

**Test Steps**:
1. Connect WebRTC client
2. Wait for bot's automated greeting

**Expected Behavior**:
- Bot initiates conversation without user prompt
- Greeting mentions "breakfast" or "morning"
- Bot asks what customer would like to order
- Response is 2 sentences max
- Warm and friendly tone
- Console shows: `🎯 CLIENT CONNECTED` with timestamp

**Observer Validation**:
- `LLMLogObserver`: Logs system greeting prompt and LLM response
- `TurnTrackingObserver`: Shows bot turn initiated

---

### TC-CF-02: Greeting & Onboarding (Lunch Time)
**Initial Condition**: 
- Time: 02:00 PM (Lunch hours: 12:00 PM - 5:00 PM)
- Client connects to bot

**Test Steps**:
1. Connect WebRTC client
2. Wait for bot's automated greeting

**Expected Behavior**:
- Greeting mentions "lunch" or "afternoon"
- Bot asks what customer would like to order
- Response is 2 sentences max

**Observer Validation**:
- Same as TC-CF-01

---

### TC-CF-03: Greeting & Onboarding (Dinner Time)
**Initial Condition**: 
- Time: 07:00 PM (Dinner hours: After 5:00 PM)
- Client connects to bot

**Test Steps**:
1. Connect WebRTC client
2. Wait for bot's automated greeting

**Expected Behavior**:
- Greeting mentions "dinner" or "evening"
- Bot asks what customer would like to order
- Response is 2 sentences max

**Observer Validation**:
- Same as TC-CF-01

---

### TC-CF-04: Menu Browsing - Breakfast Time
**Initial Condition**: 
- Time: 10:00 AM
- Connection established, greeting completed

**User Input**: "What do you have?"

**Expected Behavior**:
- Bot suggests 2-3 breakfast items (Patty Burger, Fries, Nuggets)
- Does NOT list lunch/dinner items
- Does NOT recite entire menu
- Ends with a question: "What sounds good?"
- Response under 20 words preferred

**Observer Validation**:
- `TranscriptionLogObserver`: Logs "What do you have?"
- `LLMLogObserver`: Shows system prompt with breakfast time context
- `LatencyObserver`: Reports latency from user stop to bot start

---

### TC-CF-05: Menu Browsing - Lunch Time
**Initial Condition**: 
- Time: 01:00 PM
- Connection established, greeting completed

**User Input**: "Show me the menu"

**Expected Behavior**:
- Bot suggests 2-3 lunch items (pizzas, Zinger Burger, Fries)
- Does NOT offer breakfast items (Patty Burger)
- Does NOT offer dinner-only large pizzas
- Ends with a question

**Observer Validation**:
- Same as TC-CF-04

---

### TC-CF-06: Menu Browsing - Dinner Time
**Initial Condition**: 
- Time: 08:00 PM
- Connection established, greeting completed

**User Input**: "What can I order?"

**Expected Behavior**:
- Bot suggests 2-3 dinner items including pizzas with Large size option
- Does NOT offer breakfast-only items
- Ends with a question

**Observer Validation**:
- Same as TC-CF-04

---

### TC-CF-07: Menu Browsing - Full Menu Request
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: "Tell me everything on the menu" OR "Read the whole menu"

**Expected Behavior**:
- Bot lists complete menu for current time period
- Includes all items with sizes and prices
- Still keeps response reasonably concise
- Ends with "What would you like?"

**Observer Validation**:
- `LLMLogObserver`: Response includes all menu items from system prompt

---

### TC-CF-08: Placing an Order - Single Item
**Initial Condition**: 
- Time: 06:00 PM (Dinner)
- Connection established

**User Input**: "I want a Zinger Burger"

**Expected Behavior**:
- Bot confirms: "Zinger Burger"
- Bot suggests add-on: "Would you like fries with that?" or similar
- Does NOT finalize order yet
- Keeps conversation flowing

**Observer Validation**:
- `TranscriptionLogObserver`: Logs "I want a Zinger Burger"
- `TurnTrackingObserver`: Shows user turn → bot turn transition
- `LatencyObserver`: Reports response time

---

### TC-CF-09: Placing an Order - Pizza with Size Prompt (Lunch)
**Initial Condition**: 
- Time: 03:00 PM (Lunch)
- Connection established

**User Input**: "I'll have Chicken Tikka Pizza"

**Expected Behavior**:
- Bot asks for size: "Small or Medium?"
- Does NOT offer Large (not available at lunch)
- Waits for size confirmation

**Observer Validation**:
- `LLMLogObserver`: Shows bot asking for size clarification

---

### TC-CF-10: Placing an Order - Pizza with Size Prompt (Dinner)
**Initial Condition**: 
- Time: 07:00 PM (Dinner)
- Connection established

**User Input**: "Give me Chicken Fajita Pizza"

**Expected Behavior**:
- Bot asks for size: "Small, Medium, or Large?"
- Offers all three sizes (dinner time)
- Waits for size confirmation

**Observer Validation**:
- Same as TC-CF-09

---

### TC-CF-11: Placing an Order - Complete Pizza Order
**Initial Condition**: 
- Time: 06:30 PM (Dinner)
- Connection established

**User Input Sequence**:
1. "I want Chicken Tikka Pizza"
2. "Medium size"

**Expected Behavior**:
- After first input: Bot asks for size
- After second input: Bot confirms "Medium Chicken Tikka Pizza"
- Bot suggests add-ons or asks "Anything else?"
- Tracks order in conversation context

**Observer Validation**:
- `TurnTrackingObserver`: Shows alternating user/bot turns (2 user turns, 2 bot turns)
- `LLMContextAggregatorPair`: Maintains conversation history

---

### TC-CF-12: Placing an Order - Multiple Items
**Initial Condition**: 
- Time: 02:00 PM (Lunch)
- Connection established

**User Input Sequence**:
1. "I want a Zinger Burger"
2. "Yes, add large fries" (in response to suggestion)
3. "And 6 nuggets"

**Expected Behavior**:
- Bot confirms each item as added
- After suggestion response: confirms fries
- After nuggets: confirms and asks if anything else
- Keeps mental track of all items

**Observer Validation**:
- `LLMLogObserver`: Shows accumulated context with all items
- `TurnTrackingObserver`: Shows 3 user turns, 3 bot turns minimum

---

### TC-CF-13: Modifying Orders - Size Change
**Initial Condition**: 
- Time: 07:00 PM
- Order placed: Medium Chicken Tikka Pizza

**User Input**: "Actually, make that a large"

**Expected Behavior**:
- Bot confirms change: "I'll change that from medium to large"
- Repeats updated order: "So that's a Large Chicken Tikka Pizza now, right?"
- Waits for confirmation

**Observer Validation**:
- `LLMLogObserver`: Shows context update with modified order

---

### TC-CF-14: Modifying Orders - Item Replacement
**Initial Condition**: 
- Time: 01:00 PM
- Order placed: Zinger Burger

**User Input**: "No wait, I want a Chicken Fajita Pizza instead"

**Expected Behavior**:
- Bot acknowledges change
- Asks for pizza size (Small/Medium at lunch)
- Replaces Zinger Burger with pizza in context

**Observer Validation**:
- `LLMLogObserver`: Shows context with pizza replacing burger

---

### TC-CF-15: Modifying Orders - Item Removal
**Initial Condition**: 
- Time: 06:00 PM
- Order: Zinger Burger + Large Fries

**User Input**: "Remove the fries"

**Expected Behavior**:
- Bot confirms removal
- Repeats remaining order: "So just the Zinger Burger?"
- Asks if anything else needed

**Observer Validation**:
- `LLMLogObserver`: Context shows fries removed from order

---

### TC-CF-16: Price Inquiries - Single Item
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: "How much is a Zinger Burger?"

**Expected Behavior**:
- Bot clearly states: "400 rupees" or "400 Rs"
- May ask if customer wants to order it
- Short, direct response

**Observer Validation**:
- `TranscriptionLogObserver`: Logs price inquiry
- `LLMLogObserver`: Response contains correct price

---

### TC-CF-17: Price Inquiries - Pizza Sizes
**Initial Condition**: 
- Time: 08:00 PM (Dinner)
- Connection established

**User Input**: "What are the prices for Chicken Tikka Pizza?"

**Expected Behavior**:
- Bot lists all available sizes with prices:
  - Small 560 Rs
  - Medium 850 Rs  
  - Large 1200 Rs
- Asks which size customer prefers

**Observer Validation**:
- Response includes all three dinner sizes and prices

---

### TC-CF-18: Price Inquiries - Price Concern Response
**Initial Condition**: 
- Time: 02:00 PM
- User asked about Large pizza price

**User Input**: "That's too expensive"

**Expected Behavior**:
- Bot suggests alternative: smaller size or different item
- Example: "Would you prefer a Small pizza for 560 rupees?"
- Helpful and understanding tone

**Observer Validation**:
- `LLMLogObserver`: Shows bot offering alternatives

---

### TC-CF-19: Order Confirmation - Complete Order
**Initial Condition**: 
- Time: 07:00 PM
- Order placed: 1 Medium Chicken Tikka Pizza, 1 Large Fries

**User Input**: "That's all" OR "I'm done"

**Expected Behavior**:
- Bot repeats COMPLETE order with individual prices:
  - "1 Medium Chicken Tikka Pizza for 850 rupees"
  - "1 Large Fries for 250 rupees"
- Bot states total: "Total: 1100 rupees"
- Bot explicitly asks: "Should I confirm this order?"
- Does NOT finalize until explicit YES

**Observer Validation**:
- `LLMLogObserver`: Shows complete order summary in response

---

### TC-CF-20: Order Confirmation - Explicit YES Required
**Initial Condition**: 
- Time: Any
- Order summary presented, waiting for confirmation

**User Input**: "Yes" OR "Confirm" OR "Yes, please"

**Expected Behavior**:
- Bot confirms order acceptance
- Provides time estimate: "15-20 minutes"
- Thanks customer: "Thank you for choosing Cheezious!"
- Asks if anything else needed

**Observer Validation**:
- `LLMLogObserver`: Shows final confirmation message

---

### TC-CF-21: Order Confirmation - NO to Confirmation
**Initial Condition**: 
- Time: Any
- Order summary presented, waiting for confirmation

**User Input**: "No" OR "Wait" OR "Not yet"

**Expected Behavior**:
- Bot asks what customer wants to change
- Does NOT finalize order
- Allows modifications
- Remains helpful

**Observer Validation**:
- Order remains in pending state in context

---

### TC-CF-22: Unclear Input Handling - Inaudible Speech
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: [Garbled/unclear audio transcribed as gibberish or empty]

**Expected Behavior**:
- Bot responds: "Sorry, I didn't catch that. Could you repeat?"
- Polite and patient tone
- Waits for clearer input

**Observer Validation**:
- `TranscriptionLogObserver`: Shows unclear/empty transcription
- `LLMLogObserver`: Shows bot requesting clarification

---

### TC-CF-23: Unclear Input Handling - Confused Customer
**Initial Condition**: 
- Time: 02:00 PM
- User seems unsure (multiple unclear inputs)

**User Input**: "Um... I don't know..." OR "What should I get?"

**Expected Behavior**:
- Bot offers help: "Let me help! Would you like me to suggest our popular items?"
- Suggests 2-3 lunch items
- Guides customer gently

**Observer Validation**:
- `LLMLogObserver`: Shows bot taking initiative to guide

---

### TC-CF-24: Silent User Handling - Long Pause
**Initial Condition**: 
- Time: Any
- Bot asked a question, user silent for extended period

**User Input**: [Silence for 5-10 seconds]

**Expected Behavior**:
- VAD detects silence (stop_secs=0.2)
- Smart Turn analyzer determines turn completion
- Bot gently prompts: "Are you still there? Take your time, I'm here to help!"
- Patient and friendly

**Observer Validation**:
- `VADAnalyzer`: Detects silence via Silero
- `TurnTrackingObserver`: Shows turn completion without user speech
- Bot responds to silence appropriately

---

### TC-CF-25: Silent User Handling - Normal Thinking Pause
**Initial Condition**: 
- Time: Any
- User pauses briefly while speaking

**User Input**: "I want... [pause 1-2 seconds] ...a pizza"

**Expected Behavior**:
- VAD allows brief pause (stop_secs=0.2)
- Smart Turn V3 recognizes pause is within speech
- Bot waits for complete utterance
- Does NOT interrupt during natural pause

**Observer Validation**:
- `TranscriptionLogObserver`: Logs complete sentence "I want a pizza"
- Smart Turn correctly identifies speech continuation

---

### TC-CF-26: Order Completion - Full Workflow
**Initial Condition**: 
- Time: 06:00 PM
- Full order confirmed: 1 Zinger Burger, 1 Large Fries

**User Input**: "Yes" (to confirmation)

**Expected Behavior**:
- Bot confirms: "Great! Your order is confirmed."
- Provides time: "It'll be ready in 15-20 minutes."
- Thanks customer: "Thank you for choosing Cheezious!"
- Asks: "Anything else?"

**Observer Validation**:
- `LLMLogObserver`: Shows completion message
- Conversation context maintains confirmed order

---

### TC-CF-27: Order Completion - Additional Order After Completion
**Initial Condition**: 
- Time: Any
- Previous order completed

**User Input**: "Actually, add nuggets too"

**Expected Behavior**:
- Bot reopens order
- Adds nuggets to existing order
- Goes back to order confirmation flow
- Presents updated total

**Observer Validation**:
- Context shows updated order with nuggets added

---

## 2. AUDIO & VAD BEHAVIOR TEST CASES

### TC-VAD-01: Normal Speech with VAD Enabled
**Initial Condition**: 
- Connection established
- VAD enabled (Silero, stop_secs=0.2)

**User Input**: "I want a pizza" (clear, normal speech)

**Expected Behavior**:
- VAD detects speech start
- VAD detects speech end after 0.2s silence
- Complete utterance captured
- STT processes full sentence
- Bot responds appropriately

**Observer Validation**:
- `TranscriptionLogObserver`: Shows complete transcription
- `TurnTrackingObserver`: Shows clean user turn → bot turn
- `LatencyObserver`: Reports latency from user stop to bot start

---

### TC-VAD-02: Short Pauses Within Speech
**Initial Condition**: 
- Connection established
- User thinking while speaking

**User Input**: "I want... [0.5s pause] ...a large... [0.3s pause] ...pizza"

**Expected Behavior**:
- VAD uses stop_secs=0.2 but Smart Turn V3 analyzes context
- Smart Turn determines pauses are within-speech, not end-of-turn
- Full utterance captured: "I want a large pizza"
- Bot waits for complete thought

**Observer Validation**:
- `TranscriptionLogObserver`: Shows complete sentence with pauses handled
- Smart Turn correctly defers to user completion

---

### TC-VAD-03: Long Silence After Prompt
**Initial Condition**: 
- Bot asked: "What would you like to order?"
- User silent for 8+ seconds

**User Input**: [Complete silence]

**Expected Behavior**:
- VAD detects no speech
- After extended silence, Smart Turn signals turn completion
- Bot gently prompts: "Are you still there?"
- Does not spam prompts immediately

**Observer Validation**:
- `TurnTrackingObserver`: Shows bot turn initiated after silence timeout
- Bot proactive response logged

---

### TC-VAD-04: User Interrupting Bot Mid-Speech
**Initial Condition**: 
- Bot currently speaking (TTS active)
- PipelineParams allow_interruptions=True

**User Input**: User starts speaking while bot is talking

**Expected Behavior**:
- VAD detects new user speech
- Pipeline interrupts bot's TTS immediately
- Bot stops speaking
- User's speech is captured and processed
- Bot responds to user's interruption

**Observer Validation**:
- `TurnTrackingObserver`: Shows interrupted bot turn, new user turn
- `TranscriptionLogObserver`: Logs user's interrupting speech
- `LatencyObserver`: Shows latency for interrupted response

---

### TC-VAD-05: Continuous Speech Without Clear Pauses
**Initial Condition**: 
- User speaks rapidly without pauses

**User Input**: "I want a medium chicken tikka pizza and large fries and nuggets" (no pauses)

**Expected Behavior**:
- VAD captures entire continuous speech
- Smart Turn waits for natural end (0.2s+ silence)
- Complete sentence transcribed
- Bot processes full order request

**Observer Validation**:
- `TranscriptionLogObserver`: Shows complete long sentence
- No premature turn completion

---

### TC-VAD-06: Background Noise Handling
**Initial Condition**: 
- Connection established
- Background noise present

**User Input**: User speaks with background sounds (typing, music, etc.)

**Expected Behavior**:
- Silero VAD filters background noise
- Captures user speech accurately
- Does not trigger false turn starts from noise
- Clean transcription

**Observer Validation**:
- `TranscriptionLogObserver`: Shows only user speech, not noise artifacts
- VAD correctly identifies speech vs non-speech

---

## 3. SPECIAL LOGIC VALIDATION TEST CASES

### TC-SL-01: "Can You Hear Me?" - With Transcription
**Initial Condition**: 
- Connection established
- User has spoken before (transcription exists)

**User Input**: "Can you hear me?"

**Expected Behavior**:
- Bot responds confidently: "Yes, I can hear you!" or similar
- Does NOT mention text chat or technical limitations
- Clear and reassuring response
- Short response (under 15 words)

**Observer Validation**:
- `TranscriptionLogObserver`: Shows "Can you hear me?" transcription
- `LLMLogObserver`: Response is confident affirmative

---

### TC-SL-02: "Can You Hear Me?" - First Message
**Initial Condition**: 
- Connection just established
- This is user's first utterance

**User Input**: "Can you hear me?"

**Expected Behavior**:
- Bot responds confidently: "Yes, I can hear you perfectly!"
- Follows up with: "What would you like to order?"
- Does NOT act confused or technical

**Observer Validation**:
- `TranscriptionLogObserver`: Shows transcription exists
- Response is confident YES with follow-up

---

### TC-SL-03: Breakfast Items Not Offered at Lunch
**Initial Condition**: 
- Time: 01:00 PM (Lunch)
- User asks about menu

**User Input**: "What do you have?"

**Expected Behavior**:
- Bot suggests lunch items ONLY
- Does NOT mention Patty Burger (breakfast-only)
- Suggests: pizzas, Zinger Burger, Fries, Nuggets

**Observer Validation**:
- `LLMLogObserver`: Response does not contain "Patty Burger"
- Only lunch-appropriate items mentioned

---

### TC-SL-04: Breakfast Items Not Offered at Dinner
**Initial Condition**: 
- Time: 08:00 PM (Dinner)
- User asks about menu

**User Input**: "Show me what you have"

**Expected Behavior**:
- Bot suggests dinner items ONLY
- Does NOT mention Patty Burger
- Includes Large pizza sizes

**Observer Validation**:
- Response excludes breakfast-only items
- Includes dinner-specific options (Large pizzas)

---

### TC-SL-05: Lunch-Only Size Restrictions
**Initial Condition**: 
- Time: 02:00 PM (Lunch)
- User ordering pizza

**User Input**: "I want a large Chicken Tikka Pizza"

**Expected Behavior**:
- Bot clarifies: Large not available at lunch
- Offers: "We have Small or Medium available right now"
- Guides to valid options
- Polite correction

**Observer Validation**:
- `LLMLogObserver`: Response mentions size unavailability
- Suggests valid lunch sizes

---

### TC-SL-06: Dinner Large Size Available
**Initial Condition**: 
- Time: 07:00 PM (Dinner)
- User ordering pizza

**User Input**: "Give me a large Chicken Fajita Pizza"

**Expected Behavior**:
- Bot confirms: "Large Chicken Fajita Pizza"
- Provides price: "1400 rupees"
- Asks about additions
- No size restriction

**Observer Validation**:
- Order accepted without size correction
- Large size confirmed in context

---

### TC-SL-07: Full Menu Not Read Unless Requested
**Initial Condition**: 
- Time: 03:00 PM
- User asks general question

**User Input**: "What's available?"

**Expected Behavior**:
- Bot suggests 2-3 popular items
- Does NOT list entire menu with all prices
- Keeps response concise
- Invites specific questions

**Observer Validation**:
- Response under ~50 words
- Only highlights, not full list

---

### TC-SL-08: Full Menu Read When Explicitly Requested
**Initial Condition**: 
- Time: 02:00 PM
- User explicitly requests full menu

**User Input**: "Tell me all the items and prices"

**Expected Behavior**:
- Bot lists complete lunch menu
- Includes all items with sizes and prices
- Organized by category
- Ends with question

**Observer Validation**:
- `LLMLogObserver`: Response contains all menu items from system prompt

---

### TC-SL-09: Follow-Up Question Always Asked
**Initial Condition**: 
- Time: Any
- Bot responds to any user query

**User Input**: Any valid question/order

**Expected Behavior**:
- Every bot response ends with a question
- Examples:
  - "What sounds good?"
  - "Anything else?"
  - "What size would you like?"
  - "Should I confirm this?"
- Keeps conversation flowing

**Observer Validation**:
- `LLMLogObserver`: Every assistant response ends with "?"
- Conversation remains interactive

---

### TC-SL-10: Response Brevity - Voice Optimized
**Initial Condition**: 
- Time: Any
- Normal conversation flow

**User Input**: Any standard query (not complex order)

**Expected Behavior**:
- Responses stay under 20 words when possible
- Uses contractions (I'll, you're, it's)
- Avoids lengthy explanations
- Conversational, not formal

**Observer Validation**:
- `LLMLogObserver`: Typical responses are 1-3 sentences
- Natural speech patterns evident

---

### TC-SL-11: Time-Aware Greetings
**Initial Condition**: 
- Time: 09:00 AM
- Client connects

**Expected Behavior**:
- Greeting mentions "breakfast" or "morning"

**User Input**: N/A (automated greeting)

**Observer Validation**:
- Console shows time context: "It's breakfast time"
- Greeting aligned with time of day

---

### TC-SL-12: Time Context in System Messages
**Initial Condition**: 
- Time: 02:00 PM (Lunch)
- Connection established

**User Input**: Any menu request

**Expected Behavior**:
- System prompt includes current day, date, time
- Bot uses this context appropriately
- Time-appropriate menu items offered

**Observer Validation**:
- `LLMLogObserver`: System message shows:
  - Day (e.g., "Wednesday")
  - Date (e.g., "2026-01-01")
  - Time (e.g., "02:00 PM")

---

## 4. OBSERVER & LOGGING VERIFICATION TEST CASES

### TC-OBS-01: TranscriptionLogObserver - User Speech Logging
**Initial Condition**: 
- Connection established
- TranscriptionLogObserver active

**User Input**: "I want a Zinger Burger"

**Expected Console Output**:
```
[TranscriptionLogObserver] User: "I want a Zinger Burger"
```
or similar format showing STT output

**Validation**:
- Console displays user's transcribed speech
- Timestamp included
- Clear attribution to user

---

### TC-OBS-02: LLMLogObserver - Request/Response Lifecycle
**Initial Condition**: 
- Connection established
- LLMLogObserver active

**User Input**: Any valid input

**Expected Console Output**:
- LLM request logged (prompt sent to Groq)
- System message visible
- User message visible
- Assistant response logged
- Token counts (if available)

**Validation**:
- Complete LLM interaction visible
- Prompt structure clear
- Response captured

---

### TC-OBS-03: LLMLogObserver - Context Accumulation
**Initial Condition**: 
- Connection established
- Multiple conversation turns completed

**User Input Sequence**:
1. "I want pizza"
2. "Medium size"
3. "Add fries"

**Expected Console Output**:
- LLM log shows accumulated context
- All previous user/assistant messages present
- Context grows with each turn
- System message persists

**Validation**:
- `LLMContextAggregatorPair` correctly maintains history
- Each LLM call includes full conversation context

---

### TC-OBS-04: TurnTrackingObserver - User Turn Start
**Initial Condition**: 
- Connection established
- User begins speaking

**User Input**: User starts speaking

**Expected Console Output**:
```
[TurnTrackingObserver] User turn started
```
or similar

**Validation**:
- User turn logged when VAD detects speech
- Timestamp included

---

### TC-OBS-05: TurnTrackingObserver - User Turn End
**Initial Condition**: 
- User speaking
- User finishes utterance

**User Input**: User completes sentence and pauses

**Expected Console Output**:
```
[TurnTrackingObserver] User turn ended
```

**Validation**:
- Turn end logged when Smart Turn detects completion
- Duration may be included

---

### TC-OBS-06: TurnTrackingObserver - Bot Turn Sequence
**Initial Condition**: 
- User turn completed
- Bot generating response

**Expected Console Output**:
```
[TurnTrackingObserver] Bot turn started
[TurnTrackingObserver] Bot turn ended
```

**Validation**:
- Bot turn lifecycle tracked
- Clear alternation: User → Bot → User → Bot

---

### TC-OBS-07: TurnTrackingObserver - Interruption Handling
**Initial Condition**: 
- Bot speaking (bot turn active)
- User interrupts

**User Input**: User speaks during bot turn

**Expected Console Output**:
```
[TurnTrackingObserver] Bot turn interrupted
[TurnTrackingObserver] User turn started
```

**Validation**:
- Interruption logged
- Turn switches from bot to user
- allow_interruptions=True enables this

---

### TC-OBS-08: LatencyObserver - Response Time Measurement
**Initial Condition**: 
- Connection established
- Normal conversation

**User Input**: "What's the price of fries?"

**Expected Console Output**:
```
[LatencyObserver] Latency: XXX ms (User stop → Bot start)
```

**Validation**:
- Latency measured from user speech end to bot speech start
- Includes STT, LLM, TTS processing time
- Reported in milliseconds

---

### TC-OBS-09: LatencyObserver - Varying Latencies
**Initial Condition**: 
- Multiple turns completed

**User Input**: Various queries

**Expected Console Output**:
- Multiple latency measurements
- Each user→bot turn has latency logged

**Validation**:
- Latency tracked for every user input
- Performance trends visible
- Typical range: 500-3000ms depending on complexity

---

### TC-OBS-10: Client Connection Event Logging
**Initial Condition**: 
- WebRTC client connects

**Expected Console Output**:
```
================================================================================
🎯 CLIENT CONNECTED | Time: 02:00 PM | Wednesday, 2026-01-01
================================================================================
🤖 Starting conversation with greeting...
```

**Validation**:
- Connection event logged with visual separator
- Timestamp accurate
- Day and date displayed
- Greeting initiation noted

---

### TC-OBS-11: Client Disconnection Event Logging
**Initial Condition**: 
- Client connected
- Client disconnects (closes browser, network drop)

**Expected Console Output**:
```
================================================================================
👋 CLIENT DISCONNECTED
================================================================================
```

**Validation**:
- Disconnection logged
- Task cancellation triggered
- Clean shutdown

---

### TC-OBS-12: All Observers Running Simultaneously
**Initial Condition**: 
- All 4 observers active:
  - LLMLogObserver
  - TranscriptionLogObserver
  - TurnTrackingObserver
  - LatencyObserver

**User Input**: "I want a medium pizza"

**Expected Console Output**:
- Transcription log: User speech
- Turn tracking: User turn start/end
- LLM log: Prompt and response
- Turn tracking: Bot turn start/end
- Latency: Response time measurement

**Validation**:
- No observer conflicts
- All logs interleaved correctly
- Complete observability of pipeline

---

## 5. EDGE CASE SCENARIOS TEST CASES

### TC-EDGE-01: Unavailable Item - Direct Request
**Initial Condition**: 
- Time: 02:00 PM (Lunch)
- Connection established

**User Input**: "I want biryani"

**Expected Behavior**:
- Bot politely explains item not available
- Suggests similar alternatives from lunch menu
- Example: "We don't have biryani, but our Chicken Tikka Pizza is very popular!"
- Keeps conversation positive

**Observer Validation**:
- `LLMLogObserver`: Shows bot suggesting alternatives

---

### TC-EDGE-02: Unavailable Item - Breakfast Item at Dinner
**Initial Condition**: 
- Time: 08:00 PM (Dinner)
- Connection established

**User Input**: "I'll have a Patty Burger"

**Expected Behavior**:
- Bot explains: "Patty Burger is available during breakfast hours"
- Suggests dinner alternatives: "How about a Zinger Burger?"
- Helpful and clear

**Observer Validation**:
- Response mentions time restriction
- Alternative suggested

---

### TC-EDGE-03: Delivery Inquiry
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: "Do you deliver?" OR "Can I get delivery?"

**Expected Behavior**:
- Bot responds: "We focus on takeout orders. Would you like to place one?"
- Clear about delivery policy
- Redirects to takeout
- Polite tone

**Observer Validation**:
- `LLMLogObserver`: Response mentions "takeout"

---

### TC-EDGE-04: Cancelling Order - Mid-Conversation
**Initial Condition**: 
- Time: Any
- Order in progress: Zinger Burger added

**User Input**: "Cancel that" OR "Never mind" OR "I don't want it"

**Expected Behavior**:
- Bot confirms cancellation: "No problem! Let me know if you change your mind."
- Clears current order from context
- Remains friendly and helpful
- Asks if customer wants to order something else

**Observer Validation**:
- `LLMLogObserver`: Context shows order cleared

---

### TC-EDGE-05: Cancelling Order - After Full Order Placed
**Initial Condition**: 
- Time: Any
- Complete order presented for confirmation

**User Input**: "Actually, cancel everything"

**Expected Behavior**:
- Bot acknowledges: "Sure, I've cancelled your order."
- Asks: "Would you like to start a new order?"
- Context reset

**Observer Validation**:
- Order removed from conversation context

---

### TC-EDGE-06: Repeating Same Item Multiple Times
**Initial Condition**: 
- Time: 06:00 PM
- Connection established

**User Input Sequence**:
1. "I want a Zinger Burger"
2. "Add another Zinger Burger"
3. "One more Zinger Burger"

**Expected Behavior**:
- Bot tracks quantity: "So that's 3 Zinger Burgers"
- Confirms total: "3 Zinger Burgers at 400 each = 1200 rupees"
- Handles multiples correctly

**Observer Validation**:
- `LLMLogObserver`: Context shows quantity tracking

---

### TC-EDGE-07: Correcting Same Item Repeatedly
**Initial Condition**: 
- Time: 07:00 PM
- Order started

**User Input Sequence**:
1. "Medium Chicken Tikka Pizza"
2. "No, make it large"
3. "Wait, actually medium is fine"
4. "You know what, large after all"

**Expected Behavior**:
- Bot patiently confirms each change
- Final order: Large Chicken Tikka Pizza
- Remains helpful despite multiple changes
- Confirms final decision

**Observer Validation**:
- Context shows final state: Large pizza
- No frustration in bot tone

---

### TC-EDGE-08: Abrupt Client Disconnect - During Order
**Initial Condition**: 
- Time: Any
- Order in progress: Items being added
- Client connection drops unexpectedly

**Expected Behavior**:
- `on_client_disconnected` event fires
- Console logs: "👋 CLIENT DISCONNECTED"
- Task cancelled: `await task.cancel()`
- Resources cleaned up
- No crash or hanging

**Observer Validation**:
- Disconnection logged
- No error messages
- Graceful shutdown

---

### TC-EDGE-09: Abrupt Client Disconnect - During Bot Speech
**Initial Condition**: 
- Bot actively speaking (TTS playing)
- Client disconnects mid-sentence

**Expected Behavior**:
- TTS stops immediately
- Disconnect event handled
- Task cancelled
- No resource leaks

**Observer Validation**:
- Clean shutdown despite mid-speech disconnect

---

### TC-EDGE-10: Multiple Questions in One Utterance
**Initial Condition**: 
- Time: 02:00 PM
- Connection established

**User Input**: "What's the price of a Zinger Burger and how long will it take?"

**Expected Behavior**:
- Bot answers both questions:
  - "Zinger Burger is 400 rupees"
  - "It'll be ready in 15-20 minutes"
- Asks if customer wants to order it

**Observer Validation**:
- `LLMLogObserver`: Response addresses both questions

---

### TC-EDGE-11: Ambiguous Size Reference
**Initial Condition**: 
- Time: 07:00 PM
- No previous context

**User Input**: "I want a large" (no item specified)

**Expected Behavior**:
- Bot asks for clarification: "Large what? Pizza or fries?"
- Doesn't assume
- Helps narrow down choice

**Observer Validation**:
- Bot requests missing information

---

### TC-EDGE-12: Out of Context Time Reference
**Initial Condition**: 
- Time: 09:00 AM (Breakfast)
- User asks about dinner

**User Input**: "What pizzas do you have for dinner?"

**Expected Behavior**:
- Bot acknowledges: "For dinner, we have..."
- Lists dinner pizza options with sizes
- May mention: "Right now we're serving breakfast if you'd like to order"
- Helpful with future menu info

**Observer Validation**:
- Responds to dinner query even during breakfast

---

### TC-EDGE-13: Payment/Money Inquiry
**Initial Condition**: 
- Time: Any
- Order confirmed

**User Input**: "How do I pay?" OR "Cash or card?"

**Expected Behavior**:
- Bot provides payment info (based on restaurant policy)
- Likely: "You can pay when you pick up your order"
- Clear about payment process

**Observer Validation**:
- Reasonable response about payment

---

### TC-EDGE-14: Location/Directions Inquiry
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: "Where are you located?" OR "What's your address?"

**Expected Behavior**:
- Bot responds: "We're Cheezious Restaurant in Lahore, Pakistan"
- May suggest: "Would you like to place an order for pickup?"
- Redirects to ordering

**Observer Validation**:
- Location info provided
- Returns to order flow

---

### TC-EDGE-15: Completely Off-Topic Query
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: "What's the weather today?" OR "Tell me a joke"

**Expected Behavior**:
- Bot politely redirects: "I'm here to help with your Cheezious order!"
- Offers menu suggestions
- Stays on task
- Professional boundary

**Observer Validation**:
- Bot maintains focus on restaurant ordering

---

### TC-EDGE-16: Very Long Order (5+ items)
**Initial Condition**: 
- Time: 07:00 PM
- Connection established

**User Input**: Sequential additions totaling 5+ items

**Expected Behavior**:
- Bot tracks all items correctly
- Confirmation lists all items with prices
- Calculates total accurately
- May suggest: "That's quite a feast!" (friendly comment)
- Handles large context

**Observer Validation**:
- `LLMLogObserver`: Context contains all items
- Math correct in total

---

### TC-EDGE-17: Rapid-Fire Orders (Speed Test)
**Initial Condition**: 
- Time: Any
- Connection established

**User Input**: Very fast sequential orders without waiting for full bot response

**Expected Behavior**:
- Pipeline queues inputs appropriately
- allow_interruptions=True allows this
- Bot processes all inputs
- May confirm accumulated changes
- No lost inputs

**Observer Validation**:
- `TurnTrackingObserver`: Shows rapid turn alternation
- All user inputs captured in transcription logs

---

### TC-EDGE-18: Silence After Confirmation Request
**Initial Condition**: 
- Bot asked: "Should I confirm this order?"
- User silent for 10+ seconds

**User Input**: [Extended silence]

**Expected Behavior**:
- Bot prompts: "Are you still there?" or "Should I confirm the order?"
- Waits patiently
- Doesn't auto-confirm without explicit YES

**Observer Validation**:
- Order remains unconfirmed
- Bot sends reminder prompt

---

### TC-EDGE-19: Network Latency Simulation
**Initial Condition**: 
- Simulated high network latency (500ms+ delay)
- User places order

**Expected Behavior**:
- Pipeline handles delays gracefully
- Transcription may be slower
- Bot response delayed but complete
- No data loss
- `LatencyObserver` shows increased times

**Observer Validation**:
- Higher latency values logged
- System remains stable

---

### TC-EDGE-20: Empty/Null Transcription
**Initial Condition**: 
- User speaks but STT returns empty string
- Technical STT failure

**User Input**: [Speech occurs but transcription fails]

**Expected Behavior**:
- Bot handles gracefully: "I didn't catch that, could you repeat?"
- Doesn't crash
- Waits for valid input

**Observer Validation**:
- `TranscriptionLogObserver`: Shows empty or null transcription
- Bot error handling works

---

## TEST EXECUTION NOTES

### Manual Testing Checklist
For each test case:
1. ✅ Set system time to required test time (or modify bot code temporarily)
2. ✅ Start bot: `python bot2.py` (or via Pipecat runner)
3. ✅ Connect WebRTC client
4. ✅ Speak test input clearly
5. ✅ Observe console output for observer logs
6. ✅ Verify bot response matches expected behavior
7. ✅ Check conversation context is maintained

### Console Output Verification
Expected log types during testing:
- `🎯 CLIENT CONNECTED` - Connection events
- `[TranscriptionLogObserver]` - User speech transcriptions
- `[LLMLogObserver]` - LLM requests/responses
- `[TurnTrackingObserver]` - Turn management
- `[LatencyObserver]` - Response latencies
- `👋 CLIENT DISCONNECTED` - Disconnection events

### Test Environment Requirements
- ✅ Valid GROQ_API_KEY in .env
- ✅ Valid CARTESIA_API_KEY in .env
- ✅ WebRTC client (browser or test harness)
- ✅ Microphone access enabled
- ✅ Speaker/headphones for bot audio
- ✅ Stable internet connection
- ✅ Python environment with all dependencies

### Automated Testing Considerations
To convert to automated tests:
1. Mock WebRTC transport with test audio inputs
2. Mock STT service to return predefined transcriptions
3. Mock TTS service to verify output text
4. Capture LLM context to verify state
5. Assert observer logs contain expected patterns
6. Use test time injection for time-based logic

### Test Coverage Summary
- **Total Test Cases**: 87
- **Conversation Flow**: 27 test cases
- **Audio & VAD**: 6 test cases
- **Special Logic**: 12 test cases
- **Observers**: 12 test cases
- **Edge Cases**: 20 test cases
- **Additional Validation**: 10 test cases

### Risk Areas Requiring Extra Attention
1. **Time-based menu switching** (breakfast/lunch/dinner boundaries)
2. **Order confirmation** (explicit YES requirement)
3. **Interruption handling** (allow_interruptions=True)
4. **VAD tuning** (stop_secs=0.2 balance)
5. **Context accumulation** (long conversations)
6. **Network resilience** (disconnect mid-order)

---

## ADDITIONAL VALIDATION TEST CASES

### TC-VALID-01: System Prompt Integrity
**Test**: Verify system prompt is correctly injected

**Validation**:
- `LLMLogObserver` shows system message at start
- Contains current day, date, time
- Contains full menu
- Contains all use cases
- Contains personality instructions

---

### TC-VALID-02: Menu Price Accuracy
**Test**: Verify all prices match system prompt

**Items to Validate**:
- Patty Burger: 250 Rs ✓
- Fries Small: 150 Rs ✓
- Fries Large: 250 Rs ✓
- Nuggets: 450 Rs ✓
- Chicken Tikka Pizza Small: 560 Rs ✓
- Chicken Tikka Pizza Medium: 850 Rs ✓
- Chicken Tikka Pizza Large: 1200 Rs ✓
- Chicken Fajita Pizza Small: 600 Rs ✓
- Chicken Fajita Pizza Medium: 900 Rs ✓
- Chicken Fajita Pizza Large: 1400 Rs ✓
- Zinger Burger: 400 Rs ✓

**Validation**: Bot quotes correct prices in responses

---

### TC-VALID-03: Timezone Handling
**Test**: Verify Asia/Karachi timezone used

**Validation**:
- System uses `pytz.timezone('Asia/Karachi')`
- Time in system prompt matches PKT
- Console logs show correct timezone

---

### TC-VALID-04: Pipeline Component Order
**Test**: Verify pipeline order is correct

**Expected Order**:
1. transport.input() - Audio in
2. stt - Speech to text
3. context_aggregator.user() - Add user message
4. llm - Generate response
5. tts - Text to speech
6. transport.output() - Audio out
7. context_aggregator.assistant() - Add bot message

**Validation**: Pipeline processes in exact order

---

### TC-VALID-05: Service Configuration
**Test**: Verify all services configured correctly

**Services**:
- STT: GroqSTTService with whisper-large-v3 ✓
- LLM: GroqLLMService with llama-3.1-8b-instant ✓
- TTS: CartesiaTTSService with voice_id ✓
- VAD: SileroVADAnalyzer with stop_secs=0.2 ✓
- Turn: LocalSmartTurnAnalyzerV3 ✓

**Validation**: Each service initialized with correct parameters

---

### TC-VALID-06: Transport Parameters
**Test**: Verify transport configuration

**Expected**:
- audio_in_enabled: True ✓
- audio_out_enabled: True ✓
- vad_analyzer: SileroVADAnalyzer ✓
- turn_analyzer: LocalSmartTurnAnalyzerV3 ✓

**Validation**: Transport params set correctly

---

### TC-VALID-07: Task Parameters
**Test**: Verify PipelineTask params

**Expected**:
- allow_interruptions: True ✓
- observers: [LLMLogObserver, TranscriptionLogObserver, TurnTrackingObserver, LatencyObserver] ✓

**Validation**: Task configured for interruptions and full observability

---

### TC-VALID-08: Context Aggregation
**Test**: Verify context aggregator maintains state

**Validation**:
- LLMContext initialized with system message
- LLMContextAggregatorPair wraps context
- user() aggregator adds user messages
- assistant() aggregator adds bot messages
- Context persists across turns

---

### TC-VALID-09: Event Handler Registration
**Test**: Verify event handlers attached

**Expected Handlers**:
- on_client_connected ✓
- on_client_disconnected ✓

**Validation**:
- Handlers use @transport.event_handler decorator
- Async functions
- Properly handle transport and client parameters

---

### TC-VALID-10: Greeting Automation
**Test**: Verify automated greeting on connect

**Validation**:
- `on_client_connected` appends greeting prompt to messages
- LLMRunFrame queued: `await task.queue_frames([LLMRunFrame()])`
- Bot speaks first without user input
- Time-aware greeting context injected

---

## TEST METRICS TO TRACK

### Performance Metrics
- Average latency (user stop → bot start): Target < 2000ms
- Turn-taking accuracy: > 95% correct turn detection
- Transcription accuracy: > 90% word accuracy
- Interruption success rate: 100% interruptions handled

### Functional Metrics
- Order accuracy: 100% items tracked correctly
- Price accuracy: 100% correct prices quoted
- Menu filtering: 100% time-appropriate items
- Confirmation requirement: 100% explicit YES enforcement

### Quality Metrics
- Response brevity: > 80% responses under 20 words (simple queries)
- Follow-up questions: 100% responses end with question
- Natural language: Human-like conversation flow
- Error recovery: Graceful handling of unclear input

---

## CONCLUSION

This comprehensive test suite covers:
- ✅ All use cases defined in system prompt
- ✅ Audio/VAD/turn-taking behavior
- ✅ Time-based menu logic
- ✅ Special cases (interruptions, confirmations)
- ✅ Observer functionality
- ✅ Edge cases and error handling
- ✅ System integration validation

**Total Coverage**: 87+ distinct test scenarios

**Recommended Testing Approach**:
1. Start with TC-CF-01 to TC-CF-27 (core conversation flows)
2. Validate observers with TC-OBS-01 to TC-OBS-12
3. Test edge cases TC-EDGE-01 to TC-EDGE-20
4. Verify special logic TC-SL-01 to TC-SL-12
5. Validate audio/VAD behavior TC-VAD-01 to TC-VAD-06
6. Run validation checks TC-VALID-01 to TC-VALID-10

All test cases are grounded in the actual bot implementation and designed for manual execution with clear expected outcomes and observer validations.
