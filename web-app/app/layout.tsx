import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import DashboardLayout from '@/components/DashboardLayout';
import { CartProvider } from '@/context/CartContext';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Approximate Cost Pro',
  description: 'Construction cost estimation made simple.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body className={inter.className}>
        <CartProvider>
          <DashboardLayout>{children}</DashboardLayout>
        </CartProvider>
      </body>
    </html>
  );
}
