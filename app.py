from fastapi import FastAPI
from fastapi.responses import JSONResponse
from get_temperature import today_temp  # 直接复用你写好的函数

app = FastAPI(title="Kitakyushu Weather API", version="1.0.0")

@app.get("/today")
def get_today():
    try:
        data = today_temp()
        if not data:
            return JSONResponse({"error": "no_data_found"}, status_code=502)
        return JSONResponse(data, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/")
def root():
    return {"ok": True, "endpoints": ["/today"]}
