import streamlit as st
import json
import os

st.set_page_config(page_title="Slot-Sniper 期待値算出版", layout="wide")

def load_rules():
    file_path = "machines.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

rules = load_rules()

st.title("🎰 Slot-Sniper：三次元スマスロ解析（期待値算出版）")

if not rules:
    st.error("machines.json が見つかりません。")
    st.stop()

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📥 1. 台データ入力")
    machine_name = st.selectbox("機種を選択", list(rules.keys()))
    rule = rules[machine_name]
    st.caption(f"💡 通常メモ: {rule['notes']}")
    
    is_reset = st.checkbox("🌅 朝イチ設定変更（リセット）濃厚台", value=False)
    
    if is_reset and "reset_notes" in rule:
        st.info(f"**【朝イチ専用アドバイス】**\n{rule['reset_notes']}")
        
    current_g = st.number_input("現在のハマりゲーム数 (G)", min_value=0, max_value=3000, value=100, step=10)
    
    st.markdown("---")
    section_diff = st.number_input("同一有利区間内の差枚数 (枚)", value=0, step=100)
    recent_diff = st.number_input("直近1500G間の差枚数推移 (枚)", value=0, step=100)
    history_str = st.text_input("履歴信号 (カンマ区切り)", placeholder="例: 8, 8, 245")
    current_hour = st.slider("現在の時刻", min_value=9, max_value=22, value=10)

with col2:
    st.subheader("🎯 2. 総合判定レポート")
    
    score = 50
    alerts = []
    target_g = rule["reset_target_g"] if is_reset else rule["base_target_g"]
    ceiling_g = rule["reset_ceiling"] if is_reset else rule["normal_ceiling"]
    
    # 冷遇・優遇・閉店時間によるボーダー補正
    if recent_diff >= rule["cold_zone_diff"]:
        target_g += 150
        score -= 25
        alerts.append(("error", f"🥶【冷遇区間】直近差枚が+{recent_diff}枚。ボーダーを+150G引き上げ。"))
    elif recent_diff <= rule["hot_zone_diff"]:
        target_g -= 100
        score += 20
        alerts.append(("success", f"🔥【優遇区間】直近差枚が{recent_diff}枚。ボーダーを-100G引き下げ。"))

    if current_hour >= 20:
        penalty_g = (current_hour - 19) * 80
        target_g += penalty_g
        score -= 15
        alerts.append(("warning", f"⏰【閉店欠損】{current_hour}時台のため、ボーダーを+{penalty_g}G厳格化。"))

    rem_diff = rule["tsuranuki_diff"] - section_diff
    
    # 期待値（円）計算ロジック
    # 推奨ボーダー到達で+1000円を基準とし、1Gハマるごとに約+30円として換算
    capped_g = min(current_g, ceiling_g)
    estimated_ev = 1000 + (capped_g - target_g) * 30
    
    if 0 < rem_diff <= rule["tsuranuki_margin"]:
        score += 40
        estimated_ev += 4000  # ツラヌキ直前は期待値を大幅プラス補正
        alerts.append(("success", f"🌈【ツラヌキ目前】有利区間切断ラインまで残り約{rem_diff}枚！全ツッパ推奨。"))

    # あまりに低いマイナス値の丸め処理
    if estimated_ev < -5000:
        estimated_ev = -5000

    # 期待値のデカデカ表示（Streamlitのメトリクス機能）
    st.metric(
        label="📊 推定期待値（現在の状態に基づく概算）", 
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