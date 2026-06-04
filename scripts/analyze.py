#!/usr/bin/env python3
"""A股市场成交集中度分析 — 输出结构化数据"""

import akshare as ak
import pandas as pd
import json, sys


def analyze():
    df = ak.stock_zh_a_spot()
    df = df[df['成交额'].notna()]
    df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
    df = df[df['成交额'] > 0].copy()

    df_sorted = df.sort_values('成交额', ascending=False).reset_index(drop=True)
    total_amount = float(df_sorted['成交额'].sum())
    total_stocks = len(df_sorted)

    result = {
        "total_stocks": total_stocks,
        "total_amount_yi": round(total_amount / 1e8, 2),
        "tiers": {},
        "top_stocks": [],
        "liquidity": []
    }

    # 成交集中度
    for n in [10, 20, 50, 100, 200, 300, 500, 1000]:
        if n > total_stocks:
            break
        top_n = df_sorted.head(n)
        amt = float(top_n['成交额'].sum())
        result["tiers"][str(n)] = {
            "amount_yi": round(amt / 1e8, 2),
            "pct_of_market": round(amt / total_amount * 100, 2),
            "pct_of_stocks": round(n / total_stocks * 100, 2)
        }

    # TOP 30 个股
    top30 = df_sorted.head(30)
    for _, r in top30.iterrows():
        result["top_stocks"].append({
            "code": str(r['代码']),
            "name": str(r['名称']),
            "price": round(float(r['最新价']), 2),
            "change_pct": round(float(r['涨跌幅']), 2),
            "amount_yi": round(float(r['成交额']) / 1e8, 2),
            "pct_of_market": round(float(r['成交额']) / total_amount * 100, 2)
        })

    # 流动性分布
    bins = [
        (0, 1e7, '<1000万'),
        (1e7, 5e7, '1000万-5000万'),
        (5e7, 1e8, '5000万-1亿'),
        (1e8, 5e8, '1亿-5亿'),
        (5e8, float('inf'), '>5亿'),
    ]
    for mn, mx, label in bins:
        if mx == float('inf'):
            cnt = int(len(df_sorted[df_sorted['成交额'] >= mn]))
        else:
            cnt = int(len(df_sorted[(df_sorted['成交额'] >= mn) & (df_sorted['成交额'] < mx)]))
        result["liquidity"].append({
            "range": label,
            "count": cnt,
            "pct": round(cnt / total_stocks * 100, 1)
        })

    return result


if __name__ == "__main__":
    data = analyze()
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
