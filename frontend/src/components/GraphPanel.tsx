import { useCallback, useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { useStore } from "../store";
import { api } from "../services/api";
import { Network } from "lucide-react";

const nodeColors: Record<string, string> = {
  file: "#6366f1",
  module: "#8b5cf6",
  class: "#e5c07b",
  function: "#61afef",
  method: "#c678dd",
};

export function GraphPanel() {
  const { graphData, setSelectedNode, setActiveTab } = useStore();

  const onNodeClick = useCallback(
    async (_: React.MouseEvent, node: Node) => {
      try {
        const fullNode = await api.getSymbol(node.id);
        setSelectedNode(fullNode);
        setActiveTab("search");
      } catch {
        // Graph node not found as full symbol
      }
    },
    [setSelectedNode, setActiveTab],
  );

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!graphData) return { initialNodes: [], initialEdges: [] };

    const nodes: Node[] = graphData.nodes.map((n, i) => ({
      id: n.id,
      position: { x: (i % 4) * 280, y: Math.floor(i / 4) * 140 },
      data: { label: n.label, symbol_type: n.symbol_type },
      style: {
        background: nodeColors[n.symbol_type] || "#6366f1",
        color: "#fff",
        borderRadius: "8px",
        padding: "10px 16px",
        fontSize: "12px",
        fontWeight: 500,
        border: "none",
      },
    }));

    const edges: Edge[] = graphData.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      type: "smoothstep",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "var(--stroke)" },
      labelStyle: { fill: "var(--text-secondary)", fontSize: 10 },
    }));

    return { initialNodes: nodes, initialEdges: edges };
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  if (!graphData) {
    return (
      <div className="flex items-center justify-center h-64 text-muted text-sm">
        <div className="text-center">
          <Network className="w-8 h-8 mx-auto mb-3 text-subtle" />
          <p>Click &quot;Graph&quot; to load the code graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        className="bg-background"
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(n) => nodeColors[(n.data as Record<string, string>)?.symbol_type] || "#6366f1"}
          className="bg-surface"
        />
      </ReactFlow>
    </div>
  );
}
