#!/usr/bin/env python3
"""使用缓存数据直接写入飞书表格，避免重新调API"""
import json, os, sys, time, urllib.request
from datetime import date
from collections import Counter

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.expanduser("~/.qclaw/skills-config/feishu/tokens/user_token.json")
CACHE_FILE = os.path.join(SKILL_DIR, "scripts", ".last_data.json")

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
        print(f"  {'✅' if ok else '❌'} {label}: 覆盖 行{existing}" if ok else
              f"  ❌ {label}: 覆盖失败 code={code}")
        return ok
    next_row = find_last_data_row(sheet_id, token) + 1
    ok, code, msg = put_row(sheet_id, next_row, data_row, token)
    print(f"  {'✅' if ok else '❌'} {label}: 追加 行{next_row}" if ok else
              f"  ❌ {label}: 追加失败 code={code}")
    return ok

def main():
    token = load_token()
    today_str = date.today().strftime("%m-%d")

    # 从缓存读取数据
    if not os.path.exists(CACHE_FILE):
        print(f"❌ 缓存文件不存在: {CACHE_FILE}")
        sys.exit(1)
    with open(CACHE_FILE) as f:
        data = json.load(f)

    t = data["tiers"]
    total = data["total_amount_yi"]
    rem = total - t["1000"]["amount_yi"]
    rem_stocks = data["total_stocks"] - 1000

    top10_dir = Counter(classify_direction(s["name"]) for s in data["top_stocks"][:10]).most_common(1)
    top10_dir_name = top10_dir[0][0] if top10_dir else ""

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
        rem_stocks, round(rem, 0), cat, top10_dir_name,
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
        if ok:
            print(f"  ✅ 头部明细 行{start+i}: {row[3]}")
        else:
            print(f"  ❌ 头部明细 行{start+i}: {row[3]} 失败 code={code}")
        time.sleep(0.3)
    print(f"  ✅ 头部明细: {mode} 10行 (从行{start})")

    # 流动性趋势
    init_or_write_row(SHEETS["liquidity"], HEADERS["liquidity"], liquidity_row, today_str, token, "流动性趋势")

    print(f"\n✅ 全部完成!")
    print(f"https://my.feishu.cn/sheets/{SPREADSHEET_TOKEN}")

if __name__ == "__main__":
    main()
