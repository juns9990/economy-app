// ==================== Cloudflare Worker v6 (User-Key Proxy) ====================
// 주가 프록시 + Groq AI 프록시 (사용자 키 사용)
//
// [배포]
// 1. Cloudflare Workers 에디터에서 기존 코드 전체 삭제
// 2. 이 코드 전체 붙여넣기
// 3. Deploy 클릭
//
// [환경변수 불필요]
// 사용자가 자기 Groq 키를 직접 보내고, Worker는 단순 중계만 함.

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (path === '/ai' || path.startsWith('/ai')) {
        return await handleAI(request);
      }
      return await handleStock(url);
    } catch (e) {
      return json({ error: { message: 'Worker 내부 에러: ' + (e.message || 'unknown') } }, 500);
    }
  },
};

async function handleAI(request) {
  if (request.method !== 'POST') {
    return json({ error: { message: 'POST required for /ai' } }, 405);
  }

  let userKey = request.headers.get('x-groq-key') || '';
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: { message: 'Invalid JSON body' } }, 400);
  }

  if (!userKey && body.apiKey) userKey = body.apiKey;
  delete body.apiKey;

  if (!userKey) {
    return json({ error: { message: 'API 키가 필요합니다. x-groq-key 헤더로 전달하세요.' } }, 401);
  }

  userKey = userKey.replace(/[\s\u200B-\u200D\uFEFF\u00A0]+/g, '').trim();
  if (!userKey.startsWith('gsk_')) {
    return json({ error: { message: '키 형식 오류: gsk_ 로 시작해야 합니다.' } }, 400);
  }

  const payload = {
    model: body.model || 'llama-3.3-70b-versatile',
    messages: body.messages || [],
    max_tokens: Math.min(body.max_tokens || 2000, 8000),
    temperature: body.temperature ?? 0.3,
  };
  if (body.top_p !== undefined) payload.top_p = body.top_p;

  let groqRes;
  try {
    groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (signal-pro/2.0)',
      },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    return json({ error: { message: 'Groq 서버 연결 실패: ' + e.message } }, 502);
  }

  const responseText = await groqRes.text();
  let groqData;
  try {
    groqData = JSON.parse(responseText);
  } catch {
    return json({ error: { message: 'Groq 응답 파싱 실패', raw: responseText.substring(0, 200) } }, 502);
  }

  return json(groqData, groqRes.status);
}

async function handleStock(url) {
  const sym = url.searchParams.get('sym');
  const range = url.searchParams.get('range') || '3mo';
  const interval = url.searchParams.get('interval') || '1d';

  if (!sym) {
    return json({ error: { message: 'sym 파라미터 필요' } }, 400);
  }

  const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=${range}&interval=${interval}&includePrePost=false`;

  let res;
  try {
    res = await fetch(yahooUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
      },
    });
  } catch (e) {
    return json({ error: { message: 'Yahoo 연결 실패: ' + e.message } }, 502);
  }

  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return json({ error: { message: 'Yahoo 응답 파싱 실패' } }, 502);
  }

  return json(data, res.status);
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, x-groq-key, x-api-key',
    'Access-Control-Max-Age': '86400',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(),
    },
  });
}
