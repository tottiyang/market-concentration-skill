#!/usr/bin/env python3
"""Standalone publish: writes pre-collected data to Feishu without calling akshare"""

import json, os, sys, time
from datetime import date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
sys.path.insert(0, SKILL_DIR)

# Load cached data (from the successful analyze run earlier)
data = {
    "total_stocks": 5511,
    "total_amount_yi": 17476.29,
    "tiers": {
        "10": {"amount_yi": 1369.31, "pct_of_market": 7.84, "pct_of_stocks": 0.18},
        "20": {"amount_yi": 2147.59, "pct_of_market": 12.29, "pct_of_stocks": 0.36},
        "50": {"amount_yi": 3739.54, "pct_of_market": 21.4, "pct_of_stocks": 0.91},
        "100": {"amount_yi": 5472.82, "pct_of_market": 31.32, "pct_of_stocks": 1.81},
        "200": {"amount_yi": 7597.46, "pct_of_market": 43.47, "pct_of_stocks": 3.63},
        "300": {"amount_yi": 9020.75, "pct_of_market": 51.62, "pct_of_stocks": 5.44},
        "500": {"amount_yi": 10922.3, "pct_of_market": 62.5, "pct_of_stocks": 9.07},
        "1000": {"amount_yi": 13523.5, "pct_of_market": 77.38, "pct_of_stocks": 18.15}
    },
    "top_stocks": [
        {"code":"sz300308","name":"中际旭创","price":1162.88,"change_pct":-1.45,"amount_yi":182.19,"pct_of_market":1.04},
        {"code":"sz300502","name":"新易盛","price":783.83,"change_pct":-0.24,"amount_yi":156.48,"pct_of_market":0.9},
        {"code":"sh688041","name":"海光信息","price":286.57,"change_pct":6.86,"amount_yi":149.14,"pct_of_market":0.85},
        {"code":"sh600487","name":"亨通光电","price":106.53,"change_pct":1.44,"amount_yi":148.93,"pct_of_market":0.85},
        {"code":"sz000725","name":"京东方Ａ","price":6.03,"change_pct":-7.51,"amount_yi":142.11,"pct_of_market":0.81},
        {"code":"sh600522","name":"中天科技","price":50.31,"change_pct":-7.65,"amount_yi":137.77,"pct_of_market":0.79},
        {"code":"sz300394","name":"天孚通信","price":412.4,"change_pct":-7.1,"amount_yi":127.7,"pct_of_market":0.73},
        {"code":"sh688256","name":"寒武纪","price":1259.27,"change_pct":-0.85,"amount_yi":122.47,"pct_of_market":0.7},
        {"code":"sh600183","name":"生益科技","price":146.29,"change_pct":-0.8,"amount_yi":101.3,"pct_of_market":0.58},
        {"code":"sh603986","name":"兆易创新","price":482.84,"change_pct":-3.53,"amount_yi":101.2,"pct_of_market":0.58},
        {"code":"sz002463","name":"沪电股份","price":130.5,"change_pct":-7.51,"amount_yi":92.4,"pct_of_market":0.53},
        {"code":"sz002384","name":"东山精密","price":217.45,"change_pct":-3.1,"amount_yi":92.38,"pct_of_market":0.53},
        {"code":"sh688525","name":"佰维存储","price":321.09,"change_pct":5.22,"amount_yi":90.89,"pct_of_market":0.52},
        {"code":"sz000063","name":"中兴通讯","price":38.4,"change_pct":-1.89,"amount_yi":78.08,"pct_of_market":0.45},
        {"code":"sh600584","name":"长电科技","price":74.0,"change_pct":-1.71,"amount_yi":76.46,"pct_of_market":0.44},
        {"code":"sz000636","name":"风华高科","price":60.25,"change_pct":-1.36,"amount_yi":76.07,"pct_of_market":0.44},
        {"code":"sh688126","name":"沪硅产业","price":32.95,"change_pct":3.85,"amount_yi":69.07,"pct_of_market":0.4},
        {"code":"sh601208","name":"东材科技","price":62.13,"change_pct":4.21,"amount_yi":67.98,"pct_of_market":0.39},
        {"code":"sh601138","name":"工业富联","price":71.55,"change_pct":-4.27,"amount_yi":67.9,"pct_of_market":0.39},
        {"code":"sz300476","name":"胜宏科技","price":330.75,"change_pct":-3.44,"amount_yi":67.05,"pct_of_market":0.38},
        {"code":"sh688008","name":"澜起科技","price":232.25,"change_pct":-1.75,"amount_yi":66.36,"pct_of_market":0.38},
        {"code":"sh600176","name":"中国巨石","price":39.24,"change_pct":0.31,"amount_yi":63.84,"pct_of_market":0.37},
        {"code":"sz300274","name":"阳光电源","price":142.91,"change_pct":-6.29,"amount_yi":63.07,"pct_of_market":0.36},
        {"code":"sh688981","name":"中芯国际","price":126.81,"change_pct":-0.39,"amount_yi":62.68,"pct_of_market":0.36},
        {"code":"sh688012","name":"中微公司","price":293.0,"change_pct":2.79,"amount_yi":62.05,"pct_of_market":0.36},
        {"code":"sh601869","name":"长飞光纤","price":457.96,"change_pct":-5.45,"amount_yi":61.01,"pct_of_market":0.35},
        {"code":"sz300604","name":"长川科技","price":230.56,"change_pct":8.38,"amount_yi":60.37,"pct_of_market":0.35},
        {"code":"sz300750","name":"宁德时代","price":388.65,"change_pct":-2.72,"amount_yi":58.16,"pct_of_market":0.33},
        {"code":"sz002475","name":"立讯精密","price":65.58,"change_pct":-5.42,"amount_yi":58.05,"pct_of_market":0.33},
        {"code":"sz002747","name":"埃斯顿","price":36.15,"change_pct":-3.68,"amount_yi":56.89,"pct_of_market":0.33}
    ],
    "liquidity": [
        {"range":"<1000万","count":191,"pct":3.5},
        {"range":"1000万-5000万","count":1958,"pct":35.5},
        {"range":"5000万-1亿","count":979,"pct":17.8},
        {"range":"1亿-5亿","count":1637,"pct":29.7},
        {"range":">5亿","count":746,"pct":13.5}
    ]
}

