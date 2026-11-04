import fs from 'node:fs';

const cols = [
  ['向量 RAG 知识库', 'Dify · RAGFlow 等'],
  ['图增强 RAG', 'GraphRAG · LightRAG'],
  ['时态知识图谱', 'Zep · Graphiti'],
  ['人工医学图谱', '专家构建 + 图数据库'],
  ['KEE', '知识进化引擎'],
];
const rows = [
  ['逐句引证', '每条事实定位到原句', [['p','分块级引用'],['p','文本单元级'],['p','片段级溯源'],['p','视录入规范'],['f','原句 + 字符偏移']]],
  ['双时态', '何时为真 · 何时相信', [['n','无'],['n','无'],['f','有效期 + 记录时间'],['n','版本快照'],['f','双轴 + 精度分级']]],
  ['本体可演进', '改本体不必重抽', [['n','无显式本体'],['n','无显式本体'],['p','自定义实体类型'],['n','改模式成本高'],['f','按签名增量重算']]],
  ['冲突治理', '检测 → 裁决 → 队列', [['n','新旧混合召回'],['n','摘要合并'],['p','自动失效旧边'],['p','专家人工比对'],['f','检测 + Agent + 队列']]],
  ['人工审核留痕', '决策可回放、可撤销', [['n','可改分块'],['n','无'],['n','无'],['f','全人工'],['f','审核队列 + 决策账本']]],
  ['院内私有化', '部署与运维负担', [['p','多组件自托管'],['p','库 + 外部存储'],['p','需图数据库'],['f','可本地部署'],['f','单服务 + Postgres']]],
];

const cell = (mk, txt, accent) => accent
  ? `<div class="cmp-cell card-accent"><i class="cmp-mk ${mk}"></i><span>${txt}</span></div>`
  : `<div class="cmp-cell card-fill${mk === 'n' ? ' is-n' : ''}"><i class="cmp-mk ${mk}"></i><span>${txt}</span></div>`;

const head = [
  `<div class="cmp-cell cmp-head"><span class="t-meta">能力 \\ 方案</span></div>`,
  ...cols.map(([n, s], i) => i === 4
    ? `<div class="cmp-cell cmp-head card-accent"><b style="color:var(--accent-on)">${n}</b><span class="t-meta" style="color:rgba(255,255,255,.72)">${s}</span></div>`
    : `<div class="cmp-cell cmp-head card-fill"><b>${n}</b><span class="t-meta">${s}</span></div>`),
];
const body = rows.flatMap(([t, s, cs]) => [
  `<div class="cmp-cell cmp-row"><b>${t}</b><span class="t-meta">${s}</span></div>`,
  ...cs.map(([mk, txt], i) => cell(mk, txt, i === 4)),
]);

const slide = `<!-- 14 · S15 Matrix + Hero Stat · peer comparison -->
<section class="slide" data-layout="S15" data-animate="matrix-fill">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">医疗自进化知识库 · Landscape</div>
      <div class="r">14 / 16</div>
    </div>
    <div data-anim="line" style="display:flex;flex-direction:column;gap:1.2vh">
      <div class="t-meta">Peer Comparison</div>
      <h2 style="font-family:var(--sans),var(--sans-zh);font-weight:200;font-size:min(4.8vw,8.4vh);line-height:1;letter-spacing:-.03em">和同行比，差在「可信」这一层</h2>
    </div>
    <div data-anim="up" class="cmp-grid" style="flex:1;margin-top:3.6vh">
      ${[...head, ...body].join('\n      ')}
    </div>
    <div data-anim="up" style="display:flex;justify-content:space-between;align-items:flex-end;gap:4vw;margin-top:2.6vh;padding-bottom:var(--nav-safe-bottom)">
      <div style="display:flex;align-items:flex-end;gap:1.6vw">
        <div class="t-meta" style="order:2;max-width:22ch;line-height:1.6;padding-bottom:1vh">KEE 在六项医疗刚需上<br/>全部原生支持</div>
        <div style="order:1;font-family:var(--sans);font-weight:200;font-size:min(6.4vw,10vh);line-height:.9;letter-spacing:-.04em;color:var(--accent)">6/6</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:1vh">
        <div class="t-meta" style="display:flex;gap:1.6vw;align-items:center">
          <span style="display:flex;gap:.5vw;align-items:center"><i class="cmp-mk f"></i>原生支持</span>
          <span style="display:flex;gap:.5vw;align-items:center"><i class="cmp-mk p"></i>部分 / 需二次开发</span>
          <span style="display:flex;gap:.5vw;align-items:center"><i class="cmp-mk n"></i>不支持</span>
        </div>
        <div class="t-meta" style="color:var(--text-secondary);text-transform:none;letter-spacing:.04em">按方案类别比较，依据各项目公开文档与论文（截至 2026.09），不代表具体版本的全部能力</div>
      </div>
    </div>
  </div>
</section>

`;

let h = fs.readFileSync('index.html', 'utf8');
const anchor = '<!-- 14 · S20 Stacked KPI Ledger · dark -->';
if (!h.includes(anchor)) throw new Error('anchor missing');
h = h.replace('<div class="r">14 / 15</div>', '<div class="r">15 / 16</div>')
     .replace('<div class="l">15 / 15</div>', '<div class="l">16 / 16</div>')
     .replace('<!-- 14 · S20 Stacked KPI Ledger · dark -->', '<!-- 15 · S20 Stacked KPI Ledger · dark -->')
     .replace('<!-- 15 · SWISS-CLOSING-ASCII -->', '<!-- 16 · SWISS-CLOSING-ASCII -->')
     .replace(/(\d\d) \/ 15</g, '$1 / 16<');
h = h.replace('<!-- 15 · S20 Stacked KPI Ledger · dark -->', slide + '<!-- 15 · S20 Stacked KPI Ledger · dark -->');
fs.writeFileSync('index.html', h);
