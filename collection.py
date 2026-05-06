# collection.py

SHARK_COLLECTION = {
    "calm": {
        "title": "고래상어",
        "species": "Whale Shark",
        "mood": "Calm",
        "summary": "거대한 몸집으로도 잔잔하게 바다를 유영하는 고래상어처럼, calm은 조용하고 안정적인 흐름을 닮았습니다.",
        "color": "#38bdf8",
        "habitat": "따뜻한 열대·아열대 바다",
        "personality": "느긋함, 안정감, 넓은 품",
        "keywords": ["평온", "안정", "천천히", "회복"],
        "description": "고래상어는 현존하는 가장 큰 어류로, 거대한 입으로 플랑크톤과 작은 생물을 걸러 먹습니다."    },
    "happy": {
        "title": "레오파드상어",
        "species": "Leopard Shark",
        "mood": "Happy",
        "summary": "밝은 무늬와 부드러운 움직임을 가진 레오파드상어처럼, happy는 가볍고 생기 있는 기분을 닮았습니다.",
        "color": "#5eead4",
        "habitat": "얕은 연안과 모래 바닥",
        "personality": "밝음, 경쾌함, 친근함",
        "keywords": ["기쁨", "가벼움", "생기", "미소"],
        "description": "레오파드상어는 몸의 표범무늬 같은 반점 때문에 이름이 붙었고, 얕은 연안에서 자주 발견됩니다."    },
    "angry": {
        "title": "백상아리",
        "species": "Great White Shark",
        "mood": "Angry",
        "summary": "강한 존재감과 날카로운 추진력을 가진 백상아리처럼, angry는 방향을 잡으면 힘이 되는 강한 에너지입니다.",
        "color": "#f87171",
        "habitat": "온대 연안과 외해",
        "personality": "강렬함, 직진성, 압도감",
        "keywords": ["분노", "추진력", "강함", "폭발"],
        "description": "백상아리는 뛰어난 후각을 가지고 있으며, 물속의 아주 미세한 냄새도 감지할 수 있습니다."    },
    "sad": {
        "title": "그린란드상어",
        "species": "Greenland Shark",
        "mood": "Sad",
        "summary": "깊고 차가운 바다를 천천히 지나는 그린란드상어처럼, sad는 조용히 가라앉은 마음의 깊이를 닮았습니다.",
        "color": "#818cf8",
        "habitat": "북극권과 깊은 차가운 바다",
        "personality": "깊이감, 고요함, 느린 회복",
        "keywords": ["우울", "고요", "심해", "가라앉음"],
        "description": "그린란드상어는 매우 오래 사는 상어로 알려져 있으며, 수백 년까지 생존할 수 있다고 추정됩니다."    },
    "tired": {
        "title": "너스상어",
        "species": "Nurse Shark",
        "mood": "Tired",
        "summary": "바닥 가까이 머물며 에너지를 아끼는 너스상어처럼, tired는 쉬어가야 할 몸과 마음의 신호입니다.",
        "color": "#cbd5e1",
        "habitat": "따뜻한 얕은 바다와 산호초 근처",
        "personality": "휴식, 저속, 회복",
        "keywords": ["피로", "쉼", "회복", "느림"],
        "description": "너스상어는 낮에는 바닥이나 틈 사이에서 쉬고, 주로 밤에 먹이를 찾는 습성이 있습니다."    },
    "anxious": {
        "title": "귀상어",
        "species": "Hammerhead Shark",
        "mood": "Anxious",
        "summary": "넓은 머리로 주변을 예민하게 살피는 귀상어처럼, anxious는 많은 것을 동시에 감지하는 마음과 닮았습니다.",
        "color": "#c084fc",
        "habitat": "열대·온대 바다",
        "personality": "예민함, 관찰, 경계",
        "keywords": ["불안", "걱정", "긴장", "감지"],
        "description": "귀상어의 넓은 머리 구조는 시야와 감각 기관을 넓게 활용하는 데 도움을 줍니다."    },
    "excited": {
        "title": "청상아리",
        "species": "Mako Shark",
        "mood": "Excited",
        "summary": "빠르고 날렵하게 물살을 가르는 청상아리처럼, excited는 앞으로 튀어나가려는 에너지를 닮았습니다.",
        "color": "#facc15",
        "habitat": "외해와 따뜻한 바다",
        "personality": "속도감, 기대감, 반짝임",
        "keywords": ["설렘", "속도", "기대", "도약"],
        "description": "청상아리는 상어 중에서도 매우 빠른 종으로, 순간적으로 강한 속도를 낼 수 있습니다."    },
}


def get_collection_items():
    return SHARK_COLLECTION


def get_collection_item(mood_key):
    return SHARK_COLLECTION.get(mood_key)