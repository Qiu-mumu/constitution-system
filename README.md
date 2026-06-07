# 🧠 AI 宪法系统

一套让 AI 更可信、更省 token、更自律的宪法框架。

**核心问题**：AI 编程助手（Claude Code 等）容易过度设计、讨好用户、忽视风险、缺乏自我验证。这套系统用宪法 + 辩论 + 异议检查来解决这个问题。

---

## 系统结构

```
CLAUDE.md          宪法正文（197行，18条）
CLAUDE-DNA.md      精简版 DNA（8条，日常加载）
WORKFLOW.md        完整任务处理流程（OODA + Cynefin + PDCA）
debate.py          信息隔离辩论引擎（3 Agent + 交叉审查）
dissent.py         输出异议检查（矛盾 / 过度自信 / 讨好 / 简化）
test_constitution.py  自动化测试（13项）
ROADMAP.md         改进路线图（72→85分路线）
CONTRIBUTING.md    参与指南
```

## 核心功能

- **T1/T2/T3 分级**：日常问答直接给答案（省 token），复杂决策走完整辩论
- **信息隔离辩论**：3个 Agent 基于不同知识子集独立分析、交叉审查
- **异议检查**：输出后自动检测讨好、过度自信、自相矛盾
- **成本日志**：自动追踪每次辩论的 token 消耗
- **缓存系统**：同一话题 7 天内不复辩
- **强制执行层**：MCP 服务器 + HMAC 签名，防篡改

## 快速开始

```bash
# 前置条件
pip install requests
# 环境变量：API 密钥（任选一种）
export ANTHROPIC_AUTH_TOKEN="sk-your-key"

# 辩论
python debate.py "这个方案靠谱吗？"
python debate.py "选哪个方案？" --quick        # 快速模式（2 Agent）
python debate.py "先试试看" --frugal           # 省 token 模式
python debate.py "复杂问题" --output json      # JSON 输出

# 检查输出质量
python debate.py "xxx" --quick --output json | python dissent.py

# 运行测试
python test_constitution.py                    # 完整测试（需 API）
python test_constitution.py --offline          # 离线测试（跳过 API）
```

## 日常使用

```
你说：
"查一下 Python 版本"       → T1 极简回答
"帮我分析这个架构"          → T2 辩论 + 带置信度
"用宪法跑一下XX"           → T3 完整流程
"太复杂了先试试看"         → T3 出实验方案
```

## 设计思想

借鉴 8 个框架，4 个核心在运转：

| 框架 | 用在哪 |
|------|--------|
| **OODA Loop** | T1 速度优势：能快就快，省下的时间留给复杂问题 |
| **Cynefin** | 区分 Complicated（辩论）vs Complex（实验） |
| **PDCA** | T3 实验模式：Plan→Do→Check→Act |
| **苏格拉底** | 任务启动协议：先提问厘清，不直接动手 |

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT
