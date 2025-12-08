import json
from datetime import datetime
from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT, MEMGRAPH_USERNAME, MEMGRAPH_PASSWORD
from typing import Dict, List
import sys

class ManualDataInput:
    def __init__(self):
        self.memgraph = MemgraphHandler(
            host=MEMGRAPH_HOST,
            port=MEMGRAPH_PORT,
            username=MEMGRAPH_USERNAME,
            password=MEMGRAPH_PASSWORD
        )
        
        self.entity_types = [
            "Platform", "Feature", "Tool", "Token", "Community",
            "Role", "Channel", "Game", "Person", "Organization",
            "Concept", "Technology", "Event", "Announcement"
        ]
        
        self.relation_types = [
            "has_component", "uses", "provides", "enables", "contains",
            "supports", "connects_to", "participates_in", "created_by",
            "manages", "offers", "integrates_with", "announced", "updates"
        ]
    
    def start_interactive_mode(self):
        print("\n" + "="*70)
        print("MANUAL KNOWLEDGE INPUT - IRYS NETWORK")
        print("="*70)
        print("\nConnect to Memgraph...")
        
        if not self.memgraph.connect():
            print("✗ Failed to connect to Memgraph")
            return
        
        print("✓ Connected to Memgraph\n")
        
        while True:
            print("\n" + "-"*70)
            print("OPTIONS:")
            print("1. Add Entity")
            print("2. Add Relationship")
            print("3. Add Full Triplet (subject-relation-object)")
            print("4. Bulk Import from Text")
            print("5. View Current Graph Stats")
            print("6. Exit")
            print("-"*70)
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                self._add_entity_interactive()
            elif choice == '2':
                self._add_relationship_interactive()
            elif choice == '3':
                self._add_triplet_interactive()
            elif choice == '4':
                self._bulk_import_interactive()
            elif choice == '5':
                self._show_graph_stats()
            elif choice == '6':
                break
            else:
                print("Invalid option. Try again.")
        
        self.memgraph.disconnect()
        print("\n✓ Disconnected. Goodbye!")
    
    def _add_entity_interactive(self):
        print("\n--- ADD ENTITY ---")
        
        print(f"\nAvailable entity types: {', '.join(self.entity_types)}")
        
        entity_id = input("Entity ID/Name: ").strip()
        if not entity_id:
            print("Entity ID cannot be empty")
            return
        
        entity_type = input("Entity Type: ").strip()
        if not entity_type:
            entity_type = "Entity"
        
        description = input("Description (optional): ").strip()
        source = input("Source (Twitter/Discord/etc): ").strip()
        
        if self.memgraph.node_exists(entity_id, entity_type):
            print(f"Entity '{entity_id}' already exists")
            overwrite = input("Update it? (y/n): ").strip().lower()
            if overwrite != 'y':
                return
        
        success = self.memgraph.create_node(
            node_id=entity_id,
            node_type=entity_type,
            properties={
                "description": description,
                "source": source or "manual",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if success:
            print(f"✓ Entity '{entity_id}' added successfully")
        else:
            print(f"✗ Failed to add entity")
    
    def _add_relationship_interactive(self):
        print("\n--- ADD RELATIONSHIP ---")
        
        from_id = input("From Entity ID: ").strip()
        to_id = input("To Entity ID: ").strip()
        
        if not from_id or not to_id:
            print("Both entity IDs are required")
            return
        
        print(f"\nAvailable relation types: {', '.join(self.relation_types)}")
        relation = input("Relation Type: ").strip()
        
        if not relation:
            print("Relation type cannot be empty")
            return
        
        source = input("Source (Twitter/Discord/etc): ").strip()
        
        if self.memgraph.relationship_exists(from_id, to_id, relation):
            print(f"Relationship already exists")
            return
        
        success = self.memgraph.create_relationship(
            from_id=from_id,
            to_id=to_id,
            relation_type=relation,
            properties={
                "source": source or "manual",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if success:
            print(f"✓ Relationship added: {from_id} -[{relation}]-> {to_id}")
        else:
            print(f"✗ Failed to add relationship")
    
    def _add_triplet_interactive(self):
        print("\n--- ADD TRIPLET (Subject-Relation-Object) ---")
        
        subject = input("Subject: ").strip()
        subject_type = input("Subject Type: ").strip() or "Entity"
        
        print(f"\nAvailable relation types: {', '.join(self.relation_types)}")
        relation = input("Relation: ").strip()
        
        obj = input("Object: ").strip()
        obj_type = input("Object Type: ").strip() or "Entity"
        
        source = input("Source (Twitter/Discord/etc): ").strip()
        
        if not subject or not relation or not obj:
            print("Subject, relation, and object are required")
            return
        
        self.memgraph.insert_triplet(
            subject=subject,
            subject_type=subject_type,
            relation=relation,
            obj=obj,
            obj_type=obj_type,
            source=source or "manual"
        )
        
        print(f"✓ Triplet added: ({subject}) -[{relation}]-> ({obj})")
    
    def _bulk_import_interactive(self):
        """
        Bulk import dari text - FIXED VERSION
        """
        print("\n--- BULK IMPORT FROM TEXT ---")
        print("Paste your content (from Twitter, Discord, etc)")
        print("Press Enter twice when done:")
        print("-"*70)
        
        lines = []
        empty_count = 0
        
        while True:
            try:
                line = input()
                if line == "":
                    empty_count += 1
                    if empty_count >= 2:  # Two consecutive empty lines
                        break
                else:
                    empty_count = 0
                    lines.append(line)
            except EOFError:
                break
        
        text = "\n".join(lines).strip()
        
        if not text:
            print("✗ No text provided")
            return
        
        print(f"\n✓ Received {len(text)} characters")
        print("Processing text...")
        
        # GET SOURCE INPUT - FIX: Flush stdin first
        sys.stdin.flush() if hasattr(sys.stdin, 'flush') else None
        source = input("\nSource (Twitter/Discord/etc): ").strip()
        
        print(f"\n[1/3] Extracting knowledge using LLM...")
        
        try:
            from knowledge_extractor import KnowledgeExtractor
            extractor = KnowledgeExtractor()
            
            knowledge = extractor.extract_from_text(text, source=source or "manual")
            
            if not knowledge:
                print("✗ Failed to extract knowledge from text")
                return
            
            entities = knowledge.get('entities', [])
            relationships = knowledge.get('relationships', [])
            
            print(f"\n[2/3] Extraction Results:")
            print(f"  ✓ Entities: {len(entities)}")
            if entities:
                for i, entity in enumerate(entities[:5], 1):
                    print(f"    {i}. {entity['name']} ({entity['type']})")
                if len(entities) > 5:
                    print(f"    ... and {len(entities) - 5} more")
            
            print(f"  ✓ Relationships: {len(relationships)}")
            if relationships:
                for i, rel in enumerate(relationships[:5], 1):
                    print(f"    {i}. {rel['subject']} -[{rel['relation']}]-> {rel['object']}")
                if len(relationships) > 5:
                    print(f"    ... and {len(relationships) - 5} more")
            
            if not entities and not relationships:
                print("\n✗ No knowledge extracted. Text may not contain relevant information.")
                return
            
            # CONFIRMATION - FIX: Clear input buffer
            sys.stdin.flush() if hasattr(sys.stdin, 'flush') else None
            print("\n[3/3] Insert into Memgraph?")
            confirm = input("Confirm (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                print("\nInserting into Memgraph...")
                inserted_entities = 0
                inserted_relationships = 0
                
                # Insert entities
                for entity in entities:
                    try:
                        # Check if exists
                        if not self.memgraph.node_exists(entity['name'], entity['type']):
                            success = self.memgraph.create_node(
                                node_id=entity['name'],
                                node_type=entity['type'],
                                properties={
                                    "description": entity.get('description', ''),
                                    "source": source or "manual",
                                    "timestamp": datetime.now().isoformat()
                                }
                            )
                            if success:
                                inserted_entities += 1
                    except Exception as e:
                        print(f"  ✗ Failed to insert entity {entity['name']}: {e}")
                
                # Insert relationships
                for rel in relationships:
                    try:
                        success = self.memgraph.insert_triplet(
                            subject=rel['subject'],
                            subject_type="Entity",
                            relation=rel['relation'],
                            obj=rel['object'],
                            obj_type="Entity",
                            source=source or "manual"
                        )
                        if success:
                            inserted_relationships += 1
                    except Exception as e:
                        print(f"  ✗ Failed to insert relationship: {e}")
                
                print(f"\n✓ Insertion Complete:")
                print(f"  - Entities inserted: {inserted_entities}/{len(entities)}")
                print(f"  - Relationships inserted: {inserted_relationships}/{len(relationships)}")
            else:
                print("✗ Insertion cancelled")
        
        except Exception as e:
            print(f"\n✗ Error during extraction: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_graph_stats(self):
        print("\n--- GRAPH STATISTICS ---")
        
        nodes = self.memgraph.get_all_nodes()
        relationships = self.memgraph.get_all_relationships()
        
        print(f"\nTotal Nodes: {len(nodes)}")
        print(f"Total Relationships: {len(relationships)}")
        
        # Group by type
        node_types = {}
        for node in nodes:
            node_type = node['type']
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\nNodes by Type:")
        for node_type, count in sorted(node_types.items(), key=lambda x: -x[1]):
            print(f"  - {node_type}: {count}")
        
        rel_types = {}
        for rel in relationships:
            rel_type = rel['relation']
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        print("\nRelationships by Type:")
        for rel_type, count in sorted(rel_types.items(), key=lambda x: -x[1]):
            print(f"  - {rel_type}: {count}")

def main():
    manual_input = ManualDataInput()
    manual_input.start_interactive_mode()

if __name__ == "__main__":
    main()