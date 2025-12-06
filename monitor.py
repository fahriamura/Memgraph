from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT
import json

def show_statistics():
    handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)
    
    if not handler.connect():
        print("\n✗ Cannot connect to Memgraph")
        print("Make sure Memgraph is running:")
        print("  docker run -p 7687:7687 memgraph/memgraph")
        return
    
    print("\n" + "="*70)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("="*70)

    stats = handler.get_graph_statistics()
    
    print(f"\nOverview:")
    print(f"  Total Nodes: {stats['total_nodes']}")
    print(f"  Total Relationships: {stats['total_relationships']}")
    
 
    if stats['node_types']:
        print(f"\nNode Types:")
        for node_type, count in sorted(stats['node_types'].items(), key=lambda x: -x[1]):
            print(f"  - {node_type}: {count}")
    else:
        print("\n⚠ No nodes found in graph")
    

    if stats['relationship_types']:
        print(f"\nRelationship Types:")
        for rel_type, count in sorted(stats['relationship_types'].items(), key=lambda x: -x[1]):
            print(f"  - {rel_type}: {count}")
    else:
        print("\n⚠ No relationships found in graph")
    

    nodes = handler.get_all_nodes()
    if nodes:
        recent = sorted(
            nodes, 
            key=lambda x: x['properties'].get('timestamp', ''), 
            reverse=True
        )[:10]
        
        print(f"\nRecent Additions (Last 10):")
        for i, node in enumerate(recent, 1):
            timestamp = node['properties'].get('timestamp', 'Unknown')
            source = node['properties'].get('source', 'Unknown')
            print(f"  {i}. {node['id']} ({node['type']}) - {source} @ {timestamp[:19]}")
    
    print("\n" + "="*70)
    
    handler.disconnect()

def export_graph_json(filename: str = "graph_export.json"):
    handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)
    
    if not handler.connect():
        return
    
    print(f"\nExporting graph to {filename}...")
    
    nodes = handler.get_all_nodes()
    relationships = handler.get_all_relationships()
    
    export_data = {
        "metadata": {
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
            "exported_at": handler.execute_query("RETURN datetime() as now")[0]["now"]
        },
        "nodes": nodes,
        "relationships": relationships
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Exported {len(nodes)} nodes and {len(relationships)} relationships")
    
    handler.disconnect()

def search_graph(search_term: str):
    handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)
    
    if not handler.connect():
        return
    
    print(f"\nSearching for: '{search_term}'...")
    
    results = handler.search_node_by_text(search_term)
    
    if results:
        print(f"\nFound {len(results)} matches:")
        for i, node in enumerate(results, 1):
            print(f"  {i}. {node['id']} ({node['type']})")
            desc = node['properties'].get('description', '')
            if desc:
                print(f"     Description: {desc[:100]}...")
    else:
        print(f"\n✗ No matches found for '{search_term}'")
    
    handler.disconnect()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "export":
            filename = sys.argv[2] if len(sys.argv) > 2 else "graph_export.json"
            export_graph_json(filename)
        elif command == "search":
            if len(sys.argv) > 2:
                search_graph(sys.argv[2])
            else:
                print("Usage: python monitor.py search <term>")
        else:
            print("Unknown command. Available: stats, export, search")
    else:
        show_statistics()