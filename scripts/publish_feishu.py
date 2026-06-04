#!/usr/bin/env python3
"""
成交集中度 → 飞书三 Sheet 电子表格
- 每日快照: 一行一天，核心对比
- 头部明细: 一天10行，龙头追踪
- 流动性趋势: 一行一天，风险监控

写入策略:
  首次: 写表头(R1) + 数据(R2)  后续: 覆盖已有日期，或追加到末尾
"""

import json, os, sys, time, urllib.request
from datetime import date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.expanduser("~/.qclaw/skills-config/feishu/tokens/user_token.json")

# 飞书表格配置从本地配置文件读取，避免硬编码敏感信息
SPREADSHEET_TOKEN = None
SHEETS = None

def load_config():
    """加载飞书表格配置"""
    global SPREADSHEET_TOKEN, SHEETS
    config_file = os.path.join(SKILL_DIR, "config.json")
    if os.path.exists(config_file):
        with open(config_file) as f:
            cfg = json.load(f)
            SPREADSHEET_TOKEN = cfg.get("spreadsheet_token")
            SHEETS = cfg.get("sheets")
    if not SPREADSHEET_TOKEN:
        raise RuntimeError("飞书表格配置未找到，请检查 config.json")
    if not SHEETS:
        SHEETS = {"snapshot": "000192", "top": "1MyXWU", "liquidity": "1MyXWV"}

HEADERS = {
    "snapshot": [
        "日期", "总量(亿)",
        "前10成交", "前10占比", "前20成交", "前20占比", "前50成交", "前50占比",
        "前100成交", "前100占比", "前200成交", "前200占比", "前300成交", "前300占比",
        "前500成交", "前500占比", "前1000成交", "前1000占比",
        "剩余数量", "剩余成交(亿)", "分化判定", "主线",
    ],
    "top": ["日期", "#", "代码", "名称", "涨跌%", "成交(亿)", "占比%", "方向"],
    "liquidity": [
        "日期",
        "<1000万 数量", "<1000万 占比",
        "1000-5000万 数量", "1000-5000万 占比",
        "5000万-1亿 数量", "5000万-1亿 占比",
        "1亿-5亿 数量", "1亿-5亿 占比",
        ">5亿 数量", ">5亿 占比",
        "尾部占比",
    ],
}

DIRECTION_MAP = [
    ("存储芯片", ["兆易创新","佰维存储","江波龙"]),
    ("光模块", ["中际旭创","新易盛","天孚通信","光迅科技"]),
    ("光纤光缆", ["亨通光电","长飞光纤","中天科技"]),
    ("AI服务器", ["工业富联"]),
    ("PCB/封装", ["东山精密","沪电股份","胜宏科技"]),
    ("封测", ["长电科技","通富微电","华天科技"]),
    ("芯片", ["澜起科技","海光信息","寒武纪","中芯国际"]),
    ("面板", ["京东方Ａ","TCL"]),
    ("新能源", ["宁德时代","阳光电源"]),
]


def load_token():
    return json.load(open(TOKEN_FILE))["access_token"]


def feishu_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def feishu_put(url, payload, token):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def put_row(sheet_id, row_num, row_data, token):
    url = (f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/"
           f"{SPREADSHEET_TOKEN}/values")
    payload = {
        "valueRange": {
            "range": f"{sheet_id}!A{row_num}:Z{row_num}",
            "values": [row_data]
        }
    }
    r = feishu_put(url, payload, token)
    return r.get("code") == 0, r.get("code"), r.get("msg")


def read_a1(sheet_id, token):
    """读取 A1 单元格，返回 (has_value, value)"""
    url = (f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/"
           f"{SPREADSHEET_TOKEN}/values/{sheet_id}!A1:A1")
    r = feishu_get(url, token)
    vals = r.get("data", {}).get("valueRange", {}).get("values")
    if vals and vals[0] and vals[0][0]:
        v = str(vals[0][0]).strip()
        if v:
            return True, v
    return False, ""


def find_date_row(sheet_id, today_str, token, max_rows=500):
    for row in range(1, max_rows):
        url = (f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/"
               f"{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}")
        r = feishu_get(url, token)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return None
        if str(vals[0][0]).strip() == today_str:
            return row
    return None


def find_last_data_row(sheet_id, token, max_rows=500):
    """找到最后一个有数据的行号（1-based），空表返回 0"""
    last = 0
    for row in range(1, max_rows):
        url = (f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/"
               f"{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}")
        r = feishu_get(url, token)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return last
        last = row
    return last


# ── 快照 / 流动性: 表头+数据 ──────────────────────────

def init_or_write_row(sheet_id, header_row, data_row, today_str, token, label):
    """
    首次: 写表头(R1) + 数据(R2)
    后续: 找已有日期→覆盖; 否则 找最后行+1→追加
    """
    has_header, a1_val = read_a1(sheet_id, token)

    if not has_header:
        # 全新表格: 写表头 → 写第一行数据
        ok, code, msg = put_row(sheet_id, 1, header_row, token)
        if not ok:
            print(f"  ❌ {label}: 表头失败 code={code} msg={msg}")
            return False
        ok, code, msg = put_row(sheet_id, 2, data_row, token)
        if not ok:
            print(f"  ❌ {label}: 数据失败 code={code} msg={msg}")
            return False
        print(f"  ✅ {label}: 首次写入 (R1=表头 R2=数据)")
        return True

    # 已有表头：查重/追加
    existing = find_date_row(sheet_id, today_str, token)
    if existing:
        ok, code, msg = put_row(sheet_id, existing, data_row, token)
        if ok:
            print(f"  ✅ {label}: 覆盖 行{existing}")
        else:
            print(f"  ❌ {label}: 覆盖失败 code={code} msg={msg}")
        return ok
    else:
        next_row = find_last_data_row(sheet_id, token) + 1
        ok, code, msg = put_row(sheet_id, next_row, data_row, token)
        if ok:
            print(f"  ✅ {label}: 追加 行{next_row}")
        else:
            print(f"  ❌ {label}: 追加失败 code={code} msg={msg}")
        return ok


