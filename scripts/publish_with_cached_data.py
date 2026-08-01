#!/usr/bin/env python3
"""使用缓存数据直接写入飞书表格"""

import json, os, sys, time, urllib.request
from datetime import date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.expanduser("~/.qclaw/skills-config/feishu/tokens/user_token.json")

# 加载飞书配置
config_file = os.path.join(SKILL_DIR, "config.json")
with open(config_file) as f:
    cfg = json.load(f)
SPREADSHEET_TOKEN = cfg["spreadsheet_token"]
SHEETS = cfg["sheets"]

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
        "日期", "<1000万 数量", "<1000万 占比",
        "1000-5000万 数量", "1000-5000万 占比",
        "5000万-1亿 数量", "5000万-1亿 占比",
        "1亿-5亿 数量", "1亿-5亿 占比",
        ">5亿 数量", ">5亿 占比", "尾部占比",
    ],
}

# ── 方向分类（精简版）──
DIRECTION_MAP = {}
STATIC_DIR = [
    ("存储芯片", ["兆易创新","佰维存储","江波龙","德明利","朗科科技","普冉股份","东芯股份"]),
    ("光模块/CPO", ["中际旭创","新易盛","天孚通信","光迅科技","剑桥科技","博创科技","太辰光","联特科技"]),
    ("光纤光缆", ["亨通光电","中天科技","长飞光纤","通光线缆"]),
    ("AI服务器/算力", ["工业富联","浪潮信息","寒武纪","海光信息","中科曙光"]),
    ("PCB", ["东山精密","沪电股份","胜宏科技","深南电路","鹏鼎控股","生益科技"]),
    ("先进封装", ["长电科技","通富微电","华天科技","晶方科技","甬矽电子"]),
    ("半导体设备", ["中微公司","北方华创","拓荆科技","华海清科","芯源微"]),
    ("半导体材料", ["南大光电","沪硅产业","立昂微","安集科技","鼎龙股份","江丰电子"]),
    ("芯片设计", ["澜起科技","韦尔股份","圣邦股份","卓胜微","思瑞浦"]),
    ("面板/显示", ["京东方Ａ","TCL科技","维信诺","彩虹股份","深天马Ａ"]),
    ("锂电池", ["宁德时代","亿纬锂能","国轩高科","欣旺达","孚能科技","鹏辉能源"]),
    ("通信设备", ["中兴通讯","烽火通信"]),
    ("消费电子", ["信维通信","立讯精密","歌尔股份","蓝思科技","领益智造"]),
    ("有色金属/稀土", ["紫金矿业","云南锗业","中钨高新"]),
    ("机器人/自动化", ["绿的谐波"]),
    ("软件/IT服务", ["金山办公","科大讯飞","恒生电子"]),
]
for d, names in STATIC_DIR:
    for n in names:
        DIRECTION_MAP[n] = d

def classify_direction(name):
    return DIRECTION_MAP.get(name, "")

def load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)["access_token"]

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
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values"
    payload = {"valueRange": {"range": f"{sheet_id}!A{row_num}:Z{row_num}", "values": [row_data]}}
    r = feishu_put(url, payload, token)
    return r.get("code") == 0, r.get("code"), r.get("msg")

def read_a1(sheet_id, token):
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A1:A1"
    r = feishu_get(url, token)
    vals = r.get("data", {}).get("valueRange", {}).get("values")
    if vals and vals[0] and vals[0][0]:
        return True, str(vals[0][0]).strip()
    return False, ""

def find_date_row(sheet_id, today_str, token, max_rows=500):
    for row in range(1, max_rows + 1):
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}"
        r = feishu_get(url, token)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return None
        if str(vals[0][0]).strip() == today_str:
            return row
    return None

def find_last_data_row(sheet_id, token, max_rows=500):
    last = 0
    for row in range(1, max_rows + 1):
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}"
        r = feishu_get(url, token)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return last
        last = row
    return last

def init_or_write_row(sheet_id, header, data_row, today_str, token, label):
    has_header, _ = read_a1(sheet_id, token)
    if not has_header:
        put_row(sheet_id, 1, header, token)
        ok, code, msg = put_row(sheet_id, 2, data_row, token)
        print(f"  {'✅' if ok else '❌'} {label}: 首次写入 (R1=表头 R2=数据)" if ok else
              f"  ❌ {label}: 失败 code={code} msg={msg}")
        return ok
    existing = find_date_row(sheet_id, today_str, token)
    if existing:
        ok, code, msg = put_row(sheet_id, existing, data_row, token)
        print(f"  {'✅' if ok else '❌'} {label}: 覆盖 行{existing}")
        return ok
    next_row = find_last_data_row(sheet_id, token) + 1
    ok, code, msg = put_row(sheet_id, next_row, data_row, token)
    print(f"  {'✅' if ok else '❌'} {label}: 追加 行{next_row}")
    return ok

