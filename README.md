# IBN ABBAS QURAN CENTER BOT

Le https://t.me/ibnuabbas_hara channel beken 3 gize (ጠዋት 06:00, ከሰዓት 13:00, ማታ 19:00 - Ethiopia sea'at) tirmitawi textn (5-7 mesmer) na 1 tiyake yemileTF Telegram bot.

## 1. Bot Token maggenet (BotFather)

1. Telegram lay `@BotFather` fetu.
2. `/newbot` bilu ymelu.
3. Bot sim (lemisale: `IBN ABBAS QURAN CENTER BOT`) na username (lemisale: `ibnabbas_center_bot`) situ.
4. BotFather bicha **token** yset'wal (lemisale: `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`) - eziyan aznebiw!

## 2. Bot'u weda channel admin madreg

1. Weda `@ibnuabbas_hara` channel hidu.
2. Channel settings → Administrators → Add Administrator.
3. Ale sira lay yeserachihutn bot fetu.
4. Betam yasfeligew **"Post Messages"** permission bot lay meregagex mastawek alebet.

## 3. Bot'u lememerya (computer/server lay)

```bash
# 1) Yalut file'wochn had folder wisit adirgu (kezih terekomew directory)
cd ibnabbas_bot

# 2) Yemiferelgut library'woch tzeneb
pip install -r requirements.txt

# 3) Bot token'wo environment variable adirgo situ (dehninetu lemetebek)
export BOT_TOKEN="ANCHI_TOKEN_ZIH_YIGEBA"

# 4) Bot'u aswaal
python3 bot.py
```

Bot'u eska sitzegut (weyim eska computer'u sikefel) yiseral. Bot 24/7 (bezm-ken) endiseral bidzefelgu:
- **Render.com**, **Railway.app**, weyim **PythonAnywhere** yemibalu netibawi free/paid hosting service'wochn mekute yichalal (24/7 yasserallu).
- Weyim betam yeserach VPS/server kalachihu, be `screen` weyim `tmux` weyim `systemd` service adirgo aswaal.

## 4. AI addis yizet endifetir (rejawi/optional - yemimeker)

Bot'u **hybrid** mode yiseral፦
1. Bewegen (be'iyalu post gize) Anthropic API teqemto **addis, yaltederese** post yifetral.
2. Bicha ANTHROPIC_API_KEY seteqemetu weyim network gudai ka'aggagemet, kefit
   siseram bicha ke `content.py` wist yalut 55 fallback poስቶች lay yimelesal
   (beteqetel yiletefal, adigdegimm).

AI mode leasadireg:

```bash
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"
```

Key le maggenet: https://console.anthropic.com

**Yalefu 40 AI-generated rieswoch (topics)** `state.json` wist tezareb - dagimo
endayimeta lekelakay yiyazal. Ke AI kafit ba'iginnetu, ke fallback list
yemiwet post kegn key yalebet gudai yelewim.

⚠️ **Weχ**: AI teqemto (dynamically generated) content ke Claude/AI kalefiw
gize kalebet, betekelakay quote/hadith text ayizeQotim - ke akrari be'ras'u
qal aregagi bicha yisetal. Betam, kalechihu, yale ba'ale-timhert (ustaz) gara
ke publishing befit yasayu bicha eminekker, be'akal AI content adarigo
lemekeyer weyim leme'asamat.

## 5. Ke default gize weyim ke tiyakewoch le mekeyer bicha ychlalu

- **Sea'atochn lemekeyer**: `bot.py` wisit `POST_TIMES = ["06:00", "13:00", "19:00"]` yale menged eyawet ychlalu.
- **Textochn/tiyakewochn lemekeyer weyim leme mecher**: `content.py` wisit `POSTS` list wisit alu. Aleu format temeslo aditsu yichlalu:

```python
{
    "text": "...5-7 mesmer text...",
    "question": "❓ ...tiyake..."
},
```

Bot beketel post index (`state.json` wisit yetederese) sirawun beterepe yiketetlal - slezih repeat sayiadergu.

## 6. Manastawes yemigebaw neger

Ye textochu na tiyakewochu ye'general islamawi timhert (sabr, ikhlas, salat, sedeqa, ወዘተ) new yemiyazu, tebibegn hadith/quran verse siquotu betam yetederegut/yetewequ bicha new. Kefitwoch weyim ke ba'ale-timhert (ustaz) gara before publishing eyasayu bicha eminekker.
