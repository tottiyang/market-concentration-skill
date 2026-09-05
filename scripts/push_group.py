#!/usr/bin/env python3
"""推送到飞书群机器人 webhook（两融 cron 用）

从 ~/.zshrc 读取 CHAT_BOT_URL（cron 环境不加载 shell profile，直接解析文件）。
用法：
    python3 push_group.py --text "要推送的消息"
    python3 push_group.py --file /tmp/msg.txt      # 从文件读内容（UTF-8）

退出码：0=成功/未配置跳过, 1=失败
"""
import sys, os, re, json, argparse
from pathlib import Path

import requests


def load_zshrc_env(name: str) -> str:
    """cron 环境不加载 shell profile，直接从 ~/.zshrc 读指定 env 变量。"""
    try:
        val = os.environ.get(name)
        if val:
            return val
        zshrc = Path.home() / ".zshrc"
        if not zshrc.exists():
            return ""
        content = zshrc.read_text(encoding="utf-8")
        m = re.search(rf'^\s*export\s+{name}\s*=\s*"?([^"\n#]*)"?', content, re.MULTILINE)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""


def push_group(text: str) -> bool:
    """推 text 到飞书群机器人 webhook（CHAT_BOT_URL）。返回 True=成功。"""
    url = load_zshrc_env("CHAT_BOT_URL")
    if not url:
        print("[群] 未配置 CHAT_BOT_URL，跳过群推送", file=sys.stderr)
        return False
    try:
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        resp = requests.post(url, json=payload, timeout=15)
        rj = resp.json()
        if rj.get("code") == 0 or rj.get("StatusCode") == 0:
            print("[群] 推送成功")
            return True
        print(f"[群] 推送失败 code={rj.get('code') or rj.get('StatusCode')} "
              f"msg={rj.get('msg') or rj.get('StatusMessage')}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[群] 异常: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="推送到飞书群机器人 webhook")
    parser.add_argument("--text", help="直接指定消息文本")
    parser.add_argument("--file", help="从文件读取消息内容（UTF-8）")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ 读取文件失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 无参数时从 stdin 读取（便于管道）
        text = sys.stdin.read()

    text = text.strip()
    if not text:
        print("❌ 无消息内容", file=sys.stderr)
        sys.exit(1)

    ok = push_group(text)
    sys.exit(0 if ok else 1)
