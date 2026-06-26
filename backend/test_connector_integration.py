"""
端到端集成测试 — 用真实凭据验证连接器
"""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 初始化连接器注册
import app.connectors.gc_connector
import app.connectors.coze_connector
from app.connectors import get_connector, PlatformCredential, list_platforms

GC_APPID = "699d4e01e4b05356ecdb7336"
GC_SECRET = "ZUKzVOOAcfRPAbpJtjwXSUeoooXmuwwh"

COZE_DOMAIN = "https://6dzhzw2vvm.coze.site/stream_run"
COZE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImFjY2ZkODkzLTRlMTAtNGFiOC1iMTk5LWY5NTBiMzA0MDhmZCJ9.eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbInROdkg1UmNzaFdhNlVsU1hyNmxZNGc1bW1BRGY1dm1pIl0sImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzgyNDU0NTAyLCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3NjQ5OTU2MzMyMDI3NTEwODI0Iiwic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3NjU1NTgzNzkzMDc1NDUzOTk4In0.RYrrJnvdLlYc0ZzUJke2pGxcj5cMtEPwYqjgRCSezQ7IrOKqHA3PPEGApCGGTLu8-Xk8tY_fc_lxXHqdM7AcX13I7hW3s9h3toXW1zApd5nq_q_Kw_N_iBO6kN3EFoMK7SrmLOUjG8PTrzKs5oS5SAM3EXgcudo2bHfmPQRG_e5__UHAF8eszlB-69ckSy20ZUkySanHMQxonhFWzI7W10bEuIOSRHC6IiDP9YsHXYQ_1RKcWtQT7uyrc0C4tVwhi4LdoO_ndojsEXOEyogu_av4BKgPeSXTf27dmVCDIL9dwLEnXfAVgz7V_Wlpsw05X-qD4aOAv1K5cJV2BBmXtA"


def hr(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


async def test_gc_connector():
    hr("🔵 GC 连接器测试")

    gc = get_connector("gc")
    cred = PlatformCredential(platform_type="gc", appid=GC_APPID, secret_key=GC_SECRET)

    # 1. 验证凭据
    ok = await gc.validate_credentials(cred)
    print(f"  验证凭据: {'✅' if ok else '❌'}")

    # 2. 列出 Bot
    bots = await gc.list_bots(cred)
    print(f"  Bot 发现: {len(bots)} 个")
    for b in bots:
        print(f"    - {b.name} (id={b.bot_id[:20]}...)")

    # 3. 非流式对话
    print(f"  非流式对话...")
    result = await gc.chat(cred, {"bot_id": bots[0].bot_id, "user_id": "test_001"},
                           [{"role": "user", "content": "你好，简单介绍一下你自己"}])
    print(f"    ✅ tokens={result.tokens_used}")
    print(f"    💬 {result.content[:200]}")

    # 4. 流式对话
    print(f"  流式对话...")
    full = ""
    async for chunk in gc.chat_stream(cred, {"bot_id": bots[0].bot_id},
                                       [{"role": "user", "content": "1+1=?"}]):
        if chunk == "[DONE]":
            break
        full += chunk
    print(f"    ✅ 流式完成, 共 {len(full)} 字符")
    print(f"    💬 {full[:200]}")


async def test_coze_connector():
    hr("🤖 COZE 连接器测试")

    coze = get_connector("coze")
    cred = PlatformCredential(platform_type="coze", api_token=COZE_TOKEN, domain=COZE_DOMAIN)

    # 1. 验证凭据
    ok = await coze.validate_credentials(cred)
    print(f"  验证凭据: {'✅' if ok else '❌'}")

    # 2. 列出 Bot
    bots = await coze.list_bots(cred)
    print(f"  Bot 发现: {len(bots)} 个")
    for b in bots:
        print(f"    - {b.name}")

    # 3. 非流式对话
    print(f"  非流式对话...")
    result = await coze.chat(cred, {}, [{"role": "user", "content": "你好，简单介绍你的功能"}])
    print(f"    ✅ tokens={result.tokens_used}")
    print(f"    💬 {result.content[:200]}")

    # 4. 流式对话
    print(f"  流式对话...")
    full = ""
    async for chunk in coze.chat_stream(cred, {},
                                         [{"role": "user", "content": "1+1等于几？"}]):
        if chunk == "[DONE]":
            break
        full += chunk
    print(f"    ✅ 流式完成, 共 {len(full)} 字符")
    print(f"    💬 {full[:200]}")


async def main():
    print("╔══════════════════════════════════════════╗")
    print("║  Connector Integration Tests             ║")
    print("╚══════════════════════════════════════════╝")

    # 列出平台
    platforms = list_platforms()
    print(f"\n注册平台: {[p['label'] for p in platforms]}")

    try:
        await test_gc_connector()
    except Exception as e:
        print(f"  ⚠️ GC 测试异常 (平台配置问题): {e}")

    await test_coze_connector()

    print("\n" + "="*55)
    print("  集成测试完成")

if __name__ == "__main__":
    asyncio.run(main())
