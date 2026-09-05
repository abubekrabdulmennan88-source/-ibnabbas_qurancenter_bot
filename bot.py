# -*- coding: utf-8 -*-
"""
IBN ABBAS QURAN CENTER BOT
Beken 3 gize (ጠዋት/ከሰዓት/ማታ) ወደ Telegram channel yemileTF bot.

Sira lememeriya (jemari yemihonu):
    pip install -r requirements.txt
    python bot.py
"""

import json
import logging
import os

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

from content import POSTS
from channel_translate import fetch_source_posts, translate_to_amharic

# =========================================================
# CONFIG - Eziya laye configuration'wochn adirgu
# =========================================================

# BotFather kagegnew token (dehninetu yetegebabek beqa - environment variable
# metekem yishalal, weyim betasas eziya bicha malefetin ychilalu)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")

# Channel'u username (@ kaleletew) weyim channel ID
CHANNEL_USERNAME = "@ibnuabbas_hara"

# Posting time (24-hour format), Ethiopia (Africa/Addis_Ababa) timezone
POST_TIMES = ["06:00", "13:00", "19:00"]
TIMEZONE = "Africa/Addis_Ababa"

# State file - yetalefew post yetederese eyalen lememezgeb
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

# ---------------------------------------------------------
# AI DYNAMIC CONTENT (optional) - AI addis yizet endifetir
# ---------------------------------------------------------
# Kihen key kalasqemetu bot'u endelogeg keta POSTS list eyeteqebele
# yisera (fallback). Key litseffelgu keza: https://console.anthropic.com
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-5"

# AI kahon post yetesera rieswoch (topics) tzareb - dagimo endayimeta
# lekelakay yiyazal. Bicha yalefu N rieswoch bicha yizeker.
AI_TOPIC_HISTORY_LIMIT = 40

# ---------------------------------------------------------
# SOURCE CHANNEL TRANSLATION (optional) - kelela public channel
# addis post gimito wede Amarigna yitergimal, wede @ibnuabbas_hara yiletfal
# ---------------------------------------------------------
# Ke "https://t.me/Awraq_Alyasmin" bicha ye"Awraq_Alyasmin" ken new
# yemiferelgew (@ weyim t.me/ sayhon).
SOURCE_CHANNEL_USERNAME = "Awraq_Alyasmin"

# Sesat sesat (be'iminet) ye'sechid channel'un lemayet - polling interval
TRANSLATE_CHECK_INTERVAL_MINUTES = 15

# Ke'iyalu translated post gar yemiketel attribution mesetr
TRANSLATE_ATTRIBUTION = "\n\n🔗 ምንጭ፦ @Awraq_Alyasmin"

# Yihe tirgum post'wochn yemileTfew wediya adis bot ("Translator Abubeker
# Abdu") token - ke ne'baru bot yileyal. Yihe bot @ibnuabbas_hara channel
# admin (Post Messages) mehonu yasfeligal.
TRANSLATOR_BOT_TOKEN = os.environ.get("TRANSLATOR_BOT_TOKEN", "")

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ibnabbas_bot")


