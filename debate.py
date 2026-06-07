#!/usr/bin/env python3
"""
🧬 信息隔离辩论引擎 v3.0
=======================
用法：python debate.py "你的问题"
      python debate.py "你的问题" --models all    (3个agent用不同视角)
      python debate.py "你的问题" --quick          (只用2个agent，更快)
      python debate.py "你的问题" --output json    (JSON格式输出)

无需解释，直接跑。每个agent独立API调用，互不知道对方的知识。
"""

import requests
import json
import sys
import time
import os
import hashlib
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Windows GBK 兼容 - 确保emoji能正常输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ============================================================
# 配置
# ============================================================
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")  # 必须设置环境变量，小心密钥泄露
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
MODEL = os.environ.get("ANTHROPIC_MODEL", "DeepSeek-V4-flash")
TIMEOUT = 180

# ============================================================
# 缓存系统（避免重复辩论同一话题）
# ============================================================
CACHE_DIR = os.path.expanduser("~/.claude/cache")
FINGERPRINT_DIR = os.path.join(CACHE_DIR, "fingerprint")
CACHE_TTL_DAYS = 7

def _ensure_cache_dirs():
    for d in [CACHE_DIR, FINGERPRINT_DIR]:
        os.makedirs(d, exist_ok=True)

def _fingerprint(question):
    norm = question.strip().lower()
    return hashlib.sha256(norm.encode()).hexdigest()[:16]

def cache_lookup(question):
    _ensure_cache_dirs()
    fp = _fingerprint(question)
    cache_file = os.path.join(FINGERPRINT_DIR, f"{fp}.json")
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        ct = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - ct > timedelta(days=CACHE_TTL_DAYS):
            return None
        return data
    except: return None

