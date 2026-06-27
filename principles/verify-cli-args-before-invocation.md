---
description: "首次调用不熟悉的 CLI 子命令先跑 --help，禁止猜参数名；批量调用时先批量查签名再批量执行"
triggers:
  - "CLI 参数"
  - "--help"
  - "不熟悉的子命令"
  - "repo-local helper"
  - "参数错误"
---

# 不熟悉的 CLI 子命令先跑 --help，禁止猜参数名

## 规则

首次调用一个不熟悉（或记不清参数签名）的 CLI 子命令时，**先跑一次 `--help`**，再写完整调用。

如果第一次调用报参数错误，对**剩余所有待调用的子命令**也先查 `--help`，不要继续猜。

## Why

与"路径必须先验证，禁止猜"是同一个 anti-pattern：agent 对自身 pattern matching 过度自信，用"看起来合理"的参数名代替实际签名，导致连续报错。

每次报错 → 修一个参数 → 再猜下一个，浪费的 round-trip 远多于一次 `--help` 的成本。

## 典型场景

- `aticket-cli` 的各资源子命令（例如 `ticket new` / `ticket "$TICKET_DIR" fork` / `ticket "$TICKET_DIR" context` / `ticket "$TICKET_DIR" archive`）
- repo-local helper scripts 的各子命令

## How to apply

1. 第一次调用前：`<tool> <subcommand> --help`
2. 从 help 输出中确认参数名和是否 required
3. 再写完整调用

如果一次要调用同一工具的多个子命令（如 ticket 收尾时连续 `ticket "$TICKET_DIR" log` / `ticket "$TICKET_DIR" add-item` / `ticket "$TICKET_DIR" context` / `ticket "$TICKET_DIR" archive`），**批量先查 help 再批量执行**，而不是逐个猜逐个修。
