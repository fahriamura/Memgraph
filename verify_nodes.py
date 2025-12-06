"""
Verify bahwa nodes punya labels yang benar
"""

from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT

handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)

if handler.connect():
    print("\n" + "="*70)
    print("NODE TYPE VERIFICATION")
    print("="*70)
    
    # Get all nodes grouped by type
    nodes = handler.get_all_nodes()
    
    type_counts = {}
    for node in nodes:
        node_type = node['type']
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    
    print(f"\nTotal nodes: {len(nodes)}")
    print(f"\nNodes by type:")
    
    for node_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"\n  :{node_type} ({count} nodes)")
        
        # Show sample nodes of this type
        sample_nodes = [n for n in nodes if n['type'] == node_type][:3]
        for node in sample_nodes:
            print(f"    - {node['id']}")
    
    # Check if we still have generic "Entity" labels
    if 'Entity' in type_counts:
        entity_count = type_counts['Entity']
        total_count = len(nodes)
        percentage = (entity_count / total_count * 100) if total_count > 0 else 0
        
        print(f"\n{'⚠' if percentage > 50 else '✓'} Generic Entity nodes: {entity_count}/{total_count} ({percentage:.1f}%)")
        
        if percentage > 50:
            print("\n  WARNING: More than 50% nodes are generic 'Entity' type!")
            print("  This means node type extraction or insertion is not working correctly.")
        else:
            print("\n  ✓ Most nodes have specific types!")
    else:
        print("\n✓ No generic 'Entity' nodes - all nodes have specific types!")
    
    print("\n" + "="*70)
    
    handler.disconnect()