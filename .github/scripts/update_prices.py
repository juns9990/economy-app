#!/usr/bin/env python3
"""
INVESTMENT SIGNAL - 전일 장마감 종가 자동 업데이트 스크립트
매일 오전 8시 KST 실행 → 전 거래일 종가를 HTML DB에 반영
"""
import re, json, time, urllib.request, urllib.error
from datetime import datetime

HTML_FILE = "signal-1.html"
HEADERS   = {"User-Agent": "Mozilla/5.0 (compatible; signal-bot/1.0)"}

# ── HTML 읽기 ─────────────────────────────────────────────────
with open(HTML_FILE, encoding="utf-8") as f:
    html = f.read()

# ── 종목 코드 추출 ────────────────────────────────────────────
stocks = re.findall(r'id:"(\d+)",n:"[^"]+",s:"[^"]+",m:"([KQ])"', html)
print(f"총 {len(stocks)}개 종목 처리 시작")

# ── Yahoo Finance에서 전일 종가 2일치 조회 ───────────────────
def fetch_batch(batch):
    """batch = [(code, market), ...] → {code: {p, prev, c, w52h, w52l}}"""
    results = {}
    symbols = ",".join(
        f"{code}.{'KS' if m == 'K' else 'KQ'}" for code, m in batch
    )
    url = (
        "https://query2.finance.yahoo.com/v7/finance/quote"
        f"?symbols={symbols}"
        "&fields=regularMarketPreviousClose,regularMarketPrice,"
        "fiftyTwoWeekHigh,fiftyTwoWeekLow,regularMarketChangePercent"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        for item in data.get("quoteResponse", {}).get("result", []):
            sym   = item.get("symbol", "").replace(".KS", "").replace(".KQ", "")
            prev  = item.get("regularMarketPreviousClose", 0)
            curr  = item.get("regularMarketPrice", prev)
            w52h  = item.get("fiftyTwoWeekHigh", 0)
            w52l  = item.get("fiftyTwoWeekLow", 0)
            chg   = round(item.get("regularMarketChangePercent", 0), 2)
            if prev and prev > 100:
                results[sym] = {
                    "p":    round(prev),          # 전일 종가
                    "prev": round(prev),           # prev도 동일 (정적 기준)
                    "c":    chg,                   # 당일 등락률 (참고용)
                    "w52h": round(w52h) if w52h else 0,
                    "w52l": round(w52l) if w52l else 0,
                }
    except Exception as e:
        print(f"  ⚠ 배치 오류: {e}")
    return results

# ── 배치 처리 ─────────────────────────────────────────────────
BATCH_SIZE = 8
all_prices = {}
for i in range(0, len(stocks), BATCH_SIZE):
    batch = stocks[i : i + BATCH_SIZE]
    result = fetch_batch(batch)
    all_prices.update(result)
    print(f"  [{i+len(batch)}/{len(stocks)}] {len(result)}개 수신")
    time.sleep(0.4)

print(f"\n총 {len(all_prices)}개 가격 수신 완료")

# ── HTML DB 업데이트 ─────────────────────────────────────────
updated = 0
for code, d in all_prices.items():
    if d["p"] <= 0:
        continue

    # p, c, prev, w52h, w52l 교체 패턴
    pat = (
        rf'(id:"{code}",n:"[^"]+",s:"[^"]+",m:"[KQ]",\s*p:)'
        r'(\d+)(,c:)([\d.\-]+)(,prev:)(\d+)(,w52h:)(\d+)(,w52l:)(\d+)'
    )
    m = re.search(pat, html)
    if not m:
        continue

    new_w52h = max(d["w52h"], d["p"]) if d["w52h"] else int(m.group(8))
    new_w52l = min(d["w52l"], d["p"]) if d["w52l"] else int(m.group(10))

    replacement = (
        m.group(1) + str(d["p"])   +
        m.group(3) + str(d["c"])   +
        m.group(5) + str(d["prev"])+
        m.group(7) + str(new_w52h) +
        m.group(9) + str(new_w52l)
    )
    html = html[:m.start()] + replacement + html[m.end():]
    updated += 1

# ── 업데이트 타임스탬프 기록 ──────────────────────────────────
ts = datetime.now().strftime("%Y-%m-%d %H:%M KST")
html = re.sub(
    r'(<!-- PRICE_UPDATE_TS -->)[^<]*(<!-- /PRICE_UPDATE_TS -->)',
    rf'\g<1>{ts}\g<2>',
    html,
)

# ── 저장 ─────────────────────────────────────────────────────
with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ {updated}개 종목 업데이트 완료 ({ts})")
