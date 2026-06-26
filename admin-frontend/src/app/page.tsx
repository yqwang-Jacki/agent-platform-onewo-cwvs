"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/api";

export default function AdminHomePage() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/agents");
    else router.replace("/login");
  }, [router]);

  return <div className="loading-text">加载中...</div>;
}
