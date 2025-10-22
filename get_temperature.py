# -*- coding: utf-8 -*-   # 指定文件编码（保证中文正常显示）
import requests, datetime as dt, re   # 导入必需库
from bs4 import BeautifulSoup         # 用于解析HTML

# 北九州市天气预报URL
URL = "https://tenki.jp/forecast/9/43/8220/40100/"
# 模拟浏览器访问的请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------- 工具函数：清除字符串中的多余空白 ----------
def text_clean(s):
    """去掉字符串中的多余空格、换行"""
    return re.sub(r"\s+", " ", s).strip()

# ---------- 主函数：只提取“今日”的天气信息 ----------
def scrape_today():
    # 获取网页HTML
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    # 用BeautifulSoup解析
    soup = BeautifulSoup(html, "html.parser")

    # 遍历所有 h3/h4 标签，寻找包含“今日”文字的部分
    for h in soup.find_all(["h3", "h4"]):
        title = text_clean(h.get_text())
        if title.startswith("今日"):  # 找到“今日”的天气块
            box = h.find_parent()  # 取得整个天气信息块
            if not box:
                continue

            # 从标题中提取日期（例如 “10月22日”）
            date_m = re.search(r"(\d+月\d+日)", title)
            date_jp = date_m.group(1) if date_m else title

            # 初始化字段
            weather_text = ""
            tmax = tmin = None
            sunrise = sunset = ""
            wind = ""
            pops = {"00-06": "", "06-12": "", "12-18": "", "18-24": ""}

            # 天气文案（例：“晴のち曇”）
            wx = box.find(string=re.compile("晴|曇|雨|雪"))
            if wx:
                weather_text = text_clean(wx)

            # 最高/最低气温
            tx = box.find(string=re.compile("最高"))
            if tx:
                m = re.search(r"最高\s*([\d\-]+)\s*℃", text_clean(tx.parent.get_text()))
                if m: tmax = m.group(1)
            tn = box.find(string=re.compile("最低"))
            if tn:
                m = re.search(r"最低\s*([\d\-]+)\s*℃", text_clean(tn.parent.get_text()))
                if m: tmin = m.group(1)

            # 日出/日落
            sr = box.find(string=re.compile("日の出"))
            if sr:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(sr.parent.get_text()))
                if m: sunrise = m.group(1)
            ss = box.find(string=re.compile("日の入"))
            if ss:
                m = re.search(r"(\d{2}時\d{2}分)", text_clean(ss.parent.get_text()))
                if m: sunset = m.group(1)

            # 降水確率（四个时间段）
            precip_row = box.find(string=re.compile("降水確率"))
            if precip_row:
                row = precip_row.parent.get_text(" ")
                nums = re.findall(r"\d+%", row)
                if len(nums) == 4:
                    pops["00-06"], pops["06-12"], pops["12-18"], pops["18-24"] = nums

            # 最大风速
            wind_row = box.find(string=re.compile("最大風速"))
            if wind_row:
                wind = text_clean(wind_row.parent.get_text())

            # 返回今日天气的完整信息
            return {
                "runDate": dt.datetime.utcnow().isoformat(),  # 数据抓取时间
                "city": "北九州市",
                "date": date_jp,
                "weather_text": weather_text,
                "t_max": tmax,
                "t_min": tmin,
                "pop_00_06": pops["00-06"],
                "pop_06_12": pops["06-12"],
                "pop_12_18": pops["12-18"],
                "pop_18_24": pops["18-24"],
                "wind_max": wind,
                "sunrise": sunrise,
                "sunset": sunset
            }

    # 如果找不到“今日”天气，返回空
    return {}

# ---------- 入口 ----------
if __name__ == "__main__":
    import json
    data = scrape_today()                     # 执行抓取
    print(json.dumps(data, ensure_ascii=False, indent=2))  # 美化输出JSON
