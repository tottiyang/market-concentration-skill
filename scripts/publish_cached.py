#!/usr/bin/env python3
"""用缓存的 JSON 数据写入飞书表格，绕过实时的 akshare 调用"""
import json, sys, os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

# 缓存的 analyze 输出（来自首次运行）
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

# 注入模块级 analyze 函数
import publish_feishu as pf
pf.analyze = lambda: data

pf.main()
