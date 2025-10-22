# -------------------------------
# send_json_mail.py
# -------------------------------
# 功能：获取“今日天气”数据并以 JSON 附件形式发邮件
# 优先：请求 Render API (/today)
# 兜底：直接调用本地 today_temp()
# -------------------------------

import os, ssl, json, smtplib, time, sys, requests, datetime as dt
from email.message import EmailMessage

# ====== 1) 配置区 ======
API_URL = os.getenv("TEMP_API_URL", "https://get-temperature.onrender.com/today")

# 复用你 WBGT 的 SMTP Secrets 命名（GitHub Actions → Secrets）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_ADDR   = os.getenv("TO_ADDR")

SUBJECT_PREFIX = os.getenv("MAIL_SUBJECT_PREFIX", "[GET_TEMP]")
FROM_ADDR = os.getenv("MAIL_FROM", SMTP_USER)

# ====== 2) 工具：日志 ======
def log(s):
    print(s, flush=True)

# ====== 3) 获取“今日天气” ======
def fetch_today_from_api(timeout=30) -> dict:
    """从 Render API 获取今日天气 JSON"""
    log(f"[fetch] GET {API_URL}")
    r = requests.get(API_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    log(f"[fetch] status={r.status_code}")
    r.raise_for_status()
    data = r.json()
    # 简单校验几个关键字段
    for k in ["runDate", "city", "date", "weather_text"]:
        if k not in data:
            raise RuntimeError(f"JSON missing key: {k}")
    return data

def fetch_today_from_local() -> dict:
    """直接调用仓库里的 today_temp() 做兜底"""
    from get_temperature import today_temp  # 延迟导入，防止环境无此文件时报错
    data = today_temp()
    if not data:
        raise RuntimeError("today_temp() returned empty dict")
    return data

def fetch_today() -> dict:
    """先 API，失败则本地函数兜底"""
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

    # 生成当天（JST）文件名：YYYYMMDD_today.json
    jst = dt.timezone(dt.timedelta(hours=9))
    stamp = dt.datetime.now(jst).strftime("%Y%m%d")
    filename = f"{stamp}_today.json"

    # 主题 & 正文
    subject = f"{SUBJECT_PREFIX} {stamp} 今日天气 JSON"
    body = f"自动发送：{stamp} Kitakyushu 今日天气数据，见附件 {filename}。"

    # 构造邮件
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
            # 打点信息，便于在 Actions 日志里快速确认
            log(f"[data] city={data.get('city')} date={data.get('date')} t_max={data.get('t_max')} t_min={data.get('t_min')}")
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
