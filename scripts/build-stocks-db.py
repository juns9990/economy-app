#!/usr/bin/env python3
"""
SIGNAL PRO v3.9.0 — 종목 DB 자동 생성 스크립트 (v4)
================================================
4단계 폴백 체인으로 KRX 데이터 안정 수집:
  1차: KRX 정보데이터시스템 (data.krx.co.kr) - 직접 호출
  2차: KIND 상장법인목록 (kind.krx.co.kr) - HTML 파싱
  3차: pykrx 라이브러리
  4차: 정적 백업 JSON

MADE BY JUNS
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from pathlib import Path

import requests

OUTPUT_PATH = Path("data/signal-stocks-db.json")
BACKUP_PATH = Path("data/signal-stocks-db.backup.json")
WEEKDAY_KR = ['월','화','수','목','금','토','일']

# 브라우저 위장 헤더 (KRX 차단 회피)
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SECTOR_SIMPLIFY = {
    "전기,전자": "전기전자", "운수장비": "운송장비", "철강금속": "철강금속",
    "화학": "화학", "기계": "기계", "음식료품": "음식료",
    "섬유,의복": "섬유의류", "비금속광물": "비금속", "의약품": "제약바이오",
    "건설업": "건설", "유통업": "유통", "금융업": "금융",
    "보험": "보험", "증권": "증권", "운수창고업": "물류",
    "전기가스업": "전기가스", "통신업": "통신", "서비스업": "서비스",
    "오락,문화": "엔터테인먼트", "종이,목재": "제지목재",
}


def make_aliases(name):
    common = {
        "삼성전자": ["삼전"], "SK하이닉스": ["하이닉스"],
        "삼성바이오로직스": ["삼성바이오"], "LG에너지솔루션": ["엘지엔솔", "LG엔솔"],
        "POSCO홀딩스": ["포스코", "포스코홀딩스"], "현대차": ["현대자동차"],
        "NAVER": ["네이버"], "한화에어로스페이스": ["한화에어로"],
        "한국항공우주": ["KAI"], "SK텔레콤": ["SKT"],
    }
    return common.get(name, [])


def normalize_code(ticker, market):
    return f"{ticker}.KQ" if market == "KOSDAQ" else f"{ticker}.KS"


def categorize_etf_reit(name, sector):
    if any(kw in name for kw in ["KODEX","TIGER","ACE","KBSTAR","HANARO","ARIRANG","SMART","KOSEF"]):
        return "ETF"
    elif any(kw in name for kw in ["리츠","REIT"]):
        return "리츠"
    return SECTOR_SIMPLIFY.get(sector, sector)


# ============================================================
# 방법 1: KRX 정보데이터시스템 (data.krx.co.kr) 직접 호출
# ============================================================
def fetch_from_krx_data():
    print("\n🎯 방법 1: KRX 정보데이터시스템 (data.krx.co.kr)")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": DESKTOP_UA,
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Origin": "http://data.krx.co.kr",
        "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
    })
    
    # 영업일 자동 탐색
    target_date = None
    for offset in range(10):
        d = datetime.now() - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        target_date = d.strftime("%Y%m%d")
        break
    
    if not target_date:
        return None
    
    print(f"   📅 기준일: {target_date}")
    
    all_stocks = []
    
    # 시장별 (KOSPI=STK, KOSDAQ=KSQ, KONEX=KNX)
    market_codes = {"KOSPI": "STK", "KOSDAQ": "KSQ", "KONEX": "KNX"}
    
    for market_name, mkt_id in market_codes.items():
        print(f"\n   📊 {market_name} 수집...")
        try:
            # 시가총액 데이터 가져오기 (전체 종목 + 시총 한 번에)
            payload = {
                "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
                "mktId": mkt_id,
                "trdDd": target_date,
                "money": "1",
                "csvxls_isNo": "false",
            }
            
            r = session.post(
                "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
                data=payload,
                timeout=15
            )
            
            print(f"      상태: {r.status_code}, 크기: {len(r.content)}")
            
            if r.status_code != 200:
                print(f"      ⚠️  실패")
                continue
            
            data = r.json()
            rows = data.get("OutBlock_1", [])
            
            if not rows:
                print(f"      ⚠️  데이터 없음")
                continue
            
            print(f"      ✓ {len(rows)}개 종목 받음")
            
            for row in rows:
                ticker = row.get("ISU_SRT_CD", "").strip()
                name = row.get("ISU_ABBRV", "").strip()
                if not ticker or not name:
                    continue
                
                # 시가총액 파싱
                try:
                    mkt_cap_str = row.get("MKTCAP", "0").replace(",", "")
                    market_cap = int(mkt_cap_str) if mkt_cap_str else 0
                except (ValueError, AttributeError):
                    market_cap = 0
                
                # 섹터 (이 API는 섹터 정보가 없음, 별도 호출 필요)
                sector = "기타"
                sector = categorize_etf_reit(name, sector)
                
                all_stocks.append({
                    "code": normalize_code(ticker, market_name),
                    "name": name,
                    "market": market_name,
                    "sector": sector,
                    "marketCap": market_cap,
                    "aliases": make_aliases(name),
                })
            
            time.sleep(1)  # API 부하 방지
            
        except Exception as e:
            print(f"      ❌ 에러: {str(e)[:120]}")
    
    if all_stocks:
        print(f"\n   ✅ KRX 정보데이터: 총 {len(all_stocks)}개 수집 성공")
        return all_stocks, target_date
    return None


# ============================================================
# 방법 2: KIND 상장법인목록 (kind.krx.co.kr)
# ============================================================
def fetch_from_kind():
    print("\n🎯 방법 2: KIND 상장법인목록")
    
    headers = {
        "User-Agent": DESKTOP_UA,
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://kind.krx.co.kr/corpgeneral/corpList.do",
    }
    
    all_stocks = []
    market_params = {
        "KOSPI": "stockMkt",
        "KOSDAQ": "kosdaqMkt",
        "KONEX": "konexMkt",
    }
    
    try:
        import pandas as pd
    except ImportError:
        print("   ⚠️  pandas 필요 (HTML 테이블 파싱용)")
        return None
    
    for market_name, mkt_type in market_params.items():
        print(f"\n   📊 {market_name} 수집...")
        try:
            url = f"https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType={mkt_type}"
            r = requests.get(url, headers=headers, timeout=15)
            print(f"      상태: {r.status_code}, 크기: {len(r.content)}")
            
            if r.status_code != 200:
                continue
            
            # HTML 테이블 파싱
            dfs = pd.read_html(StringIO(r.text), encoding='euc-kr')
            if not dfs:
                continue
            
            df = dfs[0]
            print(f"      ✓ {len(df)}개 종목 발견")
            
            for _, row in df.iterrows():
                name = str(row.get("회사명", "")).strip()
                ticker_raw = row.get("종목코드", "")
                if not name or not ticker_raw:
                    continue
                
                # 종목코드 6자리로 정규화
                ticker = f"{int(ticker_raw):06d}"
                sector_raw = str(row.get("업종", "기타")).strip()
                sector = categorize_etf_reit(name, sector_raw)
                
                all_stocks.append({
                    "code": normalize_code(ticker, market_name),
                    "name": name,
                    "market": market_name,
                    "sector": sector,
                    "marketCap": 0,  # KIND에는 시총 없음
                    "aliases": make_aliases(name),
                })
        except Exception as e:
            print(f"      ❌ 에러: {str(e)[:120]}")
    
    if all_stocks:
        today = datetime.now().strftime("%Y%m%d")
        print(f"\n   ✅ KIND: 총 {len(all_stocks)}개 수집 성공")
        return all_stocks, today
    return None


# ============================================================
# 방법 3: pykrx (기존)
# ============================================================
def fetch_from_pykrx():
    print("\n🎯 방법 3: pykrx 라이브러리")
    try:
        from pykrx import stock
    except ImportError:
        print("   ⚠️  pykrx 설치 안 됨")
        return None
    
    # 영업일 탐색
    target_date = None
    for offset in range(10):
        d = datetime.now() - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        date_str = d.strftime("%Y%m%d")
        try:
            tickers = stock.get_market_ticker_list(date_str, market="KOSPI")
            if tickers and len(tickers) > 10:
                target_date = date_str
                print(f"   ✓ {date_str} 데이터 확인 ({len(tickers)}개)")
                break
        except Exception:
            continue
    
    if not target_date:
        print("   ❌ pykrx: 유효 영업일 없음")
        return None
    
    all_stocks = []
    for market_name, market_code in [("KOSPI","KOSPI"), ("KOSDAQ","KOSDAQ"), ("KONEX","KONEX")]:
        try:
            tickers = stock.get_market_ticker_list(target_date, market=market_code)
            cap_df = stock.get_market_cap(target_date, market=market_code)
            for ticker in tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if not name: continue
                    market_cap = int(cap_df.loc[ticker, "시가총액"]) if ticker in cap_df.index else 0
                    all_stocks.append({
                        "code": normalize_code(ticker, market_name),
                        "name": name,
                        "market": market_name,
                        "sector": categorize_etf_reit(name, "기타"),
                        "marketCap": market_cap,
                        "aliases": make_aliases(name),
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"   ⚠️  {market_name}: {str(e)[:80]}")
    
    if all_stocks:
        print(f"   ✅ pykrx: 총 {len(all_stocks)}개")
        return all_stocks, target_date
    return None


# ============================================================
# 방법 4: 정적 백업 (이전 빌드 결과 재사용)
# ============================================================
def fetch_from_backup():
    print("\n🎯 방법 4: 백업 JSON 재사용")
    if not OUTPUT_PATH.exists():
        print("   ⚠️  백업 파일 없음")
        return None
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("count", 0) > 0:
            print(f"   ✓ 백업 {data['count']}개 종목 재사용")
            return data["stocks"], data.get("data_date", "backup")
    except Exception as e:
        print(f"   ❌ 백업 로드 실패: {e}")
    return None


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"🚀 SIGNAL PRO 종목 DB 생성 시작 (v4 멀티소스)")
    print(f"📅 현재 시각: {datetime.now().isoformat()}")
    
    # 4단계 폴백 체인
    methods = [
        ("KRX 정보데이터시스템", fetch_from_krx_data),
        ("KIND 상장법인목록", fetch_from_kind),
        ("pykrx", fetch_from_pykrx),
        ("백업 JSON", fetch_from_backup),
    ]
    
    stocks = None
    data_date = None
    method_used = None
    
    for method_name, fetch_func in methods:
        try:
            result = fetch_func()
            if result and result[0]:
                stocks, data_date = result
                method_used = method_name
                break
        except Exception as e:
            print(f"   ❌ {method_name} 예외: {str(e)[:120]}")
    
    if not stocks:
        print("\n❌ 모든 데이터 소스 실패!")
        sys.exit(1)
    
    # 시가총액 내림차순 정렬
    stocks.sort(key=lambda x: x.get("marketCap", 0), reverse=True)
    
    # 중복 제거 (code 기준)
    seen = set()
    unique_stocks = []
    for s in stocks:
        if s["code"] not in seen:
            seen.add(s["code"])
            unique_stocks.append(s)
    
    now = datetime.now()
    result = {
        "version": now.strftime("%Y.%m.%d"),
        "updated_at": now.isoformat() + "+09:00",
        "source": method_used,
        "data_date": data_date,
        "count": len(unique_stocks),
        "markets": {
            "KOSPI": sum(1 for s in unique_stocks if s["market"] == "KOSPI"),
            "KOSDAQ": sum(1 for s in unique_stocks if s["market"] == "KOSDAQ"),
            "KONEX": sum(1 for s in unique_stocks if s["market"] == "KONEX"),
        },
        "stocks": unique_stocks,
    }
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n{'='*50}")
    print(f"✅ 빌드 완료! (방법: {method_used})")
    print(f"{'='*50}")
    print(f"   📊 총 종목: {result['count']}")
    print(f"      KOSPI: {result['markets']['KOSPI']}")
    print(f"      KOSDAQ: {result['markets']['KOSDAQ']}")
    print(f"      KONEX: {result['markets']['KONEX']}")
    print(f"   💾 크기: {file_size_kb:.1f} KB")


if __name__ == "__main__":
    main()
