# -*- coding: utf-8 -*-   # 指定源码文件采用 UTF-8 编码（解释器/编辑器据此正确处理中文）。这是“编码声明注释”。

import requests, datetime as dt, re   # import 同时导入多个模块；把 datetime 模块以别名 dt 引入（as 起别名），re 是正则模块
from bs4 import BeautifulSoup         # from ... import ... 语法：只从 bs4 包中导入 BeautifulSoup 类

# 北九州市天气预报URL（变量赋值：把右侧字符串常量绑定到左侧变量名 URL）
URL = "https://tenki.jp/forecast/9/43/8220/40100/"

# 字典（dict）字面量；花括号 {} 创建字典，键值用 "key": value，逗号分隔
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"   # 字典中的一个键值对（字符串键 → 字符串值）
}

# ---------- 工具函数：清除字符串中的多余空白 ----------
def delet_unuse_text(s):                        # def 定义函数；形参 s 是传入的字符串
    """去掉字符串中的多余空格、换行"""            
    return re.sub(r"\s+", " ", s).strip()       # return 返回值；re.sub 用正则替换，把连续空白替成单空格；strip 去除首尾空白

# ---------- 主函数：只提取“今日”的天气信息 ----------
def today_temp():                                # 定义主函数，无参数
    # 获取网页HTML
    html = requests.get(URL, headers=HEADERS, timeout=30).text  # requests.get 发起 HTTP GET；关键字参数 headers/timeout
                                                               # .text 属性把响应体按推断编码解码成字符串，赋给 html

    # 用BeautifulSoup解析
    soup = BeautifulSoup(html, "html.parser")   # 调用类构造函数创建对象；第2个参数指定解析器类型为内置 html.parser

    # 遍历所有 h3/h4 标签，寻找包含“今日”文字的部分
    for h in soup.find_all(["h3", "h4"]):       # for 循环；soup.find_all 接受列表参数，查找所有 h3 或 h4 标签
        title = delet_unuse_text(h.get_text())  # 调用标签方法 .get_text() 提取纯文本；再用工具函数清洗空白
        if title.startswith("今日"):             # if 条件判断：字符串方法 .startswith 判断是否以“今日”开头
            box = h.find_parent()               # 从当前标题节点向上找父节点（包含整个“今日”天气区块）
            if not box:                         # not 逻辑否；若 box 为 None/空则条件成立
                continue                        # continue 跳过本次循环，继续下一个 h

            # 从标题中提取日期（例如 “10月22日”）
            date_m = re.search(r"(\d+月\d+日)", title)  # re.search 用正则在字符串中查找第一个匹配；\d+ 是 1+ 位数字
            date_jp = date_m.group(1) if date_m else title  # 条件表达式：有匹配则取第1个分组；否则回退用原标题

            # 初始化字段（一次性赋值多个变量：左=右链式形态）
            weather_text = ""                   # 空字符串作为默认
            tmax = tmin = None                  # 两个变量同时赋值为 None（Python 的“空值”）
            wind = ""                           

            # 天气文案（例：“晴のち曇”）
            wx = box.find(string=re.compile("晴|曇|雨|雪"))  # 在 box 内查找**文本节点**匹配任一关键字的第一个位置
            if wx:                                          # 若找到（非 None 非空）
                weather_text = delet_unuse_text(wx)         # 清洗空白后保存

            # 最高/最低气温
            tx = box.find(string=re.compile("最高"))         # 找包含“最高”的文本节点
            if tx:
                m = re.search(r"最高\s*([\d\-]+)\s*℃", delet_unuse_text(tx.parent.get_text()))
                # 正则：\s* 可有空白；([\d\-]+) 捕获若干数字或负号（温度可能为负）；℃ 字符匹配
                if m: tmax = m.group(1)                    # 若匹配成功，取第1个捕获分组（具体温度数字）

            tn = box.find(string=re.compile("最低"))         # 找包含“最低”的文本节点
            if tn:
                m = re.search(r"最低\s*([\d\-]+)\s*℃", delet_unuse_text(tn.parent.get_text()))
                if m: tmin = m.group(1)

            # 最大风速
            wind_row = box.find(string=re.compile("最大風速"))     # 找“最大風速”
            if wind_row:
                wind = delet_unuse_text(wind_row.parent.get_text())  # 提取整行并清洗

            # 返回今日天气的完整信息（字典：键值对集合）
            return {
                "weather_text": weather_text,
                "t_max": tmax,
                "t_min": tmin,
                "wind_max": wind,
            }

    # 如果找不到“今日”天气，返回空字典（语义为“无结果”）
    return {}

# ---------- 入口 ----------
if __name__ == "__main__":                        # 模块入口判断：仅当脚本被直接运行时为 True，被 import 时为 False
    import json                                   # 运行时局部导入 json 模块（也可以放顶部，这里演示就地导入）
    data = today_temp()                           # 调用主函数，得到今日数据（字典）
    print(json.dumps(data, ensure_ascii=False, indent=2))  # json.dumps 序列化为字符串；中文不转义；漂亮缩进
