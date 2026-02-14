# realtime-fund-valuator

一个无图形界面的场外基金实时估值项目。

## 功能
- 输入：`funds_list.txt`（每行一个基金代码）。
- 输出：`valuation_output.txt`（循环追加写入，每分钟刷新一次）。
- 估值逻辑：
  1. 优先基于基金前十大持仓（股票/ETF等）实时行情做加权估值。
  2. 如果持仓行情覆盖不足，则回退到基金跟踪指数估值（适用于部分 QDII/指数基金）。
- 支持 QDII：持仓行情查询支持 A 股 / 港股 / 美股代码格式。

## 安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 使用
1. 编辑 `funds_list.txt`：
```txt
161725
000311
006327
```

2. 运行（调试单次）：
```bash
fund-valuator --once
```

3. 运行（持续每 60 秒刷新）：
```bash
fund-valuator
```

> 刷新周期固定为 1 分钟。即使传入其它周期参数，也会强制按 60 秒执行。

## 输出格式
每行一条记录（tab 分隔）：
- 时间戳
- 基金代码
- 最近已披露单位净值
- 估算单位净值
- 估算涨跌幅
- 方法（holdings / index / unavailable）
- 覆盖率
- 说明

