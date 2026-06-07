#!/usr/bin/env python3
"""
SIGNAL PRO v3.9.0 — 종목 DB 자동 생성 스크립트
================================================
KRX 전체 종목(KOSPI + KOSDAQ + KONEX)을 pykrx로 수집하여
signal-stocks-db.json 파일을 생성합니다.

실행 환경: GitHub Actions (Ubuntu, Python 3.11+)
주기: 매주 일요일 06:00 KST (Cron: '0 21 * * 0' UTC)

산출물: data/signal-stocks-db.json (~250KB)

MADE BY JUNS
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pykrx import stock
except ImportError:
    print("❌ pykrx가 설치되지 않았습니다. requirements.txt 확인 필요.")
    sys.exit(1)


# ===================== CONFIG =====================
OUTPUT_PATH = Path("data/signal-stocks-db.json")
TIMEOUT_PER_QUERY = 3  # 초

# 한국시장 섹터 분류 (pykrx KRX 섹터 → 우리 앱용 한글 단순화)
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


# ===================== HELPERS =====================
def get_latest_business_day():
    """가장 최근 영업일(평일) 반환 — KRX는 평일에만 데이터 제공"""
    d = datetime.now()
    # 주말이면 금요일까지
    while d.weekday() >= 5:  # 5=토, 6=일
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def make_aliases(name: str) -> list:
    """종목명에서 자주 쓰는 별칭 자동 생성"""
    aliases = []
    # 흔한 약칭 패턴
    common_aliases = {
        "삼성전자": ["삼전"],
        "SK하이닉스": ["하이닉스"],
        "삼성바이오로직스": ["삼성바이오"],
        "LG에너지솔루션": ["엘지엔솔", "LG엔솔"],
        "POSCO홀딩스": ["포스코", "포스코홀딩스"],
        "삼성SDI": ["에스디아이"],
        "현대차": ["현대자동차"],
        "현대자동차": ["현대차"],
    }
    if name in common_aliases:
        aliases.extend(common_aliases[name])
    return aliases


def normalize_market_code(ticker: str, market: str) -> str:
    """종목코드 + Yahoo Finance suffix 부여"""
    if market == "KOSDAQ":
        return f"{ticker}.KQ"
    else:  # KOSPI, KONEX
        return f"{ticker}.KS"


# ===================== MAIN =====================
def build_stocks_db():
    print(f"🚀 SIGNAL PRO 종목 DB 생성 시작")
    print(f"📅 영업일 기준: {get_latest_business_day()}")

    target_date = get_latest_business_day()
    all_stocks = []

    # 1) KOSPI + KOSDAQ + KONEX 종목 코드 가져오기
    markets = {
        "KOSPI": "KOSPI",
        "KOSDAQ": "KOSDAQ",
        "KONEX": "KONEX",
    }

    for market_name, market_code in markets.items():
        print(f"\n📊 {market_name} 종목 수집 중...")
        try:
            tickers = stock.get_market_ticker_list(target_date, market=market_code)
            print(f"   ✓ {len(tickers)}개 종목 코드 확보")
        except Exception as e:
            print(f"   ❌ {market_name} 종목 코드 수집 실패: {e}")
            continue

        # 시가총액 일괄 조회 (효율적)
        try:
            cap_df = stock.get_market_cap(target_date, market=market_code)
            print(f"   ✓ 시가총액 데이터 {len(cap_df)}건")
        except Exception as e:
            print(f"   ⚠️  시가총액 일괄 조회 실패: {e}")
            cap_df = None

        # 섹터 분류 일괄 조회
        try:
            sector_df = stock.get_market_sector_classifications(
                target_date, market=market_code
            )
            sector_map = dict(zip(sector_df.index, sector_df["업종명"])) if sector_df is not None else {}
        except Exception:
            sector_map = {}

        # 종목별 데이터 통합
        for ticker in tickers:
            try:
                name = stock.get_market_ticker_name(ticker)

                # 시가총액
                market_cap = 0
                if cap_df is not None and ticker in cap_df.index:
                    market_cap = int(cap_df.loc[ticker, "시가총액"])

                # 섹터
                sector = sector_map.get(ticker, "기타")
                sector = SECTOR_SIMPLIFY.get(sector, sector)

                # ETF / REITs 자동 분류 (이름 기반)
                if any(kw in name for kw in ["KODEX", "TIGER", "ACE", "KBSTAR", "HANARO", "ARIRANG", "SMART"]):
                    sector = "ETF"
                elif any(kw in name for kw in ["리츠", "REIT"]):
                    sector = "리츠"

                all_stocks.append({
                    "code": normalize_market_code(ticker, market_name),
                    "name": name,
                    "market": market_name,
                    "sector": sector,
                    "marketCap": market_cap,
                    "aliases": make_aliases(name),
                })
            except Exception as e:
                print(f"   ⚠️  {ticker} 처리 실패: {e}")
                continue

    # 시가총액 내림차순 정렬 (검색시 대형주 우선 노출)
    all_stocks.sort(key=lambda x: x.get("marketCap", 0), reverse=True)

    # 결과 JSON 구조
    now = datetime.now()
    result = {
        "version": now.strftime("%Y.%m.%d"),
        "updated_at": now.isoformat() + "+09:00",
        "source": "KRX (pykrx)",
        "count": len(all_stocks),
        "markets": {
            "KOSPI": sum(1 for s in all_stocks if s["market"] == "KOSPI"),
            "KOSDAQ": sum(1 for s in all_stocks if s["market"] == "KOSDAQ"),
            "KONEX": sum(1 for s in all_stocks if s["market"] == "KONEX"),
        },
        "stocks": all_stocks,
    }

    # 출력 디렉토리 생성
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # JSON 저장 (한글 깨짐 방지)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n✅ 완료!")
    print(f"   📁 {OUTPUT_PATH}")
    print(f"   📊 총 {result['count']}개 종목")
    print(f"      - KOSPI: {result['markets']['KOSPI']}")
    print(f"      - KOSDAQ: {result['markets']['KOSDAQ']}")
    print(f"      - KONEX: {result['markets']['KONEX']}")
    print(f"   💾 파일 크기: {file_size_kb:.1f} KB")

    return result


if __name__ == "__main__":
    try:
        build_stocks_db()
    except Exception as e:
        print(f"❌ 빌드 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
