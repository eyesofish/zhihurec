# Task Plan: ZhihuRec V1 Offline Eval Deliverable

## Overall goal

把已经写好的离线 item-ranking 评估收成 V1 的正式 deliverable。成功状态是：

- `backend/app/evaluate.py` 提供纯函数 `time_split` / `recall_at_k` / `ndcg_at_k`。
- `scripts/eval_offline_metrics.py` 能驱动真实 backend 跑 80/20 replay baseline。
- `docs/v1_metrics.md` 记录 Recall@K / NDCG@K 的定义、运行方式、首条基线和解释。
- `plan/zhihurec-v1-gap-checklist/README.md` 不再把这项描述成未决，而是指向本 plan。

不改 ranking、retrieval、schema、API 行为，也不把 V2 的 FAISS / LightGBM / 多用户评估带进来。

## Subproblems

1. `01-formalize-offline-eval.md` - 给现有 offline-eval 代码和文档补正式 plan 入口、交叉引用、验证和 commit 边界 - status: verified

## Dependencies

本 plan 收口 2026-05-16 已经完成的 offline-eval 改动：

- `backend/app/evaluate.py`
- `scripts/eval_offline_metrics.py`
- `tests/test_evaluate.py`
- `docs/v1_metrics.md`

本 plan 不依赖 C2 HCI 报告，也不依赖 V2 教程仓库。

## Recommended execution order

1. 先写本 plan 的 README 和 `01-formalize-offline-eval.md`，让 deliverable 有正式入口。
2. 再更新 gap-checklist 的当前状态和 verification log，让主 handoff 文件指向本 plan。
3. 跑纯测试：`& 'C:\ProgramData\anaconda3\python.exe' -m pytest tests\test_evaluate.py -v`。
4. 跑默认测试层：`& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v`。
5. 如果本地 Docker / backend 可用，再跑真实 backend baseline；如果不可用，在 verification log 里明确说明本轮只验证了纯测试层。
6. 按计划拆 commit，不 push。

## End-to-end verification

最低验收：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pytest tests\test_evaluate.py -v
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v
```

完整验收（需要 Docker MySQL + uvicorn）：

```powershell
docker compose up -d
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_offline_metrics.py --k 10 --train-ratio 0.8
```

预期首条 baseline：

- Recall@10 = 0.0000
- NDCG@10 = 0.0000
- candidate_recall@50 = 0.1579
- test_click_events_scored = 19

## Verification log

每完成一轮验证在这里追加：`YYYY-MM-DD - <一句话结果>`。

- 2026-05-16 - 首条 offline ranking baseline 已在真实 docker MySQL + uvicorn 上跑通：97 train events posted，19 test clicks scored，Recall@10 = 0.0000，NDCG@10 = 0.0000，candidate_recall@50 = 0.1579。
- 2026-05-17 - 本 plan 入口和 checklist cross-reference 已落地；`tests/test_evaluate.py` 19 passed，默认 pytest 40 passed / 4 deselected；真实 docker MySQL + uvicorn baseline 复跑一致，request_failures = 0，Recall@10 = 0.0000，NDCG@10 = 0.0000，candidate_recall@50 = 0.1579。
