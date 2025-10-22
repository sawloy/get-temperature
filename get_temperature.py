# -*- coding: utf-8 -*-   # 指定文件编码为 UTF-8，保证中文正常显示
import requests, datetime as dt, re   # 导入 requests 用于抓网页，datetime 用于时间戳，re 用于正则表达式处理
from bs4 import BeautifulSoup         # 从 bs4 库导入 BeautifulSoup，用于解析 HTML 网页内容

# 要爬取的页面 URL：北九州市的天气预报页面
URL = "https://tenki.jp/forecast/9/43/8220/40100/"

# 设置 HTTP 请求头，模拟浏览器访问，防止被识别为爬虫
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# 定义一个工具函数：清除字符串中的多余空白字符（空格、换行等）
def text_clean(s):
    return re.sub(r"\s+", " ", s).strip()

# -------------------- 今日・明日の天気 部分 --------------------
def parse_today_tomorrow(soup):
    panels = []   # 用于保存“今日”“明日”的天气信息

    # 遍历所有 h3/h4 标签，找到标题中包含“今日”或“明日”的部分
    for h in soup.find_all(["h3","h4"]):
        title = text_clean(h.get_text())   # 获取标题文本并清理空格
        if title.startswith("今日") or title.startswith("明日"):  # 筛选出“今日”“明日”
            box = h.find_parent()  # 找到标题的父节点（包含天气信息的整个区域）
            if not box: 
                continue  # 如果没找到，跳过该循环

            # 从标题中提取日期（例如 “10月21日”）
            date_m = re.search(r"(\d+月\d+日)", title)
            date_jp = date_m.group(1) if date_m else title  # 若没匹配到，用原始标题代替

            # 初始化各字段的默认值
            weather_text = ""   # 天气文字（例：晴のち曇）
            tmax = tmin = None  # 最高气温、最低气温
            sunrise = sunset = ""  # 日出、日落
            wind = ""              # 最大风速
            pops = {"00-06":"","06-12":"","12-18":"","18-24":""}  # 不同时段的降水概率

            # ---------------- 天气文案 ----------------
            wx = box.find(string=re.compile("晴|曇|雨|雪"))   # 找包含这些天气关键字的文本
            if wx:
                weather_text = text_clean(wx)

            # ---------------- 最高气温 ----------------
            tx = box.find(string=re.compile("最高"))
            if tx:
                m = re.search(r"最高\s*([\d\-]+)\s*℃", text_clean(tx.parent.get_text()))
                if m: tmax = m.group(1)

            # ---------------- 最低气温 ----------------
            tn = box.find(string=re.compile("最低"))
            if tn:
                m = re.search(r"最低\s*([\d\-]+)\s*℃", text_clean(tn.parent.get_text()))
                if m: tmin = m.group(1)

            # ---------------- 日出・日入 ----------------
            sr = box.find(string=re.compile("日の出"))
            if sr:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(sr.parent.get_text()))
                if m: sunrise = m.group(1)
            ss = box.find(string=re.compile("日の入"))
            if ss:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(ss.parent.get_text()))
                if m: sunset = m.group(1)

            # ---------------- 降水確率 ----------------
            precip_row = box.find(string=re.compile("降水確率"))
            if precip_row:
                row = precip_row.parent.get_text(" ")  # 获取整行文字
                nums = re.findall(r"\d+%", row)        # 提取所有百分比数字
                if len(nums) == 4:                     # 若有四个值，则依次对应四个时间段
                    pops["00-06"], pops["06-12"], pops["12-18"], pops["18-24"] = nums

            # ---------------- 最大風速 ----------------
            wind_row = box.find(string=re.compile("最大風速"))
            if wind_row:
                wind = text_clean(wind_row.parent.get_text())

            # ---------------- 汇总结果 ----------------
            panels.append({
                "date": date_jp,
                "weather_text": weather_text,
                "t_max": tmax, "t_min": tmin,
                "pop_00_06": pops["00-06"], "pop_06_12": pops["06-12"],
                "pop_12_18": pops["12-18"], "pop_18_24": pops["18-24"],
                "wind_max": wind,
                "sunrise": sunrise, "sunset": sunset
            })
    return panels[:2]  # 返回前两天的数据（今日、明日）

