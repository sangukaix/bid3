import { redirect } from "next/navigation"; // 다른 주소로 바로 이동시키는 Next.js 함수

export default function DashBoardPage() { // /dashBoard 주소로 들어왔을 때 실행되는 페이지
  redirect("/dashBoard/bidList"); // 대시보드 첫 화면에서 입찰공고 목록을 표시
}