today_str = date.today().strftime("06-%d")
# Use consistent format: MM-DD
today_display = date.today().strftime("%m-%d")

# ── Config / Token ──
TOKEN_FILE = os.path.expanduser("~/.qclaw/skills-config/feishu/tokens/user_token.json")
config_file = os.path.join(SKILL_DIR, "config.json")

with open(config_file) as f:
    cfg = json.load(f)
SPREADSHEET_TOKEN = cfg["spreadsheet_token"]
SHEETS = cfg["sheets"]

with open(TOKEN_FILE) as f:
    access_token = json.load(f)["access_token"]

import urllib.request

def feishu_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def feishu_put(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def put_row(sheet_id, row_num, row_data):
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values"
    payload = {
        "valueRange": {
            "range": f"{sheet_id}!A{row_num}:Z{row_num}",
            "values": [row_data]
        }
    }
    r = feishu_put(url, payload)
    return r.get("code") == 0, r.get("code"), r.get("msg")

def read_a1(sheet_id):
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A1:A1"
    r = feishu_get(url)
    vals = r.get("data", {}).get("valueRange", {}).get("values")
    if vals and vals[0] and vals[0][0]:
        v = str(vals[0][0]).strip()
        if v:
            return True, v
    return False, ""

def find_date_row(sheet_id, target, max_rows=500):
    for row in range(1, max_rows):
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}"
        r = feishu_get(url)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return None
        if str(vals[0][0]).strip() == target:
            return row
    return None

def find_last_data_row(sheet_id, max_rows=500):
    last = 0
    for row in range(1, max_rows):
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!A{row}:A{row}"
        r = feishu_get(url)
        vals = r.get("data", {}).get("valueRange", {}).get("values")
        if not vals or not vals[0] or not (vals[0][0] or "").strip():
            return last
        last = row
    return last

def write_sheet(sheet_id, header, data_row, label):
    has_header, _ = read_a1(sheet_id)
    if not has_header:
        ok, code, msg = put_row(sheet_id, 1, header)
        if not ok:
            print(f"  ❌ {label}: header fail code={code} msg={msg}")
            return False
        ok, code, msg = put_row(sheet_id, 2, data_row)
        if ok:
            print(f"  ✅ {label}: first write (R1=header, R2=data)")
        else:
            print(f"  ❌ {label}: data fail code={code} msg={msg}")
        return ok

    existing = find_date_row(sheet_id, today_display)
    if existing:
        ok, code, msg = put_row(sheet_id, existing, data_row)
        msg_text = f"overwrite R{existing}"
    else:
        tr = find_last_data_row(sheet_id) + 1
        ok, code, msg = put_row(sheet_id, tr, data_row)
        msg_text = f"append R{tr}"

    if ok:
        print(f"  ✅ {label}: {msg_text}")
    else:
        print(f"  ❌ {label}: fail code={code} msg={msg}")
    return ok

