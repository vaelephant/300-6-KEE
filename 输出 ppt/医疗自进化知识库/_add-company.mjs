import fs from 'node:fs';

const TOTAL = 18;
const desc = 'style="font-size:max(16px,.9vw)"';

const company = `<!-- 02 · S11 Horizontal Timeline · company -->
<section class="slide" data-layout="S11" data-animate="timeline-walk">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">公司介绍 · About Us</div>
      <div class="r">02 / ${TOTAL}</div>
    </div>
    <div data-anim="line" style="display:flex;flex-direction:column;gap:1.4vh">
      <div class="t-meta">Since 2017</div>
      <h2 style="font-family:var(--sans),var(--sans-zh);font-weight:200;font-size:min(5.2vw,9.2vh);line-height:1.05;letter-spacing:-.03em">2017 年起，深耕<span style="color:var(--accent)">人工智能</span></h2>
    </div>
    <div class="timeline-h">
      <div class="tl-row">
        <div class="th-node up"><span class="dot"></span><div class="label"><span class="yr">2017</span><span class="name">起步人工智能</span><span class="desc" ${desc}>开始投入人工智能技术研发</span></div></div>
        <div class="th-node down"><span class="dot"></span><div class="label"><span class="yr">基座 01</span><span class="name">数据基座</span><span class="desc" ${desc}>打通业务场景与诊疗流程，沉淀标准化医疗数据集</span></div></div>
        <div class="th-node up"><span class="dot"></span><div class="label"><span class="yr">基座 02</span><span class="name">模型基座</span><span class="desc" ${desc}>多模态医疗大模型 + 轻量化、专用模型按需调度</span></div></div>
        <div class="th-node down"><span class="dot"></span><div class="label"><span class="yr">基座 03</span><span class="name">智能体基座</span><span class="desc" ${desc}>AI 应用全生命周期一站式管控</span></div></div>
        <div class="th-node up accent"><span class="dot"></span><div class="label"><span class="yr">今天</span><span class="name">知识进化引擎</span><span class="desc" ${desc}>让医学知识自己进化</span></div></div>
      </div>
    </div>
    <div class="t-meta nav-safe-bottom-tight" style="border-top:1px solid var(--grey-2);padding-top:1.6vh">从人工智能技术积累，到医疗 AI 体系化底盘，再到可自进化的医学知识</div>
  </div>
</section>

`;

const card = (n, cat, title, body) => `        <div class="card-fill" style="display:grid;grid-template-columns:min(7vw,12vh) 1fr;gap:2vw;align-items:center;padding:2.4vh 2vw">
          <div style="font-family:var(--sans);font-weight:200;font-size:min(6vw,10.4vh);line-height:1;color:var(--accent);letter-spacing:-.04em">${n}</div>
          <div style="display:flex;flex-direction:column;gap:.8vh"><span class="t-cat">${cat}</span><h3 class="t-h-prod">${title}</h3><p class="t-body-sm">${body}</p></div>
        </div>`;

const product = `<!-- 03 · S13 Three Forces · DrSeek product -->
<section class="slide" data-layout="S13" data-animate="three-forces">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">产品介绍 · DrSeek</div>
      <div class="r">03 / ${TOTAL}</div>
    </div>
    <div data-anim="up" style="flex:1;display:grid;grid-template-columns:5fr 11fr;gap:1.4vw;padding-bottom:var(--nav-safe-bottom);min-height:0">
      <div class="card-ink" style="position:relative;overflow:hidden;padding:4vh 2.4vw;display:flex;flex-direction:column;justify-content:space-between;gap:2.4vh">
        <span class="dot-mat" aria-hidden="true" style="position:absolute;right:-2vw;top:-2vw;width:12vw;height:12vw;color:rgba(255,255,255,.35)"></span>
        <div style="position:relative;display:flex;flex-direction:column;gap:1.6vh">
          <span class="t-cat">DrSeek · 医疗 AI 能力底盘</span>
          <p class="t-body" style="color:rgba(255,255,255,.86);max-width:20ch">医疗智能化升级，破局关键在于体系化建设。</p>
        </div>
        <h2 style="position:relative;font-family:var(--sans),var(--sans-zh);font-weight:200;font-size:min(4.6vw,8.2vh);line-height:1.08;letter-spacing:-.03em;color:var(--paper)">三大<br/><span style="color:var(--accent-bright)">技术基座</span></h2>
        <div style="position:relative;display:flex;flex-direction:column;gap:1vh;border-top:1px solid rgba(255,255,255,.22);padding-top:1.8vh">
          <span class="t-cat">核心价值</span>
          <p class="t-body-sm" style="color:rgba(255,255,255,.78)">依托统一基座能力，单点场景验证落地后，其他业务场景无需重复建设，快速复制、规模化复用。</p>
        </div>
      </div>
      <div style="display:grid;grid-template-rows:repeat(3,1fr);gap:1.4vw;min-height:0">
${card('01', 'Data Foundation', '数据基座', '打通全业务场景与诊疗流程，沉淀标准化、高质量医疗数据集，为大模型持续迭代供给可靠数据资产。')}
${card('02', 'Model Foundation', '模型基座', '以多模态医疗大模型为核心，拒绝单模型通吃全场景：依据业务需求灵活选配蒸馏量化的轻量化小模型与专用深度学习模型，按需调度，兼顾业务效果与算力成本。')}
${card('03', 'Agent Foundation', '智能体基座', '一站式管控 AI 应用从研发、测评、发布、运维监控到持续优化的全生命周期。')}
      </div>
    </div>
  </div>
</section>

`;

let h = fs.readFileSync('index.html', 'utf8');

h = h.replace(/(\d\d) \/ 16</g, (m, n) => {
  const k = Number(n);
  return `${String(k === 1 ? 1 : k + 2).padStart(2, '0')} / ${TOTAL}<`;
});
h = h.replace(/<!-- (\d\d) · /g, (m, n) => {
  const k = Number(n);
  return `<!-- ${String(k === 1 ? 1 : k + 2).padStart(2, '0')} · `;
});

const anchor = '<!-- 04 · S03 Split Statement -->';
if (!h.includes(anchor)) throw new Error('anchor missing');
h = h.replace(anchor, company + product + anchor);
fs.writeFileSync('index.html', h);
