"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { register, isLoggedIn } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "", department: "", sap_id: "", phone: "", email: "", password: "",
  });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/");
  }, [router]);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const { name, department, sap_id, phone, email, password } = form;
    if (!name || !department || !sap_id || !phone || !email || !password) {
      return setErr("请填写所有必填字段");
    }
    setLoading(true);
    try {
      await register({ name, department, sap_id, phone, email, password });
      router.push("/login");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const fields = [
    { key: "name", label: "姓名", placeholder: "张三", type: "text" },
    { key: "department", label: "部门", placeholder: "技术部", type: "text" },
    { key: "sap_id", label: "SAP工号", placeholder: "80012345", type: "text" },
    { key: "phone", label: "手机号", placeholder: "13800000000", type: "text" },
    { key: "email", label: "工作邮箱", placeholder: "zhangsan@company.com", type: "email" },
    { key: "password", label: "密码", placeholder: "至少8位", type: "password" },
  ];

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>注册</h1>
        <p className="subtitle">创建你的账号</p>

        <form onSubmit={handleSubmit}>
          {fields.map((f) => (
            <div className="form-group" key={f.key}>
              <label>{f.label}</label>
              <input
                className="auth-input"
                type={f.type}
                value={(form as Record<string, string>)[f.key]}
                onChange={(e) => update(f.key, e.target.value)}
                placeholder={f.placeholder}
              />
            </div>
          ))}
          {err && <div className="auth-error">{err}</div>}
          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? "注册中..." : "注册"}  
          </button>
        </form>

        <div className="auth-link">
          已有账号？
          <button onClick={() => router.push("/login")}>去登录</button>
        </div>
      </div>
    </div>
  );
}
