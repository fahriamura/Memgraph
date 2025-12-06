import json
from datetime import datetime
from memgraph_handler import MemgraphHandler
from config import MEMGRAPH_HOST, MEMGRAPH_PORT, MEMGRAPH_USERNAME, MEMGRAPH_PASSWORD
from typing import Dict, List

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
        
        print("Connected to Memgraph\n")
        
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
            print(f"Entity '{entity_id}' added successfully")
        else:
            print(f"Failed to add entity")
    
    def _add_relationship_interactive(self):
        """
        Add relationship interactively
        """
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
        
        # Check if relationship exists
        if self.memgraph.relationship_exists(from_id, to_id, relation):
            print(f"Relationship already exists")
            return
        
        # Create relationship
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
            print(f"Relationship added: {from_id} -[{relation}]-> {to_id}")
        else:
            print(f"Failed to add relationship")
    
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

        print("\n--- BULK IMPORT FROM TEXT ---")
        print("Paste your content (from Twitter, Discord, etc)")
        print("Press Enter twice when done:")
        print("-"*70)
        
        lines = []
        while True:
            line = input()
            if line == "":
                if len(lines) > 0 and lines[-1] == "":
                    break
            lines.append(line)
        
        text = "\n".join(lines).strip()
        
        if not text:
            print("✗ No text provided")
            return
        
        print("\nProcessing text...")
        source = input("Source (Twitter/Discord/etc): ").strip()
        

        from knowledge_extractor import KnowledgeExtractor
        extractor = KnowledgeExtractor()
        
        knowledge = extractor.extract_from_text(text, source=source or "manual")
        
        if not knowledge:
            print("✗ Failed to extract knowledge from text")
            return
        
        print(f"\nExtracted:")
        print(f"  - {len(knowledge.get('entities', []))} entities")
        print(f"  - {len(knowledge.get('relationships', []))} relationships")
        
        confirm = input("\nInsert into Memgraph? (y/n): ").strip().lower()
        
        if confirm == 'y':
 
            for entity in knowledge.get('entities', []):
                self.memgraph.create_node(
                    node_id=entity['name'],
                    node_type=entity['type'],
                    properties={
                        "description": entity.get('description', ''),
                        "source": source or "manual",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            

            for rel in knowledge.get('relationships', []):
                self.memgraph.insert_triplet(
                    subject=rel['subject'],
                    subject_type="Entity",
                    relation=rel['relation'],
                    obj=rel['object'],
                    obj_type="Entity",
                    source=source or "manual"
                )
            
            print("Knowledge inserted successfully")
        else:
            print("Insertion cancelled")
    
    def _show_graph_stats(self):

        print("\n--- GRAPH STATISTICS ---")
        
        nodes = self.memgraph.get_all_nodes()
        relationships = self.memgraph.get_all_relationships()
        
        print(f"Total Nodes: {len(nodes)}")
        print(f"Total Relationships: {len(relationships)}")
        
   
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