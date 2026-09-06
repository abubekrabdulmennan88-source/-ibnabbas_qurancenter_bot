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
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ibnabbas_bot.translate")

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
    """https://t.me/s/<username> lay yalut posts'n (id, text) tuple aድርጎ
    yimelesal, ke'aroge wede addis (ascending order) tesetreo."""
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

        text_div = msg_div.select_one("div.tgme_widget_message_text")
        if not text_div:
            # Media-only post gara text yelewim - inleFewal
            continue

        # <br> tags'n wede newline inqeyir, keza tag'wochun inawta
        for br in text_div.find_all("br"):
            br.replace_with("\n")
        raw_text = text_div.get_text()
        text = html.unescape(raw_text).strip()

        if text:
            posts.append((msg_id, text))

    posts.sort(key=lambda p: p[0])
    return posts


def translate_to_amharic(text: str):
    """Google Translate ye'wich (unofficial, netsa, API key yalasfeleg)
    endpoint teqemto tekst wede Amarigna yitergumal. Betchigir None
    yimelesal."""
    # Google's endpoint capiya (~5000 character) sile alebet, ye'iywun
    # betikikil linqefil bicha - ye'source posts sile achir aychegerim.
    chunk_size = 4500
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]

    translated_chunks = []
    for chunk in chunks:
        try:
            resp = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": "am",
                    "dt": "t",
                    "q": chunk,
                },
                headers={"User-Agent": "Mozilla/5.0 (compatible; IbnAbbasBot/1.0)"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            # data[0] is a list of [translated_segment, original_segment, ...]
            piece = "".join(seg[0] for seg in data[0] if seg[0])
            translated_chunks.append(piece)
        except Exception as e:
            logger.warning(f"Translation altichalem: {e}")
            return None

    translated = "".join(translated_chunks).strip()
    return translated or None
