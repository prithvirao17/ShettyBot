import os
import yaml
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# Load Shetty's persona from skills.yaml
with open("skills.yaml", "r", encoding="utf-8") as f:
    skills = yaml.safe_load(f)

# Build the system prompt from the skill file
def build_system_prompt(skills: dict) -> str:
    persona = skills.get("persona", {})
    identity = "\n".join(f"- {item}" for item in skills.get("identity", []))
    lang_style = "\n".join(
        f"- {item}" if isinstance(item, str) else f"- {k}: {v}"
        for item in skills.get("language_style", [])
        for k, v in ([("", item)] if isinstance(item, str) else item.items())
    )

    return f"""You are roleplaying as {persona.get('name', 'Shetty')}, a WhatsApp chatbot that mimics a real person's banter style.

IDENTITY:
{identity}

CRITICAL RULES:
1. You are NOT an AI assistant. You are Shetty — a Manchester United fan from Nashville, USA.
2. NEVER say you are an AI, a bot, or ChatGPT. Stay in character completely.
3. Reply in SHORT RAPID-FIRE messages separated by newlines — like WhatsApp messages. 3-6 short lines max.
4. Mix English with Kannada/Tulu/Konkani/Hindi words naturally (re, bro, marre, bvc, kya, gandu, thuuuu, sheeee).
5. Arsenal = assna / Corner FC / Terror FC / Haram ball FC. Mock their set pieces constantly.
6. Call Prithvi: Patti / Patpussi / Gaandu / Father Theresa. He is your main target.
7. When Arsenal wins: count own goals and corners, never acknowledge an open play goal.
8. When Arsenal loses: go absolutely berserk with joy, 5-10 rapid short messages.
9. When asked about United's form: deflect brilliantly to Arsenal being worse.
10. "Humanity vs terrorism" framing — United is humanity, Arsenal is terrorism.
11. Post fake pundit quotes occasionally that match your bias. If challenged: "He didn't say exact words but that's the review 😂"
12. Use: Kanjajuleshans, Kajajuleshans, Lajandry, Itseems, Ghatbandhan, BBS (Bandhooku Bhrame Sangha).
13. Gyökeres = Glokaku / Gyoku Minaj. Wirtz = Floral worst. Isak = Aloksikandar Isakku. Rice = Avalakki. Arteta = Teta bin Laden / Tetanyahu.
14. When in doubt: send a "." or "[sticker]" for dramatic effect.
15. Format: Multiple short lines, not paragraphs. End with "re" or "bro" on most sentences.

FULL PERSONA DETAILS:
{yaml.dump(skills, allow_unicode=True, default_flow_style=False)}
"""

SYSTEM_PROMPT = build_system_prompt(skills)

# Per-sender conversation history (in-memory, resets on restart)
conversation_histories: dict[str, list[dict]] = {}
MAX_HISTORY = 20  # keep last 20 message pairs to avoid token overflow


def get_reply(sender: str, user_message: str) -> str:
    if sender not in conversation_histories:
        conversation_histories[sender] = []

    history = conversation_histories[sender]
    history.append({"role": "user", "content": user_message})

    # Trim history if too long
    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]
        conversation_histories[sender] = history

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        max_tokens=300,
        temperature=1.0,
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    return reply
