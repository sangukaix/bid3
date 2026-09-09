type PageHeaderProps = {
  title: string;
  description?: string;
  note?: React.ReactNode;
  children?: React.ReactNode;
};

export default function PageHeader({ title, description, note, children }: PageHeaderProps) { // 모든 대시보드 페이지의 제목 위치를 통일
  return (
    <header className="page-header">
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-description">{description}</p>}
        {note && <div className="page-note">{note}</div>}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </header>
  );
}
