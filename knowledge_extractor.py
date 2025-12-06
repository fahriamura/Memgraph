"""
Extract knowledge dari scraped text menggunakan OpenAI API v1.0+
"""

from openai import OpenAI
from typing import List, Dict
import json
from config import OPENAI_API_KEY

class KnowledgeExtractor:
    def __init__(self):
        """
        Initialize knowledge extractor dengan OpenAI v1.0+
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        self.entity_types = [
            "Platform", "Feature", "Tool", "Token", "Community",
            "Role", "Channel", "Game", "Person", "Organization",
            "Concept", "Technology", "Event"
        ]
        
        self.relation_types = [
            "has_component", "uses", "provides", "enables", "contains",
            "supports", "connects_to", "participates_in", "created_by",
            "manages", "offers", "integrates_with"
        ]
    
    def extract_from_text(self, text: str, source: str = None) -> Dict:
        """
        Extract entities and relationships from text using GPT
        """
        if not text or not text.strip():
            print("⚠ Empty text, skipping extraction")
            return None
            
        prompt = f"""
Extract knowledge from the following text about Irys Network.

Text: {text[:3000]}

Extract:
1. Entities (name, type, description)
2. Relationships (subject, relation, object)

Entity types: {', '.join(self.entity_types)}
Relation types: {', '.join(self.relation_types)}

Output as JSON:
{{
  "entities": [
    {{"name": "...", "type": "...", "description": "..."}}
  ],
  "relationships": [
    {{"subject": "...", "relation": "...", "object": "..."}}
  ]
}}

Only extract factual information. Be conservative. If no clear entities/relationships found, return empty arrays.
"""
        
        try:
           
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You are a knowledge extraction expert for blockchain and web3 technologies. Extract only factual information."},
                    {"role": "user", "content": prompt}
                ],

            )
            
            content = response.choices[0].message.content
            
    
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                knowledge = json.loads(json_str)
                
                
                knowledge['source'] = source
                
                
                if not knowledge.get('entities'):
                    knowledge['entities'] = []
                if not knowledge.get('relationships'):
                    knowledge['relationships'] = []
                
                print(f"  ✓ Extracted {len(knowledge['entities'])} entities, {len(knowledge['relationships'])} relationships")
                
                return knowledge
            else:
                print("  ⚠ No valid JSON found in response")
                return None
                
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parsing error: {e}")
            print(f"  Response: {content[:200]}...")
            return None
        except Exception as e:
            print(f"  ✗ Error extracting knowledge: {e}")
            return None
    
    def extract_from_scraped_data(self, scraped_data: Dict) -> List[Dict]:
        """
        Extract knowledge from scraped content
        """
        all_knowledge = []
        
      
        if not scraped_data:
            return all_knowledge
        
        title_text = scraped_data.get('title', '')
        headings = scraped_data.get('headings', [])
        
        if headings and len(headings) > 0:
            headings_text = ' '.join([h.get('text', '') for h in headings if isinstance(h, dict)])
        else:
            headings_text = ''
        
        combined_text = f"{title_text} {headings_text}".strip()
        
        if combined_text and len(combined_text) > 20:  # Minimum length threshold
            knowledge = self.extract_from_text(
                combined_text,
                source=scraped_data.get('url')
            )
            if knowledge and (knowledge.get('entities') or knowledge.get('relationships')):
                all_knowledge.append(knowledge)
        
  
        paragraphs = scraped_data.get('paragraphs', [])
        
        if not paragraphs or len(paragraphs) == 0:
            print(f"  ⚠ No paragraphs found in {scraped_data.get('url', 'unknown')}")
            return all_knowledge
        
        chunk_size = 3
        
        for i in range(0, min(len(paragraphs), 15), chunk_size):  
            chunk = paragraphs[i:i+chunk_size]
            chunk_text = ' '.join(chunk).strip()
            
            if chunk_text and len(chunk_text) > 50: 
                knowledge = self.extract_from_text(
                    chunk_text,
                    source=scraped_data.get('url')
                )
                if knowledge and (knowledge.get('entities') or knowledge.get('relationships')):
                    all_knowledge.append(knowledge)
        
        return all_knowledge
    
    def merge_knowledge(self, knowledge_list: List[Dict]) -> Dict:
        """
        Merge multiple knowledge extractions, removing duplicates
        """
        all_entities = []
        all_relationships = []
        
        entity_set = set()
        relationship_set = set()
        
        for knowledge in knowledge_list:
            if not knowledge:
                continue
                

            for entity in knowledge.get('entities', []):
                if not entity or not entity.get('name'):
                    continue
                    
                entity_key = (entity['name'].lower(), entity.get('type', 'Unknown'))
                if entity_key not in entity_set:
                    entity_set.add(entity_key)
                    all_entities.append(entity)
            
      
            for rel in knowledge.get('relationships', []):
                if not rel or not rel.get('subject') or not rel.get('object'):
                    continue
                    
                rel_key = (
                    rel['subject'].lower(),
                    rel.get('relation', 'related_to').lower(),
                    rel['object'].lower()
                )
                if rel_key not in relationship_set:
                    relationship_set.add(rel_key)
                    all_relationships.append(rel)
        
        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "total_entities": len(all_entities),
            "total_relationships": len(all_relationships)
        }


if __name__ == "__main__":
    extractor = KnowledgeExtractor()
    
    sample_text = """
    Irys is a Layer-1 programmable datachain. It uses a Hybrid Consensus Model
    combining Proof of Work and Staking. The Irys Portal contains QuestLand,
    which rewards points on Galxe.
    """
    
    knowledge = extractor.extract_from_text(sample_text, source="test")
    
    if knowledge:
        print(json.dumps(knowledge, indent=2))
    else:
        print("No knowledge extracted")