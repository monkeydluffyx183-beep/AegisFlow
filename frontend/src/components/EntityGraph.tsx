export type GraphNode = { id: string; label?: string; type?: string; risk?: string }
export type GraphEdge = { source: string; target: string; type?: string }

export function EntityGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  return <div aria-label="Entity graph">{nodes.length} nodes · {edges.length} links</div>
}
