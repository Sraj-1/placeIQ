import { BarChart3, Brain, ClipboardCheck, FileText, Gauge, Home, Info, Map, SlidersHorizontal, Tags } from "lucide-react";
import type { ComponentType, SVGProps } from "react";

export type NavItem = { href: string; label: string; icon: ComponentType<SVGProps<SVGSVGElement>> };
export type NavGroup = { title: string; items: NavItem[] };

// One source for the desktop sidebar and the mobile drawer.
export const NAV: NavGroup[] = [
  {
    title: "Student",
    items: [
      { href: "/", label: "Home", icon: Home },
      { href: "/readiness", label: "Readiness report", icon: Gauge },
      { href: "/what-if", label: "What-if simulator", icon: SlidersHorizontal },
      { href: "/roadmap", label: "Roadmap", icon: Map },
      { href: "/profile", label: "My profile & CV", icon: FileText },
    ],
  },
  {
    title: "Placement cell",
    items: [
      { href: "/cell", label: "Batch dashboard", icon: BarChart3 },
      { href: "/cell/model", label: "Model", icon: Brain },
      { href: "/cell/evaluation", label: "Evaluation", icon: ClipboardCheck },
      { href: "/cell/annotate", label: "Annotate resumes", icon: Tags },
    ],
  },
  {
    title: "",
    items: [{ href: "/about", label: "About PlaceIQ", icon: Info }],
  },
];

export function isActive(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/cell") return pathname === "/cell";
  return pathname === href || pathname.startsWith(`${href}/`);
}
