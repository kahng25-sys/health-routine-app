import streamlit as st
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz

# ── 시간대 설정 (뉴저지 ET) ──
ET = pytz.timezone("America/New_York")

def now_local():
    return datetime.now(ET).strftime("%H:%M")

# ── 페이지 설정 ──
st.set_page_config(
    page_title="성근님의 건강 루틴",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Google Sheets 연결 ──
@st.cache_resource
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("강님의 건강 관리")

def get_worksheet(tab_name, headers):
    ss = get_sheet()
    try:
        ws = ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=500, cols=len(headers))
        ws.append_row(headers)
    return ws

def upsert_row(ws, today_str, row_data):
    rows = ws.get_all_values()
    for i, row in enumerate(rows):
        if row and str(row[0]) == today_str:
            ws.update(f"A{i+1}", [row_data])
            return
    ws.append_row(row_data)

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

TODAY      = date.today()
TODAY_STR  = TODAY.strftime("%Y-%m-%d")
DOW        = TODAY.weekday()
DOW_KR     = ["월","화","수","목","금","토","일"][DOW]
TODAY_MEAL = MEALS[DOW]

DEFAULT_EXERCISES = [
    {"name":"빠른 걷기", "meta":"30분·중강도", "done":False},
    {"name":"스트레칭",  "meta":"15분·아침",   "done":False},
    {"name":"근력 운동", "meta":"20분·상체",   "done":False},
]

DEFAULT_TODOS = [
    {"text":"아침 소금물 루틴",    "tag":"건강", "done":False},
    {"text":"오후 생맥산차 챙기기","tag":"건강", "done":False},
]

