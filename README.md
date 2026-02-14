# realtime-fund-valuator

一个无图形界面的场外基金实时估值项目。

## 功能
- 输入：`funds_list.txt`（每行一个基金代码）。
- 输出：
  - `valuation_output.txt`：全部结果
  - `valuation_hits.txt`：有效命中（可用于实时监控）
  - `valuation_misses.txt`：未有效命中
  - `valuation_miss_analysis.txt`：失败原因统计（便于后续迭代）
- 刷新周期固定 1 分钟。
- 估值逻辑：
  1. 优先基于基金前十大持仓（股票/ETF等）实时行情做加权估值。
  2. 如果持仓行情覆盖不足，则回退到基金跟踪指数估值（适用于部分 QDII/指数基金）。
- 支持 QDII：持仓行情查询支持 A 股 / 港股 / 美股代码格式。
- 支持 `--proxy`（适配 VPN/代理网络环境）。

## 环境建议（与你提供的 conda 环境兼容）
你提供的 `fundnew` 环境已包含 `python=3.10`、`setuptools`、`requests`、`beautifulsoup4` 等依赖，可直接运行：

```bash
conda activate fundnew
PYTHONPATH=src python -m realtime_fund_valuator.runner --once
```

## 使用
1. 编辑 `funds_list.txt`：
```txt
161725
000311
006327
```

2. 运行（调试单次）
```bash
PYTHONPATH=src python -m realtime_fund_valuator.runner --once
```

3. 运行（持续每 60 秒刷新）
```bash
PYTHONPATH=src python -m realtime_fund_valuator.runner
```

4. 运行（使用代理/VPN 转发）
```bash
PYTHONPATH=src python -m realtime_fund_valuator.runner --proxy http://127.0.0.1:7890
```

> 刷新周期固定为 1 分钟。即使传入其它周期参数，也会强制按 60 秒执行。

## 输出说明
每条估值记录字段（tab 分隔）：
- 时间戳
- 基金代码
- 最近已披露单位净值
- 估算单位净值
- 估算涨跌幅
- 方法（holdings / index / unavailable）
- 覆盖率
- 说明

### 失败分析分类
当前会将未命中原因归类为：
- `nav_fetch_failed`：净值读取失败
- `upstream_http_failed`：上游 HTTP 请求失败
- `quote_or_index_unavailable`：无可用持仓行情或指数行情
- `datasource_error`：数据源异常
- `other`：其它未识别原因
