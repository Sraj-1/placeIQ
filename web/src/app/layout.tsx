import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/app-shell";
import { THEME_SCRIPT } from "@/components/theme-toggle";
import { instrumentSerif, inter } from "@/lib/fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PlaceIQ", template: "%s · PlaceIQ" },
  description: "Campus placement readiness: an outcome-trained estimate, what drives it, and what to improve.",
};

export const viewport: Viewport = { themeColor: "#0a0a0a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${instrumentSerif.variable}`}>
      <body className="font-sans antialiased">
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
