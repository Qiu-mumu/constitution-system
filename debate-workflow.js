export const meta = {
  name: 'debate',
  description: '多Agent辩论模式 v2.0 — 信息隔离版：每个Agent只看角色相关的知识子集，产生真正的信息差',
  phases: [
    { title: '独立分析', detail: '3个Agent基于不同信息子集并行分析' },
    { title: '交叉审查', detail: '每个Agent审查其他视角的漏洞' },
    { title: '最终决策', detail: '综合所有输入做出最终判断' },
  ],
}

// ============================================================
// 辩论模式 v2.0 重大升级
//
// 核心改进：信息隔离
// - 之前的v1.0所有Agent用同一套知识，说的其实一样
// - v2.0 每个Agent只看与自己角色相关的Memory子集
// - 技术Agent看不到市场相关的记忆，反之亦然
// - 这产生了真正的信息差→真正的分歧→更深度的辩论
//
// 用法与之前相同：
//   Workflow({scriptPath: "debate-workflow.js", args: "问题"})
// ============================================================

const question = typeof args === 'string' ? args : JSON.stringify(args)

if (!question || question === 'undefined') {
  log('❌ 缺少问题！请传入 args 参数')
  throw new Error('Missing question')
}

log(`🎯 辩论主题：${question}`)
log('🧬 启动信息隔离模式 — 每个Agent只看自己知识子集')

// ============================================================
// Phase 1: 独立分析（并行）
// 每个Agent得到不同的"知识子集"，产生真正的信息不对称
// ============================================================
phase('独立分析')

// 每个Agent看到的上下文不同——这才是真正的信息差
const TECH_MEMORY = `
你独有的知识库（其他Agent看不到这些）：
1. 确认偏误教训：设计方案时只找支持性证据忽略反证——必须在评估时主动对抗这种倾向
2. 质量信源分级：GitHub高星项目(Stars>3000+活跃)是特级信源，优先参考现有方案
3. 宪法第十条：先寻再造——任何建造任务前先搜GitHub看有没有现有方案
4. 宪法第零条：验证先于动手，能跑的原型不等于验证
`

const MARKET_MEMORY = `
你独有的知识库（其他Agent看不到这些）：
1. 创始人手册四阶段框架：Idea→MVP→Launch→Scale，混淆阶段是致命错误
2. 创始人手册关键数据：42%创业公司死于做了没人要的东西
3. 范围纪律：AI时代加功能几乎不费力，范围蔓延比以往更容易
4. Sean Ellis测试：>40%用户说非常失望才是真实PMF信号
5. PMF后产品从被推变成被拉，早期traction不等于PMF
`

const RISK_MEMORY = `
你独有的知识库（其他Agent看不到这些）：
1. 沉默盲区教训：看到问题但选择不说——必须把"不想说的"第一个说出来
2. 虚假辩论教训：没有信息差的辩论是伪辩论，必须坚持独立判断
3. 质量信源黑名单：SEO垃圾站、币圈分析、震惊体AI新闻、"AI赚钱"培训课永不学习
4. 宪法第三条：警惕讨好/AI跟着你走——越不想说的越要说
`

