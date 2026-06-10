#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vela-flow-daily.py v2 — 외국인/기관 수급 누적 + GitHub 자동 업로드
====================================================================
Z Fold3 Termux 매일 자동 실행 (cron).
네이버 금융 -> 정규식 파싱(pandas 불필요) -> 누적 -> GitHub API 업로드.

환경변수: GH_TOKEN (GitHub Personal Access Token)
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

KEEP_DAYS = 60
UA = {"User-Agent": "Mozilla/5.0"}

TARGETS = {
    "005930":"삼성전자","000660":"SK하이닉스","373220":"LG에너지솔루션",
    "005380":"현대차","035420":"NAVER","000270":"기아",
    "012450":"한화에어로스페이스","042700":"한미반도체","207940":"삼성바이오로직스",
    "068270":"셀트리온","005490":"POSCO홀딩스","035720":"카카오",
    "051910":"LG화학","006400":"삼성SDI","105560":"KB금융",
}


def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}


def load_existing():
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
    """'+1,767,022' -> 1767022.0"""
    s = re.sub(r"[^\d\-]", "", s)
    return float(s) if s and s not in ("-", "") else 0.0


def fetch_today(code):
    """네이버 -> 최신 1거래일 (date, frgn_amt억, inst_amt억)"""
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
            date  = clean[0].replace(".", "")        # 20260609
            close = num(clean[1])                    # 종가
            inst  = num(clean[5])                    # 기관 순매매(주)
            frgn  = num(clean[6])                    # 외국인 순매매(주)
            frgn_amt = round(frgn * close / 1e8, 1)  # 억 환산
            inst_amt = round(inst * close / 1e8, 1)
            return (date, frgn_amt, inst_amt)
    return None


def main():
    if not GH_TOKEN:
        print("[오류] GH_TOKEN 환경변수 없음.  export GH_TOKEN=ghp_xxx")
        sys.exit(1)

    print("수급 누적 수집 시작...")
    existing, sha = load_existing()
    raw = existing.get("_raw", {})  # 누적 원본 {code:{date:{f,i}}}

    ok = 0; today = None
    for i, (code, name) in enumerate(TARGETS.items(), 1):
        print(f"[{i}/{len(TARGETS)}] {code} {name} ...", end=" ")
        try:
            res = fetch_today(code)
            if res:
                date, f_amt, i_amt = res
                today = date
                rec = raw.setdefault(code, {})
                rec[date] = {"f": f_amt, "i": i_amt}
                # 60일 유지
                for k in sorted(rec.keys())[:-KEEP_DAYS]:
                    del rec[k]
                ok += 1
                print(f"{date} 외 {f_amt:+.0f} / 기 {i_amt:+.0f}억")
            else:
                print("데이터 없음")
        except Exception as ex:
            print(f"실패: {str(ex)[:40]}")
        time.sleep(0.5)

    print(f"\n수집 완료: {ok}/{len(TARGETS)} ({today})")

    # 앱용 형식: data[code] = {frgn:[최근5일], inst:[최근5일]}
    out = {"updated": datetime.now().strftime("%Y-%m-%d"),
           "unit": "억원(순매수,종가환산)", "source": "naver-daily",
           "data": {}, "_raw": raw}
    for code, rec in raw.items():
        keys = sorted(rec.keys())[-5:]
        out["data"][code] = {"frgn": [rec[k]["f"] for k in keys],
                             "inst": [rec[k]["i"] for k in keys]}

    print("GitHub 업로드 중...")
    content = json.dumps(out, ensure_ascii=False, indent=1)
    body = {"message": f"수급 자동 갱신 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": base64.b64encode(content.encode()).decode()}
    if sha: body["sha"] = sha
    rr = requests.put(GH_API, headers=gh_headers(), json=body, timeout=20)
    if rr.status_code in (200, 201):
        print(f"✅ 업로드 성공 ({rr.status_code})")
    else:
        print(f"❌ 업로드 실패 ({rr.status_code}): {rr.text[:150]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
