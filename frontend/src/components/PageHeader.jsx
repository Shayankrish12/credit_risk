import NotificationBell from "@/components/NotificationBell";

export default function PageHeader({ overline, title, subtitle, actions, testid = "page-header", showBell = true }) {
  return (
    <div className="border-b border-gray-200 bg-white px-4 lg:px-8 py-5 lg:py-6 sticky top-14 lg:top-0 z-10" data-testid={testid}>
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          {overline && (
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium mb-2">{overline}</div>
          )}
          <h1 className="font-heading font-bold text-2xl lg:text-3xl tracking-tight text-[#0A0A0A]" data-testid="page-title">{title}</h1>
          {subtitle && <p className="text-sm text-gray-600 mt-1.5 max-w-2xl">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          {showBell && <div className="hidden lg:block"><NotificationBell /></div>}
        </div>
      </div>
    </div>
  );
}
