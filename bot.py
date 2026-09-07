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
import time
from datetime import date

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

from content import POSTS
from arabic_content import SHORT_TEXTS, LONG_TEXTS
from channel_translate import fetch_source_posts, translate_to_amharic, strip_links

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

# Fallback post index eyalefachew keqen (date) tegeba yisephefal - keza
# Railway sildegim/siketam state.json bicha bitfetf, dagmo dagmo weyim
# ye'atqodemu post attelefim (Railway be'ile'iginu redeploy sila'iderge
# yekefile file system yigefal, be'izhe date-based selesela beqa min
# gize'im aminet yalew new).
POST_EPOCH = date(2026, 1, 1)

# ---------------------------------------------------------
# EXTRA POSTS (achir/rezm - kel'arebegna mnach yeteserzu, be
# post gize wede amarigna yiteregemalu) - beken 1 achir + 1 rezm
# ---------------------------------------------------------
EXTRA_POST_TIMES = {"short": "08:00", "long": "22:00"}

# ---------------------------------------------------------
# AI DYNAMIC CONTENT (optional) - AI addis yizet endifetir
# ---------------------------------------------------------
# Kihen key kalasqemetu bot'u endelogeg keta POSTS list eyeteqebele
# yisera (fallback). Gemini API key be'itsa (card sayasfeleg) ke'izih
# yagenyal: https://aistudio.google.com -> "Get API key"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# AI kahon post yetesera rieswoch (topics) tzareb - dagimo endayimeta
# lekelakay yiyazal. Bicha yalefu N rieswoch bicha yizeker.
AI_TOPIC_HISTORY_LIMIT = 40

# ---------------------------------------------------------
# SOURCE CHANNEL TRANSLATION (optional) - kelela public channel(woch)
# addis post gimito wede Amarigna yitergimal, wede @ibnuabbas_hara yiletfal
# ---------------------------------------------------------
# Ke "https://t.me/Awraq_Alyasmin" bicha ye"Awraq_Alyasmin" ken new
# yemiferelgew (@ weyim t.me/ sayhon). Endezih bezu channel'wochn
# mecheveT yichalal - bicha list wist meMEmemer bicha new yasfeligew.
SOURCE_CHANNELS = [
    "Awraq_Alyasmin",
    "mutshabh",
    "gghjgvvgg",
    "Tadabor_quran",
    "Ayaat_Qurania",
    "Bukhari_Muslim_1",
    "Ahadeeth_Sahiha",
    "Qisas_AlAnbiya",
    "Seerah_Anbiya",
    "Aqwal_Salaf",
    "Durar_Salaf",
    "dorarnet_telegram",
    "ArIslamway",
    "qraan1",
    "itsTheQuraan",
    "qisasalanbiaa",
    "Qssallqran",
    "alahwaztarikharbi2831",
    "earbbb",
    "fkdudnvkd",
]

