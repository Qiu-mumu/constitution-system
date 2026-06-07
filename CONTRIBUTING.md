# 参与贡献指南

感谢你感兴趣！这是一个个人宪法系统项目，欢迎提 issue 和 PR。

## 项目结构

```
~/.claude/
  CLAUDE.md        完整宪法（286行，按需加载）
  CLAUDE-DNA.md    精简版 DNA（5条，日常加载）
  COST_LOG.md       成本日志（自动追加）
  cache/           辩论缓存（7天有效）
  mcp-servers/     Local Enforcer 服务器

./trae_projects/
  debate.py        信息隔离辩论引擎
  test_constitution.py  自动化测试
  ROADMAP.md       改进路线图
```

## 如何提交 Issue

- **Bug**：描述现象 + 期望行为 + 复现步骤
- **Feature Request**：你想加什么 + 为什么 + 大概方案
- **Question**：直接问

## 如何提交 PR

1. Fork 这个仓库
2. 开一个分支（`feat/xxx` 或 `fix/xxx`）
3. 改代码
4. 跑测试：`python test_constitution.py --offline`（保证 8/8 通过）
5. 如果改了 debate.py，可选跑完整测试：`python test_constitution.py`
6. 提 PR，描述清楚改了啥

## 代码规范

- Python 3.11+
- 不要加新的外部依赖（除非必要）
- 函数/变量名用英文，注释和用户界面用中文
- 不要删除已有的测试

## 行为准则

- 友好、务实、不装逼
- 不知道就说不知道
- 不做不记
