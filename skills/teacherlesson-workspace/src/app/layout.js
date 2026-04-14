import "./globals.css";

export const metadata = {
  title: "Teacher Workspace — 수업 관리 대시보드",
  description: "교사를 위한 통합 수업 관리 워크스페이스. 진도 관리, 수업 배치, 지도서 관리를 한 곳에서.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
