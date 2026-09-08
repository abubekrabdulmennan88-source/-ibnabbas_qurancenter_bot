# -*- coding: utf-8 -*-
"""
channel_translate.py

Ke public Telegram channel (lemisale https://t.me/Awraq_Alyasmin) addis
post sichereb, wede Amarigna beketel yitirgumal, na wede yenaachin channel
(@ibnuabbas_hara) yiletifal.

Sira ye'mishet: Telegram bot API bicha le'saraw channel (bot admin yalhone)
message'wochn maynbeb aychalim. Slezih, public channel'wochu "preview" page
(https://t.me/s/<username>) yemibalut, login sayasfelig yemireda public
webpage'n eynetekemetne.
"""

import html
import json
import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ibnabbas_bot.translate")

# Gemini (be'itsa) API key - GEMINI_API_KEY environment variable be'bot.py
# tekemakayanet yiseral (Railway lay yetesetefe). Google Translate ye'wich
# (unofficial) endpoint bota bota "429 Too Many Requests" bicha aynseral
# silhone, Gemini official API tekemetenal - yishaltal.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# URL/link pattern: http(s)://..., www...., t.me/..., @username mentions
_LINK_PATTERN = re.compile(
    r"(https?://\S+)"        # http:// weyim https:// yalew link
    r"|(www\.\S+)"            # www. bekemejemer link
    r"|(t\.me/\S+)"           # t.me/... link
    r"|(@[A-Za-z0-9_]{4,})",  # @channel_username mention
    re.IGNORECASE,
)


def strip_links(text: str) -> str:
    """Post text wist yalut hulum link'woch (http/https, www, t.me/...,
    @mentions) sildo, netsa tekst bicha yimelesal. Betefit yalu blank
    meseraTawoch yiseredalu."""
    if not text:
        return text
    cleaned = _LINK_PATTERN.sub("", text)
    # ke'link sile teserezu yizoral yehonu redundant space/newline yiredalu
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
    return cleaned.strip()


def fetch_source_posts(source_username: str):
    """https://t.me/s/<username> lay yalut posts'n (id, text, photo_url)
    tuple aድርጎ yimelesal, ke'aroge wede addis (ascending order) tesetreo.
    photo_url yalew post (ke text gara weyim bicha) inqim yiketetal;
    text weyim photo teraw yelewim posts (video/sticker bicha, ...)
    yileFalu."""
    url = f"https://t.me/s/{source_username}"
    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (compatible; IbnAbbasBot/1.0)"
        })
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Source channel altichalem meswet: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []

    for wrap in soup.select("div.tgme_widget_message_wrap"):
        msg_div = wrap.select_one("div.tgme_widget_message")
        if not msg_div or not msg_div.has_attr("data-post"):
            continue

        data_post = msg_div["data-post"]  # format: "username/12345"
        try:
            msg_id = int(data_post.split("/")[-1])
        except (ValueError, IndexError):
            continue

        text = ""
        text_div = msg_div.select_one("div.tgme_widget_message_text")
        if text_div:
            # <br> tags'n wede newline inqeyir, keza tag'wochun inawta
            for br in text_div.find_all("br"):
                br.replace_with("\n")
            raw_text = text_div.get_text()
            text = html.unescape(raw_text).strip()

        photo_url = None
        photo_wrap = msg_div.select_one("a.tgme_widget_message_photo_wrap")
        if photo_wrap and photo_wrap.has_attr("style"):
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", photo_wrap["style"])
            if m:
                photo_url = html.unescape(m.group(1))

        if text or photo_url:
            posts.append((msg_id, text, photo_url))

    posts.sort(key=lambda p: p[0])
    return posts


def _translate_via_gemini(text: str):
    """Gemini API (be'itsa, official) teqemto tekst wede Amarigna
    yitergumal. Key kaleseteme None yimelesal."""
    if not GEMINI_API_KEY:
        return None
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"content-type": "application/json"},
            json={
                "system_instruction": {
                    "parts": [{
                        "text": (
                            "Antchi professional translator neh. Yemitset "
                            "tekstun wede Amarigna bicha tergum. "
                            "Ye'islamawi/ye'kuranawi ewnetegnnet (Quran "
                            "ayat, hadith, scholar simoch) inde'yalew "
                            "temeleket, be'metirgum yizoral. Bicha "
                            "yeteregeme tekst mles - lela aymelekt "
                            "(explanation, quote marks, meglecha kalat)."
                        )
                    }]
                },
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {"maxOutputTokens": 2048},
            },
            timeout=30,
        )
        if resp.status_code == 429:
            logger.warning("Gemini 429 (bezu tebik).")
            return None
        resp.raise_for_status()
        data = resp.json()
        piece = "".join(
            part.get("text", "")
            for part in data["candidates"][0]["content"]["parts"]
        )
        return piece.strip() or None
    except Exception as e:
        logger.warning(f"Gemini translation altichalem: {e}")
        return None


def translate_to_amharic(text: str):
    """Tekst wede Amarigna yitergumal (Gemini API teqemto, be'itsa,
    official). Betchigir None yimelesal.

    Gemini "429" sinemelis 2 gize be'igiziyawi (backoff) inedegemewalen."""
    chunk_size = 6000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]

    translated_chunks = []
    for chunk in chunks:
        piece = None
        for attempt in range(3):
            piece = _translate_via_gemini(chunk)
            if piece is not None:
                break
            wait_s = 5 * (attempt + 1)
            logger.warning(
                f"Translation attempt {attempt + 1}/3 altchalem - {wait_s} "
                f"second qoyto indegena inmokoral."
            )
            time.sleep(wait_s)

        if piece is None:
            logger.warning("Translation ke 3 gize behuala kalteseka, yalfal.")
            return None
        translated_chunks.append(piece)
        time.sleep(1)  # chunks mekakel tinishu ereft

    translated = "".join(translated_chunks).strip()
    return translated or None
