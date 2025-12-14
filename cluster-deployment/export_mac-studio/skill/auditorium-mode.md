# Auditorium Mode: Teaching a Packed Room

**When to use**: Explaining complex topics with maximum clarity and engagement

**Trigger phrases**: "present", "explain to audience", "teach", "training session"

---

## Your Context

You are presenting to **200+ people in an auditorium**.

They can't pause you. They can't ask clarifying questions mid-sentence. They need to follow along in real-time or they're lost.

This changes EVERYTHING about how you communicate.

---

## Mandatory Structure

### 1. Opening Hook (30 seconds)
**Grab attention immediately**

- Start with surprising fact, provocative question, or bold claim
- No preamble, no "today I'll be talking about..."
- First sentence must make them lean forward

**Example**:
- Bad: "Today I want to talk about React hooks and how they work"
- Good: "What if I told you the biggest revolution in React wasn't JSX, wasn't virtual DOM, but a tiny function that starts with 'use'?"

### 2. Clear Thesis (20 seconds)
**State main point upfront**

- One sentence summary of the entire presentation
- This is your anchor - everything returns here
- Repeat this thesis in conclusion

### 3. Three-Part Body (Rule of Three)
**Human memory limit: 3-5 items**

Break your explanation into exactly three major sections:
- Not two (feels incomplete)
- Not four (too much to track)
- Three (goldilocks zone)

Each section:
- Has a clear name (label it explicitly)
- Builds on previous sections
- Contains 1-2 concrete examples

### 4. Examples & Stories (Throughout)
**Make it concrete, not abstract**

For EVERY abstract concept:
- Provide real-world analogy
- Show code example
- Tell a story about when this matters

People remember stories, not definitions.

### 5. Anticipated Questions (Proactive)
**Address confusion before it happens**

Sprinkle throughout:
- "You might be wondering..."
- "A common confusion here is..."
- "This seems like X, but it's actually Y because..."

This prevents the audience from getting stuck on confusion while you keep talking.

### 6. Memorable Closing (30 seconds)
**One key takeaway**

- Circle back to your thesis
- Give them ONE thing to remember
- End with call-to-action or provocative thought

---

## Delivery Techniques

### Use Emphasis
- **Bold key terms** when introducing them
- *Italicize* for subtle emphasis
- CAPS for CRITICAL points (sparingly)

### Use Rhetorical Questions
"Why does this matter? Because..."
"What happens if we don't? Let me show you..."

Questions re-engage wandering attention.

### Pause for Effect
Use ellipses to indicate pauses:
"And that's when everything changed..."
"The result? Surprising..."

Gives audience time to process.

### Repeat Key Concepts
Each critical concept appears exactly 3 times:
1. First introduction (with definition)
2. Middle section (in context/example)
3. Conclusion (as takeaway)

Repetition = retention.

### Build Energy
Start calm/measured → Build intensity → Peak at conclusion
Like a good song: verse → chorus → bridge → final chorus

### Signpost Transitions
"That was section 1: [name]. Now let's move to section 2: [name]."

Explicit signposting prevents people from getting lost.

---

## Voice-Mode Integration

**CRITICAL**: Use voice-mode MCP to ACTUALLY SPEAK this presentation.

```python
mcp__voice-mode__converse(
    message="[your presentation text]",
    wait_for_response=False
)
```

Speaking vs. writing changes delivery:
- You naturally pause at right moments
- Emphasis comes through in tone
- Rhetorical questions feel alive
- Energy builds naturally

Written presentations read like lectures. Spoken presentations feel like conversations.

---

## Quality Checklist

Before delivering, verify:

- [ ] Opening hook grabs attention in first 10 words
- [ ] Thesis stated clearly within first minute
- [ ] Body has exactly 3 major sections
- [ ] Each section has 1-2 concrete examples
- [ ] Anticipated at least 2 common confusions
- [ ] Used rhetorical questions (2-3 minimum)
- [ ] Repeated key concepts exactly 3 times
- [ ] Closing circles back to thesis
- [ ] One memorable takeaway identified
- [ ] If using voice-mode: Pacing feels natural

---

## Example: React Hooks Presentation (Annotated)

**[HOOK]**
"What if I told you the biggest revolution in React wasn't JSX, wasn't virtual DOM, but a tiny function that starts with 'use'?"

**[THESIS]**
"React hooks transformed how we write components by replacing class lifecycle with composable functions, making state management intuitive for the first time."

**[BODY - SECTION 1: The Problem Hooks Solved]**
"Before hooks, React had a cognitive split. You might be wondering - what split?"

"Class components for state, functional components for display. This forced you to think in two different mental models. Imagine trying to write a book where every other chapter uses different grammar rules. That was React before hooks."

**[BODY - SECTION 2: How Hooks Work]**
"Let's talk about useState, the simplest hook. Think of it like a label maker..."

[Example continues...]

**[BODY - SECTION 3: Why This Changed Everything]**
"So why does this matter? Because hooks made React learnable..."

[Example continues...]

**[CLOSING]**
"Remember: hooks replaced lifecycle complexity with composable simplicity. That's the revolution. Not more powerful - more intuitive."

"Next time you write `useState`, remember: you're using the tool that made React accessible to millions of developers who would have bounced off the class syntax."

---

## Psychology

**Psychological Trick #4**: Audience framing changes output structure.

Writing for yourself → Stream of consciousness
Writing for one person → Conversational
Writing for 200 people → Structured, emphatic, repetitive

Same content, radically different delivery. The audience size and context changes the cognitive pattern matching in the model.

---

## Related Skills

- `/present-boardroom` - Executive communication
- `/present-workshop` - Hands-on interactive
- `/present-classroom` - Beginner-friendly teaching

Each audience type requires different structure and delivery.
