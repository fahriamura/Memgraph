import json
import time
from datetime import datetime
from web_scraper import IrysScraper
from knowledge_extractor import KnowledgeExtractor
from simple_extractor import SimpleExtractor
from memgraph_handler import MemgraphHandler
from config import (
    MEMGRAPH_HOST, MEMGRAPH_PORT, MEMGRAPH_USERNAME, MEMGRAPH_PASSWORD,
    DATA_DIR, CACHE_FILE, IRYS_SEED_URLS, MAX_SCRAPING_DEPTH,
    OPENAI_API_KEY
)
import os

class KnowledgeGraphUpdater:
    def __init__(self):
    
        self.scraper = IrysScraper(use_selenium=False)
        
       
        if OPENAI_API_KEY:
            try:
                self.extractor = KnowledgeExtractor()
                print("✓ Using OpenAI-powered knowledge extraction")
            except Exception as e:
                print(f"⚠ OpenAI initialization failed: {e}")
                print("  Using simple rule-based extraction instead")
                self.extractor = SimpleExtractor()
        else:
            print("⚠ No OpenAI API key found")
            print("  Using simple rule-based extraction")
            self.extractor = SimpleExtractor()
        
        self.memgraph = MemgraphHandler(
            host=MEMGRAPH_HOST,
            port=MEMGRAPH_PORT,
            username=MEMGRAPH_USERNAME,
            password=MEMGRAPH_PASSWORD
        )
        
        self.cache = self._load_cache()
    
    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"processed_urls": [], "last_run": None}
    
    def _save_cache(self):
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def run_full_update(self):
        print("\n" + "="*70)
        print("KNOWLEDGE GRAPH UPDATE - IRYS NETWORK")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        

        print("\n[1/6] Connecting to Memgraph...")
        if not self.memgraph.connect():
            print("✗ Failed to connect to Memgraph. Aborting.")
            return False
        

        print("\n[2/6] Scraping Irys websites (with link following)...")
        scraped_data = self.scraper.scrape_with_depth(
            seed_urls=IRYS_SEED_URLS,
            max_depth=MAX_SCRAPING_DEPTH
        )
        
        if not scraped_data:
            print("✗ No data scraped. Aborting.")
            self.memgraph.disconnect()
            return False

        self.scraper.save_scraped_data(scraped_data)
        self.scraper.save_statistics()

        print("\n[3/6] Extracting knowledge from scraped data...")
        all_knowledge = []
        
        for i, data in enumerate(scraped_data, 1):
            url = data.get('url', 'unknown')
            page_title = data.get('title', 'Untitled')
            
            print(f"\n  [{i}/{len(scraped_data)}] Processing: {page_title}")
            print(f"  URL: {url}")
            
            try:
                knowledge_list = self.extractor.extract_from_scraped_data(data)
                all_knowledge.extend(knowledge_list)
                
                if knowledge_list:
                    total_entities = sum(len(k.get('entities', [])) for k in knowledge_list)
                    total_rels = sum(len(k.get('relationships', [])) for k in knowledge_list)
                    print(f"  ✓ Extracted {total_entities} entities, {total_rels} relationships")
                else:
                    print(f"  ⚠ No knowledge extracted from this page")
                    
            except Exception as e:
                print(f"  ✗ Error processing page: {e}")
                continue
        
        if not all_knowledge:
            print("\n✗ No knowledge extracted from any pages. Aborting.")
            self.memgraph.disconnect()
            return False
        
        print("\n[4/6] Merging extracted knowledge...")
        merged_knowledge = self.extractor.merge_knowledge(all_knowledge)
        
        print(f"  Total unique entities: {merged_knowledge['total_entities']}")
        print(f"  Total unique relationships: {merged_knowledge['total_relationships']}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        knowledge_file = f"{DATA_DIR}/knowledge_{timestamp}.json"
        with open(knowledge_file, 'w', encoding='utf-8') as f:
            json.dump(merged_knowledge, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved to: {knowledge_file}")
        
   
        print("\n[5/6] Inserting new knowledge into Memgraph...")
        inserted_count = self._insert_knowledge_to_memgraph(merged_knowledge)
        
        print(f"  ✓ Inserted {inserted_count['entities']} new entities")
        print(f"  ✓ Inserted {inserted_count['relationships']} new relationships")
        
        print("\n[6/6] Updating cache...")
        self.cache['last_run'] = datetime.now().isoformat()
        self.cache['total_pages_scraped'] = len(scraped_data)
        self.cache['processed_urls'] = [d['url'] for d in scraped_data]
        self._save_cache()

        self.memgraph.disconnect()
        self.scraper.close()
        
        print("\n" + "="*70)
        print("✓ UPDATE COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"\nSummary:")
        print(f"  - Pages scraped: {len(scraped_data)}")
        print(f"  - Entities added: {inserted_count['entities']}")
        print(f"  - Relationships added: {inserted_count['relationships']}")
        print("="*70 + "\n")
        
        return True
    
    def _insert_knowledge_to_memgraph(self, knowledge):
        """
        Insert extracted knowledge into Memgraph
        """
        inserted = {"entities": 0, "relationships": 0}
        
        # Create entity lookup map: name -> type
        entity_type_map = {}
        for entity in knowledge.get('entities', []):
            name = entity.get('name')
            if name:
                entity_type_map[name] = entity.get('type', 'Entity')
        
        print(f"\n  Inserting {len(knowledge.get('entities', []))} entities...")
        
        # Insert entities first with CORRECT types
        for entity in knowledge.get('entities', []):
            name = entity.get('name')
            if not name:
                continue
                
            entity_type = entity.get('type', 'Entity')
            
            # Check if node exists with ANY label
            exists = False
            try:
                result = self.memgraph.execute_query(
                    "MATCH (n {id: $node_id}) RETURN n",
                    {"node_id": name}
                )
                exists = result is not None and len(result) > 0
            except:
                exists = False
            
            if not exists:
                success = self.memgraph.create_node(
                    node_id=name,
                    node_type=entity_type,  # Use CORRECT type
                    properties={
                        "description": entity.get('description', ''),
                        "source": "scraped",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                if success:
                    inserted['entities'] += 1
            else:
                print(f"  ⊙ Node already exists: {name}")
        
        print(f"  ✓ Inserted {inserted['entities']} new entities")
        print(f"\n  Inserting {len(knowledge.get('relationships', []))} relationships...")
        
        # Insert relationships
        for rel in knowledge.get('relationships', []):
            subject = rel.get('subject')
            relation = rel.get('relation', 'related_to')
            obj = rel.get('object')
            
            if not subject or not obj:
                print(f"  ⚠ Skipping invalid relationship: {rel}")
                continue
            
            # Get correct types for subject and object
            subject_type = entity_type_map.get(subject, 'Entity')
            obj_type = entity_type_map.get(obj, 'Entity')
            
            # Ensure both nodes exist with CORRECT types
            for node_id, node_type in [(subject, subject_type), (obj, obj_type)]:
                # Check if node exists with ANY label
                exists = False
                try:
                    result = self.memgraph.execute_query(
                        "MATCH (n {id: $node_id}) RETURN n",
                        {"node_id": node_id}
                    )
                    exists = result is not None and len(result) > 0
                except:
                    exists = False
                
                if not exists:
                    self.memgraph.create_node(
                        node_id=node_id,
                        node_type=node_type,  # Use CORRECT type, not "Entity"
                        properties={
                            "source": "auto-created",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    print(f"    ✓ Auto-created: {node_id} ({node_type})")
            
            # Check if relationship already exists
            exists_check = self.memgraph.execute_query(
                "MATCH (a {id: $subject})-[r:" + relation + "]->(b {id: $obj}) RETURN count(r) as count",
                {"subject": subject, "obj": obj}
            )
            
            if exists_check and exists_check[0]["count"] > 0:
                print(f"  ⊙ Relationship exists: ({subject}) -[{relation}]-> ({obj})")
                continue
            
            # Create relationship
            success = self.memgraph.create_relationship(
                from_id=subject,
                to_id=obj,
                relation_type=relation,
                properties={
                    "source": "scraped",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if success:
                inserted['relationships'] += 1
        
        print(f"  ✓ Inserted {inserted['relationships']} new relationships")
        
        return inserted

def main():
    updater = KnowledgeGraphUpdater()
    updater.run_full_update()

if __name__ == "__main__":
    main()