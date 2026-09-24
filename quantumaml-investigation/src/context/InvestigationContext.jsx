import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { MOCK_CASES, getCases, getCaseById, updateCaseStatus } from '../api/casesApi';
import { getCaseGraph } from '../api/graphApi';
import {
  getExplainability,
  getSuspectProfile,
  freezeEntity,
  generateSarDossier,
  downloadSarPdf,
} from '../api/sarApi';
import { checkHealth, STATUS_CONNECTED, STATUS_OFFLINE } from '../api/healthApi';
import { subscribeOfflineMode } from '../api/client';

export const InvestigationContext = createContext(null);

export function InvestigationProvider({ children }) {
  // Case & Queue State
  const [cases, setCases] = useState(MOCK_CASES);
  const [activeCaseId, setActiveCaseId] = useState('ESC-90812');
  const [activeCase, setActiveCase] = useState(MOCK_CASES[0]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedNodeData, setSelectedNodeData] = useState(null);

  // Parallel telemetry states
  const [caseGraph, setCaseGraph] = useState(null);
  const [caseExplainability, setCaseExplainability] = useState(null);
  const [suspectProfile, setSuspectProfile] = useState(null);

  // Loading States
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingCases, setIsLoadingCases] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Backend Health State
  const [backendStatus, setBackendStatus] = useState(STATUS_OFFLINE);
  const [backendHealthy, setBackendHealthy] = useState(false);

  // Filters State
  const [filters, setFilters] = useState({
    search: '',
    rail: 'ALL',
    riskTier: 'ALL',
    status: 'ALL',
  });

  // SAR dossier remarks and freeze management
  const [sarNarrative, setSarNarrative] = useState('');
  const [investigatorNotes, setInvestigatorNotes] = useState('');
  const [filedDossiers, setFiledDossiers] = useState({});
  const [frozenEntities, setFrozenEntities] = useState({});

  // Error/Feedback message toast
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const isMountedRef = useRef(true);

  // 1. Backend Health Check Heartbeat
  const checkHealthStatus = useCallback(async () => {
    try {
      const res = await checkHealth();
      if (!isMountedRef.current) return;
      setBackendStatus(res.status);
      setBackendHealthy(Boolean(res.healthy));
    } catch {
      if (!isMountedRef.current) return;
      setBackendStatus(STATUS_OFFLINE);
      setBackendHealthy(false);
    }
  }, []);

  // Listen for offline state transitions from API client
  useEffect(() => {
    isMountedRef.current = true;

    const unsubscribe = subscribeOfflineMode((offline) => {
      if (!isMountedRef.current) return;
      if (offline) {
        setBackendStatus(STATUS_OFFLINE);
        setBackendHealthy(false);
      } else {
        setBackendStatus(STATUS_CONNECTED);
        setBackendHealthy(true);
      }
    });

    return () => {
      isMountedRef.current = false;
      unsubscribe();
    };
  }, []);

  // Poll health every 15 seconds
  useEffect(() => {
    checkHealthStatus();
    const interval = setInterval(() => {
      checkHealthStatus();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealthStatus]);

  // 2. Fetch initial triage cases on mount
  useEffect(() => {
    let isSubscribed = true;
    setIsLoadingCases(true);

    getCases()
      .then((data) => {
        if (isSubscribed && Array.isArray(data) && data.length > 0) {
          setCases(data);
          const found = data.find((c) => c.id === activeCaseId) || data[0];
          setActiveCase(found);
          setActiveCaseId(found.id);
        }
      })
      .catch((err) => {
        console.warn('[InvestigationContext] Error fetching cases:', err.message);
      })
      .finally(() => {
        if (isSubscribed) {
          setIsLoadingCases(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, []); // Run once on mount

  // 3. Parallel fetch of case telemetry whenever activeCaseId changes
  useEffect(() => {
    if (!activeCaseId) return;

    let isSubscribed = true;
    setIsLoading(true);
    setIsLoadingDetails(true);

    Promise.allSettled([
      getCaseById(activeCaseId),
      getCaseGraph(activeCaseId),
      getExplainability(activeCaseId),
      getSuspectProfile(activeCaseId, selectedNodeId),
    ]).then(([caseRes, graphRes, explainRes, profileRes]) => {
      if (!isSubscribed) return;

      if (caseRes.status === 'fulfilled' && caseRes.value) {
        setActiveCase(caseRes.value);
      }
      if (graphRes.status === 'fulfilled' && graphRes.value) {
        setCaseGraph(graphRes.value);
      }
      if (explainRes.status === 'fulfilled' && explainRes.value) {
        setCaseExplainability(explainRes.value);
      }
      if (profileRes.status === 'fulfilled' && profileRes.value) {
        setSuspectProfile(profileRes.value);
      }

      setIsLoading(false);
      setIsLoadingDetails(false);
    });

    return () => {
      isSubscribed = false;
    };
  }, [activeCaseId, selectedNodeId]);

  // Select a case and reset node inspection
  const selectCase = useCallback((caseObj) => {
    if (!caseObj) return;
    const targetCase =
      typeof caseObj === 'string'
        ? cases.find((c) => c.id === caseObj || c.sar_id === caseObj) || { id: caseObj }
        : caseObj;

    const id = targetCase.id || targetCase.sar_id;
    setActiveCaseId(id);
    setActiveCase(targetCase);
    setSelectedNodeId(null);
    setSelectedNodeData(null);
  }, [cases]);

  // Mutation Handlers
  const handleStatusChange = useCallback(async (newStatus, notes = '') => {
    if (!newStatus || !activeCaseId) return;
    try {
      const updated = await updateCaseStatus(activeCaseId, newStatus, notes);
      setActiveCase((prev) => (prev ? { ...prev, status: newStatus } : prev));
      setCases((prev) =>
        prev.map((c) =>
          c.id === activeCaseId || c.sar_id === activeCaseId
            ? { ...c, status: newStatus }
            : c
        )
      );
      setFeedbackMessage({
        type: 'success',
        text: `Status updated to ${newStatus} for case #${activeCaseId}`,
      });
      return updated;
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: `Failed to update case status: ${err.message}`,
      });
      throw err;
    }
  }, [activeCaseId]);

  const handleFreezeEntity = useCallback(async (entityId) => {
    const target = entityId || activeCaseId;
    if (!target) return;

    try {
      const res = await freezeEntity(activeCaseId, target);
      setFrozenEntities((prev) => {
        const nextState = res.frozenStatus !== undefined ? res.frozenStatus : !prev[target];
        return { ...prev, [target]: nextState };
      });
      return res;
    } catch {
      // In-memory fallback
      setFrozenEntities((prev) => {
        const nextState = !prev[target];
        return { ...prev, [target]: nextState };
      });
    }
  }, [activeCaseId]);

  const handleGenerateSar = useCallback(async (narrative, notes) => {
    if (!activeCaseId) return;
    try {
      const payload = {
        narrative: narrative || sarNarrative,
        notes: notes || investigatorNotes,
      };
      const res = await generateSarDossier(activeCaseId, payload);
      const generatedId =
        res.sar_id || `SAR-2026-${String(activeCaseId).replace(/[^0-9]/g, '') || '90812'}`;

      setFiledDossiers((prev) => ({
        ...prev,
        [activeCaseId]: generatedId,
      }));

      // Transition case status to FILED_WITH_FIU
      handleStatusChange('FILED_WITH_FIU', notes);
      return res;
    } catch (err) {
      console.error('[InvestigationContext] SAR Dossier generation failed:', err);
      throw err;
    }
  }, [activeCaseId, sarNarrative, investigatorNotes, handleStatusChange]);

  const handleDownloadPdf = useCallback(async () => {
    if (!activeCaseId) return;
    try {
      return await downloadSarPdf(activeCaseId);
    } catch (err) {
      console.error('[InvestigationContext] PDF export failed:', err);
      throw err;
    }
  }, [activeCaseId]);

  const updateFilters = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ search: '', rail: 'ALL', riskTier: 'ALL', status: 'ALL' });
  }, []);

  const recordFiledDossier = useCallback((caseId, sarId) => {
    setFiledDossiers((prev) => ({
      ...prev,
      [caseId]: sarId,
    }));
  }, []);

  const toggleAccountFreeze = handleFreezeEntity;
  const updateActiveCaseStatus = handleStatusChange;

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

        // Telemetry Data
        caseGraph,
        setCaseGraph,
        caseExplainability,
        setCaseExplainability,
        suspectProfile,
        setSuspectProfile,

        // Loading states
        isLoading,
        isLoadingCases,
        isLoadingDetails,

        // Backend health
        backendStatus,
        backendHealthy,
        checkHealthStatus,

        // Handlers
        handleStatusChange,
        handleFreezeEntity,
        handleGenerateSar,
        handleDownloadPdf,
        updateActiveCaseStatus,
        toggleAccountFreeze,

        // Narrative & Export
        sarNarrative,
        setSarNarrative,
        investigatorNotes,
        setInvestigatorNotes,
        filedDossiers,
        recordFiledDossier,
        frozenEntities,

        // Filtering
        filters,
        setFilters,
        updateFilters,
        resetFilters,

        // Feedback toasts
        feedbackMessage,
        setFeedbackMessage,
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
