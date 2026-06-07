#!/usr/bin/env python3
"""
SIGNAL PRO v3.9.0 — 종목 DB 자동 생성 스크립트 (v2)
================================================
KRX 전체 종목(KOSPI + KOSDAQ + KONEX)을 pykrx로 수집하여
signal-stocks-db.json 파일을 생성합니다.

v2 변경사항:
- 최근 영업일을 자동 탐색 (최대 7일 거슬러 올라가며 재시도)
- 데이터 빈 응답시 다음 날짜로 폴백
- 디버깅 로그 강화
- 종목 0개면 빌드 실패 처리 (Actions 알림)

MADE BY JUNS
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pykrx import stock
except ImportError:
    print("❌ pykrx가 설치되지 않았습니다.")
    sys.exit(1)


# ===================== CONFIG =====================
OUTPUT_PATH = Path("data/signal-stocks-db.json")
MAX_RETRY_DAYS = 7

SECTOR_SIMPLIFY = {
    "전기,전자": "전기전자",
    "운수장비": "운송장비",
    "철강금속": "철강금속",
    "화학": "화학",
    "기계": "기계",
    "음식료품": "음식료",
    "섬유,의복": "섬유의류",
    "비금속광물": "비금속",
    "의약품": "제약바이오",
    "건설업": "건설",
    "유통업": "유통",
    "금융업": "금융",
    "보험": "보험",
    "증권": "증권",
    "운수창고업": "물류",
    "전기가스업": "전기가스",
    "통신업": "통신",
    "서비스업": "서비스",
    "오락,문화": "엔터테인먼트",
    "종이,목재": "제지목재",
}

WEEKDAY_KR = ['월','화','수','목','금','토','일']


def find_valid_business_day():
    """KRX 데이터가 존재하는 가장 최근 영업일 자동 탐색"""
    d = datetime.now()
    for offset in range(MAX_RETRY_DAYS):
        candidate = d - timedelta(days=offset)
        date_str = candidate.strftime("%Y%m%d")
        if candidate.weekday() >= 5:
            print(f"   ⏭️  {date_str}: 주말 ({WEEKDAY_KR[candidate.weekday()]})")
            continue
        try:
            print(f"   🔍 {date_str} ({WEEKDAY_KR[candidate.weekday()]}) 데이터 확인 중...")
            tickers = stock.get_market_ticker_list(date_str, market="KOSPI")
            if tickers and len(tickers) > 100:
                print(f"   ✅ {date_str}: 유효 ({len(tickers)}개 KOSPI 확인)")
                return date_str
            else:
                print(f"   ⚠️  {date_str}: 데이터 빈약")
        except Exception as e:
            print(f"   ❌ {date_str}: {str(e)[:80]}")
            time.sleep(0.5)
    print(f"\n❌ 최근 {MAX_RETRY_DAYS}일 내 유효 영업일 없음.")
    sys.exit(1)


def make_aliases(name):
    common = {
        "삼성전자": ["삼전"],
        "SK하이닉스": ["하이닉스"],
        "삼성바이오로직스": ["삼성바이오"],
        "LG에너지솔루션": ["엘지엔솔", "LG엔솔"],
        "POSCO홀딩스": ["포스코", "포스코홀딩스"],
        "현대차": ["현대자동차"],
        "NAVER": ["네이버"],
        "한화에어로스페이스": ["한화에어로"],
        "한국항공우주": ["KAI"],
        "SK텔레콤": ["SKT"],
    }
    return common.get(name, [])


def normalize_market_code(ticker, market):
    return f"{ticker}.KQ" if market == "KOSDAQ" else f"{ticker}.KS"


def build_stocks_db():
    print(f"🚀 SIGNAL PRO 종목 DB 생성 시작")
    print(f"📅 현재 시각: {datetime.now().isoformat()}\n")
    print(f"🔎 KRX 데이터 있는 가장 최근 영업일 탐색...")
    target_date = find_valid_business_day()
    print(f"\n✅ 기준 영업일: {target_date}\n")

    all_stocks = []
    markets = {"KOSPI": "KOSPI", "KOSDAQ": "KOSDAQ", "KONEX": "KONEX"}

    for market_name, market_code in markets.items():
        print(f"\n📊 {market_name} 종목 수집 중...")
        try:
            tickers = stock.get_market_ticker_list(target_date, market=market_code)
            print(f"   ✓ {len(tickers)}개 종목 코드 확보")
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            continue

        if not tickers:
            print(f"   ⚠️  데이터 없음, 건너뜀")
            continue

        cap_df = None
        try:
            cap_df = stock.get_market_cap(target_date, market=market_code)
            print(f"   ✓ 시가총액 {len(cap_df)}건")
        except Exception as e:
            print(f"   ⚠️  시가총액 실패: {str(e)[:80]}")

        sector_map = {}
        if market_code in ("KOSPI", "KOSDAQ"):
            try:
                sector_df = stock.get_market_sector_classifications(target_date, market=market_code)
                if sector_df is not None and not sector_df.empty:
                    sector_map = dict(zip(sector_df.index, sector_df["업종명"]))
                    print(f"   ✓ 섹터 {len(sector_map)}건")
            except Exception as e:
                print(f"   ⚠️  섹터 실패: {str(e)[:80]}")

        success_count = 0
        fail_count = 0
        for ticker in tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                if not name:
                    fail_count += 1
                    continue
                market_cap = 0
                if cap_df is not None and ticker in cap_df.index:
                    try:
                        market_cap = int(cap_df.loc[ticker, "시가총액"])
                    except (KeyError, ValueError):
                        pass
                sector = sector_map.get(ticker, "기타")
                sector = SECTOR_SIMPLIFY.get(sector, sector)
                if any(kw in name for kw in ["KODEX","TIGER","ACE","KBSTAR","HANARO","ARIRANG","SMART","KOSEF"]):
                    sector = "ETF"
                elif any(kw in name for kw in ["리츠","REIT"]):
                    sector = "리츠"
                all_stocks.append({
                    "code": normalize_market_code(ticker, market_name),
                    "name": name,
                    "market": market_name,
                    "sector": sector,
                    "marketCap": market_cap,
                    "aliases": make_aliases(name),
                })
                success_count += 1
            except Exception as e:
                fail_count += 1
                if fail_count <= 3:
                    print(f"   ⚠️  {ticker}: {str(e)[:60]}")

        print(f"   ✅ {market_name}: 성공 {success_count} / 실패 {fail_count}")

    all_stocks.sort(key=lambda x: x.get("marketCap", 0), reverse=True)

    now = datetime.now()
    result = {
        "version": now.strftime("%Y.%m.%d"),
        "updated_at": now.isoformat() + "+09:00",
        "source": "KRX (pykrx)",
        "data_date": target_date,
        "count": len(all_stocks),
        "markets": {
            "KOSPI": sum(1 for s in all_stocks if s["market"] == "KOSPI"),
            "KOSDAQ": sum(1 for s in all_stocks if s["market"] == "KOSDAQ"),
            "KONEX": sum(1 for s in all_stocks if s["market"] == "KONEX"),
        },
        "stocks": all_stocks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n{'='*50}")
    print(f"✅ 빌드 완료!")
    print(f"{'='*50}")
    print(f"   📁 파일: {OUTPUT_PATH}")
    print(f"   📊 총 종목 수: {result['count']}")
    print(f"      - KOSPI: {result['markets']['KOSPI']}")
    print(f"      - KOSDAQ: {result['markets']['KOSDAQ']}")
    print(f"      - KONEX: {result['markets']['KONEX']}")
    print(f"   💾 파일 크기: {file_size_kb:.1f} KB")
    print(f"   📅 데이터 기준일: {target_date}")

    if result["count"] == 0:
        print(f"\n❌ 종목이 0개입니다. KRX 데이터 수집 실패!")
        sys.exit(1)

    return result


if __name__ == "__main__":
    try:
        build_stocks_db()
    except Exception as e:
        print(f"❌ 빌드 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
