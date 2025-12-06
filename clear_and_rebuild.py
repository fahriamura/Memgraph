# clear_and_rebuild.py
"""
Clear graph dan rebuild dengan node types yang benar
"""

from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT

handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)

if handler.connect():
    print("\n" + "="*70)
    print("CLEARING GRAPH")
    print("="*70)
    
    # Get current stats
    old_stats = handler.get_graph_statistics()
    print(f"\nCurrent graph:")
    print(f"  Nodes: {old_stats['total_nodes']}")
    print(f"  Relationships: {old_stats['total_relationships']}")
    
    # Clear all
    print("\nDeleting all relationships...")
    handler.execute_query("MATCH ()-[r]->() DELETE r")
    
    print("Deleting all nodes...")
    handler.execute_query("MATCH (n) DELETE n")
    
    # Verify
    new_stats = handler.get_graph_statistics()
    print(f"\nAfter clearing:")
    print(f"  Nodes: {new_stats['total_nodes']}")
    print(f"  Relationships: {new_stats['total_relationships']}")
    
    print("\n✓ Graph cleared successfully!")
    print("="*70)
    
    handler.disconnect()

print("\nNow run:")
print("  python scraper/main.py")
print("\nTo rebuild graph with correct node types.")