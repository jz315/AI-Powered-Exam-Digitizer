import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface NavItemProps {
  to: string;
  icon: LucideIcon;
  label: string;
  expanded: boolean;
}

export const NavItem = ({ to, icon: Icon, label, expanded }: NavItemProps) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      cn(
        "relative group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300 overflow-hidden",
        isActive
          ? "bg-primary/10 text-primary shadow-[0_0_20px_rgba(59,130,246,0.15)]"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      )
    }
  >
    {({ isActive }) => (
      <>
        {isActive && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
        )}
        
        <div className={cn("relative z-10 transition-transform duration-300", isActive ? "scale-110" : "group-hover:scale-110")}>
          <Icon className={cn("h-5 w-5", isActive ? "stroke-[2.5px]" : "stroke-[1.5px]")} />
        </div>
        
        <span
          className={cn(
            "font-medium tracking-wide whitespace-nowrap transition-all duration-300 origin-left relative z-10",
            expanded ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 hidden"
          )}
        >
          {label}
        </span>
        
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </>
    )}
  </NavLink>
);