const [techView, marketView, riskView] = await parallel([
  () => agent(`
你是一个【技术可行性专家】。你的任务是严格地从技术角度分析以下问题。

你与其他专家的区别：你偏保守、偏务实、只关注"技术上能不能做"。
你不知道市场分析和风险评估的具体内容——你只需要给出技术判断。

${TECH_MEMORY}

问题：${question}

请回答：
1. 技术上是否可行？需要哪些技术栈？
2. 开发周期和工作量估算
3. 技术难点和风险在哪？
4. 有没有现成的开源方案或替代方案？（使用你的GitHub+先寻再造知识）
5. 技术的可维护性和可扩展性如何？
  `, {
    label: '🔧 技术专家（保守派）',
    phase: '独立分析',
    schema: {
      type: 'object',
      properties: {
        feasibility: { type: 'string' },
        techStack: { type: 'array', items: { type: 'string' } },
        devTime: { type: 'string' },
        difficulties: { type: 'array', items: { type: 'string' } },
        existingSolutions: { type: 'array', items: { type: 'string' } },
        riskPoints: { type: 'array', items: { type: 'string' } },
        iDontKnow: { type: 'string', description: '这个角度我无法判断的，诚实说出来' },
      },
      required: ['feasibility', 'difficulties', 'riskPoints'],
    }
  }),

  () => agent(`
你是一个【市场与商业价值专家】。你的任务是严格地从市场和商业角度分析以下问题。

你与其他专家的区别：你偏乐观、偏机会导向、关注"有没有人愿意付钱"。
你不知道技术可行性和风险评估的具体内容——你只需要给出市场判断。

${MARKET_MEMORY}

问题：${question}

请回答：
1. 这个产品的目标用户是谁？有多少人愿意付费？（注意：42%的产品做了没人要——诚实判断）
2. 用户的痛点有多痛？是"不得不买"还是"有了更好"？
3. 市场上已有哪些竞品？它们的定价和用户评价如何？
4. 这个产品的差异化在哪？（如果没有，必须诚实指出）
5. 目前处于哪个阶段？Idea/MVP/Launch/Scale？当前阶段的核心任务是什么？
6. 变现模式？收入预期？

注意：如果你认为没有市场价值，必须说出来！不要为了迎合而编造价值。
  `, {
    label: '📈 市场专家（乐观派）',
    phase: '独立分析',
    schema: {
      type: 'object',
      properties: {
        targetUsers: { type: 'string' },
        painLevel: { type: 'string', enum: ['极痛-不得不买', '中痛-想解决', '轻痛-有了更好'] },
        competitors: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, price: { type: 'string' }, weakness: { type: 'string' } }, required: ['name'] } },
        differentiation: { type: 'string' },
        stage: { type: 'string', enum: ['Idea', 'MVP', 'Launch', 'Scale'] },
        monetization: { type: 'string' },
        revenueEstimate: { type: 'string' },
        hasValue: { type: 'boolean' },
        iDontKnow: { type: 'string', description: '这个角度我无法判断的，诚实说出来' },
      },
      required: ['targetUsers', 'painLevel', 'hasValue', 'stage', 'monetization'],
    }
  }),

  () => agent(`
你是一个【风险与合规专家】。你的任务是严格地从风险和合规角度分析以下问题。

你与其他专家的区别：你是"踩刹车的人"，你的信条是"越不想说的越要说"。
你不知道技术可行性和市场分析的具体内容——你只需要给出风险评估。

${RISK_MEMORY}

问题：${question}

请回答：
1. 法律风险：是否涉及版权、数据安全、不正当竞争、平台ToS违规？
2. 运营风险：是否依赖第三方平台？政策变化怎么办？
3. 技术风险：反爬？封号？API变更？
4. 可持续性：1年后还活着吗？
5. 最坏情况是什么？
6. 我是不是在"讨好"谁而弱化了风险？——检查自己的偏误

注意：你的角色是踩刹车的人。风险太大必须强烈警告！
  `, {
    label: '🛡️ 风险官（怀疑派）',
    phase: '独立分析',
    schema: {
      type: 'object',
      properties: {
        legalRisks: { type: 'array', items: { type: 'string' } },
        operationalRisks: { type: 'array', items: { type: 'string' } },
        techRisks: { type: 'array', items: { type: 'string' } },
        sustainability: { type: 'string' },
        worstCase: { type: 'string' },
        overallRiskLevel: { type: 'string', enum: ['低', '中', '高', '极高'] },
        isViable: { type: 'boolean' },
        blindspotCheck: { type: 'string', description: '我有没有在弱化风险？有没有在讨好？' },
        iDontKnow: { type: 'string', description: '这个角度我无法判断的，诚实说出来' },
      },
      required: ['legalRisks', 'overallRiskLevel', 'isViable', 'blindspotCheck'],
    }
  }),
])

const views = [techView, marketView, riskView].filter(Boolean)
if (views.length < 2) {
  log('❌ 太多Agent分析失败')
  throw new Error('Insufficient views')
}

log(`✅ 信息隔离分析完成：${views.length}个视角，各自基于不同知识子集`)

