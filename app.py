import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import time
import random
import base64
import re

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="7年級英文單字學習系統", page_icon="📖", layout="centered")

# --- 2. 注入自定義 CSS (優化間距與卡片) ---
st.markdown("""
    <style>
    h1 { font-size: 24px !important; margin-bottom: 5px !important; }
    .custom-card {
        background-color: #fdfaf5;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        padding: 15px 20px;
        min-height: 200px;
        display: block;
        width: 100%;
        margin-bottom: 10px;
        position: relative;
    }
    hr, .stDivider { display: none !important; }
    .button-offset {
        margin-top: -55px; 
        margin-left: 20px;
        position: relative;
        z-index: 100;
    }
    [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    .stButton > button {
        font-size: 14px !important;
        padding: 2px 10px !important;
        border-radius: 8px;
    }
    .score-box {
        font-size: 22px; font-weight: bold; text-align: center;
        color: #2e7d32; background-color: #e8f5e9;
        padding: 10px; border-radius: 10px; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 初始化 Session State ---
if 'df' not in st.session_state: st.session_state.df = None
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'show_back' not in st.session_state: st.session_state.show_back = False
if 'is_auto_playing' not in st.session_state: st.session_state.is_auto_playing = False
if 'last_voiced_state' not in st.session_state: st.session_state.last_voiced_state = None

# 聽寫專用狀態
if 'score' not in st.session_state: st.session_state.score = 0
if 'total_asked' not in st.session_state: st.session_state.total_asked = 0
if 'quiz_feedback' not in st.session_state: st.session_state.quiz_feedback = ""
if 'input_key' not in st.session_state: st.session_state.input_key = 0
if 'is_answered' not in st.session_state: st.session_state.is_answered = False

# --- 4. 語音工具 ---
def play_silent_audio(text):
    if text:
        try:
            tts = gTTS(text=text, lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            b64 = base64.b64encode(fp.getvalue()).decode()
            md = f'<audio autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.components.v1.html(md, height=0, width=0)
        except Exception: pass

def clean_text(text):
    return re.sub(r'[^\w\s]', '', str(text)).lower().strip()

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("⚙️ 控制中心")
    uploaded_file = st.file_uploader("選擇單字表", type=["xlsx", "xls"])
    if uploaded_file:
        df_up = pd.read_excel(uploaded_file)
        df_up.columns = [c.strip() for c in df_up.columns]
        st.session_state.df = df_up
    
    st.write("---")
    mode = st.radio("功能選擇", ["單字卡學習", "聽寫測驗"])
    
    if mode == "聽寫測驗":
        st.write("---")
        quiz_type = st.radio("聽寫模式", ["單字", "單字+解釋", "例句"])

# --- 6. 主畫面邏輯 ---
st.markdown(f"<h1>✨ {mode}</h1>", unsafe_allow_html=True)

if st.session_state.df is None:
    st.info("👈 請先上傳 Excel 單字表開始學習。")
else:
    df = st.session_state.df
    idx = st.session_state.current_index % len(df)
    current_row = df.iloc[idx]
    current_state_str = f"{idx}_{st.session_state.show_back}"

    # ===================== [模式 A：單字卡學習] =====================
    if mode == "單字卡學習":
        st.write(f"📖 **{idx + 1} / {len(df)}**")
        
        # 朗讀文本設定 (根據昨天 app.py)
        front_text = f"{current_row['單字']}. {current_row.get('英文解釋', '')}"
        back_text = f"{current_row.get('搭配詞', '')}. {current_row.get('例句', '')}"

        if not st.session_state.show_back:
            card_html = f"""
                <div class="custom-card">
                    <h2 style='color: #5c85d6; font-size: 40px; margin: 0px;'>{current_row['單字']}</h2>
                    <p style='color: #94a3b8; font-size: 18px; margin: 0px 0px 10px 0px;'>{current_row.get('發音', '')}</p>
                    <p style='margin: 3px 0; font-size: 18px;'><strong>中文：</strong> {current_row['中文']}</p>
                    <p style='margin: 3px 0; font-size: 18px;'><strong>解釋：</strong> {current_row.get('英文解釋', '')}</p>
                </div>
            """
        else:
            card_html = f"""
                <div class="custom-card">
                    <h2 style='color: #67b279; font-size: 30px; margin: 0px;'>{current_row.get('詞性', '')}</h2>
                    <p style='margin: 10px 0 3px 0; font-size: 18px;'><strong>搭配詞：</strong> {current_row.get('搭配詞', '')}</p>
                    <p style='margin: 3px 0; font-size: 18px;'><strong>例句：</strong> {current_row.get('例句', '')}</p>
                </div>
            """
        st.markdown(card_html, unsafe_allow_html=True)

        # 朗讀按鈕位移 (吸入卡片)
        st.markdown('<div class="button-offset">', unsafe_allow_html=True)
        btn_label = "🔊 朗讀正面" if not st.session_state.show_back else "🔊 朗讀背面"
        if st.button(btn_label, key=f"voice_btn_{current_state_str}"):
            play_silent_audio(front_text if not st.session_state.show_back else back_text)
        st.markdown('</div>', unsafe_allow_html=True)

        # 自動進入朗讀狀態的即時語音
        if st.session_state.last_voiced_state != current_state_str:
            play_silent_audio(front_text if not st.session_state.show_back else back_text)
            st.session_state.last_voiced_state = current_state_str

        # 控制按鈕列
        st.write("") 
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ 上一張", use_container_width=True):
                st.session_state.current_index = (idx - 1) % len(df)
                st.session_state.show_back = False
                st.session_state.is_auto_playing = False
                st.rerun()
        with col2:
            if st.button("🔄 翻轉卡片", use_container_width=True):
                st.session_state.show_back = not st.session_state.show_back
                st.rerun()
        with col3:
            if st.button("下一個 ➡️", use_container_width=True):
                st.session_state.current_index = (idx + 1) % len(df)
                st.session_state.show_back = False
                st.session_state.is_auto_playing = False
                st.rerun()

        # 亂數抽題與自動朗讀
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("🎲 亂數抽題", use_container_width=True):
                st.session_state.current_index = random.randint(0, len(df) - 1)
                st.session_state.show_back = False
                st.rerun()
        with bcol2:
            if not st.session_state.is_auto_playing:
                if st.button("▶️ 開始自動朗讀", use_container_width=True, type="primary"):
                    st.session_state.is_auto_playing = True
                    st.session_state.show_back = False
                    st.rerun()
            else:
                if st.button("⏹ 停止自動朗讀", use_container_width=True):
                    st.session_state.is_auto_playing = False
                    st.rerun()

        if st.session_state.is_auto_playing:
            text_to_read = front_text if not st.session_state.show_back else back_text
            wait_time = max(5, len(text_to_read) // 10 + 3)
            time.sleep(wait_time)
            if not st.session_state.show_back:
                st.session_state.show_back = True
            else:
                st.session_state.current_index = (idx + 1) % len(df)
                st.session_state.show_back = False
            st.rerun()

    # ===================== [模式 B：聽寫測驗] =====================
    elif mode == "聽寫測驗":
        # 聽寫測驗邏輯
        if quiz_type == "單字":
            correct_ans, sound_text = current_row['單字'], current_row['單字']
        elif quiz_type == "單字+解釋":
            correct_ans, sound_text = current_row['單字'], f"{current_row['單字']}. {current_row.get('英文解釋', '')}"
        else: # 例句模式
            correct_ans = current_row.get('例句', '')
            sound_text = correct_ans

        # 1. 播放題目 (可重複播放)
        if st.button("🔊 點我播放題目 (Listen)", use_container_width=True, type="primary"):
            play_silent_audio(sound_text)

        # 2. 判斷邏輯
        def handle_quiz_submit():
            user_val = st.session_state[f"quiz_input_{st.session_state.input_key}"]
            if not user_val.strip():
                st.session_state.quiz_feedback = "⚠️ 請輸入內容"
                return
            
            if clean_text(user_val) == clean_text(correct_ans):
                st.session_state.score += 1
                st.session_state.quiz_feedback = f"✅ 正確！答案是: {correct_ans}"
            else:
                st.session_state.quiz_feedback = f"❌ 錯誤！正確答案: {correct_ans}"
            
            st.session_state.total_asked += 1
            st.session_state.is_answered = True

        # 3. 輸入框
        st.text_input(
            "請輸入聽到的內容：", 
            key=f"quiz_input_{st.session_state.input_key}",
            on_change=handle_quiz_submit,
            disabled=st.session_state.is_answered,
            placeholder="輸入後按 Enter 或點下方按鈕..."
        )

        # 4. 提交按鈕
        if not st.session_state.is_answered:
            if st.button("提交 (Submit)", use_container_width=True):
                handle_quiz_submit()
                st.rerun()

        # 5. 反饋與下一題
        if st.session_state.quiz_feedback:
            if "✅" in st.session_state.quiz_feedback: st.success(st.session_state.quiz_feedback)
            else: st.error(st.session_state.quiz_feedback)

        if st.session_state.is_answered:
            if st.button("下一題 ➡️", use_container_width=True, type="secondary"):
                st.session_state.current_index = (st.session_state.current_index + 1) % len(df)
                st.session_state.quiz_feedback = ""
                st.session_state.is_answered = False
                st.session_state.input_key += 1
                st.rerun()

        # 6. 得分顯示
        st.markdown(f'<div class="score-box">得分：{st.session_state.score} / {st.session_state.total_asked}</div>', unsafe_allow_html=True)
        
        if st.button("退出並重置分數", use_container_width=True):
            st.session_state.score = 0
            st.session_state.total_asked = 0
            st.session_state.quiz_feedback = ""
            st.session_state.is_answered = False
            st.session_state.current_index = 0
            st.rerun()