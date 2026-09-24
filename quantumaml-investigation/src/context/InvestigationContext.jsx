import React, { createContext, useContext, useState, useEffect } from 'react';
import { MOCK_CASES, fetchCases } from '../api/casesApi';

export const InvestigationContext = createContext(null);

export function InvestigationProvider({ children }) {
  const [cases, setCases] = useState(MOCK_CASES);
  const [activeCaseId, setActiveCaseId] = useState('ESC-90812');
  const [activeCase, setActiveCase] = useState(MOCK_CASES[0]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    rail: 'ALL',
    riskTier: 'ALL',
    status: 'ALL',
  });
  const [isLoadingCases, setIsLoadingCases] = useState(true);

  // SAR dossier remarks and state management
  const [sarNarrative, setSarNarrative] = useState('');
  const [investigatorNotes, setInvestigatorNotes] = useState('');
  const [filedDossiers, setFiledDossiers] = useState({});
  const [frozenEntities, setFrozenEntities] = useState({});

  // Initial load from backend if available, fallback to mock data
  useEffect(() => {
    let isMounted = true;
    fetchCases()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setCases(data);
          const found = data.find((c) => c.id === activeCaseId) || data[0];
          setActiveCase(found);
          setActiveCaseId(found.id);
        }
      })
      .catch(() => {
        // Fallback already in place
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingCases(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [activeCaseId]);

  const selectCase = (caseObj) => {
    if (!caseObj) return;
    const targetCase =
      typeof caseObj === 'string'
        ? cases.find((c) => c.id === caseObj || c.sar_id === caseObj) || { id: caseObj }
        : caseObj;

    const id = targetCase.id || targetCase.sar_id;
    setActiveCaseId(id);
    setActiveCase(targetCase);
    // Clear node selection when switching cases
    setSelectedNodeId(null);
    setSelectedNodeData(null);
  };

  const updateActiveCaseStatus = (newStatus) => {
    if (!newStatus) return;
    setActiveCase((prev) => (prev ? { ...prev, status: newStatus } : prev));
    setCases((prev) =>
      prev.map((c) =>
        c.id === activeCaseId || c.sar_id === activeCaseId
          ? { ...c, status: newStatus }
          : c
      )
    );
  };

  const toggleAccountFreeze = (entityId) => {
    if (!entityId) return;
    setFrozenEntities((prev) => {
      const nextState = !prev[entityId];
      return { ...prev, [entityId]: nextState };
    });
  };

  const recordFiledDossier = (caseId, sarId) => {
    setFiledDossiers((prev) => ({
      ...prev,
      [caseId]: sarId,
    }));
  };

  const updateFilters = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({ search: '', rail: 'ALL', riskTier: 'ALL', status: 'ALL' });
  };

  return (
    <InvestigationContext.Provider
      value={{
        cases,
        setCases,
        activeCaseId,
        setActiveCaseId,
        activeCase,
        setActiveCase,
        selectCase,
        selectedNodeId,
        setSelectedNodeId,
        selectedNodeData,
        setSelectedNodeData,
        updateActiveCaseStatus,
        sarNarrative,
        setSarNarrative,
        investigatorNotes,
        setInvestigatorNotes,
        filedDossiers,
        recordFiledDossier,
        frozenEntities,
        toggleAccountFreeze,
        filters,
        setFilters,
        updateFilters,
        resetFilters,
        isLoadingCases,
      }}
    >
      {children}
    </InvestigationContext.Provider>
  );
}

export function useInvestigation() {
  const ctx = useContext(InvestigationContext);
  if (!ctx) {
    throw new Error('useInvestigation must be used within an InvestigationProvider');
  }
  return ctx;
}

export default InvestigationContext;