# =========================================================
# STATE MANAGEMENT (yetederese index lememezgeb, bot bidegeggem
# kemejemeriya sayihon endimezgib)
# =========================================================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("index", 0)
                data.setdefault("ai_topic_history", [])
                data.setdefault("last_source_msg_id", 0)
                return data
        except Exception:
            logger.warning("State file could not be read, kesera enjemralen.")
    return {"index": 0, "ai_topic_history": [], "last_source_msg_id": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


# =========================================================
# TELEGRAM SEND
# =========================================================

def send_message(text: str, token: str = None) -> bool:
    token = token or BOT_TOKEN
    if not token or token == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error(
            "BOT_TOKEN alteseTem! Environment variable BOT_TOKEN sisu weyim "
            "bot.py wisit teteka."
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": CHANNEL_USERNAME,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, data=payload, timeout=20)
        data = resp.json()
        if data.get("ok"):
            logger.info("Post teleTffwal!")
            return True
        else:
            logger.error(f"Telegram error: {data}")
            return False
    except Exception as e:
        logger.error(f"Network/send error: {e}")
        return False


# =========================================================
# AI DYNAMIC CONTENT GENERATION (optional, with fallback)
# =========================================================

AI_SYSTEM_PROMPT = """Antchi le "IBN ABBAS QURAN CENTER BOT" Telegram channel yemiseri
yeezelama timhert redakter neh. Selezih le channel post tsafe.

QEBADOWOCH (asigedaj yalebachew):
- BeAmargna bicha tsaf.
- 5-7 mesmer teretari, aregagi timhirtawi tsihuf tsaf. Ye Quran ayat, Hadith,
  weyim Sira lay yasfeligew - GN yelektewun quote (word-for-word text) atsaf.
  Befelagot beራስህ qal aregagi, weyim betekelakay astesasay lay tenager
  ("Nebiyu selamnet be'ilay yihonelet - tetenaqewal..." bequ) - EGN QUOTE ATSAF
  scha titeregagem yikeyer new sile hone.
- Beemeresha 1 tefetari, hasabin yemiyasebkl tiyake tsaf ("❓" bequ yemejemer).
- Content'u ke akrari (extreme), sectarian, weyim kektakay (controversial) 
  neger yiራqiq. Aregagi, mekakel, temokakari yehone timhirt bicha.
- Titaqebele JSON format bicha mels sit: {"topic": "kelele siyme (2-4 words
  English or Amharic)", "text": "...", "question": "❓ ..."}. Lela neger
  ke JSON wich atsaf.
"""


def _extract_json(raw_text: str):
    """Anthropic response text wisit yalewn JSON aweta."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON alterekebem")
    return json.loads(raw_text[start:end + 1])


def generate_ai_post(recent_topics):
    """Anthropic API teqemto addis (dagimo yalhone) post yifetral.
    Bicha sira sayseram (key alebet, network gudai, ...) None yimelesal -
    keza post_job() wist wede fallback list yihedal."""
    if not ANTHROPIC_API_KEY:
        return None

    avoid_text = ""
    if recent_topics:
        avoid_text = (
            "Kezih beqedmo yeteleTfu rieswoch (topics) ARE - eziyan atድገም, "
            "aዲስ ye'iyalu yehone riese mreT: " + ", ".join(recent_topics)
        )

    user_prompt = (
        "Le zare post adis yehone islamawi timhirtawi tsihuf (5-7 mesmer) "
        "gara 1 tefetari tiyake fetir. " + avoid_text
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 600,
                "system": AI_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = "".join(
            block.get("text", "") for block in data.get("content", [])
            if block.get("type") == "text"
        )
        parsed = _extract_json(raw_text)
        if "text" not in parsed or "question" not in parsed:
            raise ValueError("yeklegn field(s) yelem (missing text/question)")
        return parsed
    except Exception as e:
        logger.warning(f"AI post generation altchalem, wede fallback list inhedalen: {e}")
        return None


# =========================================================
# POST JOB - yemiketel post yemewesd na yemileTF
# =========================================================

def post_job():
    state = load_state()
    history = state.get("ai_topic_history", [])

    ai_post = generate_ai_post(history)

    if ai_post:
        full_text = f"{ai_post['text']}\n\n{ai_post['question']}"
        source = "AI"
    else:
        idx = state.get("index", 0) % len(POSTS)
        post = POSTS[idx]
        full_text = f"{post['text']}\n\n{post['question']}"
        source = "fallback-list"

    success = send_message(full_text)

    if not success:
        logger.warning("Post alteleTfem, be huletegnaw scheduled gize endgena ynesal.")
        return

    if source == "AI":
        topic = ai_post.get("topic", "").strip()
        if topic:
            history.append(topic)
            state["ai_topic_history"] = history[-AI_TOPIC_HISTORY_LIMIT:]
    else:
        state["index"] = (idx + 1) % len(POSTS)

    save_state(state)


# =========================================================
# SOURCE CHANNEL -> TRANSLATE -> FORWARD JOB
# =========================================================

def translate_and_forward_job():
    if not TRANSLATOR_BOT_TOKEN:
        logger.warning(
            "TRANSLATOR_BOT_TOKEN alteseTem - translate-forward sira "
            "insu jemro yimokoral."
        )
        return

    state = load_state()
    last_id = state.get("last_source_msg_id", 0)

    posts = fetch_source_posts(SOURCE_CHANNEL_USERNAME)
    if not posts:
        return

    # Meji gize (last_id == 0) sirawun sinjemer, yalefut posts hulu wede
    # channel'u aynelekim - kahun bicha jemro new addis posts yikeTelal.
    if last_id == 0:
        newest_id = posts[-1][0]
        state["last_source_msg_id"] = newest_id
        save_state(state)
        logger.info(
            f"Ke {SOURCE_CHANNEL_USERNAME} lay yalut yalefu posts ke'atirgum "
            f"wich yiwetalu (baseline: {newest_id}). Ke'ahun jemro addis "
            f"posts bicha yiterigemalu."
        )
        return

    new_posts = [p for p in posts if p[0] > last_id]
    if not new_posts:
        return

    for msg_id, original_text in new_posts:
        translated = translate_to_amharic(original_text)
        if not translated:
            logger.warning(
                f"Post {msg_id} altiregumem (translation altchalem) - "
                f"wede huletegnaw round inleፍ, atalefim."
            )
            break  # eziyachin wede fit atehedm, be'ideregagem sile yizoral

        full_text = translated + TRANSLATE_ATTRIBUTION
        success = send_message(full_text, token=TRANSLATOR_BOT_TOKEN)
        if not success:
            logger.warning(f"Post {msg_id} altiletefem, be'huletegnaw round inmokoral.")
            break

        state["last_source_msg_id"] = msg_id
        save_state(state)


# =========================================================
# SCHEDULER SETUP
# =========================================================

def run():
    logger.info("IBN ABBAS QURAN CENTER BOT eyeserw new...")

    scheduler = BlockingScheduler(timezone=TIMEZONE)

    for t in POST_TIMES:
        hour, minute = t.split(":")
        scheduler.add_job(
            post_job,
            "cron",
            hour=int(hour),
            minute=int(minute),
            id=f"post_{t}",
        )
        logger.info(f"Post scheduled at {t} ({TIMEZONE})")

    scheduler.add_job(
        translate_and_forward_job,
        "interval",
        minutes=TRANSLATE_CHECK_INTERVAL_MINUTES,
        id="translate_forward",
    )
    logger.info(
        f"Translate-forward ke @{SOURCE_CHANNEL_USERNAME} be'iyalu "
        f"{TRANSLATE_CHECK_INTERVAL_MINUTES} deqiqa scheduled."
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot ders adergaal.")


if __name__ == "__main__":
    run()
