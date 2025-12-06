"""
Direct JSON import untuk Memgraph - import nodes dan edges dari JSON
"""

import json
from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT
from datetime import datetime

def import_json_to_memgraph(json_file_or_string, source="json_import"):
    """
    Import JSON directly ke Memgraph
    
    Format JSON:
    {
      "nodes": [
        {"id": "Irys", "type": "Platform", "description": "..."}
      ],
      "edges": [
        {"from": "Irys", "to": "IrysVM", "relation": "has_component"}
      ]
    }
    """
    
    # Parse JSON
    if isinstance(json_file_or_string, str):
        if json_file_or_string.endswith('.json'):
            # Load from file
            with open(json_file_or_string, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Parse string
            data = json.loads(json_file_or_string)
    else:
        data = json_file_or_string
    
    # Connect to Memgraph
    handler = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)
    
    if not handler.connect():
        print("✗ Cannot connect to Memgraph")
        return False
    
    print("\n" + "="*70)
    print("IMPORTING JSON TO MEMGRAPH")
    print("="*70)
    
    # Import nodes
    nodes = data.get('nodes', [])
    print(f"\n[1/2] Importing {len(nodes)} nodes...")
    
    inserted_nodes = 0
    for node in nodes:
        node_id = node.get('id')
        node_type = node.get('type', 'Entity')
        
        if not node_id:
            print(f"  ⚠ Skipping node without id: {node}")
            continue
        
        # Check if exists
        exists = False
        try:
            result = handler.execute_query(
                "MATCH (n {id: $node_id}) RETURN n",
                {"node_id": node_id}
            )
            exists = result is not None and len(result) > 0
        except:
            exists = False
        
        if not exists:
            # Prepare properties (exclude id and type)
            properties = {k: v for k, v in node.items() if k not in ['id', 'type']}
            properties['source'] = source
            properties['timestamp'] = datetime.now().isoformat()
            
            success = handler.create_node(
                node_id=node_id,
                node_type=node_type,
                properties=properties
            )
            
            if success:
                inserted_nodes += 1
        else:
            print(f"  ⊙ Node already exists: {node_id}")
    
    print(f"  ✓ Inserted {inserted_nodes} new nodes")
    
    # Import edges/relationships
    edges = data.get('edges', [])
    print(f"\n[2/2] Importing {len(edges)} edges...")
    
    inserted_edges = 0
    for edge in edges:
        from_id = edge.get('from')
        to_id = edge.get('to')
        relation = edge.get('relation', 'related_to')
        
        if not from_id or not to_id:
            print(f"  ⚠ Skipping invalid edge: {edge}")
            continue
        
        # Check if both nodes exist
        for node_id in [from_id, to_id]:
            exists = False
            try:
                result = handler.execute_query(
                    "MATCH (n {id: $node_id}) RETURN n",
                    {"node_id": node_id}
                )
                exists = result is not None and len(result) > 0
            except:
                exists = False
            
            if not exists:
                print(f"  ⚠ Node {node_id} not found, creating as Entity...")
                handler.create_node(
                    node_id=node_id,
                    node_type="Entity",
                    properties={
                        "source": "auto-created",
                        "timestamp": datetime.now().isoformat()
                    }
                )
        
        # Check if relationship exists
        exists_check = handler.execute_query(
            f"MATCH (a {{id: $from_id}})-[r:{relation}]->(b {{id: $to_id}}) RETURN count(r) as count",
            {"from_id": from_id, "to_id": to_id}
        )
        
        if exists_check and exists_check[0]["count"] > 0:
            print(f"  ⊙ Edge exists: ({from_id}) -[{relation}]-> ({to_id})")
            continue
        
        # Prepare properties
        properties = {k: v for k, v in edge.items() if k not in ['from', 'to', 'relation']}
        properties['source'] = source
        properties['timestamp'] = datetime.now().isoformat()
        
        success = handler.create_relationship(
            from_id=from_id,
            to_id=to_id,
            relation_type=relation,
            properties=properties
        )
        
        if success:
            inserted_edges += 1
    
    print(f"  ✓ Inserted {inserted_edges} new edges")
    
    # Summary
    print("\n" + "="*70)
    print("IMPORT COMPLETED")
    print("="*70)
    print(f"  Nodes inserted: {inserted_nodes}")
    print(f"  Edges inserted: {inserted_edges}")
    print("="*70 + "\n")
    
    handler.disconnect()
    
    return True

def interactive_json_import():
    """
    Interactive JSON import
    """
    print("\n" + "="*70)
    print("JSON IMPORT TO MEMGRAPH")
    print("="*70)
    print("\nOptions:")
    print("1. Import from JSON file")
    print("2. Paste JSON directly")
    print("3. Cancel")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        # Import from file
        filename = input("\nEnter JSON file path: ").strip()
        
        try:
            import_json_to_memgraph(filename)
        except FileNotFoundError:
            print(f"✗ File not found: {filename}")
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    elif choice == '2':
        # Paste JSON
        print("\nPaste your JSON (nodes and edges):")
        print("Press Enter, then Ctrl+Z (Windows) or Ctrl+D (Linux/Mac), then Enter")
        print("-"*70)
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        json_string = '\n'.join(lines)
        
        try:
            import_json_to_memgraph(json_string)
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    else:
        print("Cancelled")

if __name__ == "__main__":
    interactive_json_import()