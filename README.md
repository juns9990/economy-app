# 📊 INVESTMENT SIGNAL PRO

> AI 기반 한국 주식 실시간 분석 PWA — v3.2.0

**MADE BY JUNS**

---

## 🚀 앱 접속

**공개 URL:** https://juns9990.github.io/economy-app/signal-pro.html

## 📁 파일 구성

| 파일 | 용도 | 배포 위치 |
|------|------|-----------|
| `signal-pro.html` | 메인 앱 (PWA) | GitHub Pages |
| `worker.js` | Yahoo Finance 프록시 | Cloudflare Workers |

## ⚙️ 세팅 (처음 한 번만)

### 1. Cloudflare Worker 배포

1. https://workers.cloudflare.com 접속
2. `worker.js` 내용을 새 Worker에 붙여넣기
3. **Deploy** 클릭
4. Worker URL 복사 (예: `https://xxx.workers.dev`)

### 2. Groq API 키 발급 (무료)

1. https://console.groq.com/keys 접속
2. Google 로그인 → **Create API Key**
3. `gsk_...` 로 시작하는 키 복사

### 3. 앱에서 키 설정

1. 앱 접속 → 사이드바 **설정**
2. **GROQ API KEY** 란에 붙여넣기
3. **💾 저장하기** 클릭

**끝!** 이제 AI 심층분석, 상담실, 글로벌 브리핑 전부 작동.

## 🎯 주요 기능

### 🌏 글로벌 시장 브리핑 (v3.1.0~)
- 매일 아침 미국 시장 데이터 자동 수집
- S&P 500, 나스닥, 다우, VIX, 10Y 국채, 달러지수
- AI가 오늘 한국 장 전망 분석 (주목/경계 섹터 추천)
- 1시간 자동 캐시 + 수동 새로고침

### 🎯 시그널 분석
- KOSPI / KOSDAQ 대부분 종목 지원
- 10개 기술 지표 자동 계산
  - RSI, MA5/20, MA20/60, 볼린저밴드
  - MACD, 모멘텀, 거래량, 기간위치
  - ATR, 추세강도
- 종합 점수 (0~100) → 매수/중립/매도 시그널
- 기간 전환: 3M / 6M / 1Y / 3Y / 10Y
- AI 심층분석 자동 실행 (2~3초)

### 💬 AI 전문가 그룹채팅
카카오톡 스타일로 5명의 AI 전문가와 대화
- 🎩 **워렌 버핏** — 가치투자
- 📊 **40년 고수** — 한국 주식 베테랑
- 🤖 **퀀트 전문가** — 통계/데이터
- 🌍 **거시경제** — 금리/환율/지정학
- 💰 **금융 전문가** — PER/PBR/재무

### 💼 포트폴리오
- 매수/매도 기록
- 실시간 평가손익
- 종목별 수익률 추적

### ⭐ 관심종목 + 🔔 가격 알림
- 시그널 페이지에서 별표 추가
- 대시보드에 실시간 시세
- 목표가 도달시 브라우저 푸시 알림

### 🧬 성향 분석
- 8문항 테스트
- 5가지 유형 (보수형 ~ 공격형)
- AI 분석이 성향 반영

### 📖 사용설명서
- 8개 섹션 상세 가이드
- 용어 사전 14개

## 🛠️ 기술 스택

- **프론트**: Vanilla JS + HTML + CSS (PWA)
- **AI**: Groq Llama 3.3 70B (브라우저 직접 호출)
- **데이터**: Yahoo Finance (Cloudflare Worker 프록시)
- **저장**: localStorage (brower-only)
- **배포**: GitHub Pages + Cloudflare Workers

## 📱 지원 환경

- PC: Chrome / Edge / Safari / Firefox
- 모바일: iOS Safari / Android Chrome
- PWA 설치 가능 (홈화면 추가)
- 반응형: 360px ~ 1920px

## 🔒 보안/프라이버시

- Groq API 키는 **본인 브라우저에만 저장**
- 외부 서버로 절대 전송 안 함
- 주가 데이터: Yahoo Finance (공개 데이터)
- 포트폴리오/관심종목도 브라우저에만 저장

## 📝 버전 히스토리

- **v3.2.0** (2026-04-22): API 키 마스킹 + 영구저장, 조회 실패 UX 개선
- **v3.1.1** (2026-04-22): 반응형 레이아웃 전면 개선
- **v3.1.0** (2026-04-22): 글로벌 시장 브리핑 추가
- **v3.0.0** (2026-04-20): Groq 브라우저 직접 호출
- **v2.9.x** (2026-04-20): Groq Llama AI 엔진 전환
- **v2.8.0** (2026-04-20): 관심종목 + 가격 알림
- **v2.7.0** (2026-04-20): AI 그룹채팅 스타일

## ⚠️ 법적 고지

이 앱은 투자 **참고용** 정보 제공 도구입니다.
- 투자자문업 등록 앱이 아님
- 모든 투자 결정은 본인 책임
- AI 분석은 과거 데이터 기반 패턴 분석이며 미래 수익 보장 안 함
- 투자 원금 손실 가능성 있음

## 📞 문의

GitHub: [@juns9990](https://github.com/juns9990)
