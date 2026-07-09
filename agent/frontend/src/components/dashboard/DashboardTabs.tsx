export type DashboardTabId = "sessions" | "live" | "review";

const TABS: { id: DashboardTabId; label: string; hint: string }[] = [
  { id: "sessions", label: "Sessions", hint: "Start runs & session history" },
  { id: "live", label: "Live", hint: "Game view & reasoning" },
  { id: "review", label: "Review", hint: "Memory, chat & event timeline" },
];

type DashboardTabsProps = {
  activeTab: DashboardTabId;
  onTabChange: (tab: DashboardTabId) => void;
  variant?: "default" | "header";
};

export function DashboardTabs({
  activeTab,
  onTabChange,
  variant = "default",
}: DashboardTabsProps) {
  if (variant === "header") {
    return (
      <nav
        className="flex flex-wrap items-center justify-center gap-0.5 rounded-lg border border-gray-800 bg-black/25 p-0.5"
        aria-label="Dashboard sections"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            title={tab.hint}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-accent text-white"
                : "text-gray-400 hover:bg-white/5 hover:text-white"
            }`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    );
  }

  return (
    <nav
      className="mb-4 flex flex-wrap gap-1 border-b border-gray-800 pb-2"
      aria-label="Dashboard sections"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          title={tab.hint}
          className={`rounded-t px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "bg-accent text-white"
              : "text-gray-400 hover:bg-white/5 hover:text-white"
          }`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
