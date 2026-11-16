import { workflow, node, trigger, sticky, ifElse, expr } from '@n8n/workflow-sdk';

const webhookTrigger = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'GET /webhook/ai-news',
    parameters: { httpMethod: 'GET', path: 'ai-news', responseMode: 'responseNode', options: {} },
    position: [240, 200]
  },
  output: [{ headers: {}, params: {}, query: {}, body: {} }]
});

const every12h = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: {
    name: 'Every 12 Hours',
    parameters: { rule: { interval: [{ field: 'hours', hoursInterval: 12 }] } },
    position: [240, 500]
  },
  output: [{}]
});

const every30m = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: {
    name: 'Every 30 Minutes',
    parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 30 }] } },
    position: [240, 700]
  },
  output: [{}]
});

const readCache = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read Cached News',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: "const cache = $getWorkflowStaticData('global');\nconst articles = (Array.isArray(cache.articles) ? cache.articles : []).map(({ translated, ...a }) => a);\nreturn [{ json: { status: 'ok', updated_at: cache.updated_at || null, articles } }];"
    },
    position: [480, 200]
  },
  output: [{ status: 'ok', updated_at: '2026-10-23T12:00:00Z', articles: [] }]
});

const hasCache = ifElse({
  version: 2.3,
  config: {
    name: 'Cache Has Articles?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
        conditions: [
          { leftValue: expr('{{ $json.articles }}'), rightValue: '', operator: { type: 'array', operation: 'notEmpty', singleValue: true } },
          { leftValue: expr("{{ $('GET /webhook/ai-news').first().json.query.refresh ?? '' }}"), rightValue: '1', operator: { type: 'string', operation: 'notEquals' } }
        ],
        combinator: 'and'
      }
    },
    position: [700, 200]
  }
});

const respond = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Respond to Widget',
    parameters: {
      respondWith: 'firstIncomingItem',
      options: {
        responseCode: 200,
        responseHeaders: { entries: [{ name: 'Cache-Control', value: 'public, max-age=300' }] }
      }
    },
    position: [3100, 200]
  }
});

const fetchHN = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Fetch Hacker News AI',
    executeOnce: true,
    onError: 'continueRegularOutput',
    parameters: {
      method: 'GET',
      url: 'https://hn.algolia.com/api/v1/search',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: {
        parameters: [
          { name: 'tags', value: 'story' },
          { name: 'query', value: 'AI LLM OpenAI Anthropic Gemini Claude GPT' },
          { name: 'optionalWords', value: 'AI LLM OpenAI Anthropic Gemini Claude GPT' },
          { name: 'numericFilters', value: expr('created_at_i>{{ Math.floor(Date.now() / 1000) - 172800 }},points>=10') },
          { name: 'hitsPerPage', value: '30' }
        ]
      },
      options: { timeout: 15000 }
    },
    position: [920, 600]
  },
  output: [{ hits: [{ objectID: '1', title: 'Example', url: 'https://example.com', created_at: '2026-10-23T11:00:00Z', points: 10, num_comments: 2 }] }]
});

const fetchHF = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Fetch HuggingFace Papers',
    executeOnce: true,
    onError: 'continueRegularOutput',
    parameters: {
      method: 'GET',
      url: 'https://huggingface.co/api/daily_papers?limit=20',
      options: { timeout: 15000 }
    },
    position: [1140, 600]
  },
  output: [{ title: 'Paper', publishedAt: '2026-10-23T08:00:00Z', paper: { id: '2610.00001', title: 'Paper', summary: 'Abstract' } }]
});

const feedList = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'RSS Feed List',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: "return [\n  'https://openai.com/news/rss.xml',\n  'https://blog.google/technology/ai/rss/',\n  'https://huggingface.co/blog/feed.xml',\n  'https://www.technologyreview.com/topic/artificial-intelligence/feed',\n  'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',\n  'https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day'\n].map(url => ({ json: { url } }));"
    },
    position: [1360, 600]
  },
  output: [{ url: 'https://openai.com/news/rss.xml' }]
});

