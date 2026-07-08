import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/Header";

export const metadata: Metadata = {
  title: "Isometric MTO Extractor",
  description: "Upload a piping isometric drawing to extract its material takeoff.",
};

// Applies the saved theme before paint, so switching to blueprint (dark)
// mode never flashes vellum (light) first on reload.
const themeInitScript = `
(function () {
  try {
    var stored = window.localStorage.getItem("mto-theme");
    if (stored === "dark") {
      document.documentElement.classList.add("dark");
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-body antialiased">
        <Header />
        {children}
      </body>
    </html>
  );
}
