import type { ReactNode } from "react";

interface ShellProps {
    children: ReactNode;
}

export function Shell({ children }: ShellProps) {
    return (
        <div className="min-h-screen bg-app-bg text-app-text">
            <div className="mx-auto max-w-content px-4 py-8">
                {children}
            </div>
        </div>
    );
}
