import React from 'react';
import { InvestigationProvider } from './context/InvestigationContext';
import { Header } from './components/layout/Header';
import { WorkbenchLayout } from './components/layout/WorkbenchLayout';

export default function App() {
  return (
    <InvestigationProvider>
      <div className="h-screen w-screen flex flex-col bg-surface-950 text-slate-100 overflow-hidden font-sans select-none">
        {/* Top Forensic Status Bar */}
        <Header />

        {/* 3-Pane Fixed Workbench Viewport */}
        <WorkbenchLayout />
      </div>
    </InvestigationProvider>
  );
}
