import localFont from "next/font/local";

// Both fonts are bundled (SIL Open Font License, see assets/fonts/*/OFL.txt), so the
// app never contacts a font service, at build time or at runtime.
export const inter = localFont({
  src: [{ path: "../assets/fonts/inter/Inter-Latin-Variable.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-inter",
  display: "swap",
});

export const instrumentSerif = localFont({
  src: [{ path: "../assets/fonts/instrument-serif/InstrumentSerif-Latin-Regular.woff2", weight: "400", style: "normal" }],
  variable: "--font-instrument-serif",
  display: "swap",
});
