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

import sqlite3

# iron-sentinel 数据库路径
DB_PATH = os.path.expanduser("~/.qclaw/skills/iron-sentinel/data/stock_data.db")

def load_direction_map():
    """从 iron-sentinel 数据库动态加载板块分类映射
    
    返回: dict {stock_name: direction_label}
    """
    if not os.path.exists(DB_PATH):
        print(f"[WARN] 数据库不存在: {DB_PATH}，回退到静态 DIRECTION_MAP")
        return _build_static_map()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 查询概念板块 + 行业分类，建立 name -> 板块 映射
        # 优先级：概念板块 > 三级行业 > 二级行业
        cursor.execute("""
            SELECT s.stock_name, 
                   GROUP_CONCAT(DISTINCT cb.board_name) as concepts,
                   GROUP_CONCAT(DISTINCT i3.name) as industry_l3,
                   GROUP_CONCAT(DISTINCT i2.name) as industry_l2
            FROM stocks s
            LEFT JOIN stock_concept sc ON s.stock_code = sc.stock_code
            LEFT JOIN concept_boards cb ON sc.board_code = cb.board_code
            LEFT JOIN stock_industry si ON s.stock_code = si.stock_code AND si.level = 'L3'
            LEFT JOIN industry_l3 i3 ON si.industry_code = i3.code
            LEFT JOIN stock_industry si2 ON s.stock_code = si2.stock_code AND si2.level = 'L2'
            LEFT JOIN industry_l2 i2 ON si2.industry_code = i2.code
            WHERE s.listing_status = 'Normal'
            GROUP BY s.stock_code
        """)
        
        direction_map = {}
        for row in cursor.fetchall():
            name, concepts, industry_l3, industry_l2 = row
            direction = _classify_stock(name, concepts or "", industry_l3 or "", industry_l2 or "")
            if direction:
                direction_map[name] = direction
        
        conn.close()
        print(f"[INFO] 动态加载完成，共 {len(direction_map)} 只个股有分类")
        return direction_map
        
    except Exception as e:
        print(f"[WARN] 数据库查询失败: {e}，回退到静态 DIRECTION_MAP")
        return _build_static_map()


def _classify_stock(name, concepts, industry_l3, industry_l2):
    """根据概念和行业分类个股方向"""
    c = (concepts + "," + industry_l3 + "," + industry_l2).lower()
    
    # 存储芯片
    if any(k in c for k in ['存储芯片', '存储器', 'nand', 'nor', 'dram']):
        return "存储芯片"
    # 光模块/CPO
    if any(k in c for k in ['光模块', 'cpo', '共封装光学', '光通信']):
        return "光模块/CPO"
    # 光纤光缆
    if any(k in c for k in ['光纤', '光缆', '光通信']):
        return "光纤光缆"
    # AI服务器/算力
    if any(k in c for k in ['ai服务器', '算力', '服务器', 'ai芯片', 'gpu', '寒武纪', '海光']):
        return "AI服务器/算力"
    # PCB
    if any(k in c for k in ['pcb', '印制电路板', '电路板']):
        return "PCB"
    # 先进封装
    if any(k in c for k in ['先进封装', '封装测试', 'chiplet', '扇出型封装']):
        return "先进封装"
    # 半导体设备
    if any(k in c for k in ['半导体设备', '刻蚀', '薄膜沉积', '光刻', '清洗设备']):
        return "半导体设备"
    # 半导体材料
    if any(k in c for k in ['半导体材料', '硅片', '光刻胶', '电子特气', '靶材']):
        return "半导体材料"
    # 芯片设计
    if any(k in c for k in ['芯片设计', '集成电路设计', '模拟芯片', '数字芯片', 'soc']):
        return "芯片设计"
    # 面板/显示
    if any(k in c for k in ['面板', '显示器件', 'oled', 'lcd', 'led']):
        return "面板/显示"
    # 锂电池
    if any(k in c for k in ['锂电池', '动力电池', '固态电池', '磷酸铁锂']):
        return "锂电池"
    # 光伏
    if any(k in c for k in ['光伏', '太阳能电池', '逆变器', '组件', '硅片']):
        return "光伏"
    # 新能源（广义，包含风电、储能等）
    if any(k in c for k in ['新能源', '储能', '风电', '氢能源']):
        return "新能源"
    # 通信设备
    if any(k in c for k in ['通信设备', '通信终端', '基站', '5g']):
        return "通信设备"
    # 消费电子
    if any(k in c for k in ['消费电子', '智能手机', '可穿戴', '耳机', '音箱']):
        return "消费电子"
    # 计算机设备
    if any(k in c for k in ['计算机设备', '服务器硬件', '工作站']):
        return "计算机设备"
    # 软件/IT服务
    if any(k in c for k in ['软件开发', 'it服务', 'saas', '云计算服务']):
        return "软件/IT服务"
    
    # 静态兜底：检查是否在 DIRECTION_MAP 中
    for direction, names in STATIC_DIRECTION_MAP:
        if name in names:
            return direction
    
    return None


