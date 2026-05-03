import json
import os
from flask import Flask, render_template_string, request

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
                "required": ALLOWED_MOODS,
            },
            "confidence": {"type": "integer"},
            "tone": {"type": "string"},
            "reason": {"type": "string"},
            "recommended_action": {"type": "string"},
        },
        "required": ["main_mood", "scores", "confidence", "tone", "reason", "recommended_action"],
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
    except Exception as error:
        fallback = analyze_mood_keyword(text)
        fallback["reason"] = f"Gemini 분석 중 오류가 발생하여 키워드 방식으로 분석했습니다. 오류: {error}"
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
@keyframes swim { 0%, 100% { transform: translateX(0) rotate(-5deg); } 50% { transform: translateX(34px) rotate(5deg); } }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } .nav { align-items: flex-start; flex-direction: column; } .viz-ui { left: 24px; right: 24px; text-align: left; } }
</style>
</head>
<body class="{{ result.theme if result else 'calm' }}">
<div class="container">
    <div class="nav">
        <div class="logo">🦈 Shark Mood Analysis</div>
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
const currentMood = {{ current_mood_json | safe }};

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

function createParticles(mood) {
    particles = [];
    bgParticles = [];
    lines = [];

    const cx = W * 0.48;
    const cy = H * 0.53;
    const scale = Math.min(W, H) * 0.095;
    const shape = makeSpeciesShape(mood.shark_name, cx, cy, scale);

    const minX = Math.min(...shape.map(p => p.x));
    const maxX = Math.max(...shape.map(p => p.x));
    const minY = Math.min(...shape.map(p => p.y));
    const maxY = Math.max(...shape.map(p => p.y));

    const count = mood.shark_name === "Whale Shark" ? 430 : 360;
    let attempts = 0;
    while (particles.length < count && attempts < count * 120) {
        attempts++;
        const p = { x: rand(minX, maxX), y: rand(minY, maxY) };
        if (pointInPolygon(p, shape)) {
            particles.push({
                x: p.x,
                y: p.y,
                baseX: p.x,
                baseY: p.y,
                vx: rand(-0.22, 0.22),
                vy: rand(-0.18, 0.18),
                size: rand(1.3, 3.1),
                phase: rand(0, Math.PI * 2),
            });
        }
    }

    for (let i = 0; i < 260; i++) {
        bgParticles.push({
            x: rand(0, W),
            y: rand(0, H),
            vx: rand(-0.08, 0.08),
            vy: rand(-0.05, 0.05),
            size: rand(0.8, 2.4),
        });
    }

    for (let i = 0; i < particles.length; i++) {
        const near = [];
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const d = Math.sqrt(dx*dx + dy*dy);
            if (d < scale * 0.75) near.push({j, d});
        }
        near.sort((a, b) => a.d - b.d);
        near.slice(0, 4).forEach(n => lines.push([i, n.j, n.d]));
    }
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

    ctx.restore();
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
    drawShark(currentMood, t);
    animationId = requestAnimationFrame(animate);
}

function startSharkVisualizer(mood) {
    resizeCanvas();
    document.getElementById("vizPill").textContent = mood.shark_name_ko;
    document.getElementById("vizSubtitle").textContent = mood.message;
    createParticles(mood);
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
    current_mood = MOODS[DEFAULT_KEY]

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        analysis = analyze_mood_gemini(text)
        main_key = analysis["main_key"]
        result = MOODS[main_key]
        percents = analysis["percents"]
        current_mood = result

    return render_template_string(
        HTML,
        text=text,
        result=result,
        percents=percents,
        moods=MOODS,
        analysis=analysis,
        current_mood_json=json.dumps(current_mood, ensure_ascii=False),
    )


if __name__ == "__main__":
    app.run(debug=True)
