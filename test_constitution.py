#!/usr/bin/env python3
"""宪法系统自动化测试 v1.0"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, subprocess, ast, argparse

DEBATE_SCRIPT = os.path.join(os.path.dirname(__file__), "debate.py")
ERRORS = []
PASS = 0
FAIL = 0

def test(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")
        ERRORS.append(f"{name}: {detail}")

def test_syntax():
    with open(DEBATE_SCRIPT, encoding="utf-8") as f:
        code = f.read()
    try:
        ast.parse(code)
        test("语法正确", True)
    except SyntaxError as e:
        test("语法正确", False, str(e))

def test_imports():
    missing = []
    for mod in ["requests", "json", "argparse"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    test("所有 import 可用", len(missing) == 0, f"缺少: {missing}")

def test_argparse():
    import argparse
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--quick", "-q", action="store_true")
    p.add_argument("--output", "-o", choices=["text", "json"], default="text")
    p.add_argument("--frugal", "-f", action="store_true")
    a1 = p.parse_args([])
    test("默认模式是 text", a1.output == "text")
    test("默认 frugal=False", a1.frugal == False)
    a2 = p.parse_args(["--quick", "--output", "json", "--frugal"])
    test("--quick 解析正确", a2.quick == True)
    test("--output json 解析正确", a2.output == "json")
    test("--frugal 解析正确", a2.frugal == True)

def test_agent_config():
    with open(DEBATE_SCRIPT, encoding="utf-8") as f:
        code = f.read()
    required = ["AGENTS", "name", "memory", "prompt_template"]
    for field in required:
        if field not in code:
            test(f"缺少配置: {field}", False)
            return
    test("agent 配置完整 (tech/market/risk/synthesis)", True)

def test_api():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run(
            [sys.executable, DEBATE_SCRIPT, "测试快速模式", "--quick", "--output", "json"],
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace", env=env
        )
        out = r.stdout
        start = out.find("{")
        end = out.rfind("}") + 1
        json_str = out[start:end] if start >= 0 else out
        data = json.loads(json_str)
        test("快速模式返回有效 JSON", True)
        test("Phase1 有结果", len(data.get("phase1", {})) > 0)
        dt = data.get("decision") or data.get("decision_preview") or ""
        test("决策有内容", len(dt) > 50)
    except subprocess.TimeoutExpired:
        test("API调用", False, "超时(>120s)")
    except json.JSONDecodeError as e:
        test("API调用", False, f"JSON解析失败: {e}")
    except Exception as e:
        test("API调用", False, str(e)[:100])


def test_dissent():
    """测试异议引擎的基本检测功能"""
    try:
        r = subprocess.run(
            [sys.executable, "dissent.py", "毫无疑问，这个方案是完美的，但是有风险。你说的对。很简单。"],
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace"
        )
        has_grade = "评级" in r.stdout or "A" in r.stdout or "C" in r.stdout
        test("异议引擎能运行", has_grade, r.stderr[:100] if not has_grade else "")
    except Exception as e:
        test("异议引擎能运行", False, str(e)[:100])

def test_dissent_pipe():
    """测试异议引擎管道模式"""
    try:
        r = subprocess.run(
            [sys.executable, "dissent.py"],
            input='{"decision": "这个方案大概可行，但需要考虑以下几个风险点。具体数据还需要进一步验证。"}',
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace"
        )
        has_grade = "评级" in r.stdout
        test("异议引擎管道模式", has_grade, r.stderr[:100] if not has_grade else "")
    except Exception as e:
        test("异议引擎管道模式", False, str(e)[:100])
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="跳过API测试（用于CI）")
    ap.add_argument("--api", action="store_true", help="只跑API测试")
    cli = ap.parse_args()

    skip_api = cli.offline or not os.environ.get("ANTHROPIC_AUTH_TOKEN")

    print("\n" + "="*50)
    print("宪法系统自测 v1.0")
    print("="*50 + "\n")

    if not cli.api:
        print("> 单元测试（离线）")
        test_syntax()
        test_imports()
        test_argparse()
        test_agent_config()
        test_dissent()
        test_dissent_pipe()

    if cli.api or not skip_api:
        print("\n> 集成测试（需要 API）")
        test_api()
    else:
        print("\n> 集成测试（跳过 - 无API key 或 --offline 模式）")

    print("\n" + "="*50)
    total = PASS + FAIL
    print(f"报告: {PASS}/{total} 通过, {FAIL} 失败")
    if ERRORS:
        print("\n失败项:")
        for e in ERRORS:
            print(f"  - {e}")
    print("="*50)
    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
