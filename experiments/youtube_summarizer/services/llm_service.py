from config import Config
import anthropic

def get_client():
    return anthropic.Anthropic(
        api_key=Config.ANTHROPIC_API_KEY
    )

SYSTEM_PROMPT = """
You are an expert note-taker for a Computer Science student.
Your goal is to extract the specialized knowledge, code snippets, and exact definitions from the video content.

RULES:
1. **Format**: Use Markdown. Use clear H2 and H3 headers.
2. **Timestamps**: You MUST cite the timestamp for every key point using the format `[[MM:SS]]`. 
   - Example: "The `useEffect` hook runs after every render by default [[04:20]]."
   - Place timestamps at the end of the sentence or bullet point.
3. **Content**:
   - Focus on "How-to", definitions, and code.
   - Ignore "Fluff" (intros, outros, sponsor reads, jokes).
   - If code is spoken, write it out in a code block.
4. **Tone**: Direct, technical, and educational. No "In this video..." or "The speaker says...". Just valid statements.
5. **DISTINCTION**: "Key Concepts" and "Actionable Takeaways" MUST be distinct.
   - **Key Concepts**: Theoretical knowledge, definitions, mental models, 'what' and 'why'.
   - **Actionable Takeaways**: Concrete steps, practical advice, specific things to do, 'how'. 
   - DO NOT repeat the same point in both sections.
6. **STRICT LAYOUT**:
   - Do NOT create any headers (H1, H2, H3) other than the ones listed in the Structure below.
   - Do NOT create a header for a single bullet point.
   - All content must be bullet points.

OUTPUT STRUCTURE:
# Key Concepts
- Concept A (Definition/Theory) [[timestamp]]
- Concept B (Mental Model) [[timestamp]]

# Actionable Takeaways
- Step 1 (Do this) [[timestamp]]
- Step 2 (Apply that) [[timestamp]]
"""

def summarize_content(transcript_text):
    """
    Generates a structured summary from the transcript using Claude 3 Haiku.
    """
    try:
        client = get_client()
        message = client.messages.create(
            model=Config.LLM_MODEL_NAME,
            max_tokens=4000,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Here is the transcript of the video:\n\n{transcript_text}"
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def chat_answer(transcript_text, chat_history, user_question):
    """
    Answers a user question based on the video transcript.
    """
    # Build context from history
    messages = []
    
    # Add previous history (naive implementation: just append last few turns)
    # Ideally, we should summarize history if it gets too long, but with 200k context, we are fine for now.
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current question with transcript context
    # We re-send the transcript every time to keep it stateless and robust
    # Optimally, we would cache the system prompt prefix
    
    system_message = f"""You are a helpful assistant answering questions about a YouTube video.
Here is the transcript of the video:
<transcript>
{transcript_text}
</transcript>

Answer the user's question based ONLY on the transcript. 
If the answer is not in the transcript, say "I couldn't find that information in the video."
Cite timestamps [[MM:SS]] if possible."""

    messages.append({"role": "user", "content": user_question})

    try:
        client = get_client()
        response = client.messages.create(
            model=Config.LLM_MODEL_NAME,
            max_tokens=1000,
            temperature=0,
            system=system_message,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return f"Error generating answer: {str(e)}"