# ── Direction helpers ──
def get_direction(name):
    dm = {
        "中际旭创":"光模块/CPO","新易盛":"光模块/CPO","天孚通信":"光模块/CPO",
        "海光信息":"AI服务器/算力","寒武纪":"AI服务器/算力","工业富联":"AI服务器/算力",
        "亨通光电":"光纤光缆","中天科技":"光纤光缆","长飞光纤":"光纤光缆",
        "京东方Ａ":"面板/显示","生益科技":"PCB","沪电股份":"PCB",
        "东山精密":"PCB","胜宏科技":"PCB",
        "兆易创新":"存储芯片","佰维存储":"存储芯片",
        "长电科技":"先进封装","沪硅产业":"半导体材料",
        "中芯国际":"芯片设计","澜起科技":"芯片设计","中微公司":"半导体设备",
        "长川科技":"半导体设备","风华高科":"电子元器件",
        "沪硅产业":"半导体材料","东材科技":"化工",
        "阳光电源":"光伏","宁德时代":"锂电池","立讯精密":"消费电子",
        "中兴通讯":"通信设备","中国巨石":"化工","埃斯顿":"机器人/自动化",
    }
    return dm.get(name, "")

from collections import Counter
def main_direction(top10):
    c = Counter(get_direction(s["name"]) for s in top10)
    return c.most_common(1)[0][0]

def classify_concentration(pct):
    if pct > 55: return "严重分化"
    if pct > 50: return "一九分化"
    if pct > 40: return "偏集中"
    return "正常"

# ── Build rows ──
# Snapshot
t = data["tiers"]
total = data["total_amount_yi"]
rem = total - t["1000"]["amount_yi"]
rem_stocks = data["total_stocks"] - 1000
direction = main_direction(data["top_stocks"][:10])
cat = classify_concentration(t["300"]["pct_of_market"])

snapshot_header = ["日期","总量(亿)","前10成交","前10占比","前20成交","前20占比","前50成交","前50占比",
    "前100成交","前100占比","前200成交","前200占比","前300成交","前300占比",
    "前500成交","前500占比","前1000成交","前1000占比","剩余数量","剩余成交(亿)","分化判定","主线"]

snapshot_row = [
    today_display, round(total),
    t["10"]["amount_yi"], f"{t['10']['pct_of_market']}%",
    t["20"]["amount_yi"], f"{t['20']['pct_of_market']}%",
    t["50"]["amount_yi"], f"{t['50']['pct_of_market']}%",
    t["100"]["amount_yi"], f"{t['100']['pct_of_market']}%",
    t["200"]["amount_yi"], f"{t['200']['pct_of_market']}%",
    t["300"]["amount_yi"], f"{t['300']['pct_of_market']}%",
    t["500"]["amount_yi"], f"{t['500']['pct_of_market']}%",
    t["1000"]["amount_yi"], f"{t['1000']['pct_of_market']}%",
    rem_stocks, round(rem), cat, direction,
]

# Top detail
top_header = ["日期","#","代码","名称","涨跌%","成交(亿)","占比%","方向"]
top_rows = []
for i, s in enumerate(data["top_stocks"][:10]):
    top_rows.append([
        today_display, i+1, s["code"], s["name"],
        f"{s['change_pct']:+.2f}", s["amount_yi"],
        f"{s['pct_of_market']}%", get_direction(s["name"]) or "",
    ])

# Liquidity
liq = data["liquidity"]
tail_pct = liq[0]["pct"] + liq[1]["pct"]
liq_header = ["日期","<1000万 数量","<1000万 占比","1000-5000万 数量","1000-5000万 占比",
    "5000万-1亿 数量","5000万-1亿 占比","1亿-5亿 数量","1亿-5亿 占比",
    ">5亿 数量",">5亿 占比","尾部占比"]
liq_row = [
    today_display,
    liq[0]["count"], f"{liq[0]['pct']}%",
    liq[1]["count"], f"{liq[1]['pct']}%",
    liq[2]["count"], f"{liq[2]['pct']}%",
    liq[3]["count"], f"{liq[3]['pct']}%",
    liq[4]["count"], f"{liq[4]['pct']}%",
    f"{tail_pct}%",
]

# ── Publish ──
print("📊 成交集中度 → 飞书表格")
print(f"   日期: {today_display}  总量: {total}亿  前300占比: {t['300']['pct_of_market']}%\n")

write_sheet(SHEETS["snapshot"], snapshot_header, snapshot_row, "每日快照")

# Top detail
sid_top = SHEETS["top"]
has_header_top, _ = read_a1(sid_top)
if not has_header_top:
    put_row(sid_top, 1, top_header)
    start = 2
    mode = "first"
else:
    exist = find_date_row(sid_top, today_display)
    if exist:
        start = exist
        mode = "overwrite"
    else:
        start = find_last_data_row(sid_top) + 1
        mode = "append"

for i, row in enumerate(top_rows):
    ok, code, msg = put_row(sid_top, start + i, row)
    if not ok:
        print(f"  ❌ 头部明细: R{start+i} fail code={code}")
    time.sleep(0.3)
print(f"  ✅ 头部明细: {mode} 10 rows (from R{start})")

write_sheet(SHEETS["liquidity"], liq_header, liq_row, "流动性趋势")

print(f"\n✅ 全部完成!")
print(f"https://my.feishu.cn/sheets/{SPREADSHEET_TOKEN}")