const readRss = node({
  type: 'n8n-nodes-base.rssFeedRead',
  version: 1.2,
  config: {
    name: 'Read RSS Feeds',
    onError: 'continueRegularOutput',
    parameters: { url: expr('{{ $json.url }}'), options: {} },
    position: [1580, 600]
  },
  output: [{ title: 'News', link: 'https://openai.com/news/x', isoDate: '2026-10-23T10:00:00Z', contentSnippet: 'Snippet' }]
});

const normalize = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Normalize & Dedupe',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const MAX_ARTICLES = 60;
const MAX_AGE_MS = 72 * 3600 * 1000;

const clean = (s, n = 300) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&[a-z#0-9]+;/gi, ' ').replace(/\\s+/g, ' ').trim().slice(0, n);
const iso = (d) => { const t = new Date(d); return isNaN(t) ? new Date().toISOString() : t.toISOString(); };
const normUrl = (u) => String(u || '').replace(/[?#].*$/, '').replace(/\\/$/, '').toLowerCase();

const CATEGORY_RULES = [
  ['Research', /\\b(paper|arxiv|research|benchmark|study|dataset|training|reasoning)\\b/i],
  ['Open Source', /\\b(open[- ]?source|open[- ]?weight|llama|mistral|qwen|deepseek|gguf|ollama|hugging ?face|localllama)\\b/i],
  ['LLMs', /\\b(gpt|llm|claude|gemini|chatgpt|language model|model|anthropic|openai)\\b/i],
  ['Tools', /\\b(tool|sdk|api|plugin|app|launch|release|agent|copilot|cli)\\b/i]
];
const categorize = (text, fallback) => {
  for (const [cat, re] of CATEGORY_RULES) if (re.test(text)) return cat;
  return fallback;
};

const SOURCE_BY_HOST = {
  'openai.com': 'OpenAI', 'blog.google': 'Google AI', 'huggingface.co': 'Hugging Face',
  'technologyreview.com': 'MIT Tech Review', 'theverge.com': 'The Verge', 'reddit.com': 'r/LocalLLaMA'
};
const sourceFromUrl = (u) => {
  const m = String(u || '').match(/^https?:\\/\\/(?:www\\.)?([^\\/:?#]+)/i);
  if (!m) return 'RSS';
  const host = m[1].toLowerCase();
  for (const [h, name] of Object.entries(SOURCE_BY_HOST)) if (host.endsWith(h)) return name;
  return host;
};

const firstImage = (htmlText) => {
  const m = String(htmlText || '').match(/<img[^>]+src=["']([^"']+)["']/i);
  return m && /^https?:/.test(m[1]) ? m[1].replace(/&amp;/g, '&') : null;
};

const fresh = [];

for (const item of $('Fetch Hacker News AI').all()) {
  for (const hit of item.json.hits || []) {
    if (!hit.title) continue;
    const url = hit.url || \`https://news.ycombinator.com/item?id=\${hit.objectID}\`;
    fresh.push({
      id: \`hn-\${hit.objectID}\`,
      title: clean(hit.title, 200),
      summary: hit.story_text ? clean(hit.story_text) : \`Debate destacado en Hacker News (\${hit.points || 0} puntos, \${hit.num_comments || 0} comentarios).\`,
      url,
      source: 'Hacker News',
      category: categorize(hit.title, 'Industry'),
      published_at: iso(hit.created_at),
      image_url: null
    });
  }
}

for (const item of $('Fetch HuggingFace Papers').all()) {
  const p = item.json.paper;
  if (!p || !p.id) continue;
  fresh.push({
    id: \`hf-\${p.id}\`,
    title: clean(p.title || item.json.title, 200),
    summary: clean(p.ai_summary || p.summary),
    url: \`https://huggingface.co/papers/\${p.id}\`,
    source: 'Hugging Face Papers',
    category: 'Research',
    published_at: iso(item.json.publishedAt || p.publishedAt),
    image_url: item.json.thumbnail || null
  });
}

for (const item of $input.all()) {
  const e = item.json;
  if (!e.title || !e.link) continue;
  const text = \`\${e.title} \${e.contentSnippet || ''}\`;
  fresh.push({
    id: \`rss-\${normUrl(e.link).replace(/[^a-z0-9]+/g, '-').slice(-80)}\`,
    title: clean(e.title, 200),
    summary: clean(e.contentSnippet || e.content || e.summary),
    url: e.link,
    source: sourceFromUrl(e.link),
    category: categorize(text, 'Industry'),
    published_at: iso(e.isoDate || e.pubDate),
    image_url: (e.enclosure && e.enclosure.url) || firstImage(e.content) || null
  });
}

const cache = $getWorkflowStaticData('global');
const previous = Array.isArray(cache.articles) ? cache.articles : [];
const cutoff = Date.now() - MAX_AGE_MS;
const seen = new Set();
const articles = [...previous.filter(a => a.translated), ...fresh, ...previous]
  .filter(a => {
    const key = normUrl(a.url);
    if (seen.has(key)) return false;
    seen.add(key);
    return new Date(a.published_at).getTime() >= cutoff;
  })
  .sort((a, b) => b.published_at.localeCompare(a.published_at))
  .slice(0, MAX_ARTICLES);

const freshByUrl = new Map(fresh.map(f => [normUrl(f.url), f]));
for (const a of articles) {
  const f = freshByUrl.get(normUrl(a.url));
  if (!a.image_url && f && f.image_url) a.image_url = f.image_url;
}

const MAX_PENDING = 40;
const pending = articles
  .map((a, i) => ({ i, title: a.title, summary: a.summary, translated: a.translated }))
  .filter(a => !a.translated)
  .slice(0, MAX_PENDING)
  .map(({ i, title, summary }) => ({ i, title, summary }));

return [{ json: { articles, pending } }];`
    },
    position: [1800, 600]
  },
  output: [{ articles: [{ id: 'hn-1', title: 'Example', summary: 'S', url: 'https://example.com', source: 'Hacker News', category: 'Industry', published_at: '2026-10-23T11:00:00Z', image_url: null }], pending: [{ i: 0, title: 'Example', summary: 'S' }] }]
});

const needsTranslation = ifElse({
  version: 2.3,
  config: {
    name: 'Needs Translation?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
        conditions: [{ leftValue: expr('{{ $json.pending }}'), rightValue: '', operator: { type: 'array', operation: 'notEmpty', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [2000, 600]
  }
});

const buildRequest = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build Gemini Request',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const pending = $input.first().json.pending;
const instruction = 'Recibes un array JSON de noticias de IA con los campos i, title y summary (normalmente en inglés). ' +
  'Para cada noticia devuelve un objeto con: i (el mismo número), title (titular traducido al español, natural y conciso, máximo 120 caracteres), ' +
  'summary (resumen ejecutivo en español de 1-2 frases, máximo 220 caracteres, basado solo en el título y el resumen recibidos; no inventes datos) ' +
  'y category (exactamente una de: LLMs, Research, Open Source, Industry, Tools). ' +
  'Mantén en su forma original los nombres propios, de modelos y de productos.';
return [{ json: { body: {
  systemInstruction: { parts: [{ text: instruction }] },
  contents: [{ role: 'user', parts: [{ text: JSON.stringify(pending) }] }],
  generationConfig: {
    temperature: 0.2,
    maxOutputTokens: 8192,
    responseMimeType: 'application/json',
    responseSchema: {
      type: 'ARRAY',
      items: {
        type: 'OBJECT',
        properties: {
          i: { type: 'INTEGER' },
          title: { type: 'STRING' },
          summary: { type: 'STRING' },
          category: { type: 'STRING', enum: ['LLMs', 'Research', 'Open Source', 'Industry', 'Tools'] }
        },
        required: ['i', 'title', 'summary', 'category']
      }
    }
  }
} } }];`
    },
    position: [2220, 500]
  },
  output: [{ body: { contents: [] } }]
});

const translate = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Translate with Gemini',
    onError: 'continueRegularOutput',
    parameters: {
      method: 'POST',
      url: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googlePalmApi',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify($json.body) }}'),
      options: { timeout: 90000 }
    },
    credentials: { googlePalmApi: { id: '6rddixYKxV939cRo', name: 'Google gemini' } },
    position: [2440, 500]
  },
  output: [{ candidates: [{ content: { parts: [{ text: '[{"i":0,"title":"Ejemplo","summary":"Resumen","category":"LLMs"}]' }] } }] }]
});

const applyAndCache = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Apply Translations & Cache',
    parameters: {
      mode: 'runOnceForAllItems',
      jsCode: `const CATEGORIES = ['LLMs', 'Research', 'Open Source', 'Industry', 'Tools'];
const source = $('Normalize & Dedupe').first().json;
const articles = source.articles.map(a => ({ ...a }));
const pendingIdx = new Set(source.pending.map(p => p.i));

const findTranslations = (v) => {
  if (Array.isArray(v)) {
    if (v.length && v[0] && typeof v[0] === 'object' && 'i' in v[0]) return v;
    for (const x of v) { const r = findTranslations(x); if (r) return r; }
    return null;
  }
  if (typeof v === 'string') {
    const m = v.match(/\\[[\\s\\S]*\\]/);
    if (!m) return null;
    try { return findTranslations(JSON.parse(m[0])); } catch { return null; }
  }
  if (v && typeof v === 'object') {
    for (const k of Object.keys(v)) { const r = findTranslations(v[k]); if (r) return r; }
  }
  return null;
};

const translations = $('Translate with Gemini').isExecuted
  ? (findTranslations($('Translate with Gemini').first().json) || [])
  : [];

for (const t of translations) {
  const i = Number(t.i);
  if (!pendingIdx.has(i) || !articles[i] || !t.title) continue;
  articles[i] = {
    ...articles[i],
    title: String(t.title).slice(0, 200),
    summary: String(t.summary || articles[i].summary).slice(0, 300),
    category: CATEGORIES.includes(t.category) ? t.category : articles[i].category,
    translated: true
  };
}

const cache = $getWorkflowStaticData('global');
const updated_at = new Date().toISOString();
cache.articles = articles;
cache.updated_at = updated_at;

return [{ json: { status: 'ok', updated_at, articles: articles.map(({ translated, ...a }) => a) } }];`
    },
    position: [2660, 600]
  },
  output: [{ status: 'ok', updated_at: '2026-10-23T12:00:00Z', articles: [{ id: 'hn-1', title: 'Ejemplo', summary: 'Resumen', url: 'https://example.com', source: 'Hacker News', category: 'LLMs', published_at: '2026-10-23T11:00:00Z', image_url: null }] }]
});

const isWebhookRun = ifElse({
  version: 2.3,
  config: {
    name: 'Called From Webhook?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
        conditions: [{ leftValue: expr("{{ $('GET /webhook/ai-news').isExecuted }}"), rightValue: '', operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [2880, 600]
  }
});

const notes = sticky(
  '## AI News API\nGET /webhook/ai-news devuelve la caché (static data); con ?refresh=1 fuerza un refresco completo antes de responder.\nLos schedules (12h + 30min) refrescan la caché desde HN, HF Papers y RSS.\nSi la caché está vacía, el webhook la rellena en caliente.\nLas noticias nuevas se traducen, resumen y clasifican con Gemini (máx. 40 por refresco); si falla, se sirven sin traducir y se reintenta.',
  [webhookTrigger, readCache, hasCache],
  { color: 4 }
);

export default workflow('ai-news-widget-api', 'AI News Widget API (12h + Real-time)')
  .add(webhookTrigger)
  .to(readCache)
  .to(hasCache
    .onTrue(respond)
    .onFalse(fetchHN))
  .add(every12h)
  .to(fetchHN)
  .add(every30m)
  .to(fetchHN)
  .add(fetchHN)
  .to(fetchHF)
  .to(feedList)
  .to(readRss)
  .to(normalize)
  .to(needsTranslation
    .onTrue(buildRequest.to(translate.to(applyAndCache)))
    .onFalse(applyAndCache))
  .add(applyAndCache)
  .to(isWebhookRun.onTrue(respond))
  .add(notes);
