# Subproblem 1: Formalize Offline Eval

## 1. Goal

把 offline-eval 的代码、脚本、测试和指标文档收成一个可交接的 V1 deliverable。

## 2. Why this step exists

当前 offline-eval 文件已经存在，但主 checklist 仍把它描述成"是否要单独开 plan"的未决项。这个 step 的作用是补正式 plan 入口，让后续读者知道这些文件为什么存在、怎么验证、怎么解释结果。

## 3. Files involved

- `backend/app/evaluate.py` - 已有纯函数 `time_split` / `recall_at_k` / `ndcg_at_k`，本 step 不改算法。
- `scripts/eval_offline_metrics.py` - 已有真实 backend driver，本 step 不改 replay 方法。
- `tests/test_evaluate.py` - 已有纯函数测试，本 step 用它做最低验证。
- `docs/v1_metrics.md` - 已有 Recall@K / NDCG@K 章节，本 step 保留其定义和首条基线。
- `plan/zhihurec-v1-gap-checklist/README.md` - 需要把 offline-eval 从"未决"改成"已 formalized，见本 plan"。
- `plan/zhihurec-v1-offline-eval/README.md` - 新 plan index。

## 4. Exact changes

- 创建 `plan/zhihurec-v1-offline-eval/README.md`，写清 goal、dependencies、执行顺序、验证命令和 verification log。
- 创建本文件，记录唯一子问题的文件边界、验证方式和出界范围。
- 修改 `plan/zhihurec-v1-gap-checklist/README.md`：
  - 顶部当前状态把 offline-eval 描述为正式 deliverable，而不是"待决定是否开 plan"。
  - "仍然 open 的两件事"只保留 C2 HCI 报告，或者明确 offline-eval 仅剩 commit 收口。
  - resume prompt 的下一步选项从"要不要开 plan"改为"本 plan 已开，验证并 commit"。
  - verification log 追加本 plan 的 cross-reference。

## 5. Out of scope

- 不改 ranking 权重。
- 不扩大 candidate pool。
- 不把 `scripts/eval_offline_metrics.py` 做成 package API。
- 不新增 ML 依赖。
- 不 push 到远端。

## 6. Done condition

- 新 plan 目录存在，并能从 gap-checklist 找到入口。
- `tests/test_evaluate.py` 通过。
- 默认 pytest 层通过，或失败项被明确记录为与本 step 无关。
- 两个 commit 按计划创建：一个 docs plan commit，一个 eval implementation commit。

## 7. Verification

最低验证命令：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pytest tests\test_evaluate.py -v
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v
```

如果本地 MySQL 和 backend 已启动，再跑：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_offline_metrics.py --k 10 --train-ratio 0.8
```

期望 live baseline 输出包含：

- `"recall_at_k": 0.0`
- `"ndcg_at_k": 0.0`
- `"candidate_recall_at_k_observed": 0.1579`
- `"test_click_events_scored": 19`

## 8. Expected output

- 一个正式 plan 目录：`plan/zhihurec-v1-offline-eval/`。
- gap-checklist 指向本 plan。
- offline-eval 代码、脚本、测试、指标文档以独立 commit 收口。

## 9. Notes for the next step

后续如果要提升 Recall@10，不应先调 ranking 权重；首条 baseline 显示 top-50 candidate_recall 也低，下一步应提升 retrieval depth。

## 10. Risks or ambiguity

- `candidate_recall_at_k_observed` 只是 top-50 feed 观察值，不是真正 internal candidate pool recall；文档必须继续保留这个 caveat。
- live baseline 依赖 docker MySQL 和 uvicorn，如果本轮环境不可用，仍可先用纯测试层验证核心 metric 函数。
