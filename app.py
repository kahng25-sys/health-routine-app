import streamlit as st
from datetime import date, datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import json

# ── 페이지 설정 ──
st.set_page_config(
    page_title="성근님의 건강 루틴",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── 뉴저지 현재 시간 ──
def nj_now():
    """뉴저지 시간(America/New_York) 반환"""
    return datetime.now(ZoneInfo("America/New_York"))

def nj_time_str():
    """HH:MM 형식 뉴저지 현재 시간"""
    return nj_now().strftime("%H:%M")

def nj_date_str():
    """YYYY-MM-DD 형식 뉴저지 오늘 날짜"""
    return nj_now().strftime("%Y-%m-%d")

# ── Google Sheets 연결 ──
@st.cache_resource
def get_sheet():
    """Google Sheets 연결 (캐시로 재사용)"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("강님의 건강 관리")  # Google Sheets 파일명

def get_worksheet(tab_name, headers):
    """시트 가져오기 (없으면 생성)"""
    ss = get_sheet()
    try:
        ws = ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=500, cols=len(headers))
        ws.append_row(headers)
    return ws

# ── 요일별 추천 식단 ──
MEALS = {
    0: dict(m="달걀 2개+그릭요거트+배+방울토마토+호두",   l="소고기 된장찌개+현미밥+연근조림",  d="달걀 스크램블+그릭요거트+사과+파프리카"),
    1: dict(m="달걀 2개+그릭요거트+사과+당근스틱+호두",   l="추어탕+잡곡밥+깍두기",             d="달걀 스크램블+그릭요거트+블루베리+방울토마토"),
    2: dict(m="달걀 2개+그릭요거트+배+방울토마토+아몬드", l="추어탕+잡곡밥+깍두기",             d="삶은달걀 2개+그릭요거트+수박+당근스틱"),
    3: dict(m="달걀 2개+그릭요거트+사과+브로콜리+호두",   l="닭갈비+현미밥+된장국(무두부)",      d="달걀 스크램블+그릭요거트+블루베리+브로콜리"),
    4: dict(m="달걀 2개+그릭요거트+배+파프리카+아몬드",   l="설렁탕+잡곡밥+깍두기",             d="삶은달걀 2개+그릭요거트+사과+방울토마토"),
    5: dict(m="달걀 2개+그릭요거트+수박+당근스틱+호두",   l="소고기 국밥+잡곡밥+무생채",        d="달걀 스크램블+그릭요거트+배+당근스틱"),
    6: dict(m="달걀 2개+그릭요거트+사과+브로콜리+아몬드", l="삼계탕(주말보양)+잡곡밥",          d="삶은달걀 2개+그릭요거트+수박+브로콜리"),
}

_NJ_NOW     = datetime.now(ZoneInfo("America/New_York"))
TODAY       = _NJ_NOW.date()
TODAY_STR   = TODAY.strftime("%Y-%m-%d")
DOW         = TODAY.weekday()  # 0=월 ~ 6=일 (Python: 월=0)
DOW_KR      = ["월","화","수","목","금","토","일"][DOW]
TODAY_MEAL  = MEALS[TODAY.weekday()]

# ── 세션 상태 초기화 ──
def init_session():
    defaults = {
        "meal_m_done": False, "meal_l_done": False, "meal_d_done": False,
        "meal_m_actual": "", "meal_l_actual": "", "meal_d_actual": "",
        "water": 0,
        "exercises": [
            {"name":"빠른 걷기","meta":"30분·중강도","done":False},
            {"name":"스트레칭","meta":"15분·아침","done":False},
            {"name":"근력 운동","meta":"20분·상체","done":False},
        ],
        "todos": [
            {"text":"아침 소금물 루틴","tag":"건강","done":False},
            {"text":"추어탕 점심 식사","tag":"건강","done":False},
            {"text":"오후 생맥산차 챙기기","tag":"건강","done":False},
        ],
        "ideas": [],
        "diary_mood": "",
        "diary_content": "",
        "data_loaded": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Sheets에서 오늘 데이터 불러오기 ──
def load_today():
    if st.session_state.get("data_loaded"):
        return
    try:
        # 식단
        ws = get_worksheet("식단기록", ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(ml)","저장시간"])
        rows = ws.get_all_records()
        for row in rows:
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.meal_m_done   = row.get("아침완료","") == "✓"
                st.session_state.meal_l_done   = row.get("점심완료","") == "✓"
                st.session_state.meal_d_done   = row.get("저녁완료","") == "✓"
                st.session_state.meal_m_actual = str(row.get("아침실제",""))
                st.session_state.meal_l_actual = str(row.get("점심실제",""))
                st.session_state.meal_d_actual = str(row.get("저녁실제",""))
                st.session_state.water         = int(row.get("수분(ml)",0) or 0)
                break
        # 일기
        ws2  = get_worksheet("일기", ["날짜","기분","일기내용","저장시간"])
        rows2 = ws2.get_all_records()
        for row in rows2:
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.diary_mood    = str(row.get("기분",""))
                st.session_state.diary_content = str(row.get("일기내용",""))
                break
        st.session_state.data_loaded = True
    except Exception as e:
        st.warning(f"데이터 불러오기 실패: {e}")

# ── Sheets에 식단 저장 ──
def save_meal():
    try:
        headers = ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(ml)","저장시간"]
        ws   = get_worksheet("식단기록", headers)
        rows = ws.get_all_values()
        row_data = [
            TODAY_STR,
            TODAY_MEAL["m"], st.session_state.meal_m_actual, "✓" if st.session_state.meal_m_done else "",
            TODAY_MEAL["l"], st.session_state.meal_l_actual, "✓" if st.session_state.meal_l_done else "",
            TODAY_MEAL["d"], st.session_state.meal_d_actual, "✓" if st.session_state.meal_d_done else "",
            st.session_state.water,
            nj_time_str()
        ]
        # 오늘 행 찾아서 업데이트 or 추가
        for i, row in enumerate(rows):
            if row and str(row[0]) == TODAY_STR:
                ws.update(f"A{i+1}", [row_data])
                return
        ws.append_row(row_data)
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ── Sheets에 일기 저장 ──
def save_diary():
    try:
        headers = ["날짜","기분","일기내용","저장시간"]
        ws   = get_worksheet("일기", headers)
        rows = ws.get_all_values()
        row_data = [TODAY_STR, st.session_state.diary_mood, st.session_state.diary_content, nj_time_str()]
        for i, row in enumerate(rows):
            if row and str(row[0]) == TODAY_STR:
                ws.update(f"A{i+1}", [row_data])
                return
        ws.append_row(row_data)
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ── Sheets에 아이디어 저장 ──
def save_idea(text, tag):
    try:
        headers = ["날짜","시간","태그","내용"]
        ws = get_worksheet("메모아이디어", headers)
        ws.append_row([TODAY_STR, nj_time_str(), tag, text])
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ══════════════════════════════════════════
# UI 시작
# ══════════════════════════════════════════
init_session()
load_today()

# CSS
st.markdown("""
<style>
  /* 전체 배경 */
  .stApp { background: #F7F7F5; }
  /* 헤더 여백 줄이기 */
  .block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 480px; }
  /* 카드 스타일 */
  .card {
    background: white; border-radius: 14px;
    padding: 16px 18px; margin-bottom: 12px;
    border: 0.5px solid rgba(0,0,0,0.10);
  }
  .card-title {
    font-size: 12px; font-weight: 600;
    color: #6B6B68; text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 10px;
  }
  /* 추천 태그 */
  .rec-tag {
    display: inline-block; font-size: 10px;
    background: #E1F5EE; color: #0F6E56;
    padding: 2px 7px; border-radius: 4px;
    font-weight: 600; margin-right: 6px;
  }
  .rec-text { font-size: 12px; color: #9E9E9A; }
  /* 배지 */
  .badge {
    display: inline-block; font-size: 11px;
    background: #E1F5EE; color: #0F6E56;
    padding: 3px 10px; border-radius: 20px;
    font-weight: 500;
  }
  /* 구분선 숨기기 */
  hr { display: none; }
  /* 버튼 커스텀 */
  .stButton>button {
    border-radius: 10px; font-weight: 500;
    border: none; width: 100%;
  }
  /* 입력창 */
  .stTextInput>div>div>input, .stTextArea>div>div>textarea {
    border-radius: 8px; font-size: 14px;
  }
  /* 탭 */
  .stTabs [data-baseweb="tab"] { font-size: 13px; }
  /* 성공 메시지 */
  .save-ok {
    text-align: center; font-size: 12px;
    color: #1D9E75; margin-top: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ──
col1, col2 = st.columns([3,1])
with col1:
    st.markdown(f"<div style='font-size:12px;color:#9E9E9A;'>{TODAY_STR} ({DOW_KR})</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:20px;font-weight:700;'>성근님의 건강 루틴</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div style='text-align:right;padding-top:10px;'><span class='badge'>목양체질</span></div>", unsafe_allow_html=True)

st.markdown("---")

# ── 탭 ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🍚 식단", "🏃 운동", "✅ 할일", "💡 메모", "📓 일기", "🛒 장보기"])

# ════════════════════════════
# 탭1: 식단
# ════════════════════════════
with tab1:
    st.markdown("<div class='card-title'>☀️ 오늘 식단</div>", unsafe_allow_html=True)

    changed = False

    for key, label, meal_key, done_key, actual_key in [
        ("m", "아침", "m", "meal_m_done", "meal_m_actual"),
        ("l", "점심", "l", "meal_l_done", "meal_l_actual"),
        ("d", "저녁", "d", "meal_d_done", "meal_d_actual"),
    ]:
        with st.container():
            col_l, col_r = st.columns([5,1])
            with col_l:
                st.markdown(f"<span class='rec-tag'>추천</span><span class='rec-text'>{TODAY_MEAL[meal_key]}</span>", unsafe_allow_html=True)
                new_actual = st.text_input(
                    f"실제_{label}",
                    value=st.session_state[actual_key],
                    placeholder="실제로 먹은 것 (추천대로면 비워두세요)",
                    label_visibility="collapsed",
                    key=f"input_{key}"
                )
                if new_actual != st.session_state[actual_key]:
                    st.session_state[actual_key] = new_actual
                    changed = True
            with col_r:
                done = st.checkbox("완료", value=st.session_state[done_key], key=f"cb_{key}", label_visibility="collapsed")
                if done != st.session_state[done_key]:
                    st.session_state[done_key] = done
                    changed = True

        st.divider()

    # 진행률
    done_count = sum([st.session_state.meal_m_done, st.session_state.meal_l_done, st.session_state.meal_d_done])
    st.progress(done_count / 3, text=f"{done_count} / 3 완료")

    # 수분 (ml 단위, 250ml 단위, 목표 2000ml)
    st.markdown("<div class='card-title'>💧 수분 섭취 (목표 2,000ml)</div>", unsafe_allow_html=True)
    new_water = st.slider(
        "수분(ml)", 0, 2000,
        st.session_state.water,
        step=250,
        label_visibility="collapsed"
    )
    if new_water != st.session_state.water:
        st.session_state.water = new_water
        changed = True

    water_ml  = st.session_state.water
    remain_ml = 2000 - water_ml
    st.progress(min(water_ml / 2000, 1.0))
    if remain_ml > 0:
        st.caption(f"💧 {water_ml:,}ml / 2,000ml  ·  {remain_ml:,}ml 남음")
    else:
        st.caption("✅ 수분 목표 달성!")

    # 아침 루틴
    st.info("🌿 기상 후 물 500ml + 소금 한 꼬집 + 레몬즙\n\n☕ 오후 생맥산차 or 오미자차 1잔")

    # Google Sheets 바로가기 버튼
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/1-z86W0vc_7b9T_hEbPgr6uAmG_C9AvFwWJGc-lcQSlo/edit"
    st.markdown(
        f'''<a href="{SHEETS_URL}" target="_blank">
            <button style="width:100%;padding:10px;margin-top:8px;
                background:#1D9E75;color:white;border:none;
                border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">
                📊 Google Sheets 열기
            </button></a>''',
        unsafe_allow_html=True
    )

    if changed:
        save_meal()
        st.markdown("<div class='save-ok'>✓ 자동 저장됨</div>", unsafe_allow_html=True)

# ════════════════════════════
# 탭2: 운동
# ════════════════════════════
with tab2:
    st.markdown("<div class='card-title'>🏋️ 오늘 운동</div>", unsafe_allow_html=True)

    ex_changed = False
    for i, ex in enumerate(st.session_state.exercises):
        col1, col2 = st.columns([5,1])
        with col1:
            st.markdown(f"**{ex['name']}** &nbsp; <span style='color:#9E9E9A;font-size:12px;'>{ex['meta']}</span>", unsafe_allow_html=True)
        with col2:
            done = st.checkbox("완료", value=ex["done"], key=f"ex_{i}", label_visibility="collapsed")
            if done != ex["done"]:
                st.session_state.exercises[i]["done"] = done
                ex_changed = True
        st.divider()

    done_ex = sum(e["done"] for e in st.session_state.exercises)
    total_ex = len(st.session_state.exercises)
    st.progress(done_ex / total_ex if total_ex else 0, text=f"{done_ex} / {total_ex} 완료")

    # 운동 추가
    st.markdown("**운동 추가**")
    col_a, col_b = st.columns([4,1])
    with col_a:
        new_ex = st.text_input("운동 추가", placeholder="운동명 입력...", label_visibility="collapsed")
    with col_b:
        if st.button("➕", use_container_width=True) and new_ex.strip():
            st.session_state.exercises.append({"name": new_ex, "meta":"직접 추가", "done": False})
            st.rerun()

# ════════════════════════════
# 탭3: 할일
# ════════════════════════════
with tab3:
    st.markdown("<div class='card-title'>📋 오늘 할일</div>", unsafe_allow_html=True)

    TAG_COLORS = {"건강":"#E1F5EE", "업무":"#E6F1FB", "일상":"#FAEEDA"}

    for i, todo in enumerate(st.session_state.todos):
        col1, col2 = st.columns([5,1])
        with col1:
            tag_color = TAG_COLORS.get(todo["tag"], "#F0F0F0")
            label_style = "text-decoration:line-through;color:#9E9E9A;" if todo["done"] else ""
            st.markdown(f"<span style='{label_style}'>{todo['text']}</span> &nbsp; <span style='background:{tag_color};font-size:10px;padding:2px 7px;border-radius:10px;'>{todo['tag']}</span>", unsafe_allow_html=True)
        with col2:
            done = st.checkbox("완료", value=todo["done"], key=f"todo_{i}", label_visibility="collapsed")
            if done != todo["done"]:
                st.session_state.todos[i]["done"] = done
                st.rerun()
        st.divider()

    # 할일 추가
    col_a, col_b, col_c = st.columns([4,2,1])
    with col_a:
        new_todo = st.text_input("할일 추가", placeholder="할일 입력...", label_visibility="collapsed")
    with col_b:
        tag_sel = st.selectbox("태그", ["건강","업무","일상"], label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_todo", use_container_width=True) and new_todo.strip():
            st.session_state.todos.append({"text": new_todo, "tag": tag_sel, "done": False})
            st.rerun()

# ════════════════════════════
# 탭4: 메모/아이디어
# ════════════════════════════
with tab4:
    st.markdown("<div class='card-title'>💡 순간 메모 & 아이디어</div>", unsafe_allow_html=True)

    idea_text = st.text_area("메모 입력", placeholder="순간 아이디어, 메모를 입력하세요...", height=100, label_visibility="collapsed")
    col_tag, col_btn = st.columns([3,1])
    with col_tag:
        idea_tag = st.selectbox("태그", ["아이디어","건강","일상","업무"], label_visibility="collapsed")
    with col_btn:
        if st.button("저장", use_container_width=True, type="primary") and idea_text.strip():
            save_idea(idea_text, idea_tag)
            st.session_state.ideas.insert(0, {"time": nj_time_str(), "tag": idea_tag, "text": idea_text})
            st.success("저장됨!")
            st.rerun()

    st.markdown("---")
    for idea in st.session_state.ideas:
        with st.container():
            st.caption(f"{idea['time']} · {idea['tag']}")
            st.markdown(idea["text"])
            st.divider()

# ════════════════════════════
# 탭5: 일기
# ════════════════════════════
with tab5:
    st.markdown("<div class='card-title'>😊 오늘 기분</div>", unsafe_allow_html=True)
    mood_options = ["😴 피곤", "😐 보통", "🙂 좋음", "😄 매우 좋음", "💪 최고"]
    mood_idx = 0
    for i, m in enumerate(mood_options):
        if st.session_state.diary_mood and st.session_state.diary_mood in m:
            mood_idx = i
            break
    mood = st.radio("기분", mood_options, index=mood_idx, horizontal=True, label_visibility="collapsed")
    if mood != st.session_state.diary_mood:
        st.session_state.diary_mood = mood

    st.markdown("<div class='card-title' style='margin-top:12px;'>✏️ 오늘의 일기</div>", unsafe_allow_html=True)
    st.caption("오늘 식단은 잘 지켰나요? 몸 상태는? 감사한 일이 있었나요?")
    diary = st.text_area("일기", value=st.session_state.diary_content, height=200, placeholder="오늘 하루를 기록해 보세요...", label_visibility="collapsed")
    if diary != st.session_state.diary_content:
        st.session_state.diary_content = diary

    st.markdown("<div class='card-title' style='margin-top:12px;'>✨ 성찰 질문</div>", unsafe_allow_html=True)
    st.markdown("오늘 식단을 잘 지켰나요?\n\n몸의 에너지 수준은 1~10 중 몇 점이었나요?\n\n내일 더 잘 하고 싶은 한 가지는?")

    if st.button("💾 일기 저장", type="primary", use_container_width=True):
        save_diary()
        st.success("✓ 일기가 저장되었습니다!")


# ════════════════════════════
# 탭6: 장보기 리스트
# ════════════════════════════
with tab6:
    st.markdown("<div class='card-title'>🛒 주간 장보기 리스트</div>", unsafe_allow_html=True)

    # 목양체질 기본 고정 식재료
    BASE_ITEMS = {
        "🥩 단백질": [
            {"name": "소고기 (국거리/불고기용)", "qty": "500g", "check": False},
            {"name": "닭고기 (삼계탕용 영계)", "qty": "1마리", "check": False},
            {"name": "달걀", "qty": "30개", "check": False},
            {"name": "추어 (미꾸라지)", "qty": "1팩", "check": False},
        ],
        "🥛 유제품": [
            {"name": "그릭요거트", "qty": "4~6개", "check": False},
        ],
        "🥦 채소·뿌리": [
            {"name": "당근", "qty": "3~4개", "check": False},
            {"name": "무", "qty": "1개", "check": False},
            {"name": "우엉", "qty": "1팩", "check": False},
            {"name": "연근", "qty": "1팩", "check": False},
            {"name": "도라지", "qty": "1팩", "check": False},
            {"name": "브로콜리", "qty": "1개", "check": False},
            {"name": "파프리카", "qty": "2~3개", "check": False},
            {"name": "방울토마토", "qty": "1팩", "check": False},
        ],
        "🍎 과일": [
            {"name": "사과", "qty": "4~5개", "check": False},
            {"name": "배", "qty": "2~3개", "check": False},
            {"name": "블루베리", "qty": "1팩", "check": False},
            {"name": "수박 (여름)", "qty": "1/4통", "check": False},
        ],
        "🌾 곡류": [
            {"name": "잡곡밥 (혼합곡)", "qty": "2kg", "check": False},
            {"name": "현미", "qty": "1kg", "check": False},
        ],
        "🫙 양념·기타": [
            {"name": "된장", "qty": "필요시", "check": False},
            {"name": "깍두기", "qty": "1팩", "check": False},
            {"name": "호두", "qty": "1팩", "check": False},
            {"name": "아몬드", "qty": "1팩", "check": False},
            {"name": "레몬", "qty": "3~4개", "check": False},
        ],
        "🍵 차·음료": [
            {"name": "오미자차", "qty": "1박스", "check": False},
            {"name": "생맥산차", "qty": "1박스", "check": False},
        ],
    }

    # 세션 초기화
    if "shopping_items" not in st.session_state:
        st.session_state.shopping_items = BASE_ITEMS.copy()
    if "custom_items" not in st.session_state:
        st.session_state.custom_items = []

    # 초기화 버튼
    col_r1, col_r2 = st.columns([3,1])
    with col_r1:
        st.caption("✅ 체크한 항목 = 이미 있음 / 구매 완료")
    with col_r2:
        if st.button("🔄 초기화", use_container_width=True):
            for cat in st.session_state.shopping_items:
                for item in st.session_state.shopping_items[cat]:
                    item["check"] = False
            st.session_state.custom_items = []
            st.rerun()

    st.divider()

    # 카테고리별 체크리스트
    checked_total = 0
    total_items = 0

    for category, items in st.session_state.shopping_items.items():
        st.markdown(f"**{category}**")
        for i, item in enumerate(items):
            total_items += 1
            col_c, col_n, col_q = st.columns([1, 5, 2])
            with col_c:
                checked = st.checkbox(
                    "체크",
                    value=item["check"],
                    key=f"shop_{category}_{i}",
                    label_visibility="collapsed"
                )
                if checked != item["check"]:
                    st.session_state.shopping_items[category][i]["check"] = checked
            with col_n:
                style = "text-decoration:line-through;color:#9E9E9A;" if item["check"] else ""
                st.markdown(f"<span style='{style}'>{item['name']}</span>", unsafe_allow_html=True)
            with col_q:
                st.caption(item["qty"])
            if checked:
                checked_total += 1
        st.divider()

    # 커스텀 추가 항목
    if st.session_state.custom_items:
        st.markdown("**➕ 추가 항목**")
        for i, item in enumerate(st.session_state.custom_items):
            col_c, col_n, col_d = st.columns([1, 5, 1])
            with col_c:
                checked = st.checkbox(
                    "체크",
                    value=item["check"],
                    key=f"custom_{i}",
                    label_visibility="collapsed"
                )
                st.session_state.custom_items[i]["check"] = checked
                if checked:
                    checked_total += 1
            with col_n:
                style = "text-decoration:line-through;color:#9E9E9A;" if item["check"] else ""
                qty_str = item['qty']
                name_str = item['name']
                st.markdown(f"<span style='{style}'>{name_str} <span style='color:#9E9E9A;font-size:12px;'>{qty_str}</span></span>", unsafe_allow_html=True)
            with col_d:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    st.session_state.custom_items.pop(i)
                    st.rerun()
        total_items += len(st.session_state.custom_items)
        st.divider()

    # 진행률
    st.progress(checked_total / total_items if total_items else 0,
                text=f"구매 완료 {checked_total} / {total_items}개")

    # 항목 추가
    st.markdown("**항목 추가**")
    col_a, col_b, col_c = st.columns([4, 2, 1])
    with col_a:
        new_item_name = st.text_input("품목", placeholder="품목명 입력...", label_visibility="collapsed")
    with col_b:
        new_item_qty = st.text_input("수량", placeholder="수량 (예: 2개)", label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_shop", use_container_width=True) and new_item_name.strip():
            st.session_state.custom_items.append({
                "name": new_item_name.strip(),
                "qty": new_item_qty.strip() or "-",
                "check": False
            })
            st.rerun()

    # Sheets 버튼
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/1-z86W0vc_7b9T_hEbPgr6uAmG_C9AvFwWJGc-lcQSlo/edit"
    st.markdown(
        f'''<a href="{SHEETS_URL}" target="_blank">
            <button style="width:100%;padding:10px;margin-top:12px;
                background:#1D9E75;color:white;border:none;
                border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">
                📊 Google Sheets 열기
            </button></a>''',
        unsafe_allow_html=True
    )import streamlit as st
from datetime import date, datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import json

# ── 페이지 설정 ──
st.set_page_config(
    page_title="성근님의 건강 루틴",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── 뉴저지 현재 시간 ──
def nj_now():
    """뉴저지 시간(America/New_York) 반환"""
    return datetime.now(ZoneInfo("America/New_York"))

def nj_time_str():
    """HH:MM 형식 뉴저지 현재 시간"""
    return nj_now().strftime("%H:%M")

def nj_date_str():
    """YYYY-MM-DD 형식 뉴저지 오늘 날짜"""
    return nj_now().strftime("%Y-%m-%d")

# ── Google Sheets 연결 ──
@st.cache_resource
def get_sheet():
    """Google Sheets 연결 (캐시로 재사용)"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("강님의 건강 관리")  # Google Sheets 파일명

def get_worksheet(tab_name, headers):
    """시트 가져오기 (없으면 생성)"""
    ss = get_sheet()
    try:
        ws = ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=500, cols=len(headers))
        ws.append_row(headers)
    return ws

# ── 요일별 추천 식단 ──
MEALS = {
    0: dict(m="달걀 2개+그릭요거트+배+방울토마토+호두",   l="소고기 된장찌개+현미밥+연근조림",  d="달걀 스크램블+그릭요거트+사과+파프리카"),
    1: dict(m="달걀 2개+그릭요거트+사과+당근스틱+호두",   l="추어탕+잡곡밥+깍두기",             d="달걀 스크램블+그릭요거트+블루베리+방울토마토"),
    2: dict(m="달걀 2개+그릭요거트+배+방울토마토+아몬드", l="추어탕+잡곡밥+깍두기",             d="삶은달걀 2개+그릭요거트+수박+당근스틱"),
    3: dict(m="달걀 2개+그릭요거트+사과+브로콜리+호두",   l="닭갈비+현미밥+된장국(무두부)",      d="달걀 스크램블+그릭요거트+블루베리+브로콜리"),
    4: dict(m="달걀 2개+그릭요거트+배+파프리카+아몬드",   l="설렁탕+잡곡밥+깍두기",             d="삶은달걀 2개+그릭요거트+사과+방울토마토"),
    5: dict(m="달걀 2개+그릭요거트+수박+당근스틱+호두",   l="소고기 국밥+잡곡밥+무생채",        d="달걀 스크램블+그릭요거트+배+당근스틱"),
    6: dict(m="달걀 2개+그릭요거트+사과+브로콜리+아몬드", l="삼계탕(주말보양)+잡곡밥",          d="삶은달걀 2개+그릭요거트+수박+브로콜리"),
}

_NJ_NOW     = datetime.now(ZoneInfo("America/New_York"))
TODAY       = _NJ_NOW.date()
TODAY_STR   = TODAY.strftime("%Y-%m-%d")
DOW         = TODAY.weekday()  # 0=월 ~ 6=일 (Python: 월=0)
DOW_KR      = ["월","화","수","목","금","토","일"][DOW]
TODAY_MEAL  = MEALS[TODAY.weekday()]

# ── 세션 상태 초기화 ──
def init_session():
    defaults = {
        "meal_m_done": False, "meal_l_done": False, "meal_d_done": False,
        "meal_m_actual": "", "meal_l_actual": "", "meal_d_actual": "",
        "water": 0,
        "exercises": [
            {"name":"빠른 걷기","meta":"30분·중강도","done":False},
            {"name":"스트레칭","meta":"15분·아침","done":False},
            {"name":"근력 운동","meta":"20분·상체","done":False},
        ],
        "todos": [
            {"text":"아침 소금물 루틴","tag":"건강","done":False},
            {"text":"추어탕 점심 식사","tag":"건강","done":False},
            {"text":"오후 생맥산차 챙기기","tag":"건강","done":False},
        ],
        "ideas": [],
        "diary_mood": "",
        "diary_content": "",
        "data_loaded": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Sheets에서 오늘 데이터 불러오기 ──
def load_today():
    if st.session_state.get("data_loaded"):
        return
    try:
        # 식단
        ws = get_worksheet("식단기록", ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(ml)","저장시간"])
        rows = ws.get_all_records()
        for row in rows:
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.meal_m_done   = row.get("아침완료","") == "✓"
                st.session_state.meal_l_done   = row.get("점심완료","") == "✓"
                st.session_state.meal_d_done   = row.get("저녁완료","") == "✓"
                st.session_state.meal_m_actual = str(row.get("아침실제",""))
                st.session_state.meal_l_actual = str(row.get("점심실제",""))
                st.session_state.meal_d_actual = str(row.get("저녁실제",""))
                st.session_state.water         = int(row.get("수분(ml)",0) or 0)
                break
        # 일기
        ws2  = get_worksheet("일기", ["날짜","기분","일기내용","저장시간"])
        rows2 = ws2.get_all_records()
        for row in rows2:
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.diary_mood    = str(row.get("기분",""))
                st.session_state.diary_content = str(row.get("일기내용",""))
                break
        st.session_state.data_loaded = True
    except Exception as e:
        st.warning(f"데이터 불러오기 실패: {e}")

# ── Sheets에 식단 저장 ──
def save_meal():
    try:
        headers = ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(ml)","저장시간"]
        ws   = get_worksheet("식단기록", headers)
        rows = ws.get_all_values()
        row_data = [
            TODAY_STR,
            TODAY_MEAL["m"], st.session_state.meal_m_actual, "✓" if st.session_state.meal_m_done else "",
            TODAY_MEAL["l"], st.session_state.meal_l_actual, "✓" if st.session_state.meal_l_done else "",
            TODAY_MEAL["d"], st.session_state.meal_d_actual, "✓" if st.session_state.meal_d_done else "",
            st.session_state.water,
            nj_time_str()
        ]
        # 오늘 행 찾아서 업데이트 or 추가
        for i, row in enumerate(rows):
            if row and str(row[0]) == TODAY_STR:
                ws.update(f"A{i+1}", [row_data])
                return
        ws.append_row(row_data)
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ── Sheets에 일기 저장 ──
def save_diary():
    try:
        headers = ["날짜","기분","일기내용","저장시간"]
        ws   = get_worksheet("일기", headers)
        rows = ws.get_all_values()
        row_data = [TODAY_STR, st.session_state.diary_mood, st.session_state.diary_content, nj_time_str()]
        for i, row in enumerate(rows):
            if row and str(row[0]) == TODAY_STR:
                ws.update(f"A{i+1}", [row_data])
                return
        ws.append_row(row_data)
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ── Sheets에 아이디어 저장 ──
def save_idea(text, tag):
    try:
        headers = ["날짜","시간","태그","내용"]
        ws = get_worksheet("메모아이디어", headers)
        ws.append_row([TODAY_STR, nj_time_str(), tag, text])
    except Exception as e:
        st.error(f"저장 실패: {e}")

# ══════════════════════════════════════════
# UI 시작
# ══════════════════════════════════════════
init_session()
load_today()

# CSS
st.markdown("""
<style>
  /* 전체 배경 */
  .stApp { background: #F7F7F5; }
  /* 헤더 여백 줄이기 */
  .block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 480px; }
  /* 카드 스타일 */
  .card {
    background: white; border-radius: 14px;
    padding: 16px 18px; margin-bottom: 12px;
    border: 0.5px solid rgba(0,0,0,0.10);
  }
  .card-title {
    font-size: 12px; font-weight: 600;
    color: #6B6B68; text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 10px;
  }
  /* 추천 태그 */
  .rec-tag {
    display: inline-block; font-size: 10px;
    background: #E1F5EE; color: #0F6E56;
    padding: 2px 7px; border-radius: 4px;
    font-weight: 600; margin-right: 6px;
  }
  .rec-text { font-size: 12px; color: #9E9E9A; }
  /* 배지 */
  .badge {
    display: inline-block; font-size: 11px;
    background: #E1F5EE; color: #0F6E56;
    padding: 3px 10px; border-radius: 20px;
    font-weight: 500;
  }
  /* 구분선 숨기기 */
  hr { display: none; }
  /* 버튼 커스텀 */
  .stButton>button {
    border-radius: 10px; font-weight: 500;
    border: none; width: 100%;
  }
  /* 입력창 */
  .stTextInput>div>div>input, .stTextArea>div>div>textarea {
    border-radius: 8px; font-size: 14px;
  }
  /* 탭 */
  .stTabs [data-baseweb="tab"] { font-size: 13px; }
  /* 성공 메시지 */
  .save-ok {
    text-align: center; font-size: 12px;
    color: #1D9E75; margin-top: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ──
col1, col2 = st.columns([3,1])
with col1:
    st.markdown(f"<div style='font-size:12px;color:#9E9E9A;'>{TODAY_STR} ({DOW_KR})</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:20px;font-weight:700;'>성근님의 건강 루틴</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div style='text-align:right;padding-top:10px;'><span class='badge'>목양체질</span></div>", unsafe_allow_html=True)

st.markdown("---")

# ── 탭 ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🍚 식단", "🏃 운동", "✅ 할일", "💡 메모", "📓 일기", "🛒 장보기"])

# ════════════════════════════
# 탭1: 식단
# ════════════════════════════
with tab1:
    st.markdown("<div class='card-title'>☀️ 오늘 식단</div>", unsafe_allow_html=True)

    changed = False

    for key, label, meal_key, done_key, actual_key in [
        ("m", "아침", "m", "meal_m_done", "meal_m_actual"),
        ("l", "점심", "l", "meal_l_done", "meal_l_actual"),
        ("d", "저녁", "d", "meal_d_done", "meal_d_actual"),
    ]:
        with st.container():
            col_l, col_r = st.columns([5,1])
            with col_l:
                st.markdown(f"<span class='rec-tag'>추천</span><span class='rec-text'>{TODAY_MEAL[meal_key]}</span>", unsafe_allow_html=True)
                new_actual = st.text_input(
                    f"실제_{label}",
                    value=st.session_state[actual_key],
                    placeholder="실제로 먹은 것 (추천대로면 비워두세요)",
                    label_visibility="collapsed",
                    key=f"input_{key}"
                )
                if new_actual != st.session_state[actual_key]:
                    st.session_state[actual_key] = new_actual
                    changed = True
            with col_r:
                done = st.checkbox("완료", value=st.session_state[done_key], key=f"cb_{key}", label_visibility="collapsed")
                if done != st.session_state[done_key]:
                    st.session_state[done_key] = done
                    changed = True

        st.divider()

    # 진행률
    done_count = sum([st.session_state.meal_m_done, st.session_state.meal_l_done, st.session_state.meal_d_done])
    st.progress(done_count / 3, text=f"{done_count} / 3 완료")

    # 수분 (ml 단위, 250ml 단위, 목표 2000ml)
    st.markdown("<div class='card-title'>💧 수분 섭취 (목표 2,000ml)</div>", unsafe_allow_html=True)
    new_water = st.slider(
        "수분(ml)", 0, 2000,
        st.session_state.water,
        step=250,
        label_visibility="collapsed"
    )
    if new_water != st.session_state.water:
        st.session_state.water = new_water
        changed = True

    water_ml  = st.session_state.water
    remain_ml = 2000 - water_ml
    st.progress(min(water_ml / 2000, 1.0))
    if remain_ml > 0:
        st.caption(f"💧 {water_ml:,}ml / 2,000ml  ·  {remain_ml:,}ml 남음")
    else:
        st.caption("✅ 수분 목표 달성!")

    # 아침 루틴
    st.info("🌿 기상 후 물 500ml + 소금 한 꼬집 + 레몬즙\n\n☕ 오후 생맥산차 or 오미자차 1잔")

    # Google Sheets 바로가기 버튼
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/1-z86W0vc_7b9T_hEbPgr6uAmG_C9AvFwWJGc-lcQSlo/edit"
    st.markdown(
        f'''<a href="{SHEETS_URL}" target="_blank">
            <button style="width:100%;padding:10px;margin-top:8px;
                background:#1D9E75;color:white;border:none;
                border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">
                📊 Google Sheets 열기
            </button></a>''',
        unsafe_allow_html=True
    )

    if changed:
        save_meal()
        st.markdown("<div class='save-ok'>✓ 자동 저장됨</div>", unsafe_allow_html=True)

# ════════════════════════════
# 탭2: 운동
# ════════════════════════════
with tab2:
    st.markdown("<div class='card-title'>🏋️ 오늘 운동</div>", unsafe_allow_html=True)

    ex_changed = False
    for i, ex in enumerate(st.session_state.exercises):
        col1, col2 = st.columns([5,1])
        with col1:
            st.markdown(f"**{ex['name']}** &nbsp; <span style='color:#9E9E9A;font-size:12px;'>{ex['meta']}</span>", unsafe_allow_html=True)
        with col2:
            done = st.checkbox("완료", value=ex["done"], key=f"ex_{i}", label_visibility="collapsed")
            if done != ex["done"]:
                st.session_state.exercises[i]["done"] = done
                ex_changed = True
        st.divider()

    done_ex = sum(e["done"] for e in st.session_state.exercises)
    total_ex = len(st.session_state.exercises)
    st.progress(done_ex / total_ex if total_ex else 0, text=f"{done_ex} / {total_ex} 완료")

    # 운동 추가
    st.markdown("**운동 추가**")
    col_a, col_b = st.columns([4,1])
    with col_a:
        new_ex = st.text_input("운동 추가", placeholder="운동명 입력...", label_visibility="collapsed")
    with col_b:
        if st.button("➕", use_container_width=True) and new_ex.strip():
            st.session_state.exercises.append({"name": new_ex, "meta":"직접 추가", "done": False})
            st.rerun()

# ════════════════════════════
# 탭3: 할일
# ════════════════════════════
with tab3:
    st.markdown("<div class='card-title'>📋 오늘 할일</div>", unsafe_allow_html=True)

    TAG_COLORS = {"건강":"#E1F5EE", "업무":"#E6F1FB", "일상":"#FAEEDA"}

    for i, todo in enumerate(st.session_state.todos):
        col1, col2 = st.columns([5,1])
        with col1:
            tag_color = TAG_COLORS.get(todo["tag"], "#F0F0F0")
            label_style = "text-decoration:line-through;color:#9E9E9A;" if todo["done"] else ""
            st.markdown(f"<span style='{label_style}'>{todo['text']}</span> &nbsp; <span style='background:{tag_color};font-size:10px;padding:2px 7px;border-radius:10px;'>{todo['tag']}</span>", unsafe_allow_html=True)
        with col2:
            done = st.checkbox("완료", value=todo["done"], key=f"todo_{i}", label_visibility="collapsed")
            if done != todo["done"]:
                st.session_state.todos[i]["done"] = done
                st.rerun()
        st.divider()

    # 할일 추가
    col_a, col_b, col_c = st.columns([4,2,1])
    with col_a:
        new_todo = st.text_input("할일 추가", placeholder="할일 입력...", label_visibility="collapsed")
    with col_b:
        tag_sel = st.selectbox("태그", ["건강","업무","일상"], label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_todo", use_container_width=True) and new_todo.strip():
            st.session_state.todos.append({"text": new_todo, "tag": tag_sel, "done": False})
            st.rerun()

# ════════════════════════════
# 탭4: 메모/아이디어
# ════════════════════════════
with tab4:
    st.markdown("<div class='card-title'>💡 순간 메모 & 아이디어</div>", unsafe_allow_html=True)

    idea_text = st.text_area("메모 입력", placeholder="순간 아이디어, 메모를 입력하세요...", height=100, label_visibility="collapsed")
    col_tag, col_btn = st.columns([3,1])
    with col_tag:
        idea_tag = st.selectbox("태그", ["아이디어","건강","일상","업무"], label_visibility="collapsed")
    with col_btn:
        if st.button("저장", use_container_width=True, type="primary") and idea_text.strip():
            save_idea(idea_text, idea_tag)
            st.session_state.ideas.insert(0, {"time": nj_time_str(), "tag": idea_tag, "text": idea_text})
            st.success("저장됨!")
            st.rerun()

    st.markdown("---")
    for idea in st.session_state.ideas:
        with st.container():
            st.caption(f"{idea['time']} · {idea['tag']}")
            st.markdown(idea["text"])
            st.divider()

# ════════════════════════════
# 탭5: 일기
# ════════════════════════════
with tab5:
    st.markdown("<div class='card-title'>😊 오늘 기분</div>", unsafe_allow_html=True)
    mood_options = ["😴 피곤", "😐 보통", "🙂 좋음", "😄 매우 좋음", "💪 최고"]
    mood_idx = 0
    for i, m in enumerate(mood_options):
        if st.session_state.diary_mood and st.session_state.diary_mood in m:
            mood_idx = i
            break
    mood = st.radio("기분", mood_options, index=mood_idx, horizontal=True, label_visibility="collapsed")
    if mood != st.session_state.diary_mood:
        st.session_state.diary_mood = mood

    st.markdown("<div class='card-title' style='margin-top:12px;'>✏️ 오늘의 일기</div>", unsafe_allow_html=True)
    st.caption("오늘 식단은 잘 지켰나요? 몸 상태는? 감사한 일이 있었나요?")
    diary = st.text_area("일기", value=st.session_state.diary_content, height=200, placeholder="오늘 하루를 기록해 보세요...", label_visibility="collapsed")
    if diary != st.session_state.diary_content:
        st.session_state.diary_content = diary

    st.markdown("<div class='card-title' style='margin-top:12px;'>✨ 성찰 질문</div>", unsafe_allow_html=True)
    st.markdown("오늘 식단을 잘 지켰나요?\n\n몸의 에너지 수준은 1~10 중 몇 점이었나요?\n\n내일 더 잘 하고 싶은 한 가지는?")

    if st.button("💾 일기 저장", type="primary", use_container_width=True):
        save_diary()
        st.success("✓ 일기가 저장되었습니다!")


# ════════════════════════════
# 탭6: 장보기 리스트
# ════════════════════════════
with tab6:
    st.markdown("<div class='card-title'>🛒 주간 장보기 리스트</div>", unsafe_allow_html=True)

    # 목양체질 기본 고정 식재료
    BASE_ITEMS = {
        "🥩 단백질": [
            {"name": "소고기 (국거리/불고기용)", "qty": "500g", "check": False},
            {"name": "닭고기 (삼계탕용 영계)", "qty": "1마리", "check": False},
            {"name": "달걀", "qty": "30개", "check": False},
            {"name": "추어 (미꾸라지)", "qty": "1팩", "check": False},
        ],
        "🥛 유제품": [
            {"name": "그릭요거트", "qty": "4~6개", "check": False},
        ],
        "🥦 채소·뿌리": [
            {"name": "당근", "qty": "3~4개", "check": False},
            {"name": "무", "qty": "1개", "check": False},
            {"name": "우엉", "qty": "1팩", "check": False},
            {"name": "연근", "qty": "1팩", "check": False},
            {"name": "도라지", "qty": "1팩", "check": False},
            {"name": "브로콜리", "qty": "1개", "check": False},
            {"name": "파프리카", "qty": "2~3개", "check": False},
            {"name": "방울토마토", "qty": "1팩", "check": False},
        ],
        "🍎 과일": [
            {"name": "사과", "qty": "4~5개", "check": False},
            {"name": "배", "qty": "2~3개", "check": False},
            {"name": "블루베리", "qty": "1팩", "check": False},
            {"name": "수박 (여름)", "qty": "1/4통", "check": False},
        ],
        "🌾 곡류": [
            {"name": "잡곡밥 (혼합곡)", "qty": "2kg", "check": False},
            {"name": "현미", "qty": "1kg", "check": False},
        ],
        "🫙 양념·기타": [
            {"name": "된장", "qty": "필요시", "check": False},
            {"name": "깍두기", "qty": "1팩", "check": False},
            {"name": "호두", "qty": "1팩", "check": False},
            {"name": "아몬드", "qty": "1팩", "check": False},
            {"name": "레몬", "qty": "3~4개", "check": False},
        ],
        "🍵 차·음료": [
            {"name": "오미자차", "qty": "1박스", "check": False},
            {"name": "생맥산차", "qty": "1박스", "check": False},
        ],
    }

    # 세션 초기화
    if "shopping_items" not in st.session_state:
        st.session_state.shopping_items = BASE_ITEMS.copy()
    if "custom_items" not in st.session_state:
        st.session_state.custom_items = []

    # 초기화 버튼
    col_r1, col_r2 = st.columns([3,1])
    with col_r1:
        st.caption("✅ 체크한 항목 = 이미 있음 / 구매 완료")
    with col_r2:
        if st.button("🔄 초기화", use_container_width=True):
            for cat in st.session_state.shopping_items:
                for item in st.session_state.shopping_items[cat]:
                    item["check"] = False
            st.session_state.custom_items = []
            st.rerun()

    st.divider()

    # 카테고리별 체크리스트
    checked_total = 0
    total_items = 0

    for category, items in st.session_state.shopping_items.items():
        st.markdown(f"**{category}**")
        for i, item in enumerate(items):
            total_items += 1
            col_c, col_n, col_q = st.columns([1, 5, 2])
            with col_c:
                checked = st.checkbox(
                    "체크",
                    value=item["check"],
                    key=f"shop_{category}_{i}",
                    label_visibility="collapsed"
                )
                if checked != item["check"]:
                    st.session_state.shopping_items[category][i]["check"] = checked
            with col_n:
                style = "text-decoration:line-through;color:#9E9E9A;" if item["check"] else ""
                st.markdown(f"<span style='{style}'>{item['name']}</span>", unsafe_allow_html=True)
            with col_q:
                st.caption(item["qty"])
            if checked:
                checked_total += 1
        st.divider()

    # 커스텀 추가 항목
    if st.session_state.custom_items:
        st.markdown("**➕ 추가 항목**")
        for i, item in enumerate(st.session_state.custom_items):
            col_c, col_n, col_d = st.columns([1, 5, 1])
            with col_c:
                checked = st.checkbox(
                    "체크",
                    value=item["check"],
                    key=f"custom_{i}",
                    label_visibility="collapsed"
                )
                st.session_state.custom_items[i]["check"] = checked
                if checked:
                    checked_total += 1
            with col_n:
                style = "text-decoration:line-through;color:#9E9E9A;" if item["check"] else ""
                qty_str = item['qty']
                name_str = item['name']
                st.markdown(f"<span style='{style}'>{name_str} <span style='color:#9E9E9A;font-size:12px;'>{qty_str}</span></span>", unsafe_allow_html=True)
            with col_d:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    st.session_state.custom_items.pop(i)
                    st.rerun()
        total_items += len(st.session_state.custom_items)
        st.divider()

    # 진행률
    st.progress(checked_total / total_items if total_items else 0,
                text=f"구매 완료 {checked_total} / {total_items}개")

    # 항목 추가
    st.markdown("**항목 추가**")
    col_a, col_b, col_c = st.columns([4, 2, 1])
    with col_a:
        new_item_name = st.text_input("품목", placeholder="품목명 입력...", label_visibility="collapsed")
    with col_b:
        new_item_qty = st.text_input("수량", placeholder="수량 (예: 2개)", label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_shop", use_container_width=True) and new_item_name.strip():
            st.session_state.custom_items.append({
                "name": new_item_name.strip(),
                "qty": new_item_qty.strip() or "-",
                "check": False
            })
            st.rerun()

    # Sheets 버튼
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/1-z86W0vc_7b9T_hEbPgr6uAmG_C9AvFwWJGc-lcQSlo/edit"
    st.markdown(
        f'''<a href="{SHEETS_URL}" target="_blank">
            <button style="width:100%;padding:10px;margin-top:12px;
                background:#1D9E75;color:white;border:none;
                border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">
                📊 Google Sheets 열기
            </button></a>''',
        unsafe_allow_html=True
    )
