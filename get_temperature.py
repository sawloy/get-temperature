# -*- coding: utf-8 -*-
# -----------------------------------------------------------
# 功能：从 tenki.jp 爬取北九州市的“今日天气”，并返回 JSON。
# 技术：Flask + BeautifulSoup
# 输出：只包含最高气温、最低气温、最大风速
# -----------------------------------------------------------

from flask import Flask, request, jsonify     # Flask 用于创建 Web 应用
from flask_cors import CORS                   # CORS 用于允许跨域访问
import requests, re                           # requests 负责请求网页，re 用于正则匹配
from bs4 import BeautifulSoup                 # BeautifulSoup 用于解析 HTML

# ---------------------------
# 初始化 Flask 应用
# ---------------------------
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 返回 JSON 时不转义中文字符

# ---------------------------
# 开启跨域访问（CORS）
# 允许 Excel Online / Power Apps 等访问这个接口
# ---------------------------
CORS(app, resources={
    r"/*": {
        "origins": [
            "*",  # 调试阶段允许所有来源（正式可以收紧）
            "https://excel.officeapps.live.com",
            "https://*.officeapps.live.com",
            "https://*.sharepoint.com",
            "https://*.office.com",
        ]
    }
}, supports_credentials=False)

# ---------------------------
# 常量：目标网页与请求头
# ---------------------------
TENKI_URL = "https://tenki.jp/forecast/9/43/8220/40100/"  # 北九州市的天气预报页面
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "ja,en;q=0.8"  # 优先请求日文页面
}

# ---------------------------
# 工具函数：清除字符串中的多余空格和换行
# ---------------------------
def _clean(s: str) -> str:
    """把字符串中的连续空格、换行等清理成一个空格"""
    return re.sub(r"\s+", " ", s or "").strip()
    # 解释：
    # r"\s+" 表示匹配任意数量的空白字符（包括空格、制表符、换行）
    # re.sub(..., s) 把这些空白替换为单个空格
    # (s or "") 表示如果 s 是 None，就用空字符串替代
    # .strip() 去掉开头和结尾的空格

# ---------------------------
# 主体解析函数：从网页中提取“今日天气”
# ---------------------------
def _parse_today(soup: BeautifulSoup) -> dict:
    """解析 tenki.jp 页面，提取今日的最高气温、最低气温、最大风速"""
    # 遍历页面中的所有 h3 和 h4 标签
    for h in soup.find_all(["h3", "h4"]):
        title = _clean(h.get_text())
        if not title.startswith("今日"):
            continue  # 如果标题不是“今日”，跳过

        # 找到包含该标题的父元素（整个“今日”天气区块）
        box = h.find_parent() or h
        # 把区块中所有文字平铺成一个字符串
        block_text = " ".join(box.stripped_strings)

        # 使用正则表达式匹配气温和风速
        # \d+ 表示一个或多个数字，[\-]? 表示可选的负号
        m1 = re.search(r"最高\s*([\-]?\d+)\s*℃", block_text)        # 最高气温
        m2 = re.search(r"最低\s*([\-]?\d+)\s*℃", block_text)        # 最低气温
        m3 = re.search(r"最大風速\s*([^\s]+.*?m/s)", block_text)     # 最大风速（例：“東の風 3m/s”）

        # 如果匹配成功就取出括号里的内容，否则为 None
        tmax = m1.group(1) if m1 else None
        tmin = m2.group(1) if m2 else None
        wind = m3.group(1) if m3 else None

        # 只返回三项数据
        return {
            "t_max": tmax,
            "t_min": tmin,
            "wind_max": wind
        }

    # 如果没有找到“今日”相关内容，则返回空字典
    return {}

# ---------------------------
# 路由：/today
# 当访问 https://.../today 时，返回今日天气 JSON
# ---------------------------
@app.get("/today")
def today():
    """GET /today —— 返回今日天气的JSON数据"""
    # 支持 ?url= 参数，可手动指定其他城市页面
    url = request.args.get("url", TENKI_URL)

    # 第一步：抓取网页
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()  # 如果HTTP状态码不是200，会抛出异常
    except Exception as e:
        return jsonify({"error": f"fetch_failed: {e}"}), 502

    # 第二步：解析网页内容
    soup = BeautifulSoup(r.text, "html.parser")
    data = _parse_today(soup)

    # 如果解析失败或结构变化
    if not data:
        return jsonify({"error": "parse_failed_or_structure_changed"}), 404

    # 第三步：返回 JSON
    return jsonify(data)

# ---------------------------
# 健康检查路由
# 访问 / 时返回“ok”，方便 Render 检查服务是否运行
# ---------------------------
@app.get("/")
def root():
    """GET / —— 用于 Render 部署测试"""
    return jsonify({"ok": True, "endpoint": "/today"})
