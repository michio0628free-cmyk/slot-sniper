import streamlit as st
import json
import os

st.set_page_config(page_title="Slot-Sniper 自動判定版", layout="wide")

def load_rules():
    file_path = "machines.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

rules = load_rules()

st.title("🎰 Slot-Sniper：三次元スマスロ解析（自動判定版）")

if not rules:
    st.error("machines.json が見つかりません。")
    st.stop()

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📥 1. データカウンター入力")
    st.caption("ホールのデータ表示機の数値をそのまま入力してください。")
    
    machine_name = st.selectbox("機種を選択", list(rules.keys()))
    rule = rules[machine_name]
    
    is_reset = st.checkbox("🌅 朝イチ設定変更（リセット）濃厚台", value=False)
    if is_reset and "reset_notes" in rule:
        st.info(f"**【朝イチ】** {rule['reset_notes']}")
        
    current_g = st.number_input("① 現在のハマりゲーム数 (G)", min_value=0, max_value=3000, value=100, step=10)
    
    st.markdown("---")
    total_g = st.number_input("② 本日の総通常ゲーム数 (G)", min_value=0, max_value=10000, value=0, step=100)
    total_diff = st.number_input("③ 現在の総差枚数 (グラフの±枚数)", value=0, step=100)
    current_hour = st.slider("④ 現在の時刻", min_value=9, max_value=22, value=10)

with col2:
    st.subheader("🎯 2. 総合判定レポート")
    
    score = 50
    alerts = []
    target_g = rule["reset_target_g"] if is_reset else rule["base_target_g"]
    ceiling_g = rule["reset_ceiling"] if is_reset else rule["normal_ceiling"]
    
    # --- 総ゲーム数と差枚数からの自動判定ロジック ---
    if total_diff >= rule.get("cold_zone_diff", 1500):
        target_g += 150
        score -= 25
        alerts.append(("error", f"🥶【冷遇警戒】差枚が+{total_diff}枚です。ボーダーを+150G厳格化。"))
    elif total_diff <= rule.get("hot_zone_diff", -1000):
        bonus_g = 100
        # 深い吸い込みで総ゲーム数が多いほど強く優遇
        if total_g >= 3000 and total_diff <= -2000:
            bonus_g = 200 
        target_g -= bonus_g
        score += 20
        alerts.append(("success", f"🔥【優遇区間】総G数{total_g}Gで{total_diff}枚。ボーダーを-{bonus_g}G引き下げ。"))

    # 閉店欠損
    if current_hour >= 20:
        penalty_g = (current_hour - 19) * 80
        target_g += penalty_g
        score -= 15
        alerts.append(("warning", f"⏰【閉店欠損】{current_hour}時台のため、ボーダーを+{penalty_g}G厳格化。"))

    # 有利区間切断までの概算距離
    rem_diff = rule["tsuranuki_diff"] - total_diff
    capped_g = min(current_g, ceiling_g)
    estimated_ev = 1000 + (capped_g - target_g) * 30
    
    if 0 < rem_diff <= rule["tsuranuki_margin"]:
        score += 40
        estimated_ev += 4000
        alerts.append(("success", f"🌈【切断目前】有利区間切断ラインまで残り約{rem_diff}枚！全ツッパ推奨。"))
    elif total_diff < -3000:
         alerts.append(("info", f"💡【切断遠い】ツラヌキラインまで遠いため、一撃の期待枚数は下がります。"))

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