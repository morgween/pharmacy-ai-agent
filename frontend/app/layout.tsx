import './global.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'Pharmacy AI Agent',
  description: 'Chat with the Pharmacy AI Agent and inspect tool-calling traces.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
