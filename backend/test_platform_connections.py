"""
测试两个平台的 API 连接
1. GC 平台: 先获取 token，再尝试对话
2. COZE 平台: 用 API Token 调 stream_run
"""

import asyncio
import httpx
import json
import sys
import io

# Fix Windows GBK encoding issue
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# GC 平台配置
# ============================================================
GC_AUTH_URL = "https://gc.4009515151.com/aics/auth/getToken"
GC_APPID = "699d4e01e4b05356ecdb7336"
GC_SECRET = "ZUKzVOOAcfRPAbpJtjwXSUeoooXmuwwh"

# ============================================================
# COZE 平台配置
# ============================================================
COZE_STREAM_URL = "https://6dzhzw2vvm.coze.site/stream_run"
COZE_API_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImFjY2ZkODkzLTRlMTAtNGFiOC1iMTk5LWY5NTBiMzA0MDhmZCJ9.eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbInROdkg1UmNzaFdhNlVsU1hyNmxZNGc1bW1BRGY1dm1pIl0sImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzgyNDU0NTAyLCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3NjQ5OTU2MzMyMDI3NTEwODI0Iiwic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3NjU1NTgzNzkzMDc1NDUzOTk4In0.RYrrJnvdLlYc0ZzUJke2pGxcj5cMtEPwYqjgRCSezQ7IrOKqHA3PPEGApCGGTLu8-Xk8tY_fc_lxXHqdM7AcX13I7hW3s9h3toXW1zApd5nq_q_Kw_N_iBO6kN3EFoMK7SrmLOUjG8PTrzKs5oS5SAM3EXgcudo2bHfmPQRG_e5__UHAF8eszlB-69ckSy20ZUkySanHMQxonhFWzI7W10bEuIOSRHC6IiDP9YsHXYQ_1RKcWtQT7uyrc0C4tVwhi4LdoO_ndojsEXOEyogu_av4BKgPeSXTf27dmVCDIL9dwLEnXfAVgz7V_Wlpsw05X-qD4aOAv1K5cJV2BBmXtA"


async def test_gc():
    """测试 GC 平台"""
    print("=" * 60)
    print("🔵 测试 GC 平台")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: 获取 token
        print(f"\n📡 Step 1: 获取 Token")
        print(f"   URL: {GC_AUTH_URL}")
        print(f"   Body: appid={GC_APPID}, secretKey={'*' * 6}")

        try:
            resp = await client.post(
                GC_AUTH_URL,
                json={"appid": GC_APPID, "secretKey": GC_SECRET},
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Headers: {dict(resp.headers)}")
            body_text = resp.text[:2000]
            print(f"   Body: {body_text}")

            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Token 获取成功!")
                print(f"   🔑 完整响应: {json.dumps(data, ensure_ascii=False, indent=2)}")

                token = data.get("data", {}).get("token") or data.get("token")
                print(f"   📌 Token: {token[:50] if token else 'N/A'}...")

                # Step 2: 尝试获取 Bot 列表
                print(f"\n📡 Step 2: 获取 Bot 列表")
                if token:
                    try:
                        # 尝试几个可能端点
                        possible_endpoints = [
                            "https://gc.4009515151.com/aics/bot/list",
                            "https://gc.4009515151.com/aics/chat/list",
                            "https://gc.4009515151.com/aics/api/bot/list",
                        ]
                        for url in possible_endpoints:
                            try:
                                r2 = await client.get(
                                    url,
                                    headers={"Authorization": f"Bearer {token}"},
                                )
                                print(f"   GET {url} → {r2.status_code}")
                                if r2.status_code == 200:
                                    print(f"   Body: {r2.text[:500]}")
                                    print(f"   ✅ 命中! 此端点可用")
                                    break
                            except Exception as e2:
                                print(f"   GET {url} → 错误: {e2}")

                    except Exception as e:
                        print(f"   ❌ Bot 列表请求失败: {e}")
            else:
                print(f"   ❌ Token 获取失败")

        except Exception as e:
            print(f"   ❌ 连接失败: {e}")


async def test_coze():
    """测试 COZE 平台"""
    print("\n" + "=" * 60)
    print("🤖 测试 COZE 平台")
    print("=" * 60)

    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    # 测试用的简单消息
    payload = {
        "content": {
            "query": {
                "prompt": [
                    {
                        "type": "text",
                        "content": {"text": "你好，请简单介绍一下你自己"},
                    }
                ]
            }
        },
        "type": "query",
        "session_id": "test_session_001",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        print(f"\n📡 调用 stream_run")
        print(f"   URL: {COZE_STREAM_URL}")
        print(f"   Token 前20字符: {COZE_API_TOKEN[:20]}...")

        try:
            async with client.stream(
                "POST",
                COZE_STREAM_URL,
                json=payload,
                headers=headers,
            ) as resp:
                print(f"   Status: {resp.status_code}")
                print(f"   Headers: {dict(resp.headers)}")
                print(f"\n   📥 SSE 事件流:")

                event_count = 0
                full_answer = ""

                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        event_count += 1
                        data_str = line[5:].strip()
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type", "unknown")

                            if event_type == "answer":
                                answer = event.get("content", {}).get("answer", "")
                                full_answer += answer
                                print(f"   [answer] {answer[:100]}")

                            elif event_type == "message_end":
                                msg_end = event.get("content", {}).get("message_end", {})
                                token_cost = msg_end.get("token_cost", {})
                                print(f"   [message_end] tokens={token_cost}")

                            elif event_type == "error":
                                print(f"   [error] {json.dumps(event, ensure_ascii=False)[:300]}")

                            else:
                                print(f"   [{event_type}] {json.dumps(event, ensure_ascii=False)[:200]}")

                        except json.JSONDecodeError:
                            print(f"   [raw] {data_str[:200]}")
                    elif line.strip():
                        print(f"   [other] {line[:200]}")

                print(f"\n   📊 总计: {event_count} 个事件")
                print(f"   💬 完整回答: {full_answer[:500]}")
                print(f"   {'✅ 成功!' if full_answer else '⚠️ 无回答内容'}")

        except Exception as e:
            print(f"   ❌ 连接失败: {e}")
            import traceback
            traceback.print_exc()


async def main():
    await test_gc()
    await test_coze()


if __name__ == "__main__":
    asyncio.run(main())