def _build_static_map():
    """从静态 DIRECTION_MAP 构建 name -> direction 字典"""
    m = {}
    for direction, names in STATIC_DIRECTION_MAP:
        for n in names:
            m[n] = direction
    return m


# 静态 DIRECTION_MAP 作为兜底
STATIC_DIRECTION_MAP = [
    ("存储芯片", ["兆易创新","佰维存储","江波龙","德明利","朗科科技","普冉股份","东芯股份","恒烁股份","聚辰股份"]),
    ("光模块/CPO", ["中际旭创","新易盛","天孚通信","光迅科技","剑桥科技","华工科技","博创科技","太辰光","德科立","联特科技"]),
    ("光纤光缆", ["亨通光电","长飞光纤","中天科技","通光线缆","永鼎股份","特发信息","汇源通信"]),
    ("AI服务器/算力", ["工业富联","浪潮信息","中科曙光","紫光股份","寒武纪","海光信息","龙芯中科","景嘉微"]),
    ("PCB", ["东山精密","沪电股份","胜宏科技","深南电路","鹏鼎控股","生益科技","景旺电子","世运电路","方正科技"]),
    ("先进封装", ["长电科技","通富微电","华天科技","晶方科技","甬矽电子","大港股份","文一科技"]),
    ("半导体设备", ["北方华创","中微公司","拓荆科技","华海清科","芯源微","盛美上海","至纯科技"]),
    ("半导体材料", ["沪硅产业","立昂微","安集科技","鼎龙股份","江丰电子","清溢光电","南大光电"]),
    ("芯片设计", ["澜起科技","韦尔股份","兆易创新","圣邦股份","卓胜微","思瑞浦","艾为电子","纳芯微","晶晨股份","瑞芯微"]),
    ("面板/显示", ["京东方Ａ","TCL科技","维信诺","彩虹股份","深天马Ａ","龙腾光电","和辉光电"]),
    ("新能源", ["宁德时代","阳光电源","隆基绿能","通威股份","TCL中环","晶澳科技","天合光能","晶科能源","亿纬锂能","比亚迪"]),
    ("锂电池", ["宁德时代","亿纬锂能","国轩高科","欣旺达","孚能科技","鹏辉能源","珠海冠宇","蔚蓝锂芯"]),
    ("光伏", ["阳光电源","隆基绿能","通威股份","TCL中环","晶澳科技","天合光能","晶科能源","正泰电器","福斯特","福莱特"]),
    ("通信设备", ["中兴通讯","烽火通信","亨通光电","中天科技","长飞光纤","武汉凡谷","大富科技","盛路通信"]),
    ("消费电子", ["立讯精密","歌尔股份","蓝思科技","领益智造","鹏鼎控股","环旭电子","长盈精密","水晶光电"]),
    ("计算机设备", ["浪潮信息","中科曙光","中国长城","同方股份","广电运通","新大陆","证通电子"]),
    ("软件/IT服务", ["金山办公","科大讯飞","恒生电子","宝信软件","用友网络","广联达","深信服","奇安信"]),
]

# 全局缓存，首次加载
direction_map_cache = None

def get_direction_map():
    """获取方向映射（带缓存）"""
    global direction_map_cache
    if direction_map_cache is None:
        direction_map_cache = load_direction_map()
    return direction_map_cache


def get_direction(name):
    """获取个股方向分类"""
    return get_direction_map().get(name)


# 删除旧的 DIRECTION_MAP 引用，改为使用 get_direction()
# DIRECTION_MAP = ... (已删除)


def classify_direction(name):
    """根据个股名称动态查询板块分类"""
    return get_direction(name) or ""


# 删除旧的 DIRECTION_MAP 引用，改为使用 get_direction()
# DIRECTION_MAP = ... (已删除)


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
            f"{s['pct_of_market']}%", get_direction(s["name"]) or "",
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
    """根据个股名称动态查询板块分类"""
    return get_direction(name) or "其他"


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