# -------------------- 10日間天気 部分 --------------------
def parse_10day(soup):
    out = []   # 存放10日天气结果
    ten_header = soup.find(string=re.compile("10日間天気"))  # 找到“10日間天気”这几个字所在的地方
    if not ten_header:
        return out
    table_parent = ten_header.find_parent()  # 找到包含整个表格的上级元素

    # ---------------- 日期 ----------------
    dates = [text_clean(x.get_text()) for x in table_parent.find_all(string=re.compile(r"\d+月\d+日"))]

    # ---------------- 天气文字（img 的 alt 属性） ----------------
    weathers = []
    for imgcap in table_parent.find_all("img", alt=True):
        alt = imgcap.get("alt")
        if alt and re.search(r"(晴|曇|雨|雪)", alt):
            weathers.append(alt)

    # ---------------- 温度（高低交替出现） ----------------
    temps = [int(x) for x in re.findall(r"\b-?\d+\b", " ".join([x.get_text() for x in table_parent.find_all(string=True)]))]

    # ---------------- 降水確率（百分比） ----------------
    pops = re.findall(r"\d+%", " ".join([x.get_text() for x in table_parent.find_all(string=True)]))

    # ---------------- 生成每天的记录 ----------------
    i_temp = 0
    i_pop = 0
    for i, d in enumerate(dates):
        tmax = temps[i_temp] if i_temp < len(temps) else None
        tmin = temps[i_temp+1] if i_temp+1 < len(temps) else None
        i_temp += 2
        weather = weathers[i] if i < len(weathers) else ""
        pop = pops[i] if i < len(pops) else ""
        out.append({
            "date": d, "weather_text": weather,
            "t_max": tmax, "t_min": tmin,
            "pop": pop
        })
    return out

# -------------------- 主函数：抓取并整合所有数据 --------------------
def scrape():
    html = requests.get(URL, headers=HEADERS, timeout=30).text   # 发送 HTTP 请求获取 HTML 文本
    soup = BeautifulSoup(html, "html.parser")                    # 用 BeautifulSoup 解析网页
    run_ts = dt.datetime.utcnow().isoformat()                    # 生成当前 UTC 时间（ISO 格式）
    city = "北九州市"                                             # 城市名称

    # 分别解析今日/明日、10日間天気
    today_tom = parse_today_tomorrow(soup)
    ten = parse_10day(soup)

    # ---------------- 整理成统一格式的行 ----------------
    rows = []
    # 今日・明日部分
    for idx, p in enumerate(today_tom):
        rows.append({
            "runDate": run_ts, "city": city,
            "section": "today" if idx == 0 else "tomorrow",
            "date": p["date"], "weather_text": p["weather_text"],
            "t_max": p["t_max"], "t_min": p["t_min"],
            "pop_00_06": p["pop_00_06"], "pop_06_12": p["pop_06_12"],
            "pop_12_18": p["pop_12_18"], "pop_18_24": p["pop_18_24"],
            "wind_max": p["wind_max"],
            "sunrise": p["sunrise"], "sunset": p["sunset"],
            "notes": ""
        })

    # 10日間天気部分
    for d in ten:
        rows.append({
            "runDate": run_ts, "city": city,
            "section": "10day",
            "date": d["date"], "weather_text": d["weather_text"],
            "t_max": d["t_max"], "t_min": d["t_min"],
            "pop_00_06": "", "pop_06_12": "", "pop_12_18": "", "pop_18_24": "",
            "wind_max": "", "sunrise": "", "sunset": "",
            "notes": f'pop={d.get("pop","")}'
        })
    return {"rows": rows}   # 返回包含所有天气记录的字典

# -------------------- 程序入口 --------------------
if __name__ == "__main__":
    import json                      # 导入 json 库，用于打印美化后的输出
    print(json.dumps(scrape(), ensure_ascii=False, indent=2))  # 打印 JSON 结果（带缩进，中文不转义）
