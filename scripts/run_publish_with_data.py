#!/usr/bin/env python3
"""用缓存的数据直接写入飞书，避免重新调API"""
import json, sys, os, importlib.util

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(SKILL_DIR, "scripts", ".last_data.json")

# 写入缓存
cache = {
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
        {"code":"sz300502","name":"新易盛","price":526.0,"change_pct":-4.55,"amount_yi":356.1,"pct_of_market":1.38},
        {"code":"sz300308","name":"中际旭创","price":1124.0,"change_pct":-2.0,"amount_yi":345.59,"pct_of_market":1.34},
        {"code":"sh600487","name":"亨通光电","price":102.4,"change_pct":-4.19,"amount_yi":231.07,"pct_of_market":0.9},
        {"code":"sz000725","name":"京东方Ａ","price":5.83,"change_pct":-3.32,"amount_yi":194.36,"pct_of_market":0.75},
        {"code":"sh600522","name":"中天科技","price":49.27,"change_pct":-1.85,"amount_yi":143.63,"pct_of_market":0.56},
        {"code":"sh600498","name":"烽火通信","price":60.99,"change_pct":9.5,"amount_yi":142.59,"pct_of_market":0.55},
        {"code":"sh603986","name":"兆易创新","price":483.5,"change_pct":0.55,"amount_yi":142.11,"pct_of_market":0.55},
        {"code":"sz002384","name":"东山精密","price":210.99,"change_pct":-0.6,"amount_yi":139.84,"pct_of_market":0.54},
        {"code":"sz300394","name":"天孚通信","price":412.3,"change_pct":0.3,"amount_yi":137.79,"pct_of_market":0.54},
        {"code":"sh688256","name":"寒武纪","price":1219.5,"change_pct":-0.93,"amount_yi":136.32,"pct_of_market":0.53},
        {"code":"sh600183","name":"生益科技","price":149.73,"change_pct":1.93,"amount_yi":125.28,"pct_of_market":0.49},
        {"code":"sz000636","name":"风华高科","price":64.3,"change_pct":7.51,"amount_yi":116.94,"pct_of_market":0.45},
        {"code":"sh688041","name":"海光信息","price":289.84,"change_pct":1.77,"amount_yi":116.36,"pct_of_market":0.45},
        {"code":"sz002428","name":"云南锗业","price":88.24,"change_pct":10.0,"amount_yi":112.82,"pct_of_market":0.44},
        {"code":"sh601138","name":"工业富联","price":69.52,"change_pct":-2.26,"amount_yi":103.44,"pct_of_market":0.4},
        {"code":"sz300750","name":"宁德时代","price":382.2,"change_pct":-1.62,"amount_yi":103.02,"pct_of_market":0.4},
        {"code":"sz000657","name":"中钨高新","price":77.95,"change_pct":6.93,"amount_yi":102.58,"pct_of_market":0.4},
        {"code":"sz002463","name":"沪电股份","price":126.91,"change_pct":-2.83,"amount_yi":99.05,"pct_of_market":0.38},
        {"code":"sh688008","name":"澜起科技","price":228.7,"change_pct":-1.0,"amount_yi":98.58,"pct_of_market":0.38},
        {"code":"sh688525","name":"佰维存储","price":324.27,"change_pct":2.29,"amount_yi":95.77,"pct_of_market":0.37},
        {"code":"sz000063","name":"中兴通讯","price":37.81,"change_pct":-1.59,"amount_yi":94.94,"pct_of_market":0.37},
        {"code":"sh600584","name":"长电科技","price":71.95,"change_pct":-2.84,"amount_yi":92.5,"pct_of_market":0.36},
        {"code":"sz300136","name":"信维通信","price":99.28,"change_pct":3.0,"amount_yi":88.95,"pct_of_market":0.35},
        {"code":"sh601899","name":"紫金矿业","price":27.33,"change_pct":-1.34,"amount_yi":88.07,"pct_of_market":0.34},
        {"code":"sz300476","name":"胜宏科技","price":325.48,"change_pct":-1.45,"amount_yi":87.32,"pct_of_market":0.34},
        {"code":"sz002281","name":"光迅科技","price":205.4,"change_pct":1.38,"amount_yi":86.38,"pct_of_market":0.34},
        {"code":"sh688012","name":"中微公司","price":303.12,"change_pct":4.85,"amount_yi":82.23,"pct_of_market":0.32},
        {"code":"sz300346","name":"南大光电","price":66.71,"change_pct":8.09,"amount_yi":82.15,"pct_of_market":0.32},
        {"code":"sh688017","name":"绿的谐波","price":367.0,"change_pct":-13.44,"amount_yi":81.93,"pct_of_market":0.32},
        {"code":"sh688498","name":"源杰科技","price":1452.0,"change_pct":0.14,"amount_yi":81.6,"pct_of_market":0.32}
    ],
    "liquidity": [
        {"range":"<1000万","count":74,"pct":1.3},
        {"range":"1000万-5000万","count":1376,"pct":25.0},
        {"range":"5000万-1亿","count":1061,"pct":19.3},
        {"range":"1亿-5亿","count":1934,"pct":35.1},
        {"range":">5亿","count":1065,"pct":19.3}
    ]
}

with open(CACHE_FILE, "w") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

# 模拟 analyze() 返回缓存数据
spec = importlib.util.spec_from_file_location("analyze", os.path.join(SKILL_DIR, "scripts", "analyze.py"))
analyze_mod = importlib.util.module_from_spec(spec)

# monkeypatch: 让 analyze() 返回缓存
def mock_analyze():
    return cache

analyze_mod.analyze = mock_analyze
sys.modules["analyze"] = analyze_mod

# 现在导入 publish 模块
pub_spec = importlib.util.spec_from_file_location("publish", os.path.join(SKILL_DIR, "scripts", "publish_feishu.py"))
pub_mod = importlib.util.module_from_spec(pub_spec)
sys.modules["publish_feishu"] = pub_mod

# 配好后再加载
pub_spec.loader.exec_module(pub_mod)

# 替换它的 analyze 引用
pub_mod.main()
