# -------------------------------
# send_json_mail.py  （精简三项版）
# -------------------------------
# 功能：获取“今日天气”数据并以 JSON 附件形式发邮件
# 优先：请求 Render API (/today)
# 兜底：脚本内直接爬 tenki.jp（不依赖 Flask）
# 输出字段：t_max, t_min, wind_max
# -------------------------------

import os, ssl, json, smtplib, time, sys, requests, re, datetime as dt
from email.message import EmailMessage
from bs4 import BeautifulSoup

# ====== 1) 配置区 ======
API_URL = os.getenv("TEMP_API_URL", "https://get-temperature.onrender.com/today")
TENKI_URL = os.getenv("TENKI_URL", "https://tenki.jp/forecast/9/43/8220/40100/")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "ja,en;q=0.8",
}

# SMTP（与 WBGT 保持一致）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_ADDR   = os.getenv("TO_ADDR")

SUBJECT_PREFIX = os.getenv("MAIL_SUBJECT_PREFIX", "[GET_TEMP]")
FROM_ADDR = os.getenv("MAIL_FROM", SMTP_USER)

REQ_KEYS = ["t_max", "t_min", "wind_max"]  # 只需要这三项

# ====== 2) 工具：日志 ======
def log(s): print(s, flush=True)

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

# ====== 3) 获取“今日天气” ======
def fetch_today_from_api(timeout=30) -> dict:
    """从 Render API 获取今日天气 JSON（只验三项）"""
    log(f"[fetch] GET {API_URL}")
    r = requests.get(API_URL, timeout=timeout, headers={"User-Agent": HEADERS["User-Agent"]})
    log(f"[fetch] status={r.status_code}")
    r.raise_for_status()
    data = r.json()
    for k in REQ_KEYS:
        if k not in data:
            raise RuntimeError(f"JSON missing key: {k}")
    return data

def fetch_today_from_local(timeout=30) -> dict:
    """直接爬 tenki.jp（不 import get_temperature，不依赖 Flask）"""
    log(f"[fallback] scrape {TENKI_URL}")
    r = requests.get(TENKI_URL, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # 找“今日”标题块
    for h in soup.find_all(["h3", "h4"]):
        title = _clean(h.get_text())
        if not title.startswith("今日"):
            continue
        box = h.find_parent() or h
        block_text = " ".join(box.stripped_strings)

        m1 = re.search(r"最高\s*([\-]?\d+)\s*℃", block_text)
        m2 = re.search(r"最低\s*([\-]?\d+)\s*℃", block_text)
        m3 = re.search(r"最大風速\s*([^\s]+.*?m/s)", block_text)

        tmax = m1.group(1) if m1 else None
        tmin = m2.group(1) if m2 else None
        wind = m3.group(1) if m3 else None

        return {"t_max": tmax, "t_min": tmin, "wind_max": wind}

    # 未匹配到“今日”块
    raise RuntimeError("parse_failed_or_structure_changed")

def fetch_today() -> dict:
    """先 API，失败则本地爬虫兜底"""
    try:
        return fetch_today_from_api()
    except Exception as e:
        log(f"[fetch] API failed -> fallback local: {e}")
        return fetch_today_from_local()

# ====== 4) 发送邮件 ======
def send_json(data: dict):
    """把 JSON 数据作为附件发送"""
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, TO_ADDR]):
        raise RuntimeError("Missing SMTP env (SMTP_HOST/PORT/USER/PASS or TO_ADDR).")

    # 附件文件名（JST 日期）
    jst = dt.timezone(dt.timedelta(hours=9))
    stamp = dt.datetime.now(jst).strftime("%Y%m%d")
    filename = f"{stamp}_today.json"

    subject = f"{SUBJECT_PREFIX} {stamp} 今日天气 JSON"
    body = f"自动发送：{stamp} Kitakyushu 今日天气（仅三项）见附件 {filename}。"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg.set_content(body)

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), indent=None).encode("utf-8")
    msg.add_attachment(payload, maintype="application", subtype="json", filename=filename)

    log(f"[smtp] connecting {SMTP_HOST}:{SMTP_PORT} as {SMTP_USER}")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    log("[smtp] sent ok")

# ====== 5) 主过程（带重试） ======
def main():
    max_attempts = 3
    delay = 20
    for i in range(1, max_attempts + 1):
        try:
            log(f"=== Attempt {i}/{max_attempts} ===")
            data = fetch_today()
            log(f"[data] t_max={data.get('t_max')} t_min={data.get('t_min')} wind={data.get('wind_max')}")
            send_json(data)
            log("=== Done ===")
            return 0
        except Exception as e:
            log(f"[error] {e}")
            if i < max_attempts:
                log(f"[retry] sleep {delay}s ...")
                time.sleep(delay)
            else:
                log("[fail] all attempts failed")
                return 1

if __name__ == "__main__":
    sys.exit(main())