def cache_store(question, mode, phase1, decision):
    _ensure_cache_dirs()
    fp = _fingerprint(question)
    data = dict(question=question, fingerprint=fp,
        cached_at=datetime.now().isoformat(),
        expires_at=(datetime.now() + timedelta(days=CACHE_TTL_DAYS)).isoformat(),
        mode=mode,
        phase1={aid:{"ok":v.get("ok"),"time":v.get("time")} for aid,v in phase1.items()},
        decision_preview=decision[:200] if decision else "")
    with open(os.path.join(FINGERPRINT_DIR, f"{fp}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 成本日志
# ============================================================
COST_LOG = os.path.expanduser("~/.claude/COST_LOG.md")
_cost_calls = 0
_cost_tokens = 0
_COST_PER_TOKEN = 0.00000015

def cost_reset():
    global _cost_calls, _cost_tokens
    _cost_calls = 0; _cost_tokens = 0

def cost_add(calls=1, tokens=0):
    global _cost_calls, _cost_tokens
    _cost_calls += calls; _cost_tokens += tokens

def cost_log(question, mode, ok=True):
    ok_flag = "OK" if ok else "FAIL"
    date_str = datetime.now().strftime("%m-%d")
    est_cost = _cost_tokens * _COST_PER_TOKEN
    line = '| ' + date_str + ' | ' + question[:30] + ' | ' + mode + ' | ' + str(_cost_calls) + '次 | ' + ok_flag + ' | ~$' + f'{est_cost:.4f}' + ' |\n'
    try:
        with open(COST_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except: pass

# ============================================================
# Agent 知识库（信息隔离 — 每个agent只能看到自己的）
# ============================================================

AGENTS = {
    "tech": {
        "name": "🔧 技术专家（保守派）",
        "memory": """
你独有的知识库（其他Agent看不到这些）：
1. 先寻再造：任何建造任务前先搜GitHub看有没有现有方案
2. 验证先于动手：能跑的原型不等于验证，42%死于做了没人要
3. 质量信源分级：GitHub高星(>3k+活跃)是特级，官方文档一级
4. 你的角色使命：偏保守、务实、只关注"技术上能不能做"
5. 不知道就说不知道，不要编造技术判断
""",
        "prompt_template": """你是一个【技术可行性专家】。你的任务是严格地从技术角度分析问题。

你与其他专家的区别：你只关注技术可行性，不知道市场分析和风险评估的内容。
你不知道其他专家看到了什么信息——你只需要给出技术判断。

{memory}

问题：{question}

请从以下技术角度分析：
1. 技术上是否可行？需要哪些技术栈？
2. 开发周期和工作量估算
3. 技术难点和风险在哪？
4. 有没有现成的开源方案或替代方案？
5. 可维护性和可扩展性如何？

注意：不知道就说不确定，不要编造！"""
    },

    "market": {
        "name": "📈 市场专家（乐观派）",
        "memory": """
你独有的知识库（其他Agent看不到这些）：
1. 四阶段框架：Idea→MVP→Launch→Scale，混淆阶段是致命错误
2. 42%创业公司死于做了没人要的东西
3. PMF信号：>40%用户说非常失望才是真实PMF
4. AI时代加功能几乎不费力，范围蔓延比以前更容易
5. 你的角色使命：偏机会导向、关注"有没有人愿意付钱"
6. 如果产品没有真实价值，必须诚实说出来
""",
        "prompt_template": """你是一个【市场与商业价值专家】。你的任务是严格地从市场和商业角度分析问题。

你与其他专家的区别：你偏乐观、偏机会导向，不知道技术可行性和风险评估的具体内容。
你不知道其他专家看到了什么信息——你只需要给出市场判断。

{memory}

问题：{question}

请从以下市场角度分析：
1. 目标用户是谁？有多少人愿意付费？
2. 痛点有多痛？（不得不买/想解决/有了更好）
3. 现有竞品？它们的定价和弱点？
4. 差异化在哪？如果没有必须诚实指出
5. 目前处于Idea/MVP/Launch/Scale哪个阶段？
6. 变现模式？收入预期？

注意：如果没有市场价值，必须直接说出来！不要为了迎合编造价值。"""
    },

    "risk": {
        "name": "🛡️ 风险官（怀疑派）",
        "memory": """
你独有的知识库（其他Agent看不到这些）：
1. 沉默盲区：看到问题但选择不说——必须把"不想说的"第一个说出来
2. 虚假辩论：没有信息差的辩论是伪辩论，必须坚持独立判断
3. 信源黑名单：SEO垃圾站、币圈分析、震惊体AI新闻、"AI赚钱"培训课
4. 警惕讨好：越不想说的越要说，确认偏误配上引擎最危险
5. 你的角色使命：你是"踩刹车的人"，整体偏保守
""",
        "prompt_template": """你是一个【风险与合规专家】。你的任务是严格地从风险和合规角度分析问题。

你与其他专家的区别：你是"踩刹车的人"，不知道技术可行性和市场分析的具体内容。
你不知道其他专家看到了什么信息——你只需要给出风险评估。

{memory}

问题：{question}

请从以下风险角度分析：
1. 法律风险：版权、数据安全、平台ToS违规？
2. 运营风险：依赖第三方？政策变化？
3. 技术风险：反爬？封号？API变更？
4. 可持续性：1年后还活着吗？
5. 最坏情况是什么？
6. 我有没有在讨好谁而弱化了风险？——检查自己的偏误

注意：你的角色是踩刹车的人。风险太大必须强烈警告！"""
    },

    "synthesis": {
        "name": "⚖️ 决策合成",
        "memory": "",
        "prompt_template": """你是一个【决策合成专家】。你综合三个有信息差的专家的判断，做出最终决策。

关键优势：你能看到每个专家标注了"我不知道"的领域——那是他们的盲区。

=== 原始问题 ===
{question}

=== 技术专家 ===
{tech_view}

=== 市场专家 ===
{market_view}

=== 风险专家 ===
{risk_view}

请做出最终判断：

🧠 各方观点
- 核心共识在哪？
- 核心分歧在哪？
- 谁"不知道"什么？

💥 关键洞见
- 信息差暴露了什么？
- 某个人知道但另一个人不知道的关键信息是什么？

🎯 最终结论
- 建议：做 / 不做 / 有条件地做
- 置信度：高 / 中 / 低
- 第一步做什么？
- 还需什么信息才能更确定？"""
    }
}


# ============================================================
# API 调用
# ============================================================

def call_api(system_prompt, user_message, max_tokens=4096, timeout=None):
    cost_add(calls=1, tokens=max_tokens)
    """直接调用 DeepSeek/Anthropic API，完全控制参数"""
    messages = [
        {"role": "user", "content": f"{system_prompt}\n\n{user_message}"}
    ]
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    try:
        start = time.time()
        actual_timeout = timeout if timeout is not None else TIMEOUT
        resp = requests.post(
            f"{BASE_URL}/messages",
            json=payload,
            headers=headers,
            timeout=actual_timeout
        )
        elapsed = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            return {"ok": True, "text": text, "time": f"{elapsed:.1f}s"}
        else:
            err = resp.text[:300]
            return {"ok": False, "error": f"HTTP {resp.status_code}: {err}", "time": f"{elapsed:.1f}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "time": "err"}


# ============================================================
# 主辩论逻辑
# ============================================================

def run_debate(question, quick=False, output_format="text", frugal=False):
    results = {}
    mt = 2048 if frugal else 4096
    cost_reset()

    # ---- 缓存检查：同一话题7天内不复辩 ----
    cached = cache_lookup(question)
    if cached and output_format == "json":
        cached["cached"] = True
        cached["mode"] = f"{'quick' if quick else 'full'} (cached)"
        cached["timestamp"] = datetime.now().isoformat()
        print(json.dumps(cached, ensure_ascii=False, indent=2))
        return

    # ---- Phase 1: 独立分析 ----
    phase1_agents = ["tech", "market"]
    if not quick:
        phase1_agents.append("risk")

    print(f"\n{'='*60}")
    print(f"🧬 信息隔离辩论 v3.0")
    print(f"📋 议题：{question}")
    print(f"🔒 模式：{'快速（2 Agent）' if quick else '完整（3 Agent + 交叉审查）'}")
    print(f"{'='*60}\n")

    print(f"▶ Phase 1：独立分析（信息隔离）")
    print(f"   每个Agent拥有不同的知识子集，互不知道对方的信息\n")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for agent_id in phase1_agents:
            agent = AGENTS[agent_id]
            prompt = agent["prompt_template"].format(memory=agent["memory"], question=question)
            future = executor.submit(call_api, prompt, "请给出你的分析。", max_tokens=mt)
            futures[future] = agent_id

        for future in as_completed(futures):
            agent_id = futures[future]
            result = future.result()
            results[agent_id] = result
            status = "✅" if result["ok"] else "❌"
            print(f"   {status} {AGENTS[agent_id]['name']} - {result.get('time', '?')}")

    # 打印失败情况
    failures = [id for id in phase1_agents if not results.get(id, {}).get("ok")]
    if failures:
        for agent_id in failures:
            print(f"\n  ❌ {AGENTS[agent_id]['name']} 失败：{results[agent_id].get('error', 'unknown')}")
        if len(failures) >= 2:
            print("\n  ⚠️ 太多agent失败，无法继续")
            return

    if output_format == "text" and not quick and not frugal:
        for agent_id in phase1_agents:
            if results.get(agent_id, {}).get("ok"):
                print(f"\n{'-'*50}")
                print(f"  {AGENTS[agent_id]['name']}")
                print(f"{'-'*50}")
                print(results[agent_id]["text"][:2000])
                if len(results[agent_id]["text"]) > 2000:
                    print(f"\n  ...(截断，共{len(results[agent_id]['text'])}字)")

    # ---- Phase 2: 交叉审查（仅完整模式） ----
    if not quick and len(phase1_agents) >= 3:
        print(f"\n\n▶ Phase 2：交叉审查")
        print(f"   每个Agent用自己的知识挑战其他人的结论\n")

        reviews = []

        # 交叉审查配置：审查者→审查目标→审查角度
        cross_reviews = [
            ("tech", "market", "🔧", "从技术角度质疑他",
             "1. 他的方案技术上可行吗？\n2. 有没有低估技术难度？\n3. 有没有他没想的工程障碍？"),
            ("market", "risk", "📈", "从市场角度质疑他",
             "1. 他是不是太保守了？\n2. 风险有没有可行应对方案？\n3. 是否忽视了机会成本？"),
            ("risk", "tech", "🛡️", "从风险角度质疑他",
             "1. 他的方案隐藏了什么安全/合规隐患？\n2. 第三方依赖风险？\n3. 他是不是因为'技术上能做'就忽略了'应不应该做'？"),
        ]

        for reviewer, target, icon, angle, questions in cross_reviews:
            reviewer_name = AGENTS[reviewer]["name"].split("（")[0]
            target_name = AGENTS[target]["name"].split("（")[0]
            if results.get(reviewer, {}).get("ok") and results.get(target, {}).get("ok"):
                prompt = AGENTS[reviewer]["prompt_template"].format(
                    memory=AGENTS[reviewer]["memory"],
                    question=f"审查【{target_name}】的结论，{angle}：\n\n{target_name}说：\n{results[target]['text'][:2000]}\n\n审查框架：\n{questions}"
                )
                r = call_api(prompt, "请给出审查意见。", max_tokens=mt)
                label = f"{icon} {reviewer_name}→审{target_name}"
                reviews.append((label, r))
                print(f"   {'✅' if r['ok'] else '❌'} {label} - {r.get('time', '?')}")

        if output_format == "text":
            for name, r in reviews:
                if r.get("ok"):
                    print(f"\n  {name}")
                    print(f"  {r['text'][:1000]}")

    # ---- Phase 3: 最终决策 ----
    print(f"\n\n▶ Phase 3：最终决策")
    print(f"   综合所有视角...\n")

    tech_text = results.get("tech", {}).get("text", "（无数据）")
    market_text = results.get("market", {}).get("text", "（无数据）")
    risk_text = results.get("risk", {}).get("text", "（无数据）")

    prompt = AGENTS["synthesis"]["prompt_template"].format(
        question=question,
        tech_view=tech_text[:1200],
        market_view=market_text[:1200],
        risk_view=risk_text[:1200]
    )
    final = call_api(prompt, "请综合所有视角做出最终决策。", max_tokens=mt, timeout=300)

    # 写入缓存
    final_text = final.get("text", "") if final["ok"] else ""
    cost_log(question, "quick" if quick else "full", final["ok"])
    cache_store(question, "quick" if quick else "full", results, final_text)

    if output_format == "json":
        output = {
            "question": question,
            "mode": "quick" if quick else "full",
            "timestamp": datetime.now().isoformat(),
            "phase1": {aid: {"ok": results.get(aid, {}).get("ok"), "time": results.get(aid, {}).get("time")} for aid in phase1_agents},
            "phase3": {"ok": final["ok"], "time": final.get("time")},
            "decision": final.get("text", final.get("error", "")) if final["ok"] else None,
            "error": final.get("error") if not final["ok"] else None,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if final["ok"]:
            print(f"{'='*60}")
            print(f"🎯 最终决策")
            print(f"{'='*60}")
            print(final["text"][:4000])
            print(f"\n{'='*60}")
            print(f"✅ 辩论完成 | {final.get('time', '?')}")
        else:
            print(f"❌ 决策失败：{final.get('error', 'unknown')}")


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="信息隔离辩论引擎 v3.0 - 无需解释，直接开辩",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python debate.py "要不要学React Native?"
  python debate.py "这个创业想法靠谱吗?" --quick
  python debate.py "选择哪个云服务?" --output json
  python debate.py "如何优化数据库查询?" --models all
        """
    )
    parser.add_argument("question", nargs="?", help="辩论议题")
    parser.add_argument("--quick", "-q", action="store_true", help="快速模式（2个agent，无交叉审查）")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--models", choices=["all", "quick"], default="all", help="使用的agent数量")
    parser.add_argument("--frugal", "-f", action="store_true", help="省token模式: 精简prompt+低max_tokens")

    args = parser.parse_args()

    question = args.question
    if not question:
        question = input("🧬 辩论议题：")

    quick_mode = args.quick or (args.models == "quick")
    run_debate(question, quick=quick_mode, output_format=args.output, frugal=args.frugal)


if __name__ == "__main__":
    main()
