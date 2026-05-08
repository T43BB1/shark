import json
import os
from flask import Flask, render_template_string, request
from collection import get_collection_items, get_collection_item

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

app = Flask(__name__)

MOODS = {
    "calm": {
        "label": "Calm",
        "shark_name": "Whale Shark",
        "shark_name_ko": "고래상어",
        "emoji": "🦈",
        "keywords": ["평온", "차분", "괜찮", "잔잔", "편안", "안정"],
        "theme": "calm",
        "primary": "#38bdf8",
        "secondary": "#0f766e",
        "message": "커다란 고래상어가 천천히 곁을 지나가요. 지금은 서두르지 않아도 괜찮아요.",
    },
    "happy": {
        "label": "Happy",
        "shark_name": "Leopard Shark",
        "shark_name_ko": "레오파드상어",
        "emoji": "🫧",
        "keywords": ["좋아", "행복", "기쁨", "신나", "즐거", "웃", "최고"],
        "theme": "happy",
        "primary": "#5eead4",
        "secondary": "#facc15",
        "message": "레오파드상어가 밝은 물결 사이를 지나가요. 오늘의 좋은 기분을 조금 더 즐겨도 좋아요.",
    },
    "angry": {
        "label": "Angry",
        "shark_name": "Great White Shark",
        "shark_name_ko": "백상아리",
        "emoji": "🌊",
        "keywords": ["화", "짜증", "열받", "분노", "빡", "싫어", "억울"],
        "theme": "angry",
        "primary": "#f87171",
        "secondary": "#7f1d1d",
        "message": "백상아리가 거친 물살을 가르고 지나가요. 올라온 감정을 밀어내지 말고 천천히 흘려보내요.",
    },
    "sad": {
        "label": "Sad",
        "shark_name": "Greenland Shark",
        "shark_name_ko": "그린란드상어",
        "emoji": "🌧️",
        "keywords": ["슬퍼", "우울", "눈물", "외로", "힘들", "가라앉", "속상", "먹구름"],
        "theme": "sad",
        "primary": "#818cf8",
        "secondary": "#312e81",
        "message": "그린란드상어가 깊은 바다에서 조용히 곁을 지켜요. 조금 가라앉는 날도 괜찮아요.",
    },
    "tired": {
        "label": "Tired",
        "shark_name": "Nurse Shark",
        "shark_name_ko": "너스상어",
        "emoji": "💤",
        "keywords": ["피곤", "지침", "졸려", "무기력", "쉬고", "번아웃", "힘빠"],
        "theme": "tired",
        "primary": "#cbd5e1",
        "secondary": "#475569",
        "message": "너스상어가 바닥 가까이 편안히 머물러요. 지금 필요한 건 속도가 아니라 회복이에요.",
    },
    "anxious": {
        "label": "Anxious",
        "shark_name": "Hammerhead Shark",
        "shark_name_ko": "귀상어",
        "emoji": "🌫️",
        "keywords": ["불안", "걱정", "긴장", "초조", "무서", "떨려", "복잡", "신경쓰"],
        "theme": "anxious",
        "primary": "#c084fc",
        "secondary": "#064e3b",
        "message": "귀상어가 넓은 시야로 주변을 살펴요. 걱정은 한 번에 하나씩만 바라봐도 충분해요.",
    },
    "excited": {
        "label": "Excited",
        "shark_name": "Mako Shark",
        "shark_name_ko": "청상아리",
        "emoji": "✨",
        "keywords": ["설레", "기대", "두근", "재밌", "흥분", "빨리", "궁금"],
        "theme": "excited",
        "primary": "#facc15",
        "secondary": "#fb7185",
        "message": "청상아리가 빠르게 빛을 가르며 헤엄쳐요. 지금의 에너지를 좋은 방향으로 써봐요.",
    },
}

DEFAULT_KEY = "calm"
ALLOWED_MOODS = list(MOODS.keys())
COLLECTION_ITEMS = get_collection_items()
ALLOWED_SHARK_KEYS = list(COLLECTION_ITEMS.keys())
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def analyze_mood_keyword(text: str):
    normalized = text.replace(" ", "").lower()
    scores = {k: 0 for k in MOODS.keys()}

    for key, mood in MOODS.items():
        for keyword in mood["keywords"]:
            if keyword in normalized:
                scores[key] += 1

    total = sum(scores.values())
    if total == 0:
        return {
            "main_key": DEFAULT_KEY,
            "percents": {k: 0 for k in MOODS.keys()},
            "confidence": 35,
            "reason": "명확히 매칭되는 감정 키워드가 없어 기본값으로 분류했습니다.",
            "tone": "neutral",
            "recommended_action": "조금 더 구체적으로 감정을 적으면 더 정확하게 분석할 수 있어요.",
            "source": "keyword fallback",
        }

    percents = {k: int((v / total) * 100) for k, v in scores.items()}
    main_key = max(scores, key=scores.get)

    return {
        "main_key": main_key,
        "percents": percents,
        "confidence": min(95, 45 + scores[main_key] * 15),
        "reason": "입력 문장에 포함된 감정 키워드를 기준으로 분석했습니다.",
        "tone": "keyword-based",
        "recommended_action": "GEMINI_API_KEY를 설정하면 문맥 기반으로 더 자연스럽게 분석됩니다.",
        "source": "keyword fallback",
    }


def normalize_ai_result(data: dict):
    main_key = data.get("main_mood", DEFAULT_KEY)
    if main_key not in ALLOWED_MOODS:
        main_key = DEFAULT_KEY

    shark_key = data.get("shark_key", main_key)
    if shark_key not in ALLOWED_SHARK_KEYS:
        shark_key = main_key

    raw_scores = data.get("scores", {}) or {}
    scores = {}
    for key in ALLOWED_MOODS:
        try:
            value = int(raw_scores.get(key, 0))
        except (TypeError, ValueError):
            value = 0
        scores[key] = max(0, min(100, value))

    if sum(scores.values()) == 0:
        scores[main_key] = 100

    try:
        confidence = int(data.get("confidence", 70))
    except (TypeError, ValueError):
        confidence = 70



    return {
        "main_key": main_key,
        "percents": scores,
        "confidence": max(0, min(100, confidence)),
        "reason": data.get("reason", "문장의 분위기와 맥락을 기준으로 감정을 분석했습니다."),
        "tone": data.get("tone", "contextual"),
        "recommended_action": data.get("recommended_action", "지금 감정을 짧게 기록해두면 좋아요!"),
        "source": "AI analysis result",
        "shark_key": shark_key,
    }


