# -*- coding: utf-8 -*-
import requests, datetime as dt, re
from bs4 import BeautifulSoup

URL = "https://tenki.jp/forecast/9/43/8220/40100/"  # 北九州市
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def text_clean(s):
    return re.sub(r"\s+", " ", s).strip()

def parse_today_tomorrow(soup):
    # 区块定位：页面中“今日・明日の天気”两个面板（顺序：今日、明日）
    panels = []
    # 用 h3/h4 标题附近的块 + 常见字段（最高/最低/降水確率/日の出/日の入）
    # 兼容：页面会把今天/明天的日期写成 “今日 10月21日(火)” 之类。
    for h in soup.find_all(["h3","h4"]):
        title = text_clean(h.get_text())
        if title.startswith("今日") or title.startswith("明日"):
            box = h.find_parent()
            if not box: 
                continue
            date_m = re.search(r"(\d+月\d+日)", title)
            date_jp = date_m.group(1) if date_m else title

            weather_text = ""
            tmax = tmin = None
            sunrise = sunset = ""
            wind = ""
            pops = {"00-06":"","06-12":"","12-18":"","18-24":""}

            # 天気文言（例：晴のち曇）
            wx = box.find(string=re.compile("晴|曇|雨|雪"))
            if wx:
                weather_text = text_clean(wx)

            # 最高/最低
            tx = box.find(string=re.compile("最高"))
            if tx:
                m = re.search(r"最高\s*([\d\-]+)\s*℃", text_clean(tx.parent.get_text()))
                if m: tmax = m.group(1)
            tn = box.find(string=re.compile("最低"))
            if tn:
                m = re.search(r"最低\s*([\d\-]+)\s*℃", text_clean(tn.parent.get_text()))
                if m: tmin = m.group(1)

            # 日の出/日の入
            sr = box.find(string=re.compile("日の出"))
            if sr:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(sr.parent.get_text()))
                if m: sunrise = m.group(1)
            ss = box.find(string=re.compile("日の入"))
            if ss:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(ss.parent.get_text()))
                if m: sunset = m.group(1)

            # 降水確率行
            precip_row = box.find(string=re.compile("降水確率"))
            if precip_row:
                row = precip_row.parent.get_text(" ")
                # 可能是 “降水確率 20% 20% 20% 0%”，按顺序映射
                nums = re.findall(r"\d+%", row)
                if len(nums) == 4:
                    pops["00-06"], pops["06-12"], pops["12-18"], pops["18-24"] = nums

            # 最大風速
            wind_row = box.find(string=re.compile("最大風速"))
            if wind_row:
                wind = text_clean(wind_row.parent.get_text())

            panels.append({
                "date": date_jp,
                "weather_text": weather_text,
                "t_max": tmax, "t_min": tmin,
                "pop_00_06": pops["00-06"], "pop_06_12": pops["06-12"],
                "pop_12_18": pops["12-18"], "pop_18_24": pops["18-24"],
                "wind_max": wind,
                "sunrise": sunrise, "sunset": sunset
            })
    return panels[:2]  # 取前两个：今日、明日

def parse_10day(soup):
    # “10日間天気”表格：抓日期/天気/最高/最低/降水確率
    out = []
    ten_header = soup.find(string=re.compile("10日間天気"))
    if not ten_header:
        return out
    table_parent = ten_header.find_parent()
    # 日期列表（例如 10月23日 等）
    dates = [text_clean(x.get_text()) for x in table_parent.find_all(string=re.compile(r"\d+月\d+日"))]
    # 天気文字
    weathers = []
    for imgcap in table_parent.find_all("img", alt=True):
        alt = imgcap.get("alt")
        if alt and re.search(r"(晴|曇|雨|雪)", alt):
            weathers.append(alt)
    # 気温(℃)一串数字，按最高/最低交替出现
    temps = [int(x) for x in re.findall(r"\b-?\d+\b", " ".join([x.get_text() for x in table_parent.find_all(string=True)]) )]
    # 这串包含很多数字，简单做法：在“気温(℃)”之后会按 高低高低……出现；为稳妥可二次校验长度
    # 降水確率：抓 % 号
    pops = re.findall(r"\d+%", " ".join([x.get_text() for x in table_parent.find_all(string=True)]))

    # 生成记录（尽量防御）
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

def scrape():
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    run_ts = dt.datetime.utcnow().isoformat()
    city = "北九州市"

    today_tom = parse_today_tomorrow(soup)
    ten = parse_10day(soup)

    # 统一输出为扁平 JSON（便于 Power Automate 写入 Excel 表）
    rows = []
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
    return {"rows": rows}

if __name__ == "__main__":
    import json
    print(json.dumps(scrape(), ensure_ascii=False, indent=2))
