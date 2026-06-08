import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { Toaster } from "@/components/ui/sonner";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TailorLoop — Profile Manager",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.className} h-full`}>
      <body className="h-full flex bg-gray-50 antialiased">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
