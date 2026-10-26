"""태그 규칙. 제목·요약에 키워드가 있으면 태그를 붙이고 히트 수로 점수를 만든다.

소스별 검색식은 DB의 sources.query에 있고, 여기는 수집된 글을 분류하는 규칙만 둔다.
"""

TAG_RULES: dict[str, list[str]] = {
    "co-scientist": ["co-scientist", "coscientist", "코사이언티스트", "ai scientist"],
    "agentic-ai": ["agentic", "ai agent", "multi-agent", "에이전트"],
    "llm": ["large language model", "llm", "gpt", "언어모델", "거대언어", "생성형 ai", "생성 ai"],
    "foundation-model": ["foundation model", "파운데이션 모델", "기반 모델"],
    "digital-twin": ["digital twin", "디지털트윈", "디지털 트윈"],
    "flood": ["flood", "홍수", "침수"],
    "drought": ["drought", "가뭄"],
    "water-quality": ["water quality", "수질", "algae", "녹조"],
    "ai-water-plant": ["ai 정수장", "water treatment", "정수장", "정수 처리"],
    "hydrology": ["hydrolog", "수문", "유역", "watershed", "river basin"],
    "water-management": ["water management", "물관리", "수자원"],
    "smart-water": ["smart water", "스마트 물관리", "관망", "water network"],
    "k-water": ["k-water", "수자원공사"],
    "physics-informed": ["physics-informed", "physics informed", "pinn"],
}

# 언어 판정: 한글 비율이 이 값을 넘으면 ko
KO_RATIO = 0.3

# 제목 유사도(0~1). 이 값을 넘으면 같은 글로 본다.
NEAR_DUP = 0.92
