# 📊 SIGNAL PRO 종목 DB 자동화

KRX 한국 시장 전체 종목(약 2,500개)을 자동 수집하여 SIGNAL PRO 앱에서 검색 가능하게 합니다.

---

## 🗂️ 파일 구조

```
economy-app/
├─ .github/
│  └─ workflows/
│     └─ stocks-db-update.yml      ← GitHub Actions (자동 갱신)
├─ scripts/
│  └─ build-stocks-db.py            ← pykrx 활용 빌드 스크립트
└─ data/
   └─ signal-stocks-db.json         ← 결과물 (자동 생성)
```

---

## 🚀 배포 방법

### 1단계: 파일 3개를 리포에 추가

```bash
cd ~/economy-app

# 디렉토리 생성
mkdir -p .github/workflows scripts data

# 파일 복사
cp /path/to/stocks-db-update.yml .github/workflows/
cp /path/to/build-stocks-db.py scripts/
cp /path/to/signal-stocks-db.json data/   # 샘플 JSON (선택)

# 커밋
git add .
git commit -m "🤖 종목 DB 자동화 추가 (SIGNAL PRO v3.9.0)"
git push
```

### 2단계: GitHub Actions 첫 실행

1. GitHub 리포 → **Actions** 탭 진입
2. **"SIGNAL PRO 종목 DB 자동 갱신"** workflow 선택
3. **"Run workflow"** 버튼 클릭 (수동 실행)
4. 약 1~2분 후 빌드 완료
5. `data/signal-stocks-db.json` 자동 갱신 + 커밋

### 3단계: 결과 확인

- GitHub Pages URL: `https://juns9990.github.io/economy-app/data/signal-stocks-db.json`
- 약 2,500개 종목, ~250KB

---

## ⏰ 자동 갱신 일정

- **매주 일요일 06:00 KST** (Cron: `0 21 * * 0` UTC)
- 변경사항이 있으면 자동 커밋
- 동일하면 커밋 안 함 (불필요한 commit 방지)

---

## 📡 앱 측 통합 코드

v3.9.0 signal-pro.html에 추가:

```javascript
// 종목 DB 전역
let STOCKS = [];
let STOCKS_DB_VERSION = null;
let STOCKS_DB_READY = false;

// 로딩
async function loadStocksDB() {
  const DB_URL = 'https://juns9990.github.io/economy-app/data/signal-stocks-db.json';
  const FALLBACK_URL = './data/signal-stocks-db.json';

  try {
    // 1차: GitHub Pages
    let r = await fetch(DB_URL, { cache: 'no-cache' });
    if (!r.ok) throw new Error('Primary fetch failed');
    const data = await r.json();

    STOCKS = data.stocks;
    STOCKS_DB_VERSION = data.version;
    STOCKS_DB_READY = true;

    console.log(`✅ 종목 DB 로드: ${data.count}개 (v${data.version})`);
    console.log(`   KOSPI: ${data.markets.KOSPI} / KOSDAQ: ${data.markets.KOSDAQ}`);

    // localStorage 캐싱 (다음 로딩 가속)
    localStorage.setItem('isp_stocks_db', JSON.stringify(data));
    localStorage.setItem('isp_stocks_db_at', Date.now().toString());
  } catch (e) {
    console.warn('⚠️ 외부 DB 로드 실패, 캐시 시도:', e);

    // 2차: localStorage 캐시
    const cached = localStorage.getItem('isp_stocks_db');
    if (cached) {
      try {
        const data = JSON.parse(cached);
        STOCKS = data.stocks;
        STOCKS_DB_VERSION = data.version + ' (cached)';
        STOCKS_DB_READY = true;
        console.log(`📦 캐시에서 ${data.count}개 종목 로드`);
        return;
      } catch (_) {}
    }

    // 3차: 하드코딩 fallback (최소 50개 종목)
    STOCKS = HARDCODED_STOCKS;
    STOCKS_DB_VERSION = 'fallback';
    STOCKS_DB_READY = true;
    console.log(`🔌 폴백 모드: ${STOCKS.length}개 종목`);
  }
}

// 앱 시작시 호출
document.addEventListener('DOMContentLoaded', () => {
  loadStocksDB();
});
```

---

## 🔍 검색 함수 변경

기존 `stockMatch()` 함수는 **변경 불필요**. 2,500개 × 정규화 비교는 1~2ms 수준.

단, DB 로딩 전 검색 시도 처리만 추가:

```javascript
function stockMatch(query) {
  if (!STOCKS_DB_READY) {
    return [];  // 로딩 중
  }
  // 기존 로직 그대로...
}
```

---

## 🧪 로컬 테스트

```bash
# pykrx 설치
pip install pykrx pandas

# 스크립트 실행
python scripts/build-stocks-db.py

# 결과 확인
cat data/signal-stocks-db.json | python -m json.tool | head -50
```

---

## ⚠️ 트러블슈팅

### Actions 빌드 실패시
- **KRX 사이트 일시 장애:** 평일 KRX 휴장일에는 실행해도 데이터 없음 → 다음 영업일 자동 재시도
- **pykrx 버전 충돌:** `requirements.txt`에 `pykrx==1.0.45` 고정

### 종목 검색 안 됨
- 브라우저 콘솔에서 `STOCKS_DB_READY` 확인
- `console.log(STOCKS.length)` — 0이면 DB 로딩 실패
- 네트워크 탭에서 `signal-stocks-db.json` fetch 상태 확인

---

## 📈 향후 확장

추가할 수 있는 데이터:
- ✅ 시가총액 (현재 포함)
- ⏳ 외국인 보유 비중 (네이버 금융 크롤링 필요)
- ⏳ 일평균 거래대금
- ⏳ 52주 최고/최저가
- ⏳ 배당수익률
- ⏳ PER / PBR

→ build-stocks-db.py에 추가 컬럼 확장 가능

---

**MADE BY JUNS · 2026.04.27**