# Sesat sesat (be'iminet) ye'sechid channel'un lemayet - polling interval
TRANSLATE_CHECK_INTERVAL_MINUTES = 15

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
                data.setdefault("last_source_msg_id", {})
                # Yalefew version (yaltemokete) "last_source_msg_id" ande
                # channel bicha (int) yiyazal neber - kahun bezu channel
                # dict endihonu inqeyir (be Awraq_Alyasmin sim inaseral).
                if isinstance(data["last_source_msg_id"], int):
                    data["last_source_msg_id"] = {
                        "Awraq_Alyasmin": data["last_source_msg_id"]
                    }
                return data
        except Exception:
            logger.warning("State file could not be read, kesera enjemralen.")
    return {"index": 0, "ai_topic_history": [], "last_source_msg_id": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def get_deterministic_index(slot_time: str) -> int:
    """Fallback list wist yalewn post index be'qen (date) na be'sa'at slot
    (06:00/13:00/19:00) meseret adirgo yiseraal - file storage atsafelegim,
    bemulu yeqerebe (deterministic) new. Bihon Railway bota lay bota
    sildegim/state.json bitgefa'im, dagmo dagmo post atileTfim."""
    days_passed = (date.today() - POST_EPOCH).days
    slot_index = POST_TIMES.index(slot_time)
    return (days_passed * len(POST_TIMES) + slot_index) % len(POSTS)


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


def send_photo(photo_url: str, caption: str = "", token: str = None) -> bool:
    """photo_url (Telegram serversu betekemetu URL) photo'n keza,
    caption gara (kalele) yiletfal. Telegram sile'irsu photo'n yiwerdal -
    inya bota download ma'derg alasfelegim."""
    token = token or BOT_TOKEN
    if not token or token == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error(
            "BOT_TOKEN alteseTem! Environment variable BOT_TOKEN sisu weyim "
            "bot.py wisit teteka."
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_USERNAME,
        "photo": photo_url,
    }
    if caption:
        payload["caption"] = caption[:1024]  # Telegram caption limit
        payload["parse_mode"] = "HTML"
    try:
        resp = requests.post(url, data=payload, timeout=30)
        data = resp.json()
        if data.get("ok"):
            logger.info("Photo teleTffwal!")
            return True
        else:
            logger.error(f"Telegram error (sendPhoto): {data}")
            return False
    except Exception as e:
        logger.error(f"Network/send error (sendPhoto): {e}")
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
    """AI response text wisit yalewn JSON aweta."""
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
    """Gemini API (be'itsa) teqemto addis (dagimo yalhone) post yifetral.
    Bicha sira sayseram (key alebet, network gudai, ...) None yimelesal -
    keza post_job() wist wede fallback list yihedal."""
    if not GEMINI_API_KEY:
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
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"content-type": "application/json"},
            json={
                "system_instruction": {
                    "parts": [{"text": AI_SYSTEM_PROMPT}]
                },
                "contents": [
                    {"role": "user", "parts": [{"text": user_prompt}]}
                ],
                "generationConfig": {"maxOutputTokens": 600},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = "".join(
            part.get("text", "")
            for part in data["candidates"][0]["content"]["parts"]
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

def post_job(slot_time: str):
    state = load_state()
    history = state.get("ai_topic_history", [])

    ai_post = generate_ai_post(history)

    if ai_post:
        full_text = f"{ai_post['text']}\n\n{ai_post['question']}"
        source = "AI"
    else:
        idx = get_deterministic_index(slot_time)
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
            save_state(state)


def extra_post_job(kind: str):
    """achir (short) weyim rezm (long) arebegna tsihuf be'file storage
    saydegef, be'qen sile'sila (deterministic) yimeret, wede amarigna
    yiteregumal, keza yileTfal."""
    pool = SHORT_TEXTS if kind == "short" else LONG_TEXTS
    if not pool:
        return

    days_passed = (date.today() - POST_EPOCH).days
    idx = days_passed % len(pool)
    arabic_text = pool[idx]

    cleaned_text = strip_links(arabic_text)
    translated = translate_to_amharic(cleaned_text)
    if not translated:
        logger.warning(
            f"Extra post ({kind}, idx={idx}) altiregumem - yalfal, wede "
            f"huletegnaw sesat ynesal."
        )
        return

    send_message(translated)


# =========================================================
# SOURCE CHANNEL -> TRANSLATE -> FORWARD JOB
# =========================================================

def _process_one_channel(state, source_username):
    """Ande source channel bicha addis posts yifelegal, yitirgumal, na
    yileTfal. state'un be'place yasተካክላል (save_state ye'silejemer sira
    new)."""
    last_ids = state.setdefault("last_source_msg_id", {})
    last_id = last_ids.get(source_username, 0)

    posts = fetch_source_posts(source_username)
    if not posts:
        return

    # Meji gize (last_id == 0) sirawun sinjemer, yalefut posts hulu wede
    # channel'u aynelekim - kahun bicha jemro new addis posts yikeTelal.
    if last_id == 0:
        newest_id = posts[-1][0]
        last_ids[source_username] = newest_id
        save_state(state)
        logger.info(
            f"Ke {source_username} lay yalut yalefu posts ke'atirgum "
            f"wich yiwetalu (baseline: {newest_id}). Ke'ahun jemro addis "
            f"posts bicha yiterigemalu."
        )
        return

    new_posts = [p for p in posts if p[0] > last_id]
    if not new_posts:
        return

    attribution = f"\n\n🔗 ምንጭ፦ @{source_username}"

    for msg_id, original_text, photo_url in new_posts:
        cleaned_text = strip_links(original_text) if original_text else ""

        if not cleaned_text and not photo_url:
            # Link bicha (weyim ken neger) yehone, gara photo yelewim post -
            # inleFal.
            last_ids[source_username] = msg_id
            save_state(state)
            continue

        translated = ""
        if cleaned_text:
            translated = translate_to_amharic(cleaned_text)
            if translated is None:
                logger.warning(
                    f"Post {msg_id} (ke {source_username}) altiregumem "
                    f"(translation altchalem) - wede huletegnaw round "
                    f"inleፍ, atalefim."
                )
                break  # eziyachin wede fit atehedm, be'ideregagem sile yizoral

        full_text = (translated + attribution) if translated else attribution.strip()

        if photo_url:
            # Photo gara (caption endihonu) weyim photo bicha (text yelewim)
            success = send_photo(photo_url, caption=full_text, token=TRANSLATOR_BOT_TOKEN)
            if success and len(full_text) > 1024:
                # Caption 1024 char bicha silemiWesed, yeqerew tekst wede
                # kalele message iniLeFew.
                send_message(full_text, token=TRANSLATOR_BOT_TOKEN)
        else:
            success = send_message(full_text, token=TRANSLATOR_BOT_TOKEN)

        if not success:
            logger.warning(
                f"Post {msg_id} (ke {source_username}) altiletefem, "
                f"be'huletegnaw round inmokoral."
            )
            break

        last_ids[source_username] = msg_id
        save_state(state)


def translate_and_forward_job():
    if not TRANSLATOR_BOT_TOKEN:
        logger.warning(
            "TRANSLATOR_BOT_TOKEN alteseTem - translate-forward sira "
            "insu jemro yimokoral."
        )
        return

    state = load_state()
    for source_username in SOURCE_CHANNELS:
        _process_one_channel(state, source_username)
        time.sleep(2)  # channel'woch mekakel ereft - rate-limit inayaggagemet


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
            args=[t],
            id=f"post_{t}",
        )
        logger.info(f"Post scheduled at {t} ({TIMEZONE})")

    for kind, t in EXTRA_POST_TIMES.items():
        hour, minute = t.split(":")
        scheduler.add_job(
            extra_post_job,
            "cron",
            hour=int(hour),
            minute=int(minute),
            args=[kind],
            id=f"extra_post_{kind}",
        )
        logger.info(f"Extra post ({kind}) scheduled at {t} ({TIMEZONE})")

    scheduler.add_job(
        translate_and_forward_job,
        "interval",
        minutes=TRANSLATE_CHECK_INTERVAL_MINUTES,
        id="translate_forward",
    )
    channels_str = ", ".join(f"@{c}" for c in SOURCE_CHANNELS)
    logger.info(
        f"Translate-forward ke {channels_str} be'iyalu "
        f"{TRANSLATE_CHECK_INTERVAL_MINUTES} deqiqa scheduled."
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot ders adergaal.")


if __name__ == "__main__":
    run()