// ============================================================
// Phase 2: 交叉审查
// 这次审查时，审查者知道被审查者的结论，
// 但审查者仍然站在自己的知识子集上做判断
// ============================================================
phase('交叉审查')

log('💥 交叉审查启动 — 每个Agent用自己的知识子集挑战其他人的结论')

const crossReviews = await parallel([
  techView ? () => agent(`
你是【技术专家】。你基于自己的技术知识库，审查【市场专家】的结论。

市场专家说：
${JSON.stringify(marketView, null, 2)}

你的技术知识库：
${TECH_MEMORY}

从技术角度质疑他：
1. 他的市场方案技术上可行吗？别被他乐观的市场分析说服
2. 他有没有低估技术难度？高估了开发速度？
3. 有没有他没想到的工程实现障碍？
  `, { label: '🔧 → 审市场', phase: '交叉审查' }) : null,

  marketView ? () => agent(`
你是【市场专家】。你基于自己的市场知识库，审查【风险专家】的结论。

风险专家说：
${JSON.stringify(riskView, null, 2)}

你的市场知识库：
${MARKET_MEMORY}

从市场角度质疑他：
1. 他是不是太保守了？有没有因为"踩刹车"而扼杀了真实机会？
2. 这些风险有没有可行的应对方案？
3. 他是否忽略了"不做这件事的机会成本"？
  `, { label: '📈 → 审风险', phase: '交叉审查' }) : null,

  riskView ? () => agent(`
你是【风险专家】。你基于自己的风险知识库，审查【技术专家】的结论。

技术专家说：
${JSON.stringify(techView, null, 2)}

你的风险知识库：
${RISK_MEMORY}

从风险角度质疑他：
1. 他的技术方案隐藏了什么安全/合规隐患？
2. 第三方依赖风险？维护风险？万一核心库作者不维护了？
3. 他是不是因为"技术上能做"就忽略了"应不应该做"？
  `, { label: '🛡️ → 审技术', phase: '交叉审查' }) : null,
].filter(Boolean))

log(`✅ 交叉审查完成`)

// ============================================================
// Phase 3: 最终决策
// 决策者综合所有信息——但决策者能看到辩论中的"我不知道"区域
// ============================================================
phase('最终决策')

const decision = await agent(`
你是一个【决策合成专家】。你综合三个有信息差的专家的判断，做出最终决策。

关键优势：你能看到每个专家标注了"我不知道"的领域——那是他们的盲区。

=== 原始问题 ===
${question}

=== 技术专家（基于技术知识子集） ===
${JSON.stringify(techView, null, 2)}

=== 市场专家（基于市场知识子集） ===
${JSON.stringify(marketView, null, 2)}

=== 风险专家（基于风险知识子集） ===
${JSON.stringify(riskView, null, 2)}

=== 交叉审查意见 ===
${crossReviews.map((r, i) => `【审查${i+1}】\n${r}`).join('\n\n')}

请做出最终判断：

🧠 【各方观点】
- 他们的核心共识在哪？
- 他们的核心分歧在哪？
- 谁"不知道"什么？

💥 【关键洞见】
- 信息差暴露了什么？
- 某个人知道但另一个人不知道的关键信息是什么？

🎯 【最终结论】
建议：做/不做/有条件地做
置信度：高/中/低
还需什么信息才能更确定？
  `, {
    label: '⚖️ 决策合成',
    phase: '最终决策',
    schema: {
      type: 'object',
      properties: {
        consensus: { type: 'string' },
        disagreement: { type: 'string' },
        infoGapInsight: { type: 'string', description: '信息差暴露了什么关键洞见' },
        recommendation: { type: 'string', enum: ['做', '不做', '有条件地做'] },
        firstStep: { type: 'string' },
        confidence: { type: 'string', enum: ['高', '中', '低'] },
        missingInfo: { type: 'string' },
      },
      required: ['recommendation', 'confidence', 'firstStep'],
    }
  })

log(`🎉 信息隔离辩论完成！结论：${decision.recommendation}（${decision.confidence}）`)

return {
  question,
  decision,
  infoGap: decision.infoGapInsight,
  rawViews: { tech: techView, market: marketView, risk: riskView },
  crossReviews,
}
