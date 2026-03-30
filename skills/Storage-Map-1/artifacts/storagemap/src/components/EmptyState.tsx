import React from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-white rounded-2xl border border-dashed border-border shadow-sm">
      <img 
        src={`${import.meta.env.BASE_URL}images/empty-box.png`} 
        alt="Empty state" 
        className="w-48 h-48 object-contain opacity-80 mb-6 drop-shadow-sm"
      />
      <h3 className="text-xl font-bold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground mb-6 max-w-md">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