def init_session():
    defaults = {
        "meal_m_done":   False, "meal_l_done":   False, "meal_d_done":   False,
        "meal_m_actual": "",    "meal_l_actual": "",    "meal_d_actual": "",
        "water":         0,
        "exercises":     [e.copy() for e in DEFAULT_EXERCISES],
        "todos":         [t.copy() for t in DEFAULT_TODOS],
        "ideas":         [],
        "diary_mood":    "",
        "diary_content": "",
        "data_loaded":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def load_today():
    if st.session_state.get("data_loaded"):
        return
    try:
        ws = get_worksheet("식단기록", ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(컵)","저장시간"])
        for row in ws.get_all_records():
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.meal_m_done   = row.get("아침완료","") == "✓"
                st.session_state.meal_l_done   = row.get("점심완료","") == "✓"
                st.session_state.meal_d_done   = row.get("저녁완료","") == "✓"
                st.session_state.meal_m_actual = str(row.get("아침실제",""))
                st.session_state.meal_l_actual = str(row.get("점심실제",""))
                st.session_state.meal_d_actual = str(row.get("저녁실제",""))
                st.session_state.water         = int(row.get("수분(컵)", 0) or 0)
                break
        ws_ex = get_worksheet("운동기록", ["날짜","운동명","메타","완료","저장시간"])
        ex_rows = [r for r in ws_ex.get_all_records() if str(r.get("날짜","")) == TODAY_STR]
        if ex_rows:
            st.session_state.exercises = [
                {"name": r["운동명"], "meta": r["메타"], "done": r.get("완료","") == "✓"}
                for r in ex_rows
            ]
        ws_td = get_worksheet("할일기록", ["날짜","내용","태그","완료","저장시간"])
        td_rows = [r for r in ws_td.get_all_records() if str(r.get("날짜","")) == TODAY_STR]
        if td_rows:
            st.session_state.todos = [
                {"text": r["내용"], "tag": r.get("태그","일상"), "done": r.get("완료","") == "✓"}
                for r in td_rows
            ]
        ws2 = get_worksheet("일기", ["날짜","기분","일기내용","저장시간"])
        for row in ws2.get_all_records():
            if str(row.get("날짜","")) == TODAY_STR:
                st.session_state.diary_mood    = str(row.get("기분",""))
                st.session_state.diary_content = str(row.get("일기내용",""))
                break
        st.session_state.data_loaded = True
    except Exception as e:
        st.warning(f"데이터 불러오기 실패: {e}")
        st.session_state.data_loaded = True

def save_meal():
    try:
        headers = ["날짜","아침추천","아침실제","아침완료","점심추천","점심실제","점심완료","저녁추천","저녁실제","저녁완료","수분(컵)","저장시간"]
        ws = get_worksheet("식단기록", headers)
        row_data = [
            TODAY_STR,
            TODAY_MEAL["m"], st.session_state.meal_m_actual, "✓" if st.session_state.meal_m_done else "",
            TODAY_MEAL["l"], st.session_state.meal_l_actual, "✓" if st.session_state.meal_l_done else "",
            TODAY_MEAL["d"], st.session_state.meal_d_actual, "✓" if st.session_state.meal_d_done else "",
            st.session_state.water, now_local()
        ]
        upsert_row(ws, TODAY_STR, row_data)
    except Exception as e:
        st.error(f"식단 저장 실패: {e}")

def save_exercises():
    try:
        headers = ["날짜","운동명","메타","완료","저장시간"]
        ws = get_worksheet("운동기록", headers)
        rows = ws.get_all_values()
        to_delete = [i+1 for i, r in enumerate(rows) if r and str(r[0]) == TODAY_STR]
        for idx in reversed(to_delete):
            ws.delete_rows(idx)
        for ex in st.session_state.exercises:
            ws.append_row([TODAY_STR, ex["name"], ex["meta"], "✓" if ex["done"] else "", now_local()])
    except Exception as e:
        st.error(f"운동 저장 실패: {e}")

def save_todos():
    try:
        headers = ["날짜","내용","태그","완료","저장시간"]
        ws = get_worksheet("할일기록", headers)
        rows = ws.get_all_values()
        to_delete = [i+1 for i, r in enumerate(rows) if r and str(r[0]) == TODAY_STR]
        for idx in reversed(to_delete):
            ws.delete_rows(idx)
        for td in st.session_state.todos:
            ws.append_row([TODAY_STR, td["text"], td["tag"], "✓" if td["done"] else "", now_local()])
    except Exception as e:
        st.error(f"할일 저장 실패: {e}")

def save_diary():
    try:
        headers = ["날짜","기분","일기내용","저장시간"]
        ws = get_worksheet("일기", headers)
        row_data = [TODAY_STR, st.session_state.diary_mood, st.session_state.diary_content, now_local()]
        upsert_row(ws, TODAY_STR, row_data)
    except Exception as e:
        st.error(f"일기 저장 실패: {e}")

def save_idea(text, tag):
    try:
        headers = ["날짜","시간","태그","내용"]
        ws = get_worksheet("메모아이디어", headers)
        ws.append_row([TODAY_STR, now_local(), tag, text])
    except Exception as e:
        st.error(f"메모 저장 실패: {e}")

# ── 물방울 버튼 HTML 렌더링 ──
def render_water_buttons(current, max_cups=12):
    """SVG 물방울 모양 버튼 렌더링"""
    buttons_html = "<div style='display:flex; gap:6px; flex-wrap:wrap; margin:8px 0;'>"
    for i in range(max_cups):
        filled = i < current
        fill_color   = "#1D9E75" if filled else "white"
        stroke_color = "#1D9E75" if filled else "#B0B0B0"
        # SVG 물방울 모양: 위가 뾰족한 방울
        buttons_html += f"""
        <div onclick="handleWater({i}, {current})"
             style="cursor:pointer; width:34px; height:34px;
                    display:flex; align-items:center; justify-content:center;">
          <svg width="26" height="32" viewBox="0 0 26 32" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 1 C13 1 2 14 2 21 C2 27.075 7.477 32 13 32 C18.523 32 24 27.075 24 21 C24 14 13 1 13 1 Z"
                  fill="{fill_color}" stroke="{stroke_color}" stroke-width="2"/>
          </svg>
        </div>"""
    buttons_html += "</div>"

    # JavaScript로 클릭 처리 → Streamlit session_state 우회 (URL 파라미터 방식)
    js = """
    <script>
    function handleWater(index, current) {
        // 채워진 걸 클릭하면 줄이기, 빈 걸 클릭하면 늘리기
        const newVal = (index < current) ? index : index + 1;
        const input = window.parent.document.querySelectorAll('input[type=number]');
        // Streamlit number_input hidden 방식 대신 query param 사용
        const url = new URL(window.parent.location.href);
        url.searchParams.set('water', newVal);
        window.parent.history.replaceState({}, '', url);
        window.parent.location.reload();
    }
    </script>
    """
    return buttons_html + js

# ══════════════════════════════════════════
# UI 시작
# ══════════════════════════════════════════
init_session()
load_today()

# URL 파라미터로 수분 업데이트 처리
params = st.query_params
if "water" in params:
    try:
        new_water = int(params["water"])
        if new_water != st.session_state.water:
            st.session_state.water = new_water
            save_meal()
        st.query_params.clear()
    except:
        pass

# ── CSS ──
st.markdown("""
<style>
  .stApp { background: #F7F7F5; }
  .block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 480px; }
  .card-title {
    font-size: 12px; font-weight: 600;
    color: #6B6B68; text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 10px;
  }
  .rec-tag {
    display: inline-block; font-size: 10px;
    background: #E1F5EE; color: #0F6E56;
    padding: 2px 7px; border-radius: 4px;
    font-weight: 600; margin-right: 6px;
  }
  .rec-text { font-size: 12px; color: #9E9E9A; }
  .badge {
    display: inline-block; font-size: 11px;
    background: #E1F5EE; color: #0F6E56;
    padding: 3px 10px; border-radius: 20px;
    font-weight: 500;
  }
  hr { display: none; }
  .stButton>button { border-radius: 10px; font-weight: 500; border: none; width: 100%; }
  .stTextInput>div>div>input,
  .stTextArea>div>div>textarea { border-radius: 8px; font-size: 14px; }
  .stTabs [data-baseweb="tab"] { font-size: 13px; }
  .save-ok { text-align: center; font-size: 12px; color: #1D9E75; margin-top: 4px; }
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🍚 식단", "🏃 운동", "✅ 할일", "💡 메모", "📓 일기"])

# ════════════════════════════
# 탭1: 식단
# ════════════════════════════
with tab1:
    st.markdown("<div class='card-title'>☀️ 오늘 식단</div>", unsafe_allow_html=True)
    meal_changed = False

    for key, label, done_key, actual_key in [
        ("m", "아침", "meal_m_done", "meal_m_actual"),
        ("l", "점심", "meal_l_done", "meal_l_actual"),
        ("d", "저녁", "meal_d_done", "meal_d_actual"),
    ]:
        col_l, col_r = st.columns([5,1])
        with col_l:
            st.markdown(f"<span class='rec-tag'>추천</span><span class='rec-text'>{TODAY_MEAL[key]}</span>", unsafe_allow_html=True)
            new_actual = st.text_input(
                f"실제_{label}", value=st.session_state[actual_key],
                placeholder="실제로 먹은 것 입력 (추천대로면 비워두세요)",
                label_visibility="collapsed", key=f"input_{key}"
            )
            if new_actual != st.session_state[actual_key]:
                st.session_state[actual_key] = new_actual
                meal_changed = True
        with col_r:
            done = st.checkbox("완료", value=st.session_state[done_key], key=f"cb_{key}", label_visibility="collapsed")
            if done != st.session_state[done_key]:
                st.session_state[done_key] = done
                meal_changed = True
        st.divider()

    done_count = sum([st.session_state.meal_m_done, st.session_state.meal_l_done, st.session_state.meal_d_done])
    st.progress(done_count / 3, text=f"{done_count} / 3 완료")

    # ── 수분 (st.button 방식) ──
    st.markdown("<div class='card-title' style='margin-top:16px;'>💧 수분 섭취 (목표 8컵)</div>", unsafe_allow_html=True)

    MAX_WATER = 12
    current_water = st.session_state.water

    water_cols = st.columns(MAX_WATER)
    for i in range(MAX_WATER):
        filled = i < current_water
        new_val = i if filled else i + 1
        with water_cols[i]:
            if st.button("💧" if filled else "○", key=f"water_{i}"):
                st.session_state.water = new_val
                save_meal()
                st.rerun()

    water = st.session_state.water
    goal_text = "✅ 목표 달성!" if water >= 8 else f"({8 - water}컵 남음)"
    st.caption(f"{water} / 8컵  {goal_text}")

    st.info("🌿 기상 후 물 500ml + 소금 한 꼬집 + 레몬즙\n\n☕ 오후 생맥산차 or 오미자차 1잔")

    col_s1, col_s2 = st.columns([1,1])
    with col_s1:
        if st.button("💾 식단 저장", use_container_width=True, type="primary"):
            save_meal()
            st.success("✓ 저장됨!")
    with col_s2:
        if meal_changed:
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

    done_ex  = sum(e["done"] for e in st.session_state.exercises)
    total_ex = len(st.session_state.exercises)
    st.progress(done_ex / total_ex if total_ex else 0, text=f"{done_ex} / {total_ex} 완료")

    col_a, col_b, col_c = st.columns([3,2,1])
    with col_a:
        new_ex = st.text_input("운동 추가", placeholder="운동명...", label_visibility="collapsed")
    with col_b:
        new_ex_meta = st.text_input("시간/강도", placeholder="예: 20분·중강도", label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_ex", use_container_width=True) and new_ex.strip():
            st.session_state.exercises.append({"name": new_ex, "meta": new_ex_meta or "직접 추가", "done": False})
            save_exercises()
            st.rerun()

    if ex_changed:
        save_exercises()
        st.markdown("<div class='save-ok'>✓ 자동 저장됨</div>", unsafe_allow_html=True)
    if st.button("💾 운동 저장", use_container_width=True, type="primary"):
        save_exercises()
        st.success("✓ 저장됨!")

# ════════════════════════════
# 탭3: 할일
# ════════════════════════════
with tab3:
    st.markdown("<div class='card-title'>📋 오늘 할일</div>", unsafe_allow_html=True)
    TAG_COLORS = {"건강":"#E1F5EE", "업무":"#E6F1FB", "일상":"#FAEEDA"}
    td_changed = False
    for i, todo in enumerate(st.session_state.todos):
        col1, col2 = st.columns([5,1])
        with col1:
            tag_color   = TAG_COLORS.get(todo["tag"], "#F0F0F0")
            label_style = "text-decoration:line-through;color:#9E9E9A;" if todo["done"] else ""
            st.markdown(
                f"<span style='{label_style}'>{todo['text']}</span> &nbsp; "
                f"<span style='background:{tag_color};font-size:10px;padding:2px 7px;border-radius:10px;'>{todo['tag']}</span>",
                unsafe_allow_html=True
            )
        with col2:
            done = st.checkbox("완료", value=todo["done"], key=f"todo_{i}", label_visibility="collapsed")
            if done != todo["done"]:
                st.session_state.todos[i]["done"] = done
                td_changed = True
        st.divider()

    col_a, col_b, col_c = st.columns([4,2,1])
    with col_a:
        new_todo = st.text_input("할일 추가", placeholder="할일 입력...", label_visibility="collapsed")
    with col_b:
        tag_sel = st.selectbox("태그", ["건강","업무","일상"], label_visibility="collapsed")
    with col_c:
        if st.button("➕", key="add_todo", use_container_width=True) and new_todo.strip():
            st.session_state.todos.append({"text": new_todo, "tag": tag_sel, "done": False})
            save_todos()
            st.rerun()

    if td_changed:
        save_todos()
        st.markdown("<div class='save-ok'>✓ 자동 저장됨</div>", unsafe_allow_html=True)
    if st.button("💾 할일 저장", use_container_width=True, type="primary"):
        save_todos()
        st.success("✓ 저장됨!")

# ════════════════════════════
# 탭4: 메모
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
            st.session_state.ideas.insert(0, {"time": now_local(), "tag": idea_tag, "text": idea_text})
            st.success("저장됨!")
            st.rerun()

    if st.session_state.ideas:
        st.markdown("---")
        for idea in st.session_state.ideas:
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
        if st.session_state.diary_mood and st.session_state.diary_mood == m:
            mood_idx = i
            break
    mood = st.radio("기분", mood_options, index=mood_idx, horizontal=True, label_visibility="collapsed")
    if mood != st.session_state.diary_mood:
        st.session_state.diary_mood = mood

    st.markdown("<div class='card-title' style='margin-top:12px;'>✏️ 오늘의 일기</div>", unsafe_allow_html=True)
    st.caption("오늘 식단은 잘 지켰나요? 몸 상태는? 감사한 일이 있었나요?")
    diary = st.text_area(
        "일기", value=st.session_state.diary_content, height=200,
        placeholder="오늘 하루를 기록해 보세요...", label_visibility="collapsed"
    )
    if diary != st.session_state.diary_content:
        st.session_state.diary_content = diary

    st.markdown("<div class='card-title' style='margin-top:12px;'>✨ 성찰 질문</div>", unsafe_allow_html=True)
    st.markdown("- 오늘 식단을 잘 지켰나요?\n- 몸의 에너지 수준은 1~10 중 몇 점이었나요?\n- 내일 더 잘 하고 싶은 한 가지는?")

    if st.button("💾 일기 저장", type="primary", use_container_width=True):
        save_diary()
        st.success("✓ 일기가 저장되었습니다!")
