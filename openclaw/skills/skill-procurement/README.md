# Skill Procurement Agent

技能采购管理员：负责从 skills.sh 和 ClawdHub 发现、审查、推荐并安装技能到指定 agent 的 workspace。

## 创建采购管理员 Agent

```bash
openclaw agents add skill-procurement --workspace ~/.openclaw/workspace-skill-procurement --name "Skill Procurement"
```

## 安装依赖技能

采购管理员需要 `find-skills` 和 `clawdhub` 技能。安装到其 workspace：

```bash
# 1. find-skills (skills.sh)
cd ~/.openclaw/workspace-skill-procurement && mkdir -p skills && npx skills add openclaw/skills@unified-find-skills -a openclaw -y

# 2. clawdhub（已 bundled，或从 ClawdHub 安装）
clawdhub install clawdhub --workdir ~/.openclaw/workspace-skill-procurement
```

skill-procurement 技能本身已 bundled 在 openclaw 中，会自动加载。

## 路由配置

通过 bindings 将技能采购相关渠道路由到该 agent，例如：

- 飞书群/话题：在 `channels.feishu` 中配置 match → `skill-procurement`
- 或使用 `@skill-procurement` 等 mention 模式

## 向后兼容

- 不修改现有 agent 行为
- 仅新增 agent 和 skill
- 现有 Fast、researcher 等 agent 保持不变
