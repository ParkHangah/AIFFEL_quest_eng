"""
Streamlit 프론트엔드
"""
import streamlit as st
import requests

# [API 엔드포인트 설정]
API_URL = "http://localhost:8000/predict"

# ---------------------------------------------------------
# [새로 추가할 전처리 함수]
# ---------------------------------------------------------
def sanitize_for_json(text: str) -> str:
    """
    텍스트의 스마트 따옴표를 표준으로 정제하고, 
    데이터 파이프라인 오류를 방지하기 위한 전처리를 수행합니다.
    """
    if not text:
        return text

    # 1. 스마트 따옴표 및 백틱을 일반 작은/큰따옴표로 변환
    quote_map = str.maketrans("‘’`“”", "'''\"\"")
    cleaned_text = text.translate(quote_map)

    # 2. 눈에 보이지 않는 Null 바이트(\x00) 등 치명적인 제어 문자 제거
    # (일반적인 줄바꿈(\n)은 백엔드 chunking 로직에서 필요하므로 그대로 보존합니다)
    cleaned_text = cleaned_text.replace('\x00', '')

    return cleaned_text

# [세션 상태(Session State) 초기화]
if "temp_text" not in st.session_state:
    st.session_state["temp_text"] = ""
if "current_input" not in st.session_state:
    st.session_state["current_input"] = ""
if "api_result" not in st.session_state:
    st.session_state["api_result"] = None
if "history_works" not in st.session_state:
    st.session_state["history_works"] = []

# ---------------------------------------------------------
# 1. 페이지 및 사이드바 설정 [1, 3]
# ---------------------------------------------------------
st.set_page_config(page_title="지능형 현지화 파이프라인", layout="wide")

with st.sidebar:
    st.header("⚙️ 설정")
    # 사이드바에 API Key 입력 [3]
    api_key = st.text_input("API Key 입력", type="password", help="발급받은 API 키를 입력하세요.")
    st.divider()
    # 그동안 작성한 작품 리스트 선택
    st.selectbox("내가 작성한 작품 리스트", ["선택하세요..."] + st.session_state["history_works"])

# ---------------------------------------------------------
# 2. 메인 화면 - 서비스 소개 및 입력부 [1, 4]
# ---------------------------------------------------------
# st.title()로 제목
st.title("지능형 현지화 파이프라인")
st.markdown("최대 5000자의 서사 텍스트를 입력받아 **다국어 번역**과 **핵심 키워드 추출**을 수행하는 프로토타입입니다.")

# 작품 제목 입력창
work_title = st.text_input("작품 제목", placeholder="작품의 제목을 입력해주세요.")

