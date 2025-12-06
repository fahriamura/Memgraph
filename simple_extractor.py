import re
from typing import List, Dict

class SimpleExtractor:
    def __init__(self):

        self.platform_keywords = ['irys', 'irysx', 'arweave', 'memgraph']
        self.feature_keywords = ['questland', 'portal', 'consensus', 'ledger']
        self.action_keywords = ['rewards', 'stakes', 'provides', 'uses', 'contains']
    
    def extract_from_text(self, text: str, source: str = None) -> Dict:
        entities = []
        relationships = []
        
        entity_pattern = r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b'
        potential_entities = re.findall(entity_pattern, text)
        
        seen = set()
        for entity in potential_entities:
            if entity.lower() not in seen and len(entity) > 2:
                seen.add(entity.lower())
                entities.append({
                    "name": entity,
                    "type": "Entity",
                    "description": f"Mentioned in {source or 'text'}"
                })
        
        return {
            "entities": entities[:10],  # Limit to 10
            "relationships": relationships,
            "source": source
        }
    
    def extract_from_scraped_data(self, scraped_data: Dict) -> List[Dict]:
        all_knowledge = []
        

        title = scraped_data.get('title', '')
        paragraphs = scraped_data.get('paragraphs', [])
        
        combined = title + ' ' + ' '.join(paragraphs[:5])
        
        knowledge = self.extract_from_text(combined, scraped_data.get('url'))
        if knowledge:
            all_knowledge.append(knowledge)
        
        return all_knowledge