// ==================== Cloudflare Worker v5 (Groq + Debug) ====================
// 주가 + Groq AI 프록시 + 상세 에러 리포팅
//
// [배포 방법]
// 1. Cloudflare Workers 에디터에서 기존 코드 전체 삭제
// 2. 이 코드 전체 복사 붙여넣기
// 3. 우측 상단 "Deploy" 클릭
//
// [환경변수]
// Name: GROQ_KEY
// Type: Secret
// Value: gsk_... (Groq API 키)

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, x-api-key, anthropic-version',
        }
      });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // ============= AI 프록시 (Groq) =============
    if (path === '/ai' || path.startsWith('/ai')) {
      if (request.method !== 'POST') {
        return json({error: {message: 'POST required for /ai'}}, 405);
      }
      
      const keyStatus = env.GROQ_KEY ? 'present' : 'MISSING';
      const keyPreview = env.GROQ_KEY ? (env.GROQ_KEY.substring(0, 7) + '...' + env.GROQ_KEY.substring(env.GROQ_KEY.length - 4)) : 'null';
      
      if (!env.GROQ_KEY) {
        return json({error: {
          message: 'GROQ_KEY 환경변수가 Worker에 설정되지 않음. Settings > Variables에서 Secret으로 추가 후 Deploy 하세요.'
        }}, 500);
      }
      
      try {
        const body = await request.json();
        const messages = (body.messages || []).map(m => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: typeof m.content === 'string' ? m.content : m.content.map(c => c.text || '').join('')
        }));

        // 요청 가능한 여러 모델 순차 시도 (첫번째 성공한 모델 사용)
        const models = [
          'llama-3.1-8b-instant',      // 14,400 req/day, 빠름
          'llama-3.3-70b-versatile',   // 1,000 req/day, 더 똑똑
        ];
        
        let lastError = null;
        let lastStatus = 0;
        
        for (const model of models) {
          const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${env.GROQ_KEY.trim()}`,
              'Content-Type': 'application/json',
              'User-Agent': 'Mozilla/5.0 (signal-pro/1.0)',
              'Accept': 'application/json',
            },
            body: JSON.stringify({
              model: model,
              messages: messages,
              max_tokens: Math.min(body.max_tokens || 1024, 8000),
              temperature: 0.7,
            })
          });

          const responseText = await groqRes.text();
          let groqData;
          try { groqData = JSON.parse(responseText); } catch { groqData = {raw: responseText}; }

          if (groqRes.ok && groqData.choices?.[0]?.message?.content) {
            const reply = {
              content: [{
                type: 'text',
                text: groqData.choices[0].message.content
              }],
              model: model,
              usage: groqData.usage,
            };
            return json(reply, 200);
          }

          lastStatus = groqRes.status;
          lastError = {
            status: groqRes.status,
            statusText: groqRes.statusText,
            model: model,
            keyStatus: keyStatus,
            keyPreview: keyPreview,
            groqError: groqData.error || groqData,
          };
          
          // 401/403 이면 다른 모델 시도해도 소용없으니 중단
          if (groqRes.status === 401 || groqRes.status === 403) break;
        }

        return json({
          error: {
            message: `Groq ${lastStatus}: ${lastError?.groqError?.message || lastError?.statusText || 'Unknown'}`,
            debug: lastError
          }
        }, lastStatus || 502);

      } catch (e) {
        return json({error: {message: 'Worker 내부 에러: ' + e.message, stack: e.stack}}, 500);
      }
    }

    // ============= 주가 데이터 =============
    try {
      const sym = url.searchParams.get('sym');
      const range = url.searchParams.get('range') || '1d';
      const interval = url.searchParams.get('interval') || '1d';

      if (!sym) {
        return json({
          status: 'ok', 
          message: 'Worker running. Use ?sym=005930.KS for stock, /ai for AI',
          groqKeySet: !!env.GROQ_KEY,
        }, 200);
      }

      const urls = [
        `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?interval=${interval}&range=${range}`,
        `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?interval=${interval}&range=${range}`,
      ];

      let lastError = null;
      for (const yUrl of urls) {
        try {
          const res = await fetch(yUrl, {
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
              'Accept': 'application/json',
            },
            cf: { cacheTtl: 60 }
          });
          if (!res.ok) { lastError = `HTTP ${res.status}`; continue; }
          const data = await res.json();
          if (data?.chart?.result?.[0]) {
            return json(data, 200, { 'Cache-Control': 'public, max-age=60' });
          }
          if (data?.chart?.error) lastError = data.chart.error.description || 'chart error';
        } catch (e) { lastError = e.message; }
      }
      return json({error: 'Yahoo 전체 실패', lastError, symbol: sym}, 502);
    } catch (e) {
      return json({error: e.message}, 500);
    }
  }
}

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      ...extraHeaders,
    }
  });
}
