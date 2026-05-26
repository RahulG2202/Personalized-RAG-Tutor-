import type { Metadata } from "next";
import type { ReactNode } from "react";
import VectorDbWarmup from "@/components/vector-db-warmup";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Tutor AI",
  description: "A personalized tutor trained on your study material.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <VectorDbWarmup />
        {children}
      </body>
    </html>
  );
}