# 분석 실행을 위한 공통 함수 (버튼 클릭 시 requests.post()로 API 호출) [1, 2]
def analyze_text(title, text):
    if not title or not text:
        st.warning("작품 제목과 텍스트를 모두 입력해주세요.")
        return
    if not api_key:
        st.warning("우측 사이드바에 API Key를 입력해주세요.")
        return
    # 💡 [핵심 추가] API 요청 전 데이터 정제(Sanitization) 실행

    sanitized_title = sanitize_for_json(title)
    sanitized_text = sanitize_for_json(text)

    with st.spinner("번역 및 키워드 추출을 진행 중입니다..."):
        headers = {"X-API-Key": api_key}
        payload = {"title": sanitized_title, "text": sanitized_text}
        try:
            response = requests.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            # 결과 저장 및 히스토리 업데이트
            st.session_state["api_result"] = response.json()
            if sanitized_title not in st.session_state["history_works"]:
                st.session_state["history_works"].append(sanitized_title)
                
            st.success("분석이 완료되었습니다!")
        except requests.exceptions.HTTPError as e:
            st.error(f"API 호출 실패 (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            st.error(f"서버에 연결할 수 없습니다: {e}")

# 탭 구성: 파일로 불러오기 / 작품 입력하기
tab1, tab2 = st.tabs(["📁 파일로 불러오기", "✍️ 작품 입력하기"])

with tab1:
    # 본인의 모델에 맞는 입력 위젯 (file_uploader)
    uploaded_file = st.file_uploader("분석할 텍스트 파일(.txt)을 업로드하세요", type=["txt"])
    file_text = ""
    if uploaded_file:
        file_text = uploaded_file.read().decode("utf-8")
        st.text_area("파일 내용 미리보기", file_text, height=150, disabled=True)
    
    if st.button("확인 (파일 분석)"):
        analyze_text(work_title, file_text)

with tab2:
    # 본인의 모델에 맞는 입력 위젯 (text_input/text_area)
    current_input = st.text_area(
        "서사 텍스트 입력 (최대 5000자)", 
        value=st.session_state["current_input"],
        height=300, 
        max_chars=5000
    )
    # 글자수 세기
    st.caption(f"현재 글자수: {len(current_input)} / 5000자")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 임시저장"):
            st.session_state["temp_text"] = current_input
            st.success("상태(Status)에 임시저장되었습니다.")
    with col2:
        if st.button("📂 임시저장 파일 불러오기"):
            st.session_state["current_input"] = st.session_state["temp_text"]
            st.rerun()  # 화면을 새로고침하여 불러온 텍스트 반영 [5]
    with col3:
        if st.button("확인 (텍스트 분석)"):
            st.session_state["current_input"] = current_input
            analyze_text(work_title, current_input)

# ---------------------------------------------------------
# 3. 작품 출력 화면 (결과 표시) [4, 6]
# ---------------------------------------------------------
if st.session_state["api_result"]:
    st.divider()
    result = st.session_state["api_result"]
    
    # 작품 제목
    st.header(f"📖 {result['title']}")
    
    # 제어 옵션 레이아웃
    ctrl_col1, ctrl_col2 = st.columns(2)
    with ctrl_col1:
        # 출력 내용 선택
        view_option = st.radio(
            "출력 내용 선택", 
            ["원문보기", "번역본보기", "원문+번역 대조보기"],
            horizontal=True
        )
    with ctrl_col2:
        # 출력 형태 선택 (p태그 display 제어)
        format_option = st.radio(
            "출력 형태 선택", 
            ["Block (단락별 줄바꿈)", "Inline (자연스럽게 이어쓰기)"],
            horizontal=True
        )

    # 작품 키워드 출력 (출력 형태에 따라 분기)
    st.subheader("🔑 작품 핵심 키워드")
    # keyword 필드가 존재하고 데이터가 있을 때만 처리
    all_keywords = result.get("keyword", [])
    
    # 인덱스 0은 원문(KOR), 인덱스 1은 번역본(ENG) 키워드 리스트입니다.
    top_orig_kw = all_keywords[0] if len(all_keywords) > 0 else []
    top_trans_kw = all_keywords[1] if len(all_keywords) > 1 else [] # <--- [1]로 수정!
    
    if view_option == "원문보기":
        st.write(f"**원문 키워드:** {', '.join(top_orig_kw)}")
    elif view_option == "번역본보기":
        st.write(f"**번역본 키워드:** {', '.join(top_trans_kw)}")
    else:
        st.write(f"**원문 키워드:** {', '.join(top_orig_kw)}")
        st.write(f"**번역본 키워드:** {', '.join(top_trans_kw)}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. 동적 CSS 및 HTML 렌더링
    # ---------------------------------------------------------
    # 사용자가 Inline을 선택하면 normal 타입 p태그는 inline, Block이면 block.
    # 대사(dialogue)와 생각(thought)은 무조건 display: block.
    wrapper_class = "block-mode" if format_option == "Block (단락별 줄바꿈)" else "inline-mode"
    
    custom_css = f"""
    <style>
    /* 기본 컨테이너 및 단락(<section>) 스타일 */
    .render-container {{ font-size: 16px; line-height: 1.6; }}
    section.paragraph {{ margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px; }}
    
    /* 일반 문장(normal) 동적 디스플레이 */
    .block-mode p.normal {{ display: block; margin-bottom: 10px; }}
    .inline-mode p.normal {{ display: inline; margin-right: 5px; }}
    
    /* 대사(dialogue)와 생각(thought)은 무조건 block, 따옴표 생성 */
    p.dialogue, p.thought {{
        display: block !important; 
        margin: 10px 0;
        padding-left: 10px;
    }}
    p.dialogue {{ font-weight: 600; color: #1565C0; }}
    p.dialogue::before {{ content: '"'; }}
    p.dialogue::after {{ content: '"'; }}
    
    p.thought {{ font-style: italic; color: #6A1B9A; }}
    p.thought::before {{ content: "'"; }}
    p.thought::after {{ content: "'"; }}
    
    /* 번역본 대조보기 시 번역 텍스트 색상 처리 */
    .translated-text {{ color: #757575; font-size: 0.95em; display: block; margin-top: 2px; }}
    </style>
    """
    
    # HTML 조립 (문단은 <section>, 문장은 <p> 태그)
    html_out = f'{custom_css}<div class="render-container {wrapper_class}">'
    
    for para in result["data"]:
        html_out += '<section class="paragraph">'

        # 💡 문단 레벨에서 타입 가져오기
        p_type = para.get("paragraph_type", 0)
        # 클래스 맵핑 (이제 문단 전체가 동일한 스타일을 가질 수도 있고, 
        # 혹은 이전처럼 개별 문장에 스타일을 줄 수도 있습니다.)
        if p_type == 1: p_class = "dialogue"
        elif p_type == 2: p_class = "thought"
        else: p_class = "normal"

        for sent in para["sentences"]:
            orig_text = sent["original_text"]
            trans_text = sent.get("translated_text", "")
            
            # 표시 내용 분기
            if view_option == "원문보기":
                disp_text = orig_text
            elif view_option == "번역본보기":
                disp_text = trans_text
            else:
                # 대조보기: 원문 아래에 번역문을 별도 span으로 배치
                disp_text = f"{orig_text}<span class='translated-text'>{trans_text}</span>"
            
            html_out += f'<p class="{p_class}">{disp_text}</p>'
            
        html_out += '</section>'
        
    html_out += '</div>'
    
    # 렌더링
    st.markdown(html_out, unsafe_allow_html=True)
