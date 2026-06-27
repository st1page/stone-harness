---
description: "验证类工具/脚本必须避免“假绿”：即使没有真正检查任何东西也输出 OK"
triggers:
  - "false green"
  - "假绿"
  - "validator false green"
  - "silent OK"
  - "scanned=0"
  - "link check"
  - "check_md_links"
  - "worktree path validation"
---

# 验证类工具必须避免“假绿”

## 背景

验证/扫描类脚本（lint、link check、validator）常用作“合格/不合格”的自动判据。

如果工具在某些环境下**没有真正扫描任何输入**，却仍输出 `OK`（甚至退出码为 0），会把问题长期隐藏，直到线上/安装后才暴露；而此时定位成本会大幅上升。

## 原则

1) **工具必须可观测**

- 至少能让人判断“是否真的做了检查”（例如输出扫描文件数、跳过文件数、命中规则数；或提供 `--stats/--verbose`）。
- 当“扫描目标为空/全量被过滤”属于异常时，应返回非 0 或显式 warning，而不是静默 `OK`。

2) **验证必须包含反证**

- 对重要的验证链路，至少保留一个“反证手段”（canary）：能在本地快速构造一个必然失败的样例，用来证明工具确实能报错。
- 反证用例不必进 git（可以是临时文件/临时目录），但必须写进运行手册或 PR checklist。

## 示例

- 反面：link check 脚本在某些 CWD 下扫描到 0 个文件，但仍输出 `OK: no missing links`。
- 正面：link check 输出 `scanned=312 ignored=18 missing=0`；若 `scanned=0` 则提示 “root/ignore 配置异常” 并退出非 0。