# ── 头部明细: 表头 + 多行数据 ──────────────────────────

def init_or_write_top(data, header_row, today_str, token):
    sid = SHEETS["top"]
    has_header, a1_val = read_a1(sid, token)

    # 构建10行数据
    data_rows = []
    for i, s in enumerate(data["top_stocks"][:10]):
        data_rows.append([
            today_str, i + 1, s["code"], s["name"],
            f"{s['change_pct']:+.2f}", s["amount_yi"],
            f"{s['pct_of_market']}%", classify_direction(s["name"]),
        ])

    if not has_header:
        # 全新: 写表头 R1, 数据 R2-R11
        ok, code, msg = put_row(sid, 1, header_row, token)
        if not ok:
            print(f"  ❌ 头部明细: 表头失败 code={code} msg={msg}")
            return False
        start = 2
        mode = "首次"
    else:
        # 已有表头：找当日已有行
        existing = find_date_row(sid, today_str, token)
        if existing:
            start = existing
            mode = "覆盖"
        else:
            start = find_last_data_row(sid, token) + 1
            mode = "追加"

    for i, row in enumerate(data_rows):
        ok, code, msg = put_row(sid, start + i, row, token)
        if not ok:
            print(f"  ❌ 头部明细: 行{start+i} 失败 code={code} msg={msg}")
            return False
        time.sleep(0.3)

    print(f"  ✅ 头部明细: {mode} 10行 (从行{start})")
    return True


# ── 数据构建 ───────────────────────────────────────────

def classify_direction(name):
    for d, names in DIRECTION_MAP:
        if any(n in name for n in names):
            return d
    return "其他"


def main_direction(top10):
    from collections import Counter
    return Counter(classify_direction(s["name"]) for s in top10).most_common(1)[0][0]


def classify_concentration(top300_pct):
    if top300_pct > 55: return "严重分化"
    if top300_pct > 50: return "一九分化"
    if top300_pct > 40: return "偏集中"
    return "正常"


def build_snapshot_row(data, today_str):
    t = data["tiers"]
    total = data["total_amount_yi"]
    rem = total - t["1000"]["amount_yi"]
    rem_stocks = data["total_stocks"] - 1000
    direction = main_direction(data["top_stocks"][:10])
    cat = classify_concentration(t["300"]["pct_of_market"])

    return [
        today_str, round(total, 0),
        t["10"]["amount_yi"],  f"{t['10']['pct_of_market']}%",
        t["20"]["amount_yi"],  f"{t['20']['pct_of_market']}%",
        t["50"]["amount_yi"],  f"{t['50']['pct_of_market']}%",
        t["100"]["amount_yi"], f"{t['100']['pct_of_market']}%",
        t["200"]["amount_yi"], f"{t['200']['pct_of_market']}%",
        t["300"]["amount_yi"], f"{t['300']['pct_of_market']}%",
        t["500"]["amount_yi"], f"{t['500']['pct_of_market']}%",
        t["1000"]["amount_yi"],f"{t['1000']['pct_of_market']}%",
        rem_stocks, round(rem, 0),
        cat, direction,
    ]


def build_liquidity_row(data, today_str):
    liq = data["liquidity"]
    tail_pct = liq[0]["pct"] + liq[1]["pct"]
    return [
        today_str,
        liq[0]["count"], f"{liq[0]['pct']}%",
        liq[1]["count"], f"{liq[1]['pct']}%",
        liq[2]["count"], f"{liq[2]['pct']}%",
        liq[3]["count"], f"{liq[3]['pct']}%",
        liq[4]["count"], f"{liq[4]['pct']}%",
        f"{tail_pct}%",
    ]


# ── Main ───────────────────────────────────────────────

def main():
    sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
    from analyze import analyze

    load_config()  # 加载飞书配置
    token = load_token()
    data = analyze()
    today_str = date.today().strftime("%m-%d")

    print(f"📊 成交集中度 → 飞书表格")
    print(f"   日期: {today_str}  总量: {data['total_amount_yi']}亿  "
          f"前300占比: {data['tiers']['300']['pct_of_market']}%")
    print()

    snapshot_row = build_snapshot_row(data, today_str)
    init_or_write_row(SHEETS["snapshot"], HEADERS["snapshot"], snapshot_row,
                      today_str, token, "每日快照")

    init_or_write_top(data, HEADERS["top"], today_str, token)

    liquidity_row = build_liquidity_row(data, today_str)
    init_or_write_row(SHEETS["liquidity"], HEADERS["liquidity"], liquidity_row,
                      today_str, token, "流动性趋势")

    print(f"\n✅ 全部完成!")
    print(f"https://my.feishu.cn/sheets/{SPREADSHEET_TOKEN}")


if __name__ == "__main__":
    main()