def analyze_mood_gemini(text: str):
    if not text.strip():
        return analyze_mood_keyword(text)

    if genai is None or types is None:
        fallback = analyze_mood_keyword(text)
        fallback["reason"] = "google-genai 패키지가 설치되어 있지 않아 키워드 방식으로 분석했습니다."
        return fallback

    if not os.getenv("GEMINI_API_KEY"):
        fallback = analyze_mood_keyword(text)
        fallback["reason"] = "GEMINI_API_KEY가 설정되어 있지 않아 키워드 방식으로 분석했습니다."
        return fallback

    schema = {
        "type": "object",
        "properties": {
            "main_mood": {"type": "string", "enum": ALLOWED_MOODS},
            "scores": {
                "type": "object",
                "properties": {key: {"type": "integer"} for key in ALLOWED_MOODS},
            },
            "confidence": {"type": "integer"},
            "tone": {"type": "string"},
            "reason": {"type": "string"},
            "recommended_action": {"type": "string"},
            "shark_key": {"type": "string", "enum": ALLOWED_SHARK_KEYS},
        },
        "required": ["main_mood", "shark_key", "scores", "confidence", "tone", "reason", "recommended_action"],
    }

    prompt = f"""
너는 한국어 일기/짧은 문장을 읽고 현재 감정을 분석하는 감정 분류기야.
반드시 아래 감정 중 하나를 main_mood로 골라.

- calm: 평온, 안정, 차분함
- happy: 기쁨, 만족, 즐거움
- angry: 분노, 짜증, 억울함
- sad: 슬픔, 우울, 가라앉음
- tired: 피로, 무기력, 번아웃
- anxious: 불안, 걱정, 긴장, 신경 쓰임
- excited: 설렘, 기대, 들뜸

기준:
- 직접적인 감정 단어가 없어도 문맥, 은유, 날씨 표현, 말투를 보고 판단해.
- 예: "오늘 먹구름이 신경쓰이네."는 calm이 아니라 anxious 또는 sad 쪽 뉘앙스로 봐야 해.
- 장난감 프로젝트용 분석이므로 의학적 진단처럼 쓰지 마.
- reason과 recommended_action은 한국어로 짧고 부드럽게 써.
- scores는 각 감정별 0~100 정수로 써.

main_mood는 감정 카테고리이고, shark_key는 해당 감정에 어울리는 실제 상어 카드 key야.
반드시 shark_key는 아래 목록 중 하나로 골라.

{ALLOWED_SHARK_KEYS}

예:
- 우울하지만 거대하고 천천히 흘러가는 느낌이면 sad_3
- 깊고 차가운 침잠이면 sad
- 외롭고 기괴한 심해 느낌이면 sad_2

분석할 문장:
{text}
"""

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        data = json.loads(response.text)
        return normalize_ai_result(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        fallback = analyze_mood_keyword(text)
        fallback["reason"] = f"AI 분석 오류: {type(e).__name__}: {e}"
        fallback["source"] = f"error: {type(e).__name__}"
        return fallback


HTML = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shark Mood Gemini</title>
<style>
body {
    font-family: Arial, sans-serif;
    margin: 0;
    background: linear-gradient(135deg, #020617, #0f172a, #164e63);
    color: white;
    min-height: 100vh;
}
body.calm { background: linear-gradient(135deg, #06283d, #136f8f); }
body.happy { background: linear-gradient(135deg, #075985, #14b8a6); }
body.angry { background: linear-gradient(135deg, #190a0a, #7f1d1d); }
body.sad { background: linear-gradient(135deg, #020617, #312e81); }
body.tired { background: linear-gradient(135deg, #111827, #475569); }
body.anxious { background: linear-gradient(135deg, #10051f, #064e3b); }
body.excited { background: linear-gradient(135deg, #3b0764, #fb7185); }
.container { max-width: 980px; margin: auto; padding: 40px 20px; }
.nav { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 28px; }
.logo { font-weight: 900; font-size: 20px; }
.nav a { color: rgba(255,255,255,0.75); text-decoration: none; margin-left: 12px; font-size: 14px; }
.hero, .card { padding: 34px; border-radius: 28px; background: rgba(255,255,255,0.11); border: 1px solid rgba(255,255,255,0.18); box-shadow: 0 30px 80px rgba(0,0,0,0.28); }
h1 { margin: 0 0 10px; font-size: clamp(40px, 7vw, 76px); letter-spacing: -0.06em; line-height: 0.95; }
.desc, .meta { color: rgba(255,255,255,0.72); line-height: 1.7; }
textarea { width: 100%; min-height: 120px; padding: 16px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.22); background: rgba(0,0,0,0.22); color: white; font-size: 16px; margin-top: 18px; box-sizing: border-box; }
button { margin-top: 12px; padding: 14px 18px; border-radius: 16px; border: 0; background: #38bdf8; font-weight: 900; cursor: pointer; }
button:hover { filter: brightness(1.08); transform: translateY(-1px); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 22px; }
.card { padding: 22px; }
.card h2, .card h3 { margin-top: 0; }
.mood-main { font-size: 44px; margin: 10px 0; }
.badge { display: inline-block; padding: 7px 10px; border-radius: 999px; background: rgba(56,189,248,0.22); color: #e0f2fe; font-weight: 800; font-size: 13px; }
.bar { height: 14px; border-radius: 10px; margin: 7px 0 14px; background: rgba(15,23,42,0.72); overflow: hidden; }
.fill { height: 100%; border-radius: 10px; background: #38bdf8; }
.code { background: rgba(0,0,0,0.25); padding: 14px; border-radius: 14px; color: rgba(255,255,255,0.78); line-height: 1.6; font-size: 14px; }
.shark-swim { font-size: 82px; animation: swim 4s ease-in-out infinite; display: inline-block; filter: drop-shadow(0 20px 24px rgba(0,0,0,.35)); }
.comfort-btn { width: 100%; margin-top: 18px; font-size: 16px; background: white; color: #06111f; }

.visualizer-modal {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: none;
    overflow: hidden;
    background: #020617;
}
.visualizer-modal.active { display: block; }
#sharkCanvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
}
.viz-ui {
    position: absolute;
    top: 8%;
    right: 8%;
    z-index: 2;
    text-align: right;
    pointer-events: none;
}
.viz-pill {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 999px;
    background: rgba(255,255,255,0.94);
    color: #020617;
    font-weight: 900;
    margin-bottom: 16px;
}
.viz-title {
    font-size: clamp(30px, 4vw, 54px);
    letter-spacing: 0.18em;
    font-weight: 300;
    text-transform: lowercase;
    text-shadow: 0 10px 30px rgba(0,0,0,0.32);
}
.viz-subtitle {
    margin-top: 18px;
    max-width: 430px;
    color: rgba(255,255,255,0.78);
    line-height: 1.7;
    font-size: 15px;
}
.close-viz {
    position: absolute;
    right: 28px;
    bottom: 28px;
    z-index: 3;
    background: rgba(255,255,255,0.92);
    color: #020617;
}

.collection-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-top: 18px;
}

.name-card {
    padding: 18px;
    border-radius: 20px;
    background: rgba(255,255,255,0.11);
    border: 1px solid rgba(255,255,255,0.18);
    cursor: pointer;
}

.name-card.locked {
    opacity: 0.35;
    filter: grayscale(1);
    cursor: default;
}

.name-card h4 {
    margin: 0 0 8px;
}

.collection-detail {
    position: fixed;
    inset: 0;
    display: none;
    z-index: 10000;
    background: rgba(2,6,23,0.72);
    backdrop-filter: blur(10px);
    align-items: center;
    justify-content: center;
    padding: 24px;
}

.collection-detail.active {
    display: flex;
}

.collection-detail-card {
    max-width: 560px;
    width: 100%;
    padding: 28px;
    border-radius: 28px;
    background: rgba(15,23,42,0.96);
    border: 1px solid rgba(255,255,255,0.18);
}

@keyframes swim { 0%, 100% { transform: translateX(0) rotate(-5deg); } 50% { transform: translateX(34px) rotate(5deg); } }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } .nav { align-items: flex-start; flex-direction: column; } .viz-ui { left: 24px; right: 24px; text-align: left; } }
</style>
</head>
<body class="{{ result.theme if result else 'calm' }}">
<div class="container">
    <div class="nav">
        <div class="logo">🦈 Shark Mood Analysis</div>
        <a href="#collection">Collection</a>
    </div>

    <section class="hero" id="analyze">
        <span class="badge">Mood Context Analysis</span>
        <h1>What shark are you today?</h1>
        <p class="desc"> 
 
            오늘의 감정을 입력해주세요. 각 감정과 어울리는 상어가 위로해줄거에요.
        </p>
        <div class="shark-swim">🦈</div>
        <form method="POST">
            <textarea name="text" placeholder="예: 오늘 먹구름이 신경쓰이네.">{{ text }}</textarea>
            <button>내 상어 찾기</button>
        </form>
    </section>

    {% if result %}
    <div class="grid">
        <section class="card">
            <span class="badge">{{ analysis.source }}</span>
            <div class="mood-main">{{ result.emoji }} {{ result.shark_name_ko }}</div>
            <p class="meta"><strong>Species:</strong> {{ result.shark_name }}</p>
            <p class="meta"><strong>Mood:</strong> {{ result.label }}</p>
            <p class="meta"><strong>Confidence:</strong> {{ analysis.confidence }}%</p>
            <p class="meta"><strong>Tone:</strong> {{ analysis.tone }}</p>
            <p class="meta"><strong>Reason:</strong> {{ analysis.reason }}</p>
            <p class="meta"><strong>추천:</strong> {{ analysis.recommended_action }}</p>
            <button class="comfort-btn" onclick="openVisualizer()">{{ result.shark_name_ko }}에게 위로받기</button>
        </section>

        <section class="card" id="breakdown">
            <h3>Emotion Breakdown</h3>
            {% for key, value in percents.items() %}
            <div>
                <strong>{{ moods[key].label }} {{ moods[key].emoji }} ({{ value }}%)</strong>
                <div class="bar"><div class="fill" style="width: {{ value }}%"></div></div>
            </div>
            {% endfor %}
        </section>
    </div>
    {% endif %}
</div>

<section class="card" id="collection" style="margin-top: 22px;">
    <h3>Shark Collection</h3>
    <p class="meta">
        감정 분석을 통해 발견한 상어 네임카드가 이곳에 수집됩니다.
    </p>
    <div id="collectionGrid" class="collection-grid"></div>
</section>

<div id="collectionDetail" class="collection-detail">
    <div class="collection-detail-card">
        <button onclick="closeCollectionDetail()">닫기</button>
        <h2 id="detailTitle"></h2>
        <p id="detailSummary" class="meta"></p>
        <div id="detailBody" class="meta"></div>
    </div>
</div>

<div class="visualizer-modal" id="visualizerModal">
    <canvas id="sharkCanvas"></canvas>
    <div class="viz-ui">
        <div class="viz-pill" id="vizPill">{{ result.shark_name_ko if result else '' }}</div>
        <div class="viz-title" id="vizTitle">shark mood visualizer</div>
        <div class="viz-subtitle" id="vizSubtitle">{{ result.message if result else '' }}</div>
    </div>
    <button class="close-viz" onclick="closeVisualizer()">닫기</button>
</div>

<script>
const collectionData = {{ collection_json | safe }};
const COLLECTION_KEY = "sharkMoodCollection";

function getCollectedSharks() {
    try {
        return JSON.parse(localStorage.getItem(COLLECTION_KEY)) || [];
    } catch {
        return [];
    }
}

function saveCollectedSharks(items) {
    localStorage.setItem(COLLECTION_KEY, JSON.stringify([...new Set(items)]));
}

function collectCurrentShark() {
    if (!currentMood || !currentMood.key || currentMood.key === null) return;

    const collected = getCollectedSharks();
    if (!collected.includes(currentMood.key)) {
        collected.push(currentMood.key);
        saveCollectedSharks(collected);
    }
}

function renderCollection() {
    const grid = document.getElementById("collectionGrid");
    if (!grid) return;

    const collected = getCollectedSharks();
    grid.innerHTML = "";

    Object.entries(collectionData).forEach(([key, item]) => {
        const isCollected = collected.includes(key);

        const card = document.createElement("div");
        card.className = `name-card ${isCollected ? "" : "locked"}`;
        card.style.borderColor = isCollected ? item.color : "rgba(255,255,255,0.18)";

        card.innerHTML = `
            <h4>${isCollected ? (item.emoji || '') + ' ' + item.title : "???"}</h4>
            <p class="meta">${isCollected ? item.species : "아직 발견하지 못한 상어입니다."}</p>
            <span class="badge">${isCollected ? item.mood : "Locked"}</span>
        `;

        if (isCollected) {
            card.onclick = () => openCollectionDetail(key);
        }

        grid.appendChild(card);
    });
}

function openCollectionDetail(key) {
    const item = collectionData[key];
    if (!item) return;

    document.getElementById("detailTitle").textContent = (item.emoji || '') + ' ' + item.title;
    document.getElementById("detailSummary").textContent = item.summary;
    document.getElementById("detailBody").innerHTML = `
        <div style="font-size:64px;text-align:center;margin:12px 0;">${item.emoji || '🦈'}</div>
        <p><strong>Species:</strong> ${item.species}</p>
        <p><strong>Mood:</strong> ${item.mood}</p>
        <p><strong>Habitat:</strong> ${item.habitat}</p>
        <p><strong>Personality:</strong> ${item.personality}</p>
        <p><strong>Keywords:</strong> ${item.keywords.join(", ")}</p>
        <p style="margin-top: 14px;">${item.description}</p>
    `;

    document.getElementById("collectionDetail").classList.add("active");
}

function closeCollectionDetail() {
    document.getElementById("collectionDetail").classList.remove("active");
}

const currentMood = {{ current_mood_json | safe }};

collectCurrentShark();
renderCollection();

function openVisualizer() {
    const modal = document.getElementById("visualizerModal");
    modal.classList.add("active");
    startSharkVisualizer(currentMood);
}

function closeVisualizer() {
    document.getElementById("visualizerModal").classList.remove("active");
    stopSharkVisualizer();
}

let animationId = null;
let particles = [];
let bgParticles = [];
let lines = [];
let backgroundSharks = [];
let canvas, ctx, W, H;

function resizeCanvas() {
    canvas = document.getElementById("sharkCanvas");
    ctx = canvas.getContext("2d");
    W = canvas.width = window.innerWidth * window.devicePixelRatio;
    H = canvas.height = window.innerHeight * window.devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    W = window.innerWidth;
    H = window.innerHeight;
}

function rand(min, max) { return Math.random() * (max - min) + min; }

function pointInPolygon(point, polygon) {
    const x = point.x, y = point.y;
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].x, yi = polygon[i].y;
        const xj = polygon[j].x, yj = polygon[j].y;
        const intersect = ((yi > y) !== (yj > y)) &&
            (x < (xj - xi) * (y - yi) / ((yj - yi) || 0.00001) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

function makeSpeciesShape(species, cx, cy, scale) {
    const s = scale;

    // 각 종별 실루엣을 과장해서 구분감이 나도록 구성
    // 좌측 = 꼬리 / 우측 = 머리

    if (species === "Whale Shark") {
        // 고래상어: 매우 크고 둥근 몸통, 넓은 머리, 짧은 꼬리
        return [
            {x: cx - 4.8*s, y: cy - 0.2*s},
            {x: cx - 3.9*s, y: cy - 0.95*s},
            {x: cx - 2.1*s, y: cy - 1.25*s},
            {x: cx + 0.4*s, y: cy - 1.18*s},
            {x: cx + 2.7*s, y: cy - 0.82*s},
            {x: cx + 4.25*s, y: cy - 0.38*s},
            {x: cx + 4.95*s, y: cy + 0.05*s},
            {x: cx + 4.35*s, y: cy + 0.55*s},
            {x: cx + 2.4*s, y: cy + 0.95*s},
            {x: cx - 0.2*s, y: cy + 1.12*s},
            {x: cx - 2.4*s, y: cy + 0.9*s},
            {x: cx - 3.7*s, y: cy + 0.52*s},
            {x: cx - 4.75*s, y: cy + 1.05*s},
            {x: cx - 4.35*s, y: cy + 0.18*s},
            {x: cx - 5.1*s, y: cy - 0.95*s},
        ];
    }

    if (species === "Great White Shark") {
        // 백상아리: 날카로운 머리, 큰 삼각 등지느러미, 강한 꼬리
        return [
            {x: cx - 4.75*s, y: cy - 0.05*s},
            {x: cx - 3.75*s, y: cy - 0.72*s},
            {x: cx - 2.25*s, y: cy - 0.78*s},
            {x: cx - 0.75*s, y: cy - 1.95*s},
            {x: cx - 0.18*s, y: cy - 0.72*s},
            {x: cx + 2.15*s, y: cy - 0.55*s},
            {x: cx + 4.85*s, y: cy - 0.04*s},
            {x: cx + 3.1*s, y: cy + 0.5*s},
            {x: cx + 0.75*s, y: cy + 0.72*s},
            {x: cx - 1.2*s, y: cy + 0.52*s},
            {x: cx - 2.0*s, y: cy + 1.35*s},
            {x: cx - 1.82*s, y: cy + 0.45*s},
            {x: cx - 3.55*s, y: cy + 0.42*s},
            {x: cx - 5.2*s, y: cy + 1.22*s},
            {x: cx - 4.35*s, y: cy + 0.08*s},
            {x: cx - 5.22*s, y: cy - 1.08*s},
        ];
    }

    if (species === "Hammerhead Shark") {
        // 귀상어: 머리를 T자 형태로 표현
        return [
            {x: cx - 4.65*s, y: cy - 0.08*s},
            {x: cx - 3.55*s, y: cy - 0.7*s},
            {x: cx - 2.15*s, y: cy - 0.78*s},
            {x: cx - 0.9*s, y: cy - 1.55*s},
            {x: cx - 0.25*s, y: cy - 0.62*s},
            {x: cx + 2.7*s, y: cy - 0.48*s},
            {x: cx + 3.15*s, y: cy - 1.08*s},
            {x: cx + 5.15*s, y: cy - 0.92*s},
            {x: cx + 5.35*s, y: cy - 0.32*s},
            {x: cx + 3.65*s, y: cy - 0.1*s},
            {x: cx + 3.65*s, y: cy + 0.1*s},
            {x: cx + 5.35*s, y: cy + 0.32*s},
            {x: cx + 5.15*s, y: cy + 0.92*s},
            {x: cx + 3.15*s, y: cy + 1.08*s},
            {x: cx + 2.65*s, y: cy + 0.52*s},
            {x: cx + 0.75*s, y: cy + 0.68*s},
            {x: cx - 0.9*s, y: cy + 0.55*s},
            {x: cx - 1.8*s, y: cy + 1.2*s},
            {x: cx - 1.6*s, y: cy + 0.43*s},
            {x: cx - 3.65*s, y: cy + 0.38*s},
            {x: cx - 5.05*s, y: cy + 1.08*s},
            {x: cx - 4.3*s, y: cy + 0.08*s},
            {x: cx - 5.05*s, y: cy - 1.02*s},
        ];
    }

    if (species === "Mako Shark") {
        // 청상아리: 길고 얇고 빠른 화살형
        return [
            {x: cx - 5.0*s, y: cy - 0.02*s},
            {x: cx - 3.95*s, y: cy - 0.55*s},
            {x: cx - 2.0*s, y: cy - 0.52*s},
            {x: cx - 0.72*s, y: cy - 1.55*s},
            {x: cx - 0.18*s, y: cy - 0.48*s},
            {x: cx + 2.75*s, y: cy - 0.34*s},
            {x: cx + 5.35*s, y: cy - 0.02*s},
            {x: cx + 3.05*s, y: cy + 0.36*s},
            {x: cx + 0.7*s, y: cy + 0.5*s},
            {x: cx - 1.2*s, y: cy + 0.38*s},
            {x: cx - 2.0*s, y: cy + 1.08*s},
            {x: cx - 1.75*s, y: cy + 0.32*s},
            {x: cx - 3.8*s, y: cy + 0.32*s},
            {x: cx - 5.35*s, y: cy + 0.92*s},
            {x: cx - 4.45*s, y: cy + 0.06*s},
            {x: cx - 5.35*s, y: cy - 0.92*s},
        ];
    }

    if (species === "Nurse Shark") {
        // 너스상어: 낮고 둥글고 바닥에 붙은 듯한 형태
        return [
            {x: cx - 4.45*s, y: cy + 0.18*s},
            {x: cx - 3.55*s, y: cy - 0.32*s},
            {x: cx - 1.75*s, y: cy - 0.42*s},
            {x: cx - 0.4*s, y: cy - 0.82*s},
            {x: cx + 0.05*s, y: cy - 0.42*s},
            {x: cx + 2.05*s, y: cy - 0.32*s},
            {x: cx + 4.25*s, y: cy + 0.02*s},
            {x: cx + 3.45*s, y: cy + 0.55*s},
            {x: cx + 1.0*s, y: cy + 0.78*s},
            {x: cx - 1.5*s, y: cy + 0.74*s},
            {x: cx - 2.35*s, y: cy + 0.98*s},
            {x: cx - 2.15*s, y: cy + 0.55*s},
            {x: cx - 3.5*s, y: cy + 0.55*s},
            {x: cx - 4.95*s, y: cy + 0.95*s},
            {x: cx - 4.22*s, y: cy + 0.18*s},
            {x: cx - 4.82*s, y: cy - 0.6*s},
        ];
    }

    if (species === "Greenland Shark") {
        // 그린란드상어: 두껍고 둔중한 심해형
        return [
            {x: cx - 4.7*s, y: cy + 0.03*s},
            {x: cx - 3.7*s, y: cy - 0.68*s},
            {x: cx - 1.75*s, y: cy - 0.86*s},
            {x: cx - 0.5*s, y: cy - 1.12*s},
            {x: cx + 0.2*s, y: cy - 0.82*s},
            {x: cx + 2.4*s, y: cy - 0.62*s},
            {x: cx + 4.45*s, y: cy - 0.18*s},
            {x: cx + 4.9*s, y: cy + 0.08*s},
            {x: cx + 3.72*s, y: cy + 0.46*s},
            {x: cx + 1.42*s, y: cy + 0.78*s},
            {x: cx - 1.45*s, y: cy + 0.74*s},
            {x: cx - 2.25*s, y: cy + 0.94*s},
            {x: cx - 2.05*s, y: cy + 0.5*s},
            {x: cx - 3.62*s, y: cy + 0.55*s},
            {x: cx - 5.05*s, y: cy + 0.95*s},
            {x: cx - 4.38*s, y: cy + 0.08*s},
            {x: cx - 5.02*s, y: cy - 0.8*s},
        ];
    }

    if (species === "Leopard Shark") {
        // 레오파드상어: 부드럽고 날렵한 형태
        return [
            {x: cx - 4.35*s, y: cy + 0.02*s},
            {x: cx - 3.4*s, y: cy - 0.48*s},
            {x: cx - 1.45*s, y: cy - 0.55*s},
            {x: cx - 0.25*s, y: cy - 1.22*s},
            {x: cx + 0.35*s, y: cy - 0.52*s},
            {x: cx + 2.55*s, y: cy - 0.38*s},
            {x: cx + 4.45*s, y: cy - 0.04*s},
            {x: cx + 3.08*s, y: cy + 0.42*s},
            {x: cx + 1.05*s, y: cy + 0.58*s},
            {x: cx - 1.12*s, y: cy + 0.5*s},
            {x: cx - 1.85*s, y: cy + 1.02*s},
            {x: cx - 1.7*s, y: cy + 0.38*s},
            {x: cx - 3.35*s, y: cy + 0.42*s},
            {x: cx - 4.75*s, y: cy + 0.82*s},
            {x: cx - 4.12*s, y: cy + 0.06*s},
            {x: cx - 4.72*s, y: cy - 0.72*s},
        ];
    }

    if (species === "Zebra Shark") {
        // 제브라상어: 길고 유연한 몸, 긴 꼬리, 둥근 머리
        return [
            {x: cx - 5.2*s, y: cy - 0.1*s},
            {x: cx - 4.2*s, y: cy - 0.52*s},
            {x: cx - 2.5*s, y: cy - 0.58*s},
            {x: cx - 0.8*s, y: cy - 0.92*s},
            {x: cx - 0.1*s, y: cy - 0.52*s},
            {x: cx + 1.8*s, y: cy - 0.42*s},
            {x: cx + 3.5*s, y: cy - 0.22*s},
            {x: cx + 4.5*s, y: cy + 0.05*s},
            {x: cx + 3.6*s, y: cy + 0.38*s},
            {x: cx + 1.5*s, y: cy + 0.55*s},
            {x: cx - 0.5*s, y: cy + 0.52*s},
            {x: cx - 2.2*s, y: cy + 0.48*s},
            {x: cx - 3.8*s, y: cy + 0.35*s},
            {x: cx - 5.0*s, y: cy + 0.72*s},
            {x: cx - 4.6*s, y: cy + 0.05*s},
            {x: cx - 5.4*s, y: cy - 0.65*s},
        ];
    }

    if (species === "Angel Shark") {
        // 엔젤상어: 납작하고 넓은 가오리형, 큰 가슴지느러미
        return [
            {x: cx - 4.0*s, y: cy - 0.05*s},
            {x: cx - 3.2*s, y: cy - 0.35*s},
            {x: cx - 1.8*s, y: cy - 0.38*s},
            {x: cx - 0.5*s, y: cy - 0.55*s},
            {x: cx + 0.8*s, y: cy - 0.42*s},
            {x: cx + 2.2*s, y: cy - 0.85*s},
            {x: cx + 3.8*s, y: cy - 0.35*s},
            {x: cx + 4.5*s, y: cy + 0.05*s},
            {x: cx + 3.8*s, y: cy + 0.4*s},
            {x: cx + 2.2*s, y: cy + 0.9*s},
            {x: cx + 0.8*s, y: cy + 0.48*s},
            {x: cx - 0.5*s, y: cy + 0.58*s},
            {x: cx - 1.8*s, y: cy + 0.42*s},
            {x: cx - 3.2*s, y: cy + 0.38*s},
            {x: cx - 4.2*s, y: cy + 0.55*s},
            {x: cx - 3.8*s, y: cy + 0.05*s},
            {x: cx - 4.2*s, y: cy - 0.48*s},
        ];
    }

    if (species === "Blue Shark") {
        // 블루상어: 길고 날씬한 유선형, 긴 가슴지느러미
        return [
            {x: cx - 5.0*s, y: cy - 0.02*s},
            {x: cx - 4.0*s, y: cy - 0.48*s},
            {x: cx - 2.2*s, y: cy - 0.52*s},
            {x: cx - 0.6*s, y: cy - 1.25*s},
            {x: cx + 0.0*s, y: cy - 0.48*s},
            {x: cx + 2.5*s, y: cy - 0.35*s},
            {x: cx + 5.0*s, y: cy - 0.02*s},
            {x: cx + 3.2*s, y: cy + 0.32*s},
            {x: cx + 1.0*s, y: cy + 0.45*s},
            {x: cx - 0.2*s, y: cy + 0.85*s},
            {x: cx - 1.5*s, y: cy + 1.25*s},
            {x: cx - 1.3*s, y: cy + 0.42*s},
            {x: cx - 3.5*s, y: cy + 0.35*s},
            {x: cx - 5.2*s, y: cy + 0.82*s},
            {x: cx - 4.5*s, y: cy + 0.05*s},
            {x: cx - 5.3*s, y: cy - 0.78*s},
        ];
    }

    if (species === "Port Jackson Shark") {
        // 포트잭슨상어: 둥근 머리, 두꺼운 몸, 짧은 주둥이
        return [
            {x: cx - 4.2*s, y: cy + 0.02*s},
            {x: cx - 3.3*s, y: cy - 0.55*s},
            {x: cx - 1.5*s, y: cy - 0.72*s},
            {x: cx - 0.3*s, y: cy - 1.05*s},
            {x: cx + 0.3*s, y: cy - 0.68*s},
            {x: cx + 2.0*s, y: cy - 0.55*s},
            {x: cx + 3.5*s, y: cy - 0.28*s},
            {x: cx + 4.2*s, y: cy + 0.08*s},
            {x: cx + 3.5*s, y: cy + 0.42*s},
            {x: cx + 2.0*s, y: cy + 0.62*s},
            {x: cx + 0.2*s, y: cy + 0.72*s},
            {x: cx - 1.5*s, y: cy + 0.65*s},
            {x: cx - 2.5*s, y: cy + 0.88*s},
            {x: cx - 2.3*s, y: cy + 0.42*s},
            {x: cx - 3.5*s, y: cy + 0.42*s},
            {x: cx - 4.5*s, y: cy + 0.72*s},
            {x: cx - 3.9*s, y: cy + 0.05*s},
            {x: cx - 4.5*s, y: cy - 0.55*s},
        ];
    }

    if (species === "Bull Shark") {
        // 황소상어: 두껍고 뭉툴한 몸, 짧고 둥근 주둥이, 큰 등지느러미
        return [
            {x: cx - 4.5*s, y: cy - 0.02*s},
            {x: cx - 3.5*s, y: cy - 0.72*s},
            {x: cx - 2.0*s, y: cy - 0.78*s},
            {x: cx - 0.6*s, y: cy - 1.65*s},
            {x: cx + 0.0*s, y: cy - 0.72*s},
            {x: cx + 2.0*s, y: cy - 0.58*s},
            {x: cx + 3.8*s, y: cy - 0.18*s},
            {x: cx + 4.5*s, y: cy + 0.08*s},
            {x: cx + 3.5*s, y: cy + 0.52*s},
            {x: cx + 1.5*s, y: cy + 0.72*s},
            {x: cx - 0.5*s, y: cy + 0.65*s},
            {x: cx - 1.8*s, y: cy + 1.15*s},
            {x: cx - 1.6*s, y: cy + 0.48*s},
            {x: cx - 3.2*s, y: cy + 0.48*s},
            {x: cx - 5.0*s, y: cy + 1.05*s},
            {x: cx - 4.2*s, y: cy + 0.05*s},
            {x: cx - 5.0*s, y: cy - 0.92*s},
        ];
    }

    if (species === "Tiger Shark") {
        // 타이거상어: 크고 두꺼운 몸, 둥근 주둥이, 넓은 꼬리
        return [
            {x: cx - 5.0*s, y: cy - 0.05*s},
            {x: cx - 3.8*s, y: cy - 0.75*s},
            {x: cx - 2.0*s, y: cy - 0.85*s},
            {x: cx - 0.5*s, y: cy - 1.55*s},
            {x: cx + 0.1*s, y: cy - 0.78*s},
            {x: cx + 2.2*s, y: cy - 0.62*s},
            {x: cx + 4.2*s, y: cy - 0.22*s},
            {x: cx + 5.0*s, y: cy + 0.08*s},
            {x: cx + 4.0*s, y: cy + 0.48*s},
            {x: cx + 1.8*s, y: cy + 0.78*s},
            {x: cx - 0.5*s, y: cy + 0.72*s},
            {x: cx - 2.0*s, y: cy + 1.18*s},
            {x: cx - 1.8*s, y: cy + 0.52*s},
            {x: cx - 3.5*s, y: cy + 0.52*s},
            {x: cx - 5.5*s, y: cy + 1.15*s},
            {x: cx - 4.6*s, y: cy + 0.08*s},
            {x: cx - 5.5*s, y: cy - 1.0*s},
        ];
    }

    if (species === "Goblin Shark") {
        // 고블린상어: 긴 주둥이가 앞으로 돌출, 얇은 몸
        return [
            {x: cx - 4.5*s, y: cy + 0.02*s},
            {x: cx - 3.5*s, y: cy - 0.42*s},
            {x: cx - 1.8*s, y: cy - 0.48*s},
            {x: cx - 0.5*s, y: cy - 1.0*s},
            {x: cx + 0.0*s, y: cy - 0.45*s},
            {x: cx + 2.0*s, y: cy - 0.35*s},
            {x: cx + 3.5*s, y: cy - 0.55*s},
            {x: cx + 5.5*s, y: cy - 0.35*s},
            {x: cx + 6.0*s, y: cy + 0.02*s},
            {x: cx + 5.2*s, y: cy + 0.25*s},
            {x: cx + 3.5*s, y: cy + 0.18*s},
            {x: cx + 2.0*s, y: cy + 0.38*s},
            {x: cx + 0.0*s, y: cy + 0.45*s},
            {x: cx - 1.8*s, y: cy + 0.42*s},
            {x: cx - 3.2*s, y: cy + 0.35*s},
            {x: cx - 4.8*s, y: cy + 0.72*s},
            {x: cx - 4.2*s, y: cy + 0.05*s},
            {x: cx - 4.8*s, y: cy - 0.62*s},
        ];
    }

    if (species === "Basking Shark") {
        // 바스킹상어: 거대한 몸, 큰 입, 둥근 실루엿
        return [
            {x: cx - 4.8*s, y: cy - 0.15*s},
            {x: cx - 3.8*s, y: cy - 0.85*s},
            {x: cx - 2.0*s, y: cy - 1.1*s},
            {x: cx + 0.2*s, y: cy - 1.05*s},
            {x: cx + 2.5*s, y: cy - 0.75*s},
            {x: cx + 4.2*s, y: cy - 0.35*s},
            {x: cx + 5.0*s, y: cy + 0.05*s},
            {x: cx + 4.5*s, y: cy + 0.55*s},
            {x: cx + 2.5*s, y: cy + 0.92*s},
            {x: cx + 0.0*s, y: cy + 1.05*s},
            {x: cx - 2.0*s, y: cy + 0.88*s},
            {x: cx - 3.5*s, y: cy + 0.55*s},
            {x: cx - 4.8*s, y: cy + 0.95*s},
            {x: cx - 4.3*s, y: cy + 0.15*s},
            {x: cx - 5.1*s, y: cy - 0.85*s},
        ];
    }

    if (species === "Wobbegong Shark") {
        // 우바잉상어: 매우 납작하고 넓은 카펫형
        return [
            {x: cx - 4.0*s, y: cy + 0.05*s},
            {x: cx - 3.2*s, y: cy - 0.25*s},
            {x: cx - 1.5*s, y: cy - 0.3*s},
            {x: cx - 0.3*s, y: cy - 0.48*s},
            {x: cx + 0.8*s, y: cy - 0.32*s},
            {x: cx + 2.5*s, y: cy - 0.65*s},
            {x: cx + 4.2*s, y: cy - 0.28*s},
            {x: cx + 4.8*s, y: cy + 0.05*s},
            {x: cx + 4.2*s, y: cy + 0.32*s},
            {x: cx + 2.5*s, y: cy + 0.7*s},
            {x: cx + 0.8*s, y: cy + 0.38*s},
            {x: cx - 0.3*s, y: cy + 0.52*s},
            {x: cx - 1.5*s, y: cy + 0.35*s},
            {x: cx - 3.0*s, y: cy + 0.28*s},
            {x: cx - 4.2*s, y: cy + 0.45*s},
            {x: cx - 3.8*s, y: cy + 0.08*s},
            {x: cx - 4.2*s, y: cy - 0.35*s},
        ];
    }

    if (species === "Cookiecutter Shark") {
        // 쿠키커터상어: 작고 원통형, 짧은 주둥이
        return [
            {x: cx - 3.5*s, y: cy + 0.02*s},
            {x: cx - 2.8*s, y: cy - 0.38*s},
            {x: cx - 1.5*s, y: cy - 0.48*s},
            {x: cx - 0.3*s, y: cy - 0.72*s},
            {x: cx + 0.2*s, y: cy - 0.45*s},
            {x: cx + 1.5*s, y: cy - 0.38*s},
            {x: cx + 3.0*s, y: cy - 0.15*s},
            {x: cx + 3.5*s, y: cy + 0.05*s},
            {x: cx + 3.0*s, y: cy + 0.25*s},
            {x: cx + 1.5*s, y: cy + 0.42*s},
            {x: cx + 0.0*s, y: cy + 0.48*s},
            {x: cx - 1.5*s, y: cy + 0.45*s},
            {x: cx - 2.5*s, y: cy + 0.35*s},
            {x: cx - 3.8*s, y: cy + 0.55*s},
            {x: cx - 3.3*s, y: cy + 0.05*s},
            {x: cx - 3.8*s, y: cy - 0.48*s},
        ];
    }

    if (species === "Thresher Shark") {
        // 환도상어: 몸길이의 절반인 긴 꼬리지느러미
        return [
            {x: cx - 6.5*s, y: cy - 0.8*s},
            {x: cx - 5.5*s, y: cy - 0.15*s},
            {x: cx - 4.5*s, y: cy - 0.05*s},
            {x: cx - 3.2*s, y: cy - 0.48*s},
            {x: cx - 1.5*s, y: cy - 0.52*s},
            {x: cx - 0.3*s, y: cy - 1.15*s},
            {x: cx + 0.2*s, y: cy - 0.48*s},
            {x: cx + 2.0*s, y: cy - 0.38*s},
            {x: cx + 4.0*s, y: cy - 0.05*s},
            {x: cx + 3.0*s, y: cy + 0.35*s},
            {x: cx + 1.0*s, y: cy + 0.48*s},
            {x: cx - 1.0*s, y: cy + 0.42*s},
            {x: cx - 2.5*s, y: cy + 0.82*s},
            {x: cx - 2.2*s, y: cy + 0.35*s},
            {x: cx - 3.8*s, y: cy + 0.32*s},
            {x: cx - 5.0*s, y: cy + 0.15*s},
            {x: cx - 6.5*s, y: cy + 0.55*s},
        ];
    }

    if (species === "Saw Shark") {
        // 톱상어: 긴 톱 모양 주둥이가 앞으로 돌출
        return [
            {x: cx - 4.2*s, y: cy + 0.02*s},
            {x: cx - 3.2*s, y: cy - 0.38*s},
            {x: cx - 1.5*s, y: cy - 0.42*s},
            {x: cx - 0.3*s, y: cy - 0.82*s},
            {x: cx + 0.2*s, y: cy - 0.4*s},
            {x: cx + 2.0*s, y: cy - 0.32*s},
            {x: cx + 3.5*s, y: cy - 0.18*s},
            {x: cx + 5.0*s, y: cy - 0.12*s},
            {x: cx + 6.2*s, y: cy + 0.0*s},
            {x: cx + 5.0*s, y: cy + 0.12*s},
            {x: cx + 3.5*s, y: cy + 0.2*s},
            {x: cx + 2.0*s, y: cy + 0.35*s},
            {x: cx + 0.2*s, y: cy + 0.42*s},
            {x: cx - 1.5*s, y: cy + 0.4*s},
            {x: cx - 3.0*s, y: cy + 0.32*s},
            {x: cx - 4.5*s, y: cy + 0.58*s},
            {x: cx - 3.9*s, y: cy + 0.05*s},
            {x: cx - 4.5*s, y: cy - 0.52*s},
        ];
    }

    if (species === "Spinner Shark") {
        // 스피너상어: 날렵하고 긴 몸, 뾰족한 주둥이, 역동적 형태
        return [
            {x: cx - 5.0*s, y: cy - 0.02*s},
            {x: cx - 4.0*s, y: cy - 0.52*s},
            {x: cx - 2.2*s, y: cy - 0.55*s},
            {x: cx - 0.8*s, y: cy - 1.35*s},
            {x: cx - 0.1*s, y: cy - 0.5*s},
            {x: cx + 2.0*s, y: cy - 0.38*s},
            {x: cx + 4.5*s, y: cy - 0.05*s},
            {x: cx + 3.2*s, y: cy + 0.35*s},
            {x: cx + 1.2*s, y: cy + 0.48*s},
            {x: cx - 0.8*s, y: cy + 0.42*s},
            {x: cx - 1.8*s, y: cy + 0.95*s},
            {x: cx - 1.6*s, y: cy + 0.35*s},
            {x: cx - 3.5*s, y: cy + 0.35*s},
            {x: cx - 5.2*s, y: cy + 0.85*s},
            {x: cx - 4.5*s, y: cy + 0.05*s},
            {x: cx - 5.3*s, y: cy - 0.82*s},
        ];
    }

    return [
        {x: cx - 4.3*s, y: cy + 0.05*s},
        {x: cx - 3.2*s, y: cy - 0.5*s},
        {x: cx - 1.4*s, y: cy - 0.55*s},
        {x: cx - 0.35*s, y: cy - 1.45*s},
        {x: cx + 0.15*s, y: cy - 0.55*s},
        {x: cx + 2.45*s, y: cy - 0.42*s},
        {x: cx + 4.4*s, y: cy - 0.04*s},
        {x: cx + 2.9*s, y: cy + 0.38*s},
        {x: cx + 0.8*s, y: cy + 0.58*s},
        {x: cx - 1.05*s, y: cy + 0.46*s},
        {x: cx - 1.8*s, y: cy + 1.08*s},
        {x: cx - 1.65*s, y: cy + 0.38*s},
        {x: cx - 3.3*s, y: cy + 0.4*s},
        {x: cx - 4.75*s, y: cy + 0.95*s},
        {x: cx - 4.1*s, y: cy + 0.08*s},
        {x: cx - 4.75*s, y: cy - 0.8*s},
    ];
}

function getSharkConfig(species) {
    const base = {
        bodyLength: 3.2,
        bodyHeight: 0.55,
        bodyCount: 520,
        headLength: 0.75,
        headHeight: 0.5,
        headCount: 130,
        tailStemLength: 0.75,
        tailStemHeight: 0.18,
        tailFinLength: 0.75,
        tailFinHeight: 0.62,
        dorsalX: -0.55,
        dorsalWidth: 0.8,
        dorsalHeight: 1.1,
        dorsalCount: 95,
        pectoralX: 0.05,
        pectoralLength: 0.95,
        pectoralHeight: 0.75,
        pectoralCount: 95,
    };

    const configs = {
        "Whale Shark": {
            ...base,
            bodyLength: 3.7,
            bodyHeight: 0.82,
            bodyCount: 720,
            headLength: 0.9,
            headHeight: 0.72,
            tailStemHeight: 0.14,
            dorsalHeight: 0.72,
            pectoralHeight: 0.62,
        },
        "Great White Shark": {
            ...base,
            bodyLength: 3.45,
            bodyHeight: 0.6,
            headLength: 1.05,
            headHeight: 0.42,
            dorsalHeight: 1.35,
            tailFinHeight: 0.8,
        },
        "Hammerhead Shark": {
            ...base,
            bodyLength: 3.0,
            bodyHeight: 0.47,
            headLength: 0.52,
            headHeight: 0.38,
            dorsalHeight: 0.95,
            tailFinHeight: 0.68,
        },
        "Mako Shark": {
            ...base,
            bodyLength: 3.8,
            bodyHeight: 0.38,
            bodyCount: 460,
            headLength: 1.15,
            headHeight: 0.32,
            dorsalHeight: 1.1,
            tailStemLength: 0.95,
            tailFinHeight: 0.72,
        },
        "Nurse Shark": {
            ...base,
            bodyLength: 3.25,
            bodyHeight: 0.5,
            headLength: 0.9,
            headHeight: 0.48,
            dorsalHeight: 0.55,
            pectoralHeight: 0.48,
            tailFinHeight: 0.5,
        },
        "Greenland Shark": {
            ...base,
            bodyLength: 3.45,
            bodyHeight: 0.68,
            bodyCount: 620,
            headLength: 0.8,
            headHeight: 0.52,
            dorsalHeight: 0.45,
            tailFinHeight: 0.5,
        },
        "Leopard Shark": {
            ...base,
            bodyLength: 3.25,
            bodyHeight: 0.43,
            bodyCount: 480,
            headLength: 0.75,
            headHeight: 0.36,
            dorsalHeight: 0.8,
            pectoralHeight: 0.58,
        },
        "Zebra Shark": { ...base, bodyCount: 500 },
        "Angel Shark": { ...base, bodyCount: 550 },
        "Blue Shark": { ...base, bodyCount: 460 },
        "Port Jackson Shark": { ...base, bodyCount: 540 },
        "Bull Shark": { ...base, bodyCount: 580 },
        "Tiger Shark": { ...base, bodyCount: 650 },
        "Goblin Shark": { ...base, bodyCount: 420 },
        "Basking Shark": { ...base, bodyCount: 700 },
        "Wobbegong Shark": { ...base, bodyCount: 480 },
        "Cookiecutter Shark": { ...base, bodyCount: 350 },
        "Thresher Shark": { ...base, bodyCount: 480 },
        "Saw Shark": { ...base, bodyCount: 440 },
        "Spinner Shark": { ...base, bodyCount: 460 },
    };

    return configs[species] || base;
}



function createParticles(mood) {
    particles = [];
    bgParticles = [];
    lines = [];

    const cx = W * 0.46;
    const cy = H * 0.55;
    const s = Math.min(W, H) * 0.11;

    const species = mood.shark_name;
    const config = getSharkConfig(species);
    const sharkOutline = makeSpeciesShape(species, cx, cy, s);

    function addParticle(x, y, sizeMin = 1.4, sizeMax = 3.1) {
        particles.push({
            x, y, baseX: x, baseY: y,
            vx: rand(-0.12, 0.12), vy: rand(-0.1, 0.1),
            size: rand(sizeMin, sizeMax), phase: rand(0, Math.PI * 2),
        });
    }

    // 외곽선을 따라 밀도 높은 입자 배치
    for (let i = 0; i < sharkOutline.length; i++) {
        const a = sharkOutline[i];
        const b = sharkOutline[(i + 1) % sharkOutline.length];
        const segLen = Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2);
        const count = Math.max(8, Math.floor(segLen / 3));
        for (let j = 0; j < count; j++) {
            const t = j / count;
            addParticle(a.x + (b.x - a.x) * t + rand(-2, 2), a.y + (b.y - a.y) * t + rand(-2, 2), 1.5, 2.8);
        }
    }

    // 내부를 채우는 입자 (outline 안에만)
    const bounds = sharkOutline.reduce((acc, p) => ({
        minX: Math.min(acc.minX, p.x), maxX: Math.max(acc.maxX, p.x),
        minY: Math.min(acc.minY, p.y), maxY: Math.max(acc.maxY, p.y),
    }), {minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity});

    let filled = 0;
    const targetFill = config.bodyCount || 520;
    while (filled < targetFill) {
        const px = rand(bounds.minX, bounds.maxX);
        const py = rand(bounds.minY, bounds.maxY);
        if (pointInPolygon({x: px, y: py}, sharkOutline)) {
            addParticle(px, py, 1.2, 2.6);
            filled++;
        }
    }



    // 배경 입자
    for (let i = 0; i < 280; i++) {
        bgParticles.push({
            x: rand(0, W),
            y: rand(0, H),
            vx: rand(-0.08, 0.08),
            vy: rand(-0.05, 0.05),
            size: rand(0.8, 2.2),
        });
    }

    // 가까운 점끼리 연결
    for (let i = 0; i < particles.length; i++) {
        const near = [];
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const d = Math.sqrt(dx * dx + dy * dy);
            if (d < s * 0.34) near.push({ j, d });
        }
        near.sort((a, b) => a.d - b.d);
        near.slice(0, 4).forEach(n => lines.push([i, n.j, n.d]));
    }
}

function createBackgroundSharks() {
    backgroundSharks = [];

    const collected = getCollectedSharks();

    collected.forEach((key, index) => {
        const item = collectionData[key];
        if (!item) return;

        // 현재 메인 상어는 배경에서 제외
        if (currentMood && currentMood.key === key) return;

        const moodLike = {
            shark_name: item.species,
            shark_name_ko: item.title,
            primary: item.color || "#ffffff",
            secondary: "#0f172a",
        };

        const scale = Math.min(W, H) * 0.025;
        const startX = rand(-W * 0.2, W * 1.1);
        const startY = rand(H * 0.18, H * 0.82);
        const shape = makeSpeciesShape(moodLike.shark_name, startX, startY, scale);

        backgroundSharks.push({
            key,
            mood: moodLike,
            shape,
            x: startX,
            y: startY,
            scale,
            speed: rand(0.08, 0.22),
            drift: rand(0.0012, 0.0024),
            phase: rand(0, Math.PI * 2),
            alpha: rand(0.28, 0.46),
        });
    });
}

function drawBackground(mood, t) {
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, mood.primary);
    grad.addColorStop(0.48, "#3153b7");
    grad.addColorStop(1, mood.secondary);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    const glow = ctx.createRadialGradient(W * 0.28, H * 0.16, 0, W * 0.28, H * 0.16, W * 0.75);
    glow.addColorStop(0, "rgba(255,255,255,0.18)");
    glow.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    ctx.globalAlpha = 0.22;
    for (let i = 0; i < bgParticles.length; i++) {
        const p = bgParticles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -20) p.x = W + 20;
        if (p.x > W + 20) p.x = -20;
        if (p.y < -20) p.y = H + 20;
        if (p.y > H + 20) p.y = -20;

        for (let j = i + 1; j < Math.min(i + 7, bgParticles.length); j++) {
            const q = bgParticles[j];
            const dx = p.x - q.x;
            const dy = p.y - q.y;
            const d = Math.sqrt(dx*dx + dy*dy);
            if (d < 120) {
                ctx.strokeStyle = `rgba(255,255,255,${0.16 * (1 - d / 120)})`;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(q.x, q.y);
                ctx.stroke();
            }
        }
        ctx.fillStyle = "rgba(255,255,255,0.34)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.globalAlpha = 1;
}

function drawSpeciesDetails(mood, t, moveX, moveY) {
    const cx = W * 0.48 + moveX;
    const cy = H * 0.53 + moveY;
    const s = Math.min(W, H) * 0.095;

    ctx.save();
    ctx.shadowColor = "rgba(255,255,255,0.8)";
    ctx.shadowBlur = 12;

    if (mood.shark_name === "Whale Shark") {
        // 고래상어: 몸 전체의 흰 점무늬
        ctx.fillStyle = "rgba(255,255,255,0.72)";
        for (let row = -4; row <= 4; row++) {
            for (let col = -7; col <= 6; col++) {
                const x = cx + col * s * 0.42 + (row % 2) * s * 0.18;
                const y = cy + row * s * 0.18 + Math.sin(t * 0.001 + col) * 1.5;
                ctx.beginPath();
                ctx.arc(x, y, s * 0.035, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }

    if (mood.shark_name === "Leopard Shark") {
        // 레오파드상어: 불규칙한 반점
        ctx.strokeStyle = "rgba(255,255,255,0.62)";
        ctx.lineWidth = 1.4;
        for (let i = 0; i < 24; i++) {
            const x = cx - s * 2.5 + (i % 8) * s * 0.62;
            const y = cy - s * 0.35 + Math.floor(i / 8) * s * 0.32 + Math.sin(i) * 8;
            ctx.beginPath();
            ctx.ellipse(x, y, s * 0.06, s * 0.035, i, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Hammerhead Shark") {
        // 귀상어: 양쪽으로 뻗은 머리 라인 강조
        ctx.strokeStyle = "rgba(255,255,255,0.88)";
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.moveTo(cx + s * 3.05, cy);
        ctx.lineTo(cx + s * 5.25, cy - s * 0.55);
        ctx.moveTo(cx + s * 3.05, cy);
        ctx.lineTo(cx + s * 5.25, cy + s * 0.55);
        ctx.stroke();

        ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.beginPath(); ctx.arc(cx + s * 5.15, cy - s * 0.72, s * 0.055, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(cx + s * 5.15, cy + s * 0.72, s * 0.055, 0, Math.PI * 2); ctx.fill();
    }

    if (mood.shark_name === "Great White Shark") {
        // 백상아리: 큰 등지느러미와 날카로운 주둥이 강조
        ctx.strokeStyle = "rgba(255,255,255,0.9)";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(cx - s * 0.75, cy - s * 1.86);
        ctx.lineTo(cx - s * 0.18, cy - s * 0.72);
        ctx.lineTo(cx - s * 1.25, cy - s * 0.76);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(cx + s * 4.55, cy - s * 0.02);
        ctx.lineTo(cx + s * 5.08, cy - s * 0.02);
        ctx.stroke();
    }

    if (mood.shark_name === "Mako Shark") {
        // 청상아리: 속도감 있는 빛줄기
        ctx.strokeStyle = "rgba(255,255,255,0.32)";
        ctx.lineWidth = 1.2;
        for (let i = 0; i < 8; i++) {
            const y = cy - s * 0.8 + i * s * 0.22;
            ctx.beginPath();
            ctx.moveTo(cx - s * 5.8, y);
            ctx.lineTo(cx - s * 3.8, y + Math.sin(t * 0.003 + i) * 8);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Nurse Shark") {
        // 너스상어: 바닥 가까운 잔잔한 라인
        ctx.strokeStyle = "rgba(255,255,255,0.32)";
        ctx.lineWidth = 1.5;
        for (let i = 0; i < 4; i++) {
            ctx.beginPath();
            ctx.moveTo(cx - s * 4.2, cy + s * (1.0 + i * 0.15));
            ctx.quadraticCurveTo(cx, cy + s * (1.25 + i * 0.13), cx + s * 4.2, cy + s * (1.0 + i * 0.15));
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Greenland Shark") {
        // 그린란드상어: 심해 느낌의 느린 glow
        const pulse = 0.18 + Math.sin(t * 0.001) * 0.06;
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, s * 4.6);
        grad.addColorStop(0, `rgba(180,190,255,${pulse})`);
        grad.addColorStop(1, "rgba(180,190,255,0)");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, W, H);
    }

    if (mood.shark_name === "Zebra Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.45)";
        ctx.lineWidth = 1.2;
        for (let i = 0; i < 12; i++) {
            const x = cx - s * 3 + i * s * 0.5;
            ctx.beginPath();
            ctx.moveTo(x, cy - s * 0.4 + Math.sin(t * 0.001 + i) * 3);
            ctx.lineTo(x + s * 0.1, cy + s * 0.4 + Math.cos(t * 0.001 + i) * 3);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Angel Shark") {
        ctx.fillStyle = "rgba(255,255,200,0.35)";
        for (let i = 0; i < 30; i++) {
            const x = cx - s * 4 + Math.sin(i * 7.3 + t * 0.0005) * s * 4;
            const y = cy + s * 0.6 + Math.cos(i * 5.1) * s * 0.3;
            ctx.beginPath();
            ctx.arc(x, y, s * 0.02, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    if (mood.shark_name === "Blue Shark") {
        ctx.strokeStyle = "rgba(100,200,255,0.4)";
        ctx.lineWidth = 1.3;
        for (let i = 0; i < 5; i++) {
            ctx.beginPath();
            for (let x = -s * 5; x < s * 5; x += 8) {
                const y = cy + i * s * 0.25 - s * 0.5 + Math.sin(x * 0.02 + t * 0.002 + i) * s * 0.08;
                if (x === -s * 5) ctx.moveTo(cx + x, y);
                else ctx.lineTo(cx + x, y);
            }
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Port Jackson Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.6)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx + s * 2.5, cy - s * 0.2, s * 0.4, -0.8, 0.8);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(cx + s * 2.5, cy + s * 0.2, s * 0.4, -0.8, 0.8);
        ctx.stroke();
    }

    if (mood.shark_name === "Bull Shark") {
        const ringR = (t * 0.03) % (s * 3);
        const ringAlpha = Math.max(0, 0.5 - ringR / (s * 3));
        ctx.strokeStyle = `rgba(248,113,113,${ringAlpha})`;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
        ctx.stroke();
    }

    if (mood.shark_name === "Tiger Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.3)";
        ctx.lineWidth = 2.5;
        for (let i = 0; i < 8; i++) {
            const x = cx - s * 2 + i * s * 0.55;
            const wave = Math.sin(t * 0.001 + i) * 2;
            ctx.beginPath();
            ctx.moveTo(x + wave, cy - s * 0.6);
            ctx.quadraticCurveTo(x + s * 0.15, cy, x + wave, cy + s * 0.6);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Goblin Shark") {
        ctx.fillStyle = "rgba(200,180,255,0.6)";
        for (let i = 0; i < 8; i++) {
            const flicker = Math.sin(t * 0.003 + i * 2.1) * 0.3 + 0.5;
            ctx.globalAlpha = flicker;
            const x = cx + Math.cos(i * 0.8) * s * 2.5;
            const y = cy + Math.sin(i * 1.2) * s * 1.2;
            ctx.beginPath();
            ctx.arc(x, y, s * 0.05, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    if (mood.shark_name === "Basking Shark") {
        ctx.fillStyle = "rgba(200,255,200,0.4)";
        for (let i = 0; i < 40; i++) {
            const x = cx - s * 4 + ((i * 37 + t * 0.02) % (s * 8));
            const y = cy - s * 1 + Math.sin(i * 3.7) * s * 1.5;
            ctx.beginPath();
            ctx.arc(x, y, s * 0.018, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    if (mood.shark_name === "Wobbegong Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.25)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 15; i++) {
            const x = cx - s * 3.5 + i * s * 0.48;
            const y = cy + s * 0.3;
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.quadraticCurveTo(x + s * 0.1, y + s * 0.15 + Math.sin(t * 0.002 + i) * 3, x + s * 0.24, y);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Cookiecutter Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.5)";
        ctx.lineWidth = 1.5;
        for (let i = 0; i < 5; i++) {
            const x = cx - s * 1.5 + i * s * 0.75;
            const y = cy + Math.sin(t * 0.002 + i) * s * 0.1;
            ctx.beginPath();
            ctx.arc(x, y, s * 0.12, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    if (mood.shark_name === "Thresher Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.4)";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        for (let a = 0; a < Math.PI * 1.5; a += 0.1) {
            const r = s * 1.5 + Math.sin(a * 3 + t * 0.003) * s * 0.2;
            const x = cx - s * 4 + Math.cos(a) * r;
            const y = cy + Math.sin(a) * r * 0.4;
            if (a === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    if (mood.shark_name === "Saw Shark") {
        ctx.strokeStyle = "rgba(255,255,255,0.55)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < 12; i++) {
            const x = cx + s * 1.5 + i * s * 0.35;
            const y = cy + (i % 2 === 0 ? -s * 0.1 : s * 0.1);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    if (mood.shark_name === "Spinner Shark") {
        ctx.strokeStyle = "rgba(255,255,200,0.4)";
        ctx.lineWidth = 1.5;
        const spin = t * 0.003;
        ctx.beginPath();
        for (let a = 0; a < Math.PI * 2; a += 0.15) {
            const r = s * 1.2 + Math.sin(a * 3 + spin) * s * 0.3;
            const x = cx + Math.cos(a + spin) * r;
            const y = cy + Math.sin(a + spin) * r * 0.5;
            if (a === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    ctx.restore();
}

function drawBackgroundSharks(t) {
    backgroundSharks.forEach(shark => {
    shark.x += shark.speed;

    if (shark.x > W + 180) {
        shark.x = -180;
        shark.baseY = rand(H * 0.18, H * 0.82);
    }

    if (!shark.baseY) shark.baseY = shark.y;

        const swimX = Math.sin(t * shark.drift + shark.phase) * 24;
        const swimY = Math.sin(t * shark.drift * 0.75 + shark.phase) * 16;
        const roll = Math.sin(t * shark.drift * 0.55 + shark.phase) * 0.04;

        ctx.save();
        ctx.globalAlpha = Math.min(1, shark.alpha * 2.2);
        ctx.strokeStyle = "rgba(255,255,255,0.9)";
        ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.shadowBlur = 18;

        const movedShape = makeSpeciesShape(
            shark.mood.shark_name,
            shark.x + swimX,
            shark.baseY + swimY,
            shark.scale
);

        // 외곽선
        ctx.beginPath();
        movedShape.forEach((p, i) => {
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.stroke();

        // 내부 점들
        for (let i = 0; i < 28; i++) {
            const p = movedShape[Math.floor(Math.random() * movedShape.length)];
            const q = movedShape[Math.floor(Math.random() * movedShape.length)];

            const x = (p.x + q.x) / 2 + rand(-8, 8);
            const y = (p.y + q.y) / 2 + rand(-8, 8);

            ctx.beginPath();
            ctx.arc(x, y, rand(0.8, 1.8), 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    });
}


function drawShark(mood, t) {
    const speedFactor = mood.shark_name === "Mako Shark" ? 1.8 : mood.shark_name === "Nurse Shark" ? 0.45 : 1;
    const moveX = Math.sin(t * 0.001 * speedFactor) * 12;
    const moveY = Math.cos(t * 0.0014 * speedFactor) * 8;

    lines.forEach(([a, b, d]) => {
        const p = particles[a];
        const q = particles[b];
        const alpha = Math.max(0.12, 0.55 - d / 230);
        ctx.strokeStyle = `rgba(255,255,255,${alpha})`;
        ctx.lineWidth = 1.15;
        ctx.beginPath();
        ctx.moveTo(p.x + moveX, p.y + moveY);
        ctx.lineTo(q.x + moveX, q.y + moveY);
        ctx.stroke();
    });

    particles.forEach(p => {
        const x = p.x + moveX + Math.sin(t * 0.002 + p.phase) * 1.7;
        const y = p.y + moveY + Math.cos(t * 0.002 + p.phase) * 1.5;

        ctx.shadowColor = "rgba(255,255,255,0.9)";
        ctx.shadowBlur = 9;
        ctx.fillStyle = "rgba(255,255,255,0.88)";
        ctx.beginPath();
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
    });

    drawSpeciesDetails(mood, t, moveX, moveY);
}

function animate(t) {
    drawBackground(currentMood, t);
    drawBackgroundSharks(t);
    drawShark(currentMood, t);
    animationId = requestAnimationFrame(animate);
}

function startSharkVisualizer(mood) {
    resizeCanvas();
    document.getElementById("vizPill").textContent = mood.shark_name_ko;
    document.getElementById("vizSubtitle").textContent = mood.message;

    createParticles(mood);
    createBackgroundSharks();

    cancelAnimationFrame(animationId);
    animationId = requestAnimationFrame(animate);
}

function stopSharkVisualizer() {
    cancelAnimationFrame(animationId);
}

window.addEventListener("resize", () => {
    if (document.getElementById("visualizerModal").classList.contains("active")) {
        startSharkVisualizer(currentMood);
    }
});
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    result = None
    percents = {}
    analysis = None
    current_mood = {"key": None}

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        analysis = analyze_mood_gemini(text)
        main_key = analysis["main_key"]
        shark_key = analysis.get("shark_key", main_key)

        collection_item = get_collection_item(shark_key)
        base_mood = MOODS[main_key]

        result = {
            **base_mood,
            "key": shark_key,
            "shark_name": collection_item["species"],
            "shark_name_ko": collection_item["title"],
            "emoji": collection_item.get("emoji", "🦈"),
            "primary": collection_item.get("color", base_mood["primary"]),
            "message": collection_item.get("summary", base_mood["message"]),
}
        percents = analysis["percents"]
        # 퍼센테이지에 따라 컬렉션 키 결정
        pct = percents.get(main_key, 0)
        if pct >= 70:
            collection_key = f"{main_key}_3"
        elif pct >= 40:
            collection_key = f"{main_key}_2"
        else:
            collection_key = main_key
        # _3이나 _2가 컬렉션에 없으면 기본으로 fallback
        if not get_collection_item(collection_key):
            collection_key = main_key
        current_mood = dict(result)
        current_mood["key"] = shark_key

    return render_template_string(
        HTML,
        text=text,
        result=result,
        percents=percents,
        moods=MOODS,
        analysis=analysis,
        current_mood_json=json.dumps(current_mood, ensure_ascii=False),
        collection_items=get_collection_items(),
        collection_json=json.dumps(get_collection_items(), ensure_ascii=False),
    )


if __name__ == "__main__":
    app.run(debug=True)
