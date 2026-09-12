"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
export default function AdminEntry() {
 const [allowed,setAllowed]=useState(false); const pathname=usePathname();
 useEffect(()=>{
  let cancelled=false;
  const token=localStorage.getItem("auth_token");
  if(!token){const timer=window.setTimeout(()=>setAllowed(false),0);return()=>window.clearTimeout(timer);}
  fetch(API_BASE_URL+"/api/maintenance/routing/",{headers:{Authorization:"Token "+token}})
   .then(r=>{if(!cancelled)setAllowed(r.ok);}).catch(()=>{if(!cancelled)setAllowed(false);});
  return ()=>{cancelled=true;};
 },[pathname]);
 if(!allowed || pathname.startsWith("/maintenance"))return null;
 return <Link href="/maintenance" aria-label="관리자 유지보수" title="관리자 유지보수"
  className="fixed bottom-3 right-3 z-40 flex h-7 w-7 items-center justify-center rounded-full border border-slate-300 bg-white/90 text-slate-500 shadow hover:text-blue-700">●</Link>;
}