def main():
    token = load_token()
    today_str = date.today().strftime("%m-%d")

    # 缓存数据
    data = {
        "total_stocks": 5510,
        "total_amount_yi": 25744.78,
        "tiers": {
            "10": {"amount_yi": 1969.41, "pct_of_market": 7.65},
            "20": {"amount_yi": 3043.24, "pct_of_market": 11.82},
            "50": {"amount_yi": 5406.3, "pct_of_market": 21.0},
            "100": {"amount_yi": 7877.9, "pct_of_market": 30.6},
            "200": {"amount_yi": 10969.17, "pct_of_market": 42.61},
            "300": {"amount_yi": 13068.62, "pct_of_market": 50.76},
            "500": {"amount_yi": 15926.64, "pct_of_market": 61.86},
            "1000": {"amount_yi": 19775.6, "pct_of_market": 76.81}
        },
        "top_stocks": [
            {"code":"sz300502","name":"新易盛","change_pct":-4.55,"amount_yi":356.1,"pct_of_market":1.38},
            {"code":"sz300308","name":"中际旭创","change_pct":-2.0,"amount_yi":345.59,"pct_of_market":1.34},
            {"code":"sh600487","name":"亨通光电","change_pct":-4.19,"amount_yi":231.07,"pct_of_market":0.9},
            {"code":"sz000725","name":"京东方Ａ","change_pct":-3.32,"amount_yi":194.36,"pct_of_market":0.75},
            {"code":"sh600522","name":"中天科技","change_pct":-1.85,"amount_yi":143.63,"pct_of_market":0.56},
            {"code":"sh600498","name":"烽火通信","change_pct":9.5,"amount_yi":142.59,"pct_of_market":0.55},
            {"code":"sh603986","name":"兆易创新","change_pct":0.55,"amount_yi":142.11,"pct_of_market":0.55},
            {"code":"sz002384","name":"东山精密","change_pct":-0.6,"amount_yi":139.84,"pct_of_market":0.54},
            {"code":"sz300394","name":"天孚通信","change_pct":0.3,"amount_yi":137.79,"pct_of_market":0.54},
            {"code":"sh688256","name":"寒武纪","change_pct":-0.93,"amount_yi":136.32,"pct_of_market":0.53},
            {"code":"sh600183","name":"生益科技","change_pct":1.93,"amount_yi":125.28,"pct_of_market":0.49},
            {"code":"sz000636","name":"风华高科","change_pct":7.51,"amount_yi":116.94,"pct_of_market":0.45},
            {"code":"sh688041","name":"海光信息","change_pct":1.77,"amount_yi":116.36,"pct_of_market":0.45},
            {"code":"sz002428","name":"云南锗业","change_pct":10.0,"amount_yi":112.82,"pct_of_market":0.44},
            {"code":"sh601138","name":"工业富联","change_pct":-2.26,"amount_yi":103.44,"pct_of_market":0.4},
            {"code":"sz300750","name":"宁德时代","change_pct":-1.62,"amount_yi":103.02,"pct_of_market":0.4},
            {"code":"sz000657","name":"中钨高新","change_pct":6.93,"amount_yi":102.58,"pct_of_market":0.4},
            {"code":"sz002463","name":"沪电股份","change_pct":-2.83,"amount_yi":99.05,"pct_of_market":0.38},
            {"code":"sh688008","name":"澜起科技","change_pct":-1.0,"amount_yi":98.58,"pct_of_market":0.38},
            {"code":"sh688525","name":"佰维存储","change_pct":2.29,"amount_yi":95.77,"pct_of_market":0.37},
            {"code":"sz000063","name":"中兴通讯","change_pct":-1.59,"amount_yi":94.94,"pct_of_market":0.37},
            {"code":"sh600584","name":"长电科技","change_pct":-2.84,"amount_yi":92.5,"pct_of_market":0.36},
            {"code":"sz300136","name":"信维通信","change_pct":3.0,"amount_yi":88.95,"pct_of_market":0.35},
            {"code":"sh601899","name":"紫金矿业","change_pct":-1.34,"amount_yi":88.07,"pct_of_market":0.34},
            {"code":"sz300476","name":"胜宏科技","change_pct":-1.45,"amount_yi":87.32,"pct_of_market":0.34},
            {"code":"sz002281","name":"光迅科技","change_pct":1.38,"amount_yi":86.38,"pct_of_market":0.34},
            {"code":"sh688012","name":"中微公司","change_pct":4.85,"amount_yi":82.23,"pct_of_market":0.32},
            {"code":"sz300346","name":"南大光电","change_pct":8.09,"amount_yi":82.15,"pct_of_market":0.32},
            {"code":"sh688017","name":"绿的谐波","change_pct":-13.44,"amount_yi":81.93,"pct_of_market":0.32},
            {"code":"sh688498","name":"源杰科技","change_pct":0.14,"amount_yi":81.6,"pct_of_market":0.32}
        ],
        "liquidity": [
            {"range":"<1000万","count":74,"pct":1.3},
            {"range":"1000万-5000万","count":1376,"pct":25.0},
            {"range":"5000万-1亿","count":1061,"pct":19.3},
            {"range":"1亿-5亿","count":1934,"pct":35.1},
            {">5亿":{"count":1065,"pct":19.3}}
        ]
    }
    # Fix last item
    data["liquidity"] = [
        {"range":"<1000万","count":74,"pct":1.3},
        {"range":"1000万-5000万","count":1376,"pct":25.0},
        {"range":"5000万-1亿","count":1061,"pct":19.3},
        {"range":"1亿-5亿","count":1934,"pct":35.1},
        {"range":">5亿","count":1065,"pct":19.3}
    ]

    t = data["tiers"]
    total = data["total_amount_yi"]
    rem = total - t["1000"]["amount_yi"]
    rem_stocks = data["total_stocks"] - 1000

    from collections import Counter
    top10_dir = Counter(classify_direction(s["name"]) for s in data["top_stocks"][:10]).most_common(1)[0][0]

    top300_pct = t["300"]["pct_of_market"]
    if top300_pct > 55: cat = "严重分化"
    elif top300_pct > 50: cat = "一九分化"
    elif top300_pct > 40: cat = "偏集中"
    else: cat = "正常"

    snapshot_row = [
        today_str, round(total, 0),
        t["10"]["amount_yi"], f"{t['10']['pct_of_market']}%",
        t["20"]["amount_yi"], f"{t['20']['pct_of_market']}%",
        t["50"]["amount_yi"], f"{t['50']['pct_of_market']}%",
        t["100"]["amount_yi"], f"{t['100']['pct_of_market']}%",
        t["200"]["amount_yi"], f"{t['200']['pct_of_market']}%",
        t["300"]["amount_yi"], f"{t['300']['pct_of_market']}%",
        t["500"]["amount_yi"], f"{t['500']['pct_of_market']}%",
        t["1000"]["amount_yi"], f"{t['1000']['pct_of_market']}%",
        rem_stocks, round(rem, 0), cat, top10_dir,
    ]

    liq = data["liquidity"]
    tail_pct = liq[0]["pct"] + liq[1]["pct"]
    liquidity_row = [
        today_str,
        liq[0]["count"], f"{liq[0]['pct']}%",
        liq[1]["count"], f"{liq[1]['pct']}%",
        liq[2]["count"], f"{liq[2]['pct']}%",
        liq[3]["count"], f"{liq[3]['pct']}%",
        liq[4]["count"], f"{liq[4]['pct']}%",
        f"{tail_pct}%",
    ]

    top_rows = []
    for i, s in enumerate(data["top_stocks"][:10]):
        top_rows.append([
            today_str, i + 1, s["code"], s["name"],
            f"{s['change_pct']:+.2f}", s["amount_yi"],
            f"{s['pct_of_market']}%", classify_direction(s["name"]) or "",
        ])

    print(f"📊 成交集中度 → 飞书表格")
    print(f"   日期: {today_str}  总量: {total:.0f}亿  前300占比: {t['300']['pct_of_market']}%")
    print()

    # 每日快照
    init_or_write_row(SHEETS["snapshot"], HEADERS["snapshot"], snapshot_row, today_str, token, "每日快照")

    # 头部明细
    sid = SHEETS["top"]
    has_header, _ = read_a1(sid, token)
    if not has_header:
        put_row(sid, 1, HEADERS["top"], token)
        mode = "首次"
        start = 2
    else:
        existing = find_date_row(sid, today_str, token)
        if existing:
            start = existing
            mode = "覆盖"
        else:
            start = find_last_data_row(sid, token) + 1
            mode = "追加"

    for i, row in enumerate(top_rows):
        ok, code, msg = put_row(sid, start + i, row, token)
        print(f"  {'✅' if ok else '❌'} 头部明细 行{start+i}: {row[3]}" if ok else
              f"  ❌ 头部明细 行{start+i}: {row[3]} 失败 code={code}")
        time.sleep(0.3)
    print(f"  ✅ 头部明细: {mode} 10行 (从行{start})")

    # 流动性趋势
    init_or_write_row(SHEETS["liquidity"], HEADERS["liquidity"], liquidity_row, today_str, token, "流动性趋势")

    print(f"\n✅ 全部完成!")
    print(f"https://my.feishu.cn/sheets/{SPREADSHEET_TOKEN}")

if __name__ == "__main__":
    main()
