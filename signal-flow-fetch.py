#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal-flow-fetch.py — 외국인/기관 수급 데이터 수집 (PC 실행용)
================================================================
KRX가 클라우드 IP를 차단하므로 PC(또는 Z Fold3 Termux)에서 실행.
결과 JSON을 GitHub Pages(economy-app/data/)에 올리면 앱이 읽음.

사용법:
    pip install pykrx
    python signal-flow-fetch.py

출력: signal-flow-db.json
    → economy-app/data/signal-flow-db.json 위치에 업로드

주기: 장 마감 후 하루 1회 권장 (수급은 일 단위 확정)
"""

import json
import sys
from datetime import datetime, timedelta

try:
    from pykrx import stock
except ImportError:
    print("pykrx가 필요합니다:  pip install pykrx")
    sys.exit(1)

# ── 수집 대상 종목 (관심종목 + 핵심 대형주) ──────────────
# 필요하면 여기에 코드(6자리)를 추가하세요.
TARGET_CODES = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "373220",  # LG에너지솔루션
    "005380",  # 현대차
    "035420",  # NAVER
    "000270",  # 기아
    "012450",  # 한화에어로스페이스
    "042700",  # 한미반도체
    "207940",  # 삼성바이오로직스
    "068270",  # 셀트리온
    "005490",  # POSCO홀딩스
    "035720",  # 카카오
    "051910",  # LG화학
    "006400",  # 삼성SDI
    "105560",  # KB금융
]

DAYS = 5          # 최근 N거래일
LOOKBACK = 12     # 달력일 여유 (주말/공휴일 고려)


def recent_trading_dates(n=DAYS):
    """최근 n 거래일 (YYYYMMDD 문자열, 오래된→최신)"""
    end = datetime.now()
    start = end - timedelta(days=LOOKBACK)
    s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    # 삼성전자 기준 영업일 추출
    df = stock.get_market_ohlcv(s, e, "005930")
    dates = [d.strftime("%Y%m%d") for d in df.index][-n:]
    return dates


def fetch_flow(code, dates):
    """종목별 외국인/기관 순매수액(억원) — 최근 거래일들"""
    frgn, inst = [], []
    s, e = dates[0], dates[-1]
    try:
        # 거래대금 기준 순매수 (단위: 원) → 억으로 환산
        df = stock.get_market_trading_value_by_date(s, e, code)
        # 컬럼명은 버전에 따라 '외국인','기관합계' 등
        col_frgn = next((c for c in df.columns if "외국" in c), None)
        col_inst = next((c for c in df.columns if "기관" in c), None)
        for d in dates:
            try:
                row = df.loc[df.index.strftime("%Y%m%d") == d]
                if len(row):
                    f = float(row[col_frgn].iloc[0]) / 1e8 if col_frgn else 0
                    i = float(row[col_inst].iloc[0]) / 1e8 if col_inst else 0
                    frgn.append(round(f, 1))
                    inst.append(round(i, 1))
                else:
                    frgn.append(0); inst.append(0)
            except Exception:
                frgn.append(0); inst.append(0)
    except Exception as ex:
        print(f"  ! {code} 수집 실패: {ex}")
        return None
    return {"frgn": frgn, "inst": inst}


def main():
    print("수급 데이터 수집 시작...")
    dates = recent_trading_dates()
    print(f"대상 거래일: {dates}")

    data = {}
    for i, code in enumerate(TARGET_CODES, 1):
        print(f"[{i}/{len(TARGET_CODES)}] {code} ...", end=" ")
        flow = fetch_flow(code, dates)
        if flow:
            data[code] = flow
            print(f"외 {flow['frgn'][-1]:+.0f} / 기 {flow['inst'][-1]:+.0f}억")
        else:
            print("skip")

    out = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "dates": dates,
        "unit": "억원(순매수)",
        "data": data,
    }
    with open("signal-flow-db.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\n완료: signal-flow-db.json ({len(data)}개 종목)")
    print("→ economy-app/data/signal-flow-db.json 위치에 업로드하세요.")


if __name__ == "__main__":
    main()
