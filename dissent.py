#!/usr/bin/env python3
"""
🧪 异议引擎 Dissent Engine v1.0
===============================
用法: python debate.py "xxx" --output json | python dissent.py
      python dissent.py "某段文本"
      python dissent.py < output.json

自动检查输出中的5类问题：
  C1: 自相矛盾
  C2: 过度自信(无证据的确定性声明)
  C3: 信心超过证据强度
  C4: 忽略冲突信息
  C5: 过度简化
"""

import sys, re, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ============================================================
# 信号词库
# ============================================================

# 过度自信信号（确定性断言，没有证据支撑）
OVERCONFIDENCE_PATTERNS = [
    r"毫无疑问",
    r"一定是",
    r"必然",
    r"绝对[不]?会",
    r"100%",
    r"肯定[不]?是",
    r"完全可以确定",
    r"不可能[有]?别的",
    r"唯一[的]?[办法途径方案]",
    r"百分之百",
    r"永远[不]?会",
    r"所有[的]?[情况场景]",
    r"从不",
    r"总是",
    r"肯定地说",
    r"毫无疑问地",
    r"definitely",
    r"absolutely",
    r"certainly",
    r"undoubtedly",
    r"without [a]? doubt",
    r"no question",
    r"must be",
    r"never",
    r"always",
]

# 证据薄弱信号（说了很多但没实质内容）
WEAK_EVIDENCE_PATTERNS = [
    r"众所周知",
    r"大家都[知道认同]",
    r"普遍认为",
    r"很[明显显然]",
    r"不用说",
    r"明眼人[都]?[知道看出]",
    r"业界[普遍公认]?",
    r"根据[经验常识]",
    r"as we all know",
    r"it is obvious",
    r"clearly",
    r"of course",
    r"naturally",
]

# 讨好信号
FLATTERY_PATTERNS = [
    r"你说得对",
    r"你[的]?想法[很非常]?好",
    r"这个[问题想法]?很[好棒精彩]",
    r"你[的]?[观察判断]?很[对准确]",
    r"good [pointquestion]",
    r"great [questionidea]",
    r"excellent [pointobservation]",
    r"you're [rightcorrect]",
    r"that's a [great excellent]",
]

# 矛盾检测信号（转折词 + 肯定/否定对）
CONTRADICTION_MARKERS = [
    (r"但是|然而|不过|可是|但", r"一定|肯定|绝对|必然"),  # 但是...肯定
    (r"从[^。]*来看[，,]", r"然而|但是"),  # 从X来看...然而
    (r"[^。]*[是的确][^。]*，", r"但是[^。]*不[^。]*"),  # 是X...但是不Y
]

# 过度简化的信号
OVERSIMPLIFICATION_PATTERNS = [
    r"[只就]需要[做搞弄]?[一两]步",
    r"[很非]?简单",
    r"轻松[实现搞定解决]",
    r"几分钟[就]?能[做好搞定]",
    r"没有[什么]?难度",
    r"轻而易举",
    r"easy",
    r"trivial",
    r"just [do add use]",
    r"simple [matter solution]",
    r"no [big real]? problem",
]


# ============================================================
# 检测函数
# ============================================================

def check_overconfidence(text):
    hits = []
    for pat in OVERCONFIDENCE_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            if m not in hits:
                hits.append(m)
    return hits

def check_weak_evidence(text):
    hits = []
    for pat in WEAK_EVIDENCE_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            if m not in hits:
                hits.append(m)
    return hits

def check_flattery(text):
    hits = []
    for pat in FLATTERY_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            if m not in hits:
                hits.append(m)
    return hits

def check_contradiction(text):
    """C1: 检测自相矛盾"""
    # 简单检测：找"肯定"和"但"同时出现的段落
    paragraphs = text.split("\n")
    contradictions = []
    for para in paragraphs:
        para_lower = para.lower()
        # 同段落内出现相反立场
        has_positive = any(w in para_lower for w in ["肯定", "一定", "必然", "绝对"])
        has_negative = any(w in para_lower for w in ["但是", "然而", "不过", "但", "风险", "问题在于", "不足"])
        if has_positive and has_negative:
            contradictions.append(f"段落内出现肯定+转折: {para[:80]}...")
    return contradictions

