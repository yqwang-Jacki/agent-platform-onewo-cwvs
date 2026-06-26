"""
Final verification: COZE connector full flow
"""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import app.connectors.coze_connector
from app.connectors import get_connector, PlatformCredential

COZE_DOMAIN = "https://6dzhzw2vvm.coze.site/stream_run"
COZE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImFjY2ZkODkzLTRlMTAtNGFiOC1iMTk5LWY5NTBiMzA0MDhmZCJ9.eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbInROdkg1UmNzaFdhNlVsU1hyNmxZNGc1bW1BRGY1dm1pIl0sImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzgyNDU0NTAyLCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3NjQ5OTU2MzMyMDI3NTEwODI0Iiwic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3NjU1NTgzNzkzMDc1NDUzOTk4In0.RYrrJnvdLlYc0ZzUJke2pGxcj5cMtEPwYqjgRCSezQ7IrOKqHA3PPEGApCGGTLu8-Xk8tY_fc_lxXHqdM7AcX13I7hW3s9h3toXW1zApd5nq_q_Kw_N_iBO6kN3EFoMK7SrmLOUjG8PTrzKs5oS5SAM3EXgcudo2bHfmPQRG_e5__UHAF8eszlB-69ckSy20ZUkySanHMQxonhFWzI7W10bEuIOSRHC6IiDP9YsHXYQ_1RKcWtQT7uyrc0C4tVwhi4LdoO_ndojsEXOEyogu_av4BKgPeSXTf27dmVCDIL9dwLEnXfAVgz7V_Wlpsw05X-qD4aOAv1K5cJV2BBmXtA"

async def main():
    coze = get_connector("coze")
    cred = PlatformCredential(platform_type="coze", api_token=COZE_TOKEN, domain=COZE_DOMAIN)

    # Validate
    ok = await coze.validate_credentials(cred)
    print(f"Validate: {'PASS' if ok else 'FAIL'}")

    # List bots
    bots = await coze.list_bots(cred)
    print(f"Bots: {len(bots)} found")
    
    # Chat
    result = await coze.chat(cred, {}, [{"role":"user","content":"hi"}])
    print(f"Chat: tokens={result.tokens_used}, content_len={len(result.content)}")
    print(f"Content: {result.content[:150]}")

    # Stream
    full = ""
    async for chunk in coze.chat_stream(cred, {}, [{"role":"user","content":"1+1"}]):
        if chunk == "[DONE]": break
        full += chunk
    print(f"\nStream: {len(full)} chars")

    print("\n=== All COZE tests PASSED ===")

asyncio.run(main())
