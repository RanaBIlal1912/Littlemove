"""
Chatbot engine for the Mila widget.

Keyword matching works with no API key.
AI fallback via Anthropic claude-haiku requires ANTHROPIC_API_KEY env var.
"""
import logging
import os

from django.utils import timezone

logger = logging.getLogger(__name__)

RATE_LIMIT = 20       # messages per session per hour
RATE_WINDOW = 3600    # seconds (1 hour)
SESSION_KEY = "chatbot_times"


# ── Rate limiting ─────────────────────────────────────────────────────────────

def _recent_count(session):
    """Return how many messages this session has sent in the last hour."""
    now = timezone.now().timestamp()
    times = [t for t in session.get(SESSION_KEY, []) if now - t < RATE_WINDOW]
    session[SESSION_KEY] = times
    return len(times)


def _record_message(session):
    now = timezone.now().timestamp()
    times = session.get(SESSION_KEY, [])
    times.append(now)
    session[SESSION_KEY] = times[-(RATE_LIMIT * 2):]  # keep list bounded


# ── Keyword matching ──────────────────────────────────────────────────────────

def _keyword_match(user_msg, bot_answers, faqs):
    """
    Return the best matching BotAnswer or FAQ, or None.
    Scoring: count how many of the answer's keywords appear in the message.
    """
    msg_lower = user_msg.lower()
    words = set(msg_lower.split())

    best = None
    best_score = 0

    for answer in bot_answers:
        kws = answer.keyword_list()
        score = sum(1 for kw in kws if kw in msg_lower)
        if score > best_score:
            best_score = score
            best = {"text": answer.answer, "source": "answer"}

    for faq in faqs:
        # score based on how many words from the question appear in the message
        q_words = [w.strip("?!.,") for w in faq.question.lower().split() if len(w) >= 2]
        score = sum(1 for w in q_words if w in msg_lower)
        if score > best_score:
            best_score = score
            best = {"text": faq.answer, "source": "faq"}

    return best if best_score > 0 else None


# ── AI fallback ───────────────────────────────────────────────────────────────

def _ai_response(user_msg, bot_answers, faqs, products, store_settings):
    """
    Use Claude claude-haiku-4-5 to generate an answer grounded in store data.
    Returns answer string, or None if AI is unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed; AI answers disabled.")
        return None

    faq_block = "\n".join(f"Q: {f.question}\nA: {f.answer}" for f in faqs)
    answers_block = "\n".join(f"Q: {a.question}\nA: {a.answer}" for a in bot_answers)
    products_block = "\n".join(
        f"- {p.name}: Rs {p.price:,}, stock {p.stock}, age {p.age_label}"
        for p in products[:40]
    )

    system = (
        f"You are {store_settings.bot_name}, the helpful toy guide for {store_settings.store_name}, "
        f"a children's developmental toy shop in Pakistan.\n\n"
        f"=== Store FAQs ===\n{faq_block}\n\n"
        f"=== Prepared answers ===\n{answers_block}\n\n"
        f"=== Current products ===\n{products_block}\n\n"
        f"Rules:\n"
        f"- Answer ONLY questions about {store_settings.store_name}: products, delivery, payments, age-suitability.\n"
        f"- Never make up prices, stock levels, or delivery times — use only the data above.\n"
        f"- Keep answers to 2-3 sentences max.\n"
        f"- When unsure, say 'I'm not sure' and suggest WhatsApp: wa.me/{store_settings.whatsapp_number}\n"
        f"- Reply in English. Be warm and friendly."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("Anthropic API error: %s", exc)
        return None


# ── Main entry point ──────────────────────────────────────────────────────────

def get_bot_response(request, user_message):
    """
    Process a visitor message and return a response dict:
      {"answer": str, "matched": bool, "rate_limited": bool}
    """
    from store.models import BotAnswer, BotSettings, ChatLog, FAQ, Product, StoreSettings

    bot = BotSettings.load()

    if not bot.enabled:
        return {"answer": "", "matched": False, "rate_limited": False, "disabled": True}

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    # Rate limit
    if _recent_count(request.session) >= RATE_LIMIT:
        return {
            "answer": "You've sent a lot of messages! Please wait a bit, or chat with our team on WhatsApp.",
            "matched": False,
            "rate_limited": True,
        }
    _record_message(request.session)

    # Load data
    bot_answers = list(BotAnswer.objects.filter(active=True))
    faqs = list(FAQ.objects.filter(active=True))

    match = _keyword_match(user_message, bot_answers, faqs)

    answer_text = None
    matched = False

    if match:
        answer_text = match["text"]
        matched = True
    elif bot.use_ai:
        products = list(Product.objects.live().select_related("category")[:50])
        store = StoreSettings.load()
        ai_text = _ai_response(user_message, bot_answers, faqs, products, store)
        if ai_text:
            answer_text = ai_text
            matched = True

    if not answer_text:
        answer_text = bot.fallback_message

    # Log
    try:
        ChatLog.objects.create(
            session_key=request.session.session_key or "",
            question=user_message[:500],
            answer=answer_text[:1000],
            matched=matched,
        )
    except Exception:
        pass

    return {"answer": answer_text, "matched": matched, "rate_limited": False}
