"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login, isLoggedIn } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (!account || !password) return setErr("请填写账号和密码");
    setLoading(true);
    try {
      await login(account, password);
      router.replace("/");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>登录</h1>
        <p className="subtitle">使用手机号或邮箱登录</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>手机号 / 邮箱</label>
            <input
              className="auth-input"
              type="text"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="13800000000"
            />
          </div>
          <div className="form-group">
            <label>密码</label>
            <input
              className="auth-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
            />
          </div>
          {err && <div className="auth-error">{err}</div>}
          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        <div className="auth-link">
          没有账号？
          <button onClick={() => router.push("/register")}>立即注册</button>
        </div>
      </div>
    </div>
  );
}
