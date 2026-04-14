import { Link, useLocation } from "wouter";
import { BookOpen, Library, Settings, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

export function Shell({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  const navItems = [
    { name: "내 교과서", path: "/", icon: Library },
    { name: "설정", path: "/settings", icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 glass-panel border-r border-border md:fixed md:inset-y-0 z-40">
        <div className="p-6 flex flex-col h-full">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-teal-600 flex items-center justify-center shadow-lg shadow-primary/20">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold font-display text-foreground">수업 트래커</h1>
          </div>

          <nav className="flex-1 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location === item.path;
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 group",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <Icon className={cn("w-5 h-5 transition-transform group-hover:scale-110", isActive && "text-primary")} />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto p-4 bg-accent/50 rounded-2xl border border-primary/10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center border border-border">
                <span className="font-bold text-sm text-primary">T</span>
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">김선생님</p>
                <p className="text-xs text-muted-foreground">초등 5학년 1반</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 md:ml-64 p-4 md:p-8 lg:p-12 relative min-h-screen">
        {/* Decorative Background Elements */}
        <div className="absolute top-0 left-0 right-0 h-64 bg-gradient-to-b from-primary/5 to-transparent -z-10 pointer-events-none" />
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-secondary/10 rounded-full blur-[100px] -z-10 pointer-events-none" />
        
        {/* Header (Mobile) */}
        <header className="md:hidden flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-display">수업 트래커</h2>
          <button className="p-2 bg-white rounded-full shadow-sm border border-border">
            <Bell className="w-5 h-5 text-muted-foreground" />
          </button>
        </header>

        {children}
      </main>
    </div>
  );
}
