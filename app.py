import streamlit as st
import json
import os
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Slot-Sniper AI自動判定版", layout="wide")

if "ai_machine" not in st.session_state:
    st.session_state.ai_machine = "Lスマスロ北斗の拳"
if "ai_current_g" not in st.session_state:
    st.session_state.ai_current_g = 0
if "ai_total_g" not in st.session_state:
    st.session_state.ai_total_g = 0
if "ai_total_diff" not in st.session_state:
    st.session_state.ai_total_diff = 0

def load_rules():
    file_path = "machines.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

rules = load_rules()
st.title("🎰 Slot-Sniper：AI自動解析（Vision AI搭載版）")

if not rules:
    st.error("machines.json が見つかりません。")
    st.stop()

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📸 画像からAI自動入力")
    st.caption("データサイトのスクショ（スランプグラフ含む）を選択してください。")
    uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])

    if uploaded_file is not None:
        if st.button("✨ AIでグラフと数値を読み取る"):
            with st.spinner("AIがグラフと文字を解析しています（数秒かかります）..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    target_model = None
                    # 画像エラーから判明した、確実に使える最新の無料枠モデルを優先指定
                    for pref in ['models/gemini-2.5-flash', 'models/gemini-3.5-flash', 'models/gemini-2.5-pro']:
                        if pref in available_models:
                            target_model = pref.replace("models/", "")
                            break
                            
                    # 万が一指定モデルがない場合は、リストの中から「flash」と名の付く軽量モデルを安全に探す
                    if not target_model:
                        flash_models = [m for m in available_models if 'flash' in m]
                        if flash_models:
                            target_model = flash_models[0].replace("models/", "")
                        elif available_models:
                            target_model = available_models[0].replace("models/", "")
                        else:
                            raise Exception("このAPIキーで利用できる画像解析モデルが見つかりません。")

                    st.info(f"💡 自動選択されたAIモデル: {target_model} で解析中...")
                    model = genai.GenerativeModel(target_model)
                    img = Image.open(uploaded_file)

                    prompt = """
                    あなたはプロのパチスロデータアナリストです。画像から以下の4つの数値を読み取り、JSON形式で出力してください。
                    スランプグラフ画像の場合、グラフの右端（最新の点）の目盛りを読んで「現在の差枚数」を推測してください。

                    【出力JSONフォーマット】
                    ```json
                    {
                      "machine": "機種名（文字列。分からない場合は空文字）",
                      "current_g": 現在のハマりゲーム数（数値。分からない場合は0）,
                      "total_g": 累計ゲーム数（数値）,
                      "total_diff": スランプグラフから推測される現在の差枚数（数値。マイナスなら負の値。例: 2400, -500）
                    }
                    ```
                    """
                    
                    response = model.generate_content([prompt, img])
                    
                    raw_text = response.text.strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                        
                    result = json.loads(raw_text.strip())

                    detected_machine = result.get("machine", "")
                    if detected_machine in rules:
                        st.session_state.ai_machine = detected_machine
                    
                    st.session_state.ai_current_g = int(result.get("current_g", 0))
                    st.session_state.ai_total_g = int(result.get("total_g", 0))
                    st.session_state.ai_total_diff = int(result.get("total_diff", 0))

                    st.success("✅ 読み取り完了！入力枠に自動反映されました。")

                except Exception as e:
                    st.error(f"⚠️ AIエラー詳細: {e}")

    st.markdown("---")
    st.subheader("📥 1. データカウンター入力")
    
    machine_name = st.selectbox("機種を選択", list(rules.keys()), key="ai_machine")
    rule = rules[machine_name]
    
    is_reset = st.checkbox("🌅 朝イチ設定変更（リセット）濃厚台", value=False)
    
    current_g = st.number_input("① 現在のハマりゲーム数 (G)", min_value=0, max_value=3000, step=10, key="ai_current_g")
    total_g = st.number_input("② 本日の総通常ゲーム数 (G)", min_value=0, max_value=10000, step=10, key="ai_total_g")
    total_diff = st.number_input("③ 現在の総差枚数 (グラフの±枚数)", step=100, key="ai_total_diff")
    current_hour = st.slider("④ 現在の時刻", min_value=9, max_value=22, value=10)

with col2:
    st.subheader("🎯 2. 総合判定レポート")
    
    score = 50
    alerts = []
    target_g = rule["reset_target_g"] if is_reset else rule["base_target_g"]
    ceiling_g = rule["reset_ceiling"] if is_reset else rule["normal_ceiling"]
    
    if total_diff >= rule.get("cold_zone_diff", 1500):
        target_g += 150
        score -= 25
        alerts.append(("error", f"🥶【冷遇警戒】差枚が+{total_diff}枚です。ボーダーを+150G厳格化。"))
    elif total_diff <= rule.get("hot_zone_diff", -1000):
        bonus_g = 100
        if total_g >= 3000 and total_diff <= -2000:
            bonus_g = 200 
        target_g -= bonus_g
        score += 20
        alerts.append(("success", f"🔥【優遇区間】総G数{total_g}Gで{total_diff}枚。ボーダーを-{bonus_g}G引き下げ。"))

    if current_hour >= 20:
        penalty_g = (current_hour - 19) * 80
        target_g += penalty_g
        score -= 15
        alerts.append(("warning", f"⏰【閉店欠損】{current_hour}時台のため、ボーダーを+{penalty_g}G厳格化。"))

    rem_diff = rule["tsuranuki_diff"] - total_diff
    capped_g = min(current_g, ceiling_g)
    estimated_ev = 1000 + (capped_g - target_g) * 30
    
    if 0 < rem_diff <= rule["tsuranuki_margin"]:
        score += 40
        estimated_ev += 4000
        alerts.append(("success", f"🌈【切断目前】有利区間切断ラインまで残り約{rem_diff}枚！全ツッパ推奨。"))

    if estimated_ev < -5000:
        estimated_ev = -5000

    st.metric(
        label="📊 推定期待値（自動補正後）", 
        value=f"{'+' if estimated_ev > 0 else ''}{estimated_ev:,} 円",
        delta="プラス期待値！打てます" if estimated_ev > 0 else "マイナス期待値（見送り推奨）",
        delta_color="normal" if estimated_ev > 0 else "inverse"
    )

    st.markdown("---")

    if current_g >= target_g:
        score += 30
        alerts.append(("success", f"✅【狙い目到達】現在{current_g}G（推奨ボーダー: {target_g}G〜 / 天井: {ceiling_g}G）"))
    else:
        alerts.append(("info", f"⏳【G数不足】推奨ボーダー（{target_g}G）まで、あと {target_g - current_g}G 足りません。"))

    score = max(0, min(100, score))

    if score >= 75:
        st.success(f"### 判定：🔥 全ツッパ（スコア: {score}/100）")
    elif score >= 55:
        st.warning(f"### 判定：⚡ 条件付き（スコア: {score}/100）")
    else:
        st.error(f"### 判定：❌ 見送り（スコア: {score}/100）")

    st.progress(score)
    for level, msg in alerts:
        if level == "success": st.success(msg)
        elif level == "error": st.error(msg)
        elif level == "warning": st.warning(msg)
        else: st.info(msg)