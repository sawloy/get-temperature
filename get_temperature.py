# -*- coding: utf-8 -*-
# 与 WBGT 风格一致：一个文件里包含 Flask 应用与路由
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, re, datetime as dt
from bs4 import BeautifulSoup

# ---------------------------
# 初始化 Flask 应用
# ---------------------------
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 返回 JSON 不转义中文

# ---------------------------
# 开启跨域（与 WBGT 相同策略）
# ---------------------------
CORS(app, resources={
    r"/*": {
        "origins": [
            "*",  # 调试方便；正式可收紧
            "https://excel.officeapps.live.com",
            "https://*.officeapps.live.com",
            "https://*.sharepoint.com",
            "https://*.office.com",
        ]
    }
}, supports_credentials=False)

# ---------------------------
# 目标页面与通用请求头
# ---------------------------
TENKI_URL = "https://tenki.jp/forecast/9/43/8220/40100/"  # 北九州市
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def _clean(s: str) -> str:
    """去掉多余空白"""
    return re.sub(r"\s+", " ", s or "").strip()

def _parse_today(soup: BeautifulSoup) -> dict:
    """从 tenki.jp 页面解析“今日”天气"""
    for h in soup.find_all(["h3", "h4"]):
        title = _clean(h.get_text())
        if not title.startswith("今日"):
            continue
        box = h.find_parent() or h

        # 日期（如 10月22日）
        m = re.search(r"(\d+月\d+日)", title)
        date_jp = m.group(1) if m else ""

        # 天气文案 / 最高 / 最低 / 最大风速
        weather_text, tmax, tmin, wind = "", None, None, ""

        wx = box.find(string=re.compile("晴|曇|雨|雪"))
        if wx:
            weather_text = _clean(wx)

        tx = box.find(string=re.compile("最高"))
        if tx:
            m = re.search(r"最高\s*([\d\-]+)\s*℃", _clean(tx.parent.get_text()))
            if m: tmax = m.group(1)

        tn = box.find(string=re.compile("最低"))
        if tn:
            m = re.search(r"最低\s*([\d\-]+)\s*℃", _clean(tn.parent.get_text()))
            if m: tmin = m.group(1)

        wind_row = box.find(string=re.compile("最大風速"))
        if wind_row:
            wind = _clean(wind_row.parent.get_text())

        return {
            "runDate": dt.datetime.utcnow().isoformat(),
            "city": "北九州市",
            "date": date_jp,
            "weather_text": weather_text,
            "t_max": tmax,
            "t_min": tmin,
            "wind_max": wind
        }
    return {}

# ---------------------------
# 路由：/today  —— 返回“今日天气” JSON
# ---------------------------
@app.get("/today")
def today():
    # 可选支持 ?url= 覆盖，保持与 WBGT 思路一致（便于以后切换城市/页面）
    url = request.args.get("url", TENKI_URL)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"fetch_failed: {e}"}), 502

    soup = BeautifulSoup(r.text, "html.parser")
    data = _parse_today(soup)
    if not data:
        return jsonify({"error": "parse_failed_or_structure_changed"}), 404
    return jsonify(data)

# ---------------------------
# 健康检查
# ---------------------------
@app.get("/")
def root():
    return jsonify({"ok": True, "endpoints": ["/today"]})
