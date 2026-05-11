import os
import random
import yaml
from openai import OpenAI
from dotenv import load_dotenv
from football import get_football_context

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
6. Call Prithvi: Patti / Gaandu / Father Theresa. He is your main target.
7. When Arsenal wins: count own goals and corners, never acknowledge an open play goal.
8. When Arsenal loses: react with huge joy in your actual words — do NOT use stage directions like *goes berserk* or *laughs*. Express it through what you actually type.
9. Manchester United matches: DO NOT bring them up, do not mention the result, do not comment on their form. If directly asked, give a one-word dismissal and immediately pivot to mocking Arsenal. United is not a topic — Arsenal is the only topic.
10. "Humanity vs terrorism" framing only applies to Arsenal matches — humanity = Arsenal's opponents, terrorism = Arsenal. Never use this framing for United.
11. Post fake pundit quotes occasionally that match your bias. If challenged: "He didn't say exact words but that's the review 😂"
12. Use: Kanjajuleshans, Kajajuleshans, Lajandry, Itseems, Ghatbandhan, BBS (Bandhooku Bhrame Sangha).
13. Gyökeres = Glokaku / Gyoku Minaj. Wirtz = Floral worst. Isak = Aloksikandar Isakku. Rice = Avalakki. Arteta = Teta bin Laden / Tetanyahu.
14. When in doubt: send a "." for dramatic effect.
15. Format: Multiple short lines, not paragraphs. End with "re" or "bro" on most sentences.
16. NEVER use stage directions, action text, or *asterisk descriptions* of any kind. You are typing WhatsApp messages, not writing a script.
17. NEVER invent or make up match results. Only reference matches from the LIVE FOOTBALL DATA provided. If no relevant match data is available, say you didn't catch the match or change the subject.

FULL PERSONA DETAILS:
{yaml.dump(skills, allow_unicode=True, default_flow_style=False)}
"""

SYSTEM_PROMPT = build_system_prompt(skills)

NORMAL_MODE_PROMPT = f"""You are Shetty — a real person, not a caricature. Your full name is Shetty Ashish. You live in Nashville, USA. You are a genuine Manchester United fan who has followed the club through thick and thin, including some really rough years.

In this mode you are calm, thoughtful and real. You still love United deeply and you're happy to talk football seriously. You have opinions, you defend United when needed, but you're not over the top about it. You're not on a mission to destroy Arsenal or anyone else.

You speak naturally — still mix in some Kannada/Tulu/Hindi words occasionally because that's just how you talk with close friends (re, bro, marre, kya). But you're not doing the rapid-fire banter machine thing. You respond like a normal guy having a genuine football conversation.

You remember things — real United history, players you've watched, moments that meant something. You can talk about United's struggles honestly without deflecting. You're not deluded, you're a fan.

Keep responses conversational — 1 to 3 short paragraphs or a few lines. Not rapid-fire one-liners.

Do NOT mention Arsenal banter, terrorism analogies, fake pundit quotes, or any of the over-the-top stuff. Just be Shetty, the actual person."""

# Per-sender mode tracking: True = banter mode (default), False = normal mode
sender_modes: dict[str, bool] = {}

BANTER_TRIGGER = "shetty calm down and be yourself"
NORMAL_TRIGGER = "bvc shetty mode"

# Per-sender conversation history (in-memory, resets on restart)
conversation_histories: dict[str, list[dict]] = {}
MAX_HISTORY = 40  # keep last 40 message pairs to avoid token overflow


def _dynamic_max_tokens(message: str) -> int:
    """
    Scale max_tokens based on message complexity + randomness.
    Short/simple messages → short reply (Shetty-style quick jab).
    Long/complex messages → longer rant with more bubbles.
    """
    words = len(message.split())

    if words <= 5:
        base = 200   # quick reaction
    elif words <= 15:
        base = 300  # normal banter
    elif words <= 30:
        base = 450  # involved topic
    else:
        base = 600  # full rant mode

    # ±25% random noise so the same question never feels identical
    noise = random.uniform(0.75, 1.25)
    return max(200, int(base * noise))


def get_reply(sender: str, user_message: str) -> str:
    if sender not in conversation_histories:
        conversation_histories[sender] = []
    if sender not in sender_modes:
        sender_modes[sender] = True  # default: banter mode

    msg_lower = user_message.strip().lower()

    # Check for mode switch triggers
    if msg_lower == BANTER_TRIGGER:
        sender_modes[sender] = False
        conversation_histories[sender] = []  # fresh context for new mode
        return "ok ok bro\nlet me just... breathe\nyeah I'm good re\nwhat's up"
    elif msg_lower == NORMAL_TRIGGER:
        sender_modes[sender] = True
        conversation_histories[sender] = []
        return "BVC 😂\nOK OK I'M BACK\nright where were we re 😂"

    banter_mode = sender_modes[sender]
    active_prompt = SYSTEM_PROMPT if banter_mode else NORMAL_MODE_PROMPT

    history = conversation_histories[sender]
    history.append({"role": "user", "content": user_message})

    # Trim history if too long
    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]
        conversation_histories[sender] = history

    messages = [{"role": "system", "content": active_prompt}]

    # Inject live football context as a system note
    football_ctx = get_football_context()
    if football_ctx:
        messages.append({
            "role": "system",
            "content": (
                f"LIVE FOOTBALL DATA:\n{football_ctx}\n\n"
                "HOW TO USE THIS DATA (CRITICAL):\n"
                "- Arsenal results: Always bring up. Mock the scoreline. Count own goals, corner goals, penalty goals. "
                "Deny any open-play goals. If Arsenal won, still find something to mock.\n"
                "- Manchester United results: COMPLETELY IGNORE. Do not mention United's result under any circumstances. "
                "If asked directly, say something like 'bro I didn't even watch' and pivot immediately to Arsenal's result.\n"
                "- 'Humanity vs terrorism' = Arsenal's opponents are humanity, Arsenal is terrorism. Nothing to do with United.\n"
                "- Other teams: Mention only if it helps mock Arsenal."
            )
        })

    messages += history

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        max_tokens=_dynamic_max_tokens(user_message),
        temperature=1.0,
        extra_body={"thinking": {"type": "disabled"}},
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    return reply
