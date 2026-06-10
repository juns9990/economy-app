#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vela-flow-daily.py v3 — 시총 상위 N종목 수급 누적 + GitHub 자동 업로드
====================================================================
Z Fold3 Termux 매일 자동 실행 (cron).
네이버 시총상위 자동 수집 -> 종목별 수급 파싱 -> 누적 -> GitHub 업로드.
pandas 불필요 (requests + 정규식).

환경변수: GH_TOKEN
사용:  export GH_TOKEN=ghp_xxx ; python vela-flow-daily.py
"""

import json, os, sys, time, re, base64
from datetime import datetime
import requests

GH_OWNER = "juns9990"
GH_REPO  = "economy-app"
GH_PATH  = "data/signal-flow-db.json"
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_API   = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{GH_PATH}"

TOP_N     = 500     # 수집할 시총 상위 종목 수
KEEP_DAYS = 60      # 종목당 유지 거래일
REQ_DELAY = 0.35    # 종목 간 딜레이(초) — 네이버 차단 방지
UA = {"User-Agent": "Mozilla/5.0"}


def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}


def get_top_codes(n=TOP_N):
    """네이버 시총상위에서 코스피+코스닥 상위 n종목 코드 수집."""
    codes, names = [], {}
    # sosok=0 코스피, sosok=1 코스닥. 페이지당 50개.
    for sosok in (0, 1):
        pages = (n // 50) + 1
        for page in range(1, pages + 1):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            try:
                r = requests.get(url, headers=UA, timeout=10)
                r.encoding = "euc-kr"
                # 코드 + 종목명 같이 추출
                found = re.findall(
                    r'/item/main\.naver\?code=(\d{6})">([^<]+)</a>', r.text)
                if not found:
                    break
                for code, name in found:
                    if code not in names:
                        codes.append(code)
                        names[code] = name.strip()
            except Exception:
                break
            time.sleep(0.2)
        if len(codes) >= n:
            pass  # 코스피 다 받고 코스닥도 추가
    # 시총 큰 순으로 이미 정렬돼 있음. 상위 n개.
    top = codes[:n]
    return top, names


def gh_load():
    try:
        r = requests.get(GH_API, headers=gh_headers(), timeout=15)
        if r.status_code == 200:
            j = r.json()
            content = base64.b64decode(j["content"]).decode("utf-8")
            return json.loads(content), j["sha"]
        if r.status_code == 404:
            return {}, None
        print(f"  기존 읽기 실패 {r.status_code}")
        return {}, None
    except Exception as ex:
        print(f"  기존 읽기 예외: {ex}")
        return {}, None


def num(s):
    s = re.sub(r"[^\d\-]", "", s)
    return float(s) if s and s not in ("-", "") else 0.0


def fetch_today(code):
    """네이버 -> 최신 1거래일 (date, frgn억, inst억). 데이터 없으면 None."""
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.DOTALL)
    for tr in trs:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.DOTALL)
        clean = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", "")
                 .replace("\n", "").replace("\t", "").strip() for c in cells]
        clean = [c for c in clean if c]
        if len(clean) >= 7 and re.match(r"\d{4}\.\d{2}\.\d{2}", clean[0]):
            date  = clean[0].replace(".", "")
            close = num(clean[1])
            inst  = num(clean[5])
            frgn  = num(clean[6])
            return (date, round(frgn * close / 1e8, 1), round(inst * close / 1e8, 1))
    return None


def main():
    if not GH_TOKEN:
        print("[오류] GH_TOKEN 환경변수 없음.  export GH_TOKEN=ghp_xxx")
        sys.exit(1)

    print(f"시총 상위 {TOP_N}종목 목록 수집...")
    codes, names = get_top_codes(TOP_N)
    print(f"  대상 종목: {len(codes)}개")

    existing, sha = gh_load()
    raw = existing.get("_raw", {})

    print("수급 수집 시작...")
    ok = had = 0; today = None; t0 = time.time()
    for i, code in enumerate(codes, 1):
        try:
            res = fetch_today(code)
            if res:
                date, f_amt, i_amt = res
                today = date
                rec = raw.setdefault(code, {})
                rec[date] = {"f": f_amt, "i": i_amt}
                for k in sorted(rec.keys())[:-KEEP_DAYS]:
                    del rec[k]
                ok += 1
                if f_amt != 0 or i_amt != 0:
                    had += 1
            # 진행 표시 (50개마다)
            if i % 50 == 0:
                el = int(time.time() - t0)
                print(f"  [{i}/{len(codes)}] 수집 {ok} · 유효 {had} · {el}s")
        except Exception:
            pass
        time.sleep(REQ_DELAY)

    print(f"\n수집 완료: {ok}/{len(codes)} (수급있음 {had}) ({today})")

    # 앱용 형식 (최근 5일)
    out = {"updated": datetime.now().strftime("%Y-%m-%d"),
           "unit": "억원(순매수,종가환산)", "source": "naver-daily",
           "count": ok, "data": {}, "_raw": raw, "_names": names}
    for code, rec in raw.items():
        keys = sorted(rec.keys())[-5:]
        out["data"][code] = {"frgn": [rec[k]["f"] for k in keys],
                             "inst": [rec[k]["i"] for k in keys]}

    print("GitHub 업로드 중...")
    content = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    body = {"message": f"수급 자동 갱신 {datetime.now().strftime('%Y-%m-%d %H:%M')} ({ok}종목)",
            "content": base64.b64encode(content.encode()).decode()}
    if sha: body["sha"] = sha
    rr = requests.put(GH_API, headers=gh_headers(), json=body, timeout=30)
    if rr.status_code in (200, 201):
        print(f"✅ 업로드 성공 ({rr.status_code}) · {ok}종목")
    else:
        print(f"❌ 업로드 실패 ({rr.status_code}): {rr.text[:150]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
