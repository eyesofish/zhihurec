# 任务计划：ZhihuRec 1M 数据准备

## 总体目标
根据 THUIR 官方 README 确认 ZhihuRec-1M 的获取方式，创建所需的本地目录结构，只下载官方 1M 相关文件，并记录文件检查结果与本地检查脚本。

## 子问题
1. `01-confirm-source-and-blockers.md` - 核对官方 README 中的关键说明，并判断下载能否自动进行，还是需要人工确认 - 状态：已验证
2. `02-local-layout-and-artifacts.md` - 创建所需目录；如果允许下载，则完成数据检查结果与检查脚本 - 状态：已验证

## 依赖关系
第 2 步依赖第 1 步，因为具体下载动作必须遵循官方 README，而且可能会被共享网页或人工确认步骤阻塞。

## 推荐执行顺序
先执行第 1 步，避免下载错误的数据集或使用非官方来源。再执行第 2 步，创建本地目录结构、只获取需要的官方文件、完成校验，并写出检查脚本。

## 端到端验证
1. 确认官方 README 明确说明存在 `ZhihuRec-1M`，并列出数据集的 8 个文件，且下载入口来自 README 中的链接。
2. 确认官方链接到底是文件直链，还是需要人工确认的共享网页。
3. 确认 `data/zhihurec_1m/raw`、`data/zhihurec_1m/meta`、`scripts` 已创建。
4. 如果继续下载，则确认 `data/zhihurec_1m/raw` 下的 8 个目标文件都存在且非空，并生成 `data/zhihurec_1m/meta/check.txt` 与 `scripts/inspect_zhihurec.py`。

## 当前状态
官方 README 已完成核对。下载入口解析后是清华云盘公开共享目录页面，目录里提供的是 8 个官方压缩 CSV 文件和一个 README，而不是单独的 ZhihuRec-1M 压缩包。在获得人工确认后，已经下载这 8 个官方文件，并依据 README 中给出的 1M 行数在本地裁切出 1M 版本；同时生成了 `data/zhihurec_1m/meta/check.txt`，并创建、验证了 `scripts/inspect_zhihurec.py`。
