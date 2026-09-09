import { redirect } from "next/navigation"; // 다른 주소로 바로 이동시키는 Next.js 함수

export default function RootPage() { // / 주소로 들어왔을 때 실행되는 페이지
  redirect("/mainPage"); // 메인 페이지 주소로 이동
}
