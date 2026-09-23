import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { useInvestigation } from '../../context/InvestigationContext';
import { fetchGraphData } from '../../api/graphApi';
import { getGraphTheme } from '../../styles/graphTheme';
import { GraphControls } from './GraphControls';
import { FundsHopTimeline } from './FundsHopTimeline';
import { Loader } from '../common/Loader';

const LAYOUT_CONFIGS = {
  cose: {
    name: 'cose',
    animate: true,
    animationDuration: 500,
    randomize: false,
    fit: true,
    padding: 60,
    nodeRepulsion: 8000,
    idealEdgeLength: 120,
    edgeElasticity: 100,
  },
  concentric: {
    name: 'concentric',
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 60,
    minNodeSpacing: 60,
  },
  breadthfirst: {
    name: 'breadthfirst',
    animate: true,
    animationDuration: 500,
    fit: true,
    directed: true,
    padding: 60,
    spacingFactor: 1.3,
  },
  circle: {
    name: 'circle',
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 60,
  },
};

export function EntityLinkGraph() {
  const { activeCaseId, setSelectedNodeId, setSelectedNodeData } = useInvestigation();
  const cyRef = useRef(null);

  const [graphData, setGraphData] = useState({
    elements: [],
    nodes: [],
    edges: [],
    summary: {},
    timeline: [],
  });
  const [loading, setLoading] = useState(true);
  const [currentLayout, setCurrentLayout] = useState('cose');
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [selectedEntityInfo, setSelectedEntityInfo] = useState(null);

  // Load graph elements when activeCaseId changes
  useEffect(() => {
    let isMounted = true;

    fetchGraphData(activeCaseId)
      .then((data) => {
        if (!isMounted) return;
        setGraphData(data);
        setSelectedEntityInfo(null);
        setSelectedNodeId(null);
        setSelectedNodeData(null);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeCaseId, setSelectedNodeId, setSelectedNodeData]);

  // Run layout after elements update or layout switches
  const runLayout = useCallback(
    (layoutName = currentLayout) => {
      if (!cyRef.current) return;
      const cy = cyRef.current;
      const config = LAYOUT_CONFIGS[layoutName] || LAYOUT_CONFIGS.cose;
      const layout = cy.layout(config);
      layout.run();
    },
    [currentLayout]
  );

  // Resize and fit handler
  const handleFit = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.resize();
      cyRef.current.fit(undefined, 50);
    }
  }, []);

  const handleZoomIn = () => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom({
        level: cy.zoom() * 1.25,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      });
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom({
        level: cy.zoom() * 0.8,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      });
    }
  };

  const handleReset = () => {
    runLayout(currentLayout);
    handleFit();
  };

  const handleLayoutChange = (newLayout) => {
    setCurrentLayout(newLayout);
    runLayout(newLayout);
  };

  const handleToggleLabels = () => {
    setShowEdgeLabels((prev) => !prev);
  };

  // Window resize handler
  useEffect(() => {
    const onResize = () => {
      if (cyRef.current) {
        cyRef.current.resize();
      }
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Update Cytoscape stylesheet when showEdgeLabels toggles
  const theme = useMemo(() => getGraphTheme(showEdgeLabels), [showEdgeLabels]);

  useEffect(() => {
    if (cyRef.current) {
      cyRef.current.style(theme).update();
    }
  }, [theme]);

  // Bind Cytoscape event listeners
  const onCyInit = useCallback(
    (cy) => {
      cyRef.current = cy;
      cy.resize();

      // Node selection tap
      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        const data = node.data();
        setSelectedNodeId(data.id);
        setSelectedNodeData(data);
        setSelectedEntityInfo(data);
      });

      // Edge tap
      cy.on('tap', 'edge', (evt) => {
        const edge = evt.target;
        const data = edge.data();
        setSelectedEntityInfo({
          type: 'TRANSFER_HOP',
          label: `${data.source} → ${data.target}`,
          amount: data.formattedAmount,
          rail: data.rail,
          latency: `${data.latencySeconds}s`,
          isHighVelocity: data.isHighVelocity,
        });
      });

      // Background canvas tap deselects
      cy.on('tap', (evt) => {
        if (evt.target === cy) {
          setSelectedNodeId(null);
          setSelectedNodeData(null);
          setSelectedEntityInfo(null);
        }
      });

      // Run initial layout after slight mount delay
      setTimeout(() => {
        cy.resize();
        const layout = cy.layout(LAYOUT_CONFIGS.cose);
        layout.run();
        cy.fit(undefined, 50);
      }, 100);
    },
    [setSelectedNodeId, setSelectedNodeData]
  );

  return (
    <div className="w-full h-full flex flex-col relative bg-surface-950 overflow-hidden select-none">
      {/* Top Floating Graph Controls HUD */}
      <div className="absolute top-3 right-3 z-30">
        <GraphControls
          currentLayout={currentLayout}
          onLayoutChange={handleLayoutChange}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onFit={handleFit}
          onReset={handleReset}
          showEdgeLabels={showEdgeLabels}
          onToggleLabels={handleToggleLabels}
        />
      </div>

      {/* Selected Entity Float Badge (when a node or edge is tapped) */}
      {selectedEntityInfo && (
        <div className="absolute top-3 left-3 z-30 p-2.5 rounded-xl bg-surface-950/90 backdrop-blur-md border border-cyan-500/40 shadow-xl font-mono text-xs max-w-xs space-y-1 animate-fade-in">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-bold text-cyan-400 uppercase">
              {selectedEntityInfo.type}
            </span>
            {selectedEntityInfo.riskTier && (
              <span className="text-[9px] px-1.5 py-0.2 rounded font-bold bg-rose-950 text-rose-300 border border-rose-800">
                {selectedEntityInfo.riskTier}
              </span>
            )}
          </div>
          <div className="text-slate-100 font-bold truncate">
            {selectedEntityInfo.label}
          </div>
          {selectedEntityInfo.balance && (
            <div className="text-[11px] text-slate-400">
              Holding: <span className="text-cyan-300 font-semibold">{selectedEntityInfo.balance}</span>
            </div>
          )}
          {selectedEntityInfo.amount && (
            <div className="text-[11px] text-slate-400">
              Transfer: <span className="text-amber-300 font-semibold">{selectedEntityInfo.amount}</span> ({selectedEntityInfo.rail})
            </div>
          )}
        </div>
      )}

      {/* Center Graph Canvas Container */}
      <div className="flex-1 w-full h-full relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-950/80 z-20 backdrop-blur-sm">
            <Loader label={`Generating topology for ${activeCaseId}...`} />
          </div>
        ) : null}

        {graphData.elements.length > 0 ? (
          <CytoscapeComponent
            elements={graphData.elements}
            stylesheet={theme}
            layout={LAYOUT_CONFIGS[currentLayout]}
            cy={onCyInit}
            className="w-full h-full absolute inset-0 bg-surface-950"
            wheelSensitivity={0.3}
          />
        ) : !loading ? (
          <div className="flex items-center justify-center h-full text-slate-500 font-mono text-xs">
            No graph elements available for {activeCaseId}.
          </div>
        ) : null}
      </div>

      {/* Bottom Funds Hop Velocity Timeline Drawer */}
      <FundsHopTimeline
        timeline={graphData.timeline}
        summary={graphData.summary}
      />
    </div>
  );
}

export default EntityLinkGraph;