def check_oversimplification(text):
    """C5: 检测过度简化"""
    hits = []
    for pat in OVERSIMPLIFICATION_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            if m not in hits:
                hits.append(m)
    return hits


def analyze(text, source_label="output"):
    """完整分析一段文本，返回报告"""
    issues = []

    # C1: 自相矛盾
    c1 = check_contradiction(text)
    if c1:
        issues.append({
            "id": "C1",
            "title": "自相矛盾",
            "severity": "🔴",
            "detail": c1[0],
            "count": len(c1),
        })

    # C2: 过度自信
    c2 = check_overconfidence(text)
    if c2:
        c2_display = " | ".join(c2[:5])
        severity = "🔴" if len(c2) >= 3 else "🟡"
        issues.append({
            "id": "C2",
            "title": "过度自信（无证据的确定性声明）",
            "severity": severity,
            "detail": f"发现 {len(c2)} 处过度自信信号: {c2_display}",
            "count": len(c2),
        })

    # C3: 证据薄弱
    c3 = check_weak_evidence(text)
    if c3:
        c3_display = " | ".join(c3[:5])
        issues.append({
            "id": "C3",
            "title": "证据薄弱（用常识代替论证）",
            "severity": "🟡",
            "detail": f"发现 {len(c3)} 处证据薄弱信号: {c3_display}",
            "count": len(c3),
        })

    # C4: 讨好
    c4 = check_flattery(text)
    if c4:
        c4_display = " | ".join(c4[:5])
        issues.append({
            "id": "C4",
            "title": "可能讨好（AI渴望被点赞）",
            "severity": "🟡",
            "detail": f"发现 {len(c4)} 处讨好信号: {c4_display}",
            "count": len(c4),
        })

    # C5: 过度简化
    c5 = check_oversimplification(text)
    if c5:
        c5_display = " | ".join(c5[:5])
        issues.append({
            "id": "C5",
            "title": "过度简化（复杂问题被轻描淡写）",
            "severity": "🟡",
            "detail": f"发现 {len(c5)} 处简化信号: {c5_display}",
            "count": len(c5),
        })

    # 综合评分
    total_issues = len(issues)
    total_signals = sum(i["count"] for i in issues)
    if total_issues == 0:
        overall = {"grade": "A", "label": "通过 - 无明显异议", "score": 95}
    elif total_issues <= 2 and total_signals <= 5:
        overall = {"grade": "B", "label": "基本通过 - 少量异议信号", "score": 80}
    elif total_issues <= 4 and total_signals <= 10:
        overall = {"grade": "C", "label": "建议修改 - 较多异议信号", "score": 65}
    else:
        overall = {"grade": "D", "label": "需大幅修改 - 大量异议信号", "score": 45}

    return {
        "source": source_label,
        "overall": overall,
        "issues": issues,
        "total_signals": total_signals,
    }


def main():
    # 读取输入：优先 argv（参数），其次 stdin（管道）
    args = sys.argv[1:]

    if args:
        text = " ".join(args)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("用法: python debate.py 'xxx' --output json | python dissent.py")
        print("      python dissent.py '某段文本'")
        sys.exit(1)

    # 如果是 JSON（来自 debate.py --output json），提取 decision 字段
    if text.strip().startswith("{"):
        try:
            data = json.loads(text)
            if "decision" in data:
                text = data["decision"]
            elif "error" in data:
                print(f"[异议引擎] 输入包含错误: {data['error']}")
                sys.exit(0)
        except json.JSONDecodeError:
            pass

    result = analyze(text)

    sep = "=" * 50
    print("")
    print(sep)
    print("异议引擎报告")
    print(sep)
    print("来源: " + result["source"])
    g = result["overall"]
    print("综合评级: " + g["grade"] + " - " + g["label"] + " (" + str(g["score"]) + "/100)")
    print("总信号数: " + str(result["total_signals"]))
    print(sep)

    if result["issues"]:
        for iss in result["issues"]:
            print("")
            print("  " + iss["severity"] + " " + iss["id"] + ": " + iss["title"])
            print("    " + iss["detail"])
    else:
        print("")
        print("  未检测到异议信号")

    print("")
    print(sep)
if __name__ == "__main__":
    main()
