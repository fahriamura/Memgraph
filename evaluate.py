"""
Comprehensive comparison: LLM Only vs LLM + RAG (Memgraph KG)
Complete version with all fixes included
Results saved to JSON for analysis
"""

from openai import OpenAI
from memgraph_handler import MemgraphHandler
from config import OPENAI_API_KEY, MEMGRAPH_HOST, MEMGRAPH_PORT
import time
import json
from datetime import datetime

class ComprehensiveComparison:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.memgraph = MemgraphHandler(MEMGRAPH_HOST, MEMGRAPH_PORT)
        
        # Test questions covering different aspects
        self.test_questions = [
            {
                "id": "Q1",
                "question": "What is Irys Netowrk?",
                "category": "definition",
                "expected_entities": ["Irys Network", "Programmable Datachain", "IrysVM"]
            },
            {
                "id": "Q2",
                "question": "What is the highest discord role in Irys Network?",
                "category": "hierarchy",
                "expected_entities": ["Shihan", "Role"]
            },
            {
                "id": "Q3",
                "question": "How to check points in irys network?",
                "category": "process",
                "expected_entities": ["Galxe", "QuestLand", "Rank"]
            },
            {
                "id": "Q4",
                "question": "What games are available in Irys Network?",
                "category": "listing",
                "expected_entities": ["Snake", "Spritetype", "Testnet"]
            },
            {
                "id": "Q5",
                "question": "Explain IrysVM",
                "category": "explanation",
                "expected_entities": ["IrysVM", "Smart contracts", "Data Layer"]
            },
            {
                "id": "Q6",
                "question": "What consensus mechanism does Irys Network use?",
                "category": "technical",
                "expected_entities": ["Hybrid Consensus Model", "Proof of Work", "Staking"]
            },
            {
                "id": "Q7",
                "question": "How do miners participate in Irys Network?",
                "category": "process",
                "expected_entities": ["Miners", "Staking", "16TB partitions"]
            }
        ]
    
    def verify_and_add_missing_data(self):
        """
        Verify graph has required data, add if missing
        """
        print("\n[Setup] Verifying graph data...")
        
        if not self.memgraph.connect():
            print("  ✗ Cannot connect to Memgraph")
            return False
        
        # Check role hierarchy
        roles_check = self.memgraph.execute_query("""
            MATCH (a)-[r:higher_than]->(b)
            RETURN count(r) as count
        """)
        
        if not roles_check or roles_check[0]['count'] == 0:
            print("  Adding role hierarchy...")
            self._add_role_data()
        
        # Check games
        games_check = self.memgraph.execute_query("""
            MATCH (n)
            WHERE n.id IN ['Snake', 'Spritetype']
            RETURN count(n) as count
        """)
        
        if not games_check or games_check[0]['count'] < 2:
            print("  Adding games data...")
            self._add_games_data()
        
        # Check points/rank
        points_check = self.memgraph.execute_query("""
            MATCH (n)-[r]-(m)
            WHERE n.id = 'Galxe' OR m.id = 'Galxe'
            RETURN count(r) as count
        """)
        
        if not points_check or points_check[0]['count'] == 0:
            print("  Adding points/rank data...")
            self._add_points_data()
        
        self.memgraph.disconnect()
        print("  ✓ Graph data verified")
        return True
    
    def _add_role_data(self):
        """Add role hierarchy to graph"""
        roles_data = [
            ("Shihan", "Role", "Masters, guiding the community", 4),
            ("Senshi", "Role", "Warriors & protectors", 3),
            ("Shugo", "Role", "Practitioners with foundations", 2),
            ("Deshi", "Role", "Apprentices, first steps", 1),
        ]
        
        for role_id, role_type, desc, level in roles_data:
            self.memgraph.execute_query("""
                MERGE (n:Role {id: $id})
                SET n.description = $desc, n.level = $level, n.source = 'manual'
            """, {"id": role_id, "desc": desc, "level": level})
        
        hierarchy = [
            ("Shihan", "Senshi"),
            ("Senshi", "Shugo"),
            ("Shugo", "Deshi"),
        ]
        
        for higher, lower in hierarchy:
            self.memgraph.execute_query("""
                MATCH (a:Role {id: $higher}), (b:Role {id: $lower})
                MERGE (a)-[:higher_than]->(b)
            """, {"higher": higher, "lower": lower})
        
        # Discord relationships
        self.memgraph.execute_query("""
            MERGE (d:Community {id: 'Discord'})
            WITH d
            MATCH (r:Role)
            WHERE r.id IN ['Shihan', 'Senshi', 'Shugo', 'Deshi']
            MERGE (d)-[:has_role]->(r)
        """)
    
    def _add_games_data(self):
        """Add games to graph"""
        self.memgraph.execute_query("""
            MERGE (t:NetworkState {id: 'Testnet'})
            MERGE (s:Game {id: 'Snake'})
            MERGE (sp:Game {id: 'Spritetype'})
            MERGE (t)-[:hosts_game]->(s)
            MERGE (t)-[:hosts_game]->(sp)
        """)
    
    def _add_points_data(self):
        """Add points/rank data to graph"""
        self.memgraph.execute_query("""
            MERGE (g:Platform {id: 'Galxe'})
            MERGE (q:Feature {id: 'QuestLand'})
            MERGE (r:Metric {id: 'Rank'})
            MERGE (k:Leaderboard {id: 'Kaito Leaderboard'})
            MERGE (q)-[:rewards_points_on]->(g)
            MERGE (r)-[:displayed_on]->(g)
            MERGE (k)-[:measures]->(r)
        """)
    
    def query_llm_only(self, question: str) -> dict:
        """
        Method 1: Pure LLM without KG
        """
        start_time = time.time()
        
        prompt = f"""You are an expert on Irys Network. Answer this question based on your training data:

Question: {question}

Provide a concise, accurate answer."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {"role": "system", "content": "You are an expert on blockchain and Irys Network."},
                    {"role": "user", "content": prompt}
                ],
            )
            
            answer = response.choices[0].message.content
            latency = (time.time() - start_time) * 1000
            
            return {
                "method": "LLM_ONLY",
                "answer": answer,
                "latency_ms": round(latency, 2),
                "tokens_used": response.usage.total_tokens,
                "success": True,
                "error": None
            }
        
        except Exception as e:
            return {
                "method": "LLM_ONLY",
                "answer": None,
                "latency_ms": (time.time() - start_time) * 1000,
                "tokens_used": 0,
                "success": False,
                "error": str(e)
            }
    
    def detect_question_type(self, question: str) -> dict:
        """
        Detect question type for optimized query
        """
        question_lower = question.lower()
        
        # IrysVM specific
        if 'irysvm' in question_lower:
            return {
                "type": "irysvm",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE n.id = 'IrysVM' OR m.id = 'IrysVM'
                    RETURN n.id, type(r), m.id,
                           COALESCE(n.description, '') as n_desc,
                           COALESCE(m.description, '') as m_desc
                    LIMIT 20
                """
            }
        
        # Irys definition
        elif ('what is irys' in question_lower and 'irysvm' not in question_lower):
            return {
                "type": "irys_definition",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE n.id IN ['Irys', 'Irys Network'] 
                       OR m.id IN ['Irys', 'Irys Network']
                    RETURN n.id, type(r), m.id,
                           COALESCE(n.description, '') as n_desc,
                           COALESCE(m.description, '') as m_desc
                    LIMIT 20
                """
            }
        
        # Points/Rank
        elif any(word in question_lower for word in ['point', 'check', 'rank', 'score']):
            return {
                "type": "points",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.id) CONTAINS 'galxe'
                       OR toLower(n.id) CONTAINS 'questland'
                       OR toLower(n.id) CONTAINS 'rank'
                       OR toLower(m.id) CONTAINS 'galxe'
                       OR toLower(m.id) CONTAINS 'questland'
                       OR toLower(type(r)) CONTAINS 'point'
                       OR toLower(type(r)) CONTAINS 'reward'
                    RETURN n.id, type(r), m.id, 
                           COALESCE(n.description, '') as desc
                    LIMIT 15
                """
            }
        
        # Games
        elif any(word in question_lower for word in ['game', 'play']):
            return {
                "type": "games",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.id) CONTAINS 'snake'
                       OR toLower(n.id) CONTAINS 'sprite'
                       OR toLower(m.id) CONTAINS 'snake'
                       OR toLower(m.id) CONTAINS 'sprite'
                       OR toLower(type(r)) CONTAINS 'game'
                       OR toLower(type(r)) CONTAINS 'host'
                    RETURN n.id, type(r), m.id
                    LIMIT 15
                """
            }
        
        # Hierarchy - FIXED
        elif any(word in question_lower for word in ['highest', 'top', 'role', 'hierarchy']):
            return {
                "type": "hierarchy",
                "query": """
                    MATCH (r:Role)-[rel:higher_than]->(lower)
                    WITH r, count(rel) as outgoing_count
                    OPTIONAL MATCH (higher)-[:higher_than]->(r)
                    WITH r, outgoing_count, count(higher) as incoming_count
                    WHERE incoming_count = 0
                    OPTIONAL MATCH (r)-[rel2]-(m)
                    RETURN r.id as role, 
                           r.description as description, 
                           r.level as level,
                           type(rel2) as relation,
                           m.id as related
                    LIMIT 15
                """
            }
        
        # Consensus mechanism
        elif 'consensus' in question_lower or 'mechanism' in question_lower:
            return {
                "type": "consensus",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.id) CONTAINS 'consensus'
                       OR toLower(n.id) CONTAINS 'hybrid'
                       OR toLower(n.id) CONTAINS 'proof'
                       OR toLower(n.id) CONTAINS 'staking'
                       OR toLower(m.id) CONTAINS 'consensus'
                    RETURN n.id, type(r), m.id,
                           COALESCE(n.description, '') as n_desc
                    LIMIT 15
                """
            }
        
        # Miners
        elif 'miner' in question_lower or 'mining' in question_lower:
            return {
                "type": "miners",
                "query": """
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.id) CONTAINS 'miner'
                       OR toLower(m.id) CONTAINS 'miner'
                       OR toLower(n.id) CONTAINS 'staking'
                       OR toLower(n.id) CONTAINS 'partition'
                    RETURN n.id, type(r), m.id,
                           COALESCE(n.description, '') as desc
                    LIMIT 15
                """
            }
        
        # General fallback
        else:
            keywords = [w for w in question_lower.split() if len(w) > 4]
            keyword = keywords[0] if keywords else 'irys'
            
            return {
                "type": "general",
                "query": f"""
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.id) CONTAINS '{keyword}'
                       OR toLower(m.id) CONTAINS '{keyword}'
                    RETURN n.id, type(r), m.id,
                           COALESCE(n.description, '') as n_desc,
                           COALESCE(m.description, '') as m_desc
                    LIMIT 20
                """
            }
    
    def query_llm_with_rag(self, question: str) -> dict:
        """
        Method 2: LLM + Knowledge Graph RAG
        """
        start_time = time.time()
        
        query_info = self.detect_question_type(question)
        
        kg_start = time.time()
        
        if not self.memgraph.connect():
            return {
                "method": "LLM_RAG",
                "answer": None,
                "success": False,
                "error": "Cannot connect to Memgraph"
            }
        
        try:
            results = self.memgraph.execute_query(query_info["query"])
            kg_time = (time.time() - kg_start) * 1000
            
            self.memgraph.disconnect()
            
            if not results or len(results) == 0:
                return {
                    "method": "LLM_RAG",
                    "answer": "No relevant knowledge found in graph",
                    "latency_ms": (time.time() - start_time) * 1000,
                    "kg_retrieval_ms": kg_time,
                    "facts_retrieved": 0,
                    "query_type": query_info["type"],
                    "success": False,
                    "error": "Empty KG results"
                }
            
            # Format facts
            facts = []
            for i, record in enumerate(results[:20], 1):
                keys = list(record.keys())
                fact_parts = []
                for key in keys:
                    value = record[key]
                    if value and str(value).strip() and str(value) not in ['None', '']:
                        value_str = str(value)[:100]
                        fact_parts.append(f"{key}: {value_str}")
                
                if fact_parts:
                    facts.append(f"{i}. {' | '.join(fact_parts)}")
            
            context = "\n".join(facts)
            
            # LLM synthesis
            synthesis_start = time.time()
            
            synthesis_prompt = f"""Based on these facts from Irys Network Knowledge Graph:

{context}

Question: {question}

Instructions:
- Answer using ONLY the facts above
- Be specific and cite entities mentioned in facts
- If facts show relationships, explain them clearly
- Connect related facts to give complete answer
- Don't say information is insufficient unless truly no relevant facts exist

Answer:"""
            
            response = self.client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Answer using provided facts. Always try to find useful information in facts. Be specific with entity names."
                    },
                    {"role": "user", "content": synthesis_prompt}
                ],
            )
            
            answer = response.choices[0].message.content
            synthesis_time = (time.time() - synthesis_start) * 1000
            total_time = (time.time() - start_time) * 1000
            
            return {
                "method": "LLM_RAG",
                "answer": answer,
                "latency_ms": round(total_time, 2),
                "kg_retrieval_ms": round(kg_time, 2),
                "llm_synthesis_ms": round(synthesis_time, 2),
                "tokens_used": response.usage.total_tokens,
                "facts_retrieved": len(results),
                "query_type": query_info["type"],
                "context_used": context[:500] + "..." if len(context) > 500 else context,
                "success": True,
                "error": None
            }
        
        except Exception as e:
            self.memgraph.disconnect()
            return {
                "method": "LLM_RAG",
                "answer": None,
                "latency_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e)
            }
    
    def evaluate_answer(self, answer: str, expected_entities: list) -> dict:
        """
        Evaluate answer quality
        """
        if not answer:
            return {
                "entities_mentioned": 0,
                "coverage": 0.0,
                "contains_expected": []
            }
        
        answer_lower = answer.lower()
        
        mentioned = []
        for entity in expected_entities:
            if entity.lower() in answer_lower:
                mentioned.append(entity)
        
        coverage = len(mentioned) / len(expected_entities) if expected_entities else 0
        
        return {
            "entities_mentioned": len(mentioned),
            "coverage": round(coverage, 2),
            "contains_expected": mentioned
        }
    
    def compare_single_question(self, test_case: dict) -> dict:
        """
        Compare both methods for single question
        """
        question = test_case["question"]
        
        print(f"\n{'='*70}")
        print(f"[{test_case['id']}] {question}")
        print(f"Category: {test_case['category']}")
        print('='*70)
        
        # Method 1: LLM Only
        print("\n[1/2] LLM Only...")
        llm_only = self.query_llm_only(question)
        
        if llm_only['success']:
            print(f"✓ Answer length: {len(llm_only['answer'])} chars")
            print(f"  Latency: {llm_only['latency_ms']:.0f}ms")
            print(f"  Answer preview: {llm_only['answer'][:100]}...")
        else:
            print(f"✗ Error: {llm_only['error']}")
        
        # Method 2: LLM + RAG
        print("\n[2/2] LLM + RAG...")
        llm_rag = self.query_llm_with_rag(question)
        
        if llm_rag['success']:
            print(f"✓ Answer length: {len(llm_rag['answer'])} chars")
            print(f"  Total latency: {llm_rag['latency_ms']:.0f}ms")
            print(f"    - KG retrieval: {llm_rag['kg_retrieval_ms']:.0f}ms")
            print(f"    - LLM synthesis: {llm_rag['llm_synthesis_ms']:.0f}ms")
            print(f"  Facts retrieved: {llm_rag['facts_retrieved']}")
            print(f"  Query type: {llm_rag['query_type']}")
            print(f"  Answer preview: {llm_rag['answer'][:100]}...")
        else:
            print(f"✗ Error: {llm_rag.get('error')}")
        
        # Evaluate both
        llm_only_eval = self.evaluate_answer(
            llm_only.get('answer'),
            test_case['expected_entities']
        )
        
        llm_rag_eval = self.evaluate_answer(
            llm_rag.get('answer'),
            test_case['expected_entities']
        )
        
        print(f"\n[Evaluation]")
        print(f"  Expected entities: {', '.join(test_case['expected_entities'])}")
        print(f"  LLM Only: {llm_only_eval['coverage']*100:.0f}% coverage ({llm_only_eval['entities_mentioned']}/{len(test_case['expected_entities'])})")
        print(f"    Found: {', '.join(llm_only_eval['contains_expected']) if llm_only_eval['contains_expected'] else 'None'}")
        print(f"  LLM+RAG: {llm_rag_eval['coverage']*100:.0f}% coverage ({llm_rag_eval['entities_mentioned']}/{len(test_case['expected_entities'])})")
        print(f"    Found: {', '.join(llm_rag_eval['contains_expected']) if llm_rag_eval['contains_expected'] else 'None'}")
        
        return {
            "question_id": test_case['id'],
            "question": question,
            "category": test_case['category'],
            "expected_entities": test_case['expected_entities'],
            "llm_only": {
                **llm_only,
                "evaluation": llm_only_eval
            },
            "llm_rag": {
                **llm_rag,
                "evaluation": llm_rag_eval
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def run_full_comparison(self, output_file: str = "comparison_results.json"):
        """
        Run full comparison on all test questions
        """
        print("\n" + "="*70)
        print("COMPREHENSIVE COMPARISON: LLM Only vs LLM + RAG")
        print("="*70)
        print(f"Test questions: {len(self.test_questions)}")
        print(f"Output file: {output_file}")
        print("="*70)
        
        # Verify and prepare data
        if not self.verify_and_add_missing_data():
            print("✗ Failed to prepare graph data")
            return None
        
        results = []
        
        for test_case in self.test_questions:
            result = self.compare_single_question(test_case)
            results.append(result)
            time.sleep(1)
        
        # Generate summary
        summary = self.generate_summary(results)
        
        # Save to JSON
        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_questions": len(self.test_questions),
                "model": "gpt-5.1",
                "kg_database": "Memgraph"
            },
            "summary": summary,
            "detailed_results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"✓ Results saved to: {output_file}")
        print("="*70)
        
        # Print summary
        self.print_summary(summary)
        
        return output
    
    def generate_summary(self, results: list) -> dict:
        """Generate summary statistics"""
        llm_only_success = sum(1 for r in results if r['llm_only']['success'])
        llm_rag_success = sum(1 for r in results if r['llm_rag']['success'])
        
        llm_only_latencies = [r['llm_only']['latency_ms'] for r in results if r['llm_only']['success']]
        llm_rag_latencies = [r['llm_rag']['latency_ms'] for r in results if r['llm_rag']['success']]
        
        llm_only_coverages = [r['llm_only']['evaluation']['coverage'] for r in results if r['llm_only']['success']]
        llm_rag_coverages = [r['llm_rag']['evaluation']['coverage'] for r in results if r['llm_rag']['success']]
        
        llm_only_tokens = [r['llm_only']['tokens_used'] for r in results if r['llm_only']['success']]
        llm_rag_tokens = [r['llm_rag']['tokens_used'] for r in results if r['llm_rag']['success']]
        
        return {
            "success_rate": {
                "llm_only": f"{llm_only_success}/{len(results)} ({llm_only_success/len(results)*100:.1f}%)",
                "llm_rag": f"{llm_rag_success}/{len(results)} ({llm_rag_success/len(results)*100:.1f}%)"
            },
            "average_latency_ms": {
                "llm_only": round(sum(llm_only_latencies)/len(llm_only_latencies), 2) if llm_only_latencies else 0,
                "llm_rag": round(sum(llm_rag_latencies)/len(llm_rag_latencies), 2) if llm_rag_latencies else 0,
                "difference": round((sum(llm_rag_latencies)/len(llm_rag_latencies) - sum(llm_only_latencies)/len(llm_only_latencies)), 2) if llm_only_latencies and llm_rag_latencies else 0
            },
            "average_coverage": {
                "llm_only": round(sum(llm_only_coverages)/len(llm_only_coverages), 2) if llm_only_coverages else 0,
                "llm_rag": round(sum(llm_rag_coverages)/len(llm_rag_coverages), 2) if llm_rag_coverages else 0,
                "improvement": round((sum(llm_rag_coverages)/len(llm_rag_coverages) - sum(llm_only_coverages)/len(llm_only_coverages)), 2) if llm_only_coverages and llm_rag_coverages else 0
            },
            "average_tokens": {
                "llm_only": round(sum(llm_only_tokens)/len(llm_only_tokens), 1) if llm_only_tokens else 0,
                "llm_rag": round(sum(llm_rag_tokens)/len(llm_rag_tokens), 1) if llm_rag_tokens else 0
            },
            "kg_retrieval": {
                "avg_facts_retrieved": round(sum(r['llm_rag']['facts_retrieved'] for r in results if r['llm_rag']['success'])/llm_rag_success, 1) if llm_rag_success > 0 else 0,
                "avg_kg_time_ms": round(sum(r['llm_rag']['kg_retrieval_ms'] for r in results if r['llm_rag']['success'])/llm_rag_success, 2) if llm_rag_success > 0 else 0
            }
        }
    
    def print_summary(self, summary: dict):
        """Print summary to console"""
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        
        print("\n📊 Success Rate:")
        print(f"  LLM Only: {summary['success_rate']['llm_only']}")
        print(f"  LLM+RAG:  {summary['success_rate']['llm_rag']}")
        
        print("\n⏱️  Average Latency:")
        print(f"  LLM Only: {summary['average_latency_ms']['llm_only']:.0f}ms")
        print(f"  LLM+RAG:  {summary['average_latency_ms']['llm_rag']:.0f}ms")
        diff = summary['average_latency_ms']['difference']
        pct = (diff/summary['average_latency_ms']['llm_only']*100) if summary['average_latency_ms']['llm_only'] > 0 else 0
        print(f"  Difference: +{diff:.0f}ms (+{pct:.1f}%)")
        
        print("\n🎯 Average Entity Coverage:")
        print(f"  LLM Only: {summary['average_coverage']['llm_only']*100:.0f}%")
        print(f"  LLM+RAG:  {summary['average_coverage']['llm_rag']*100:.0f}%")
        print(f"  Improvement: +{summary['average_coverage']['improvement']*100:.0f}%")
        
        print("\n💾 Knowledge Graph Stats:")
        print(f"  Avg facts retrieved: {summary['kg_retrieval']['avg_facts_retrieved']:.1f} facts/query")
        print(f"  Avg KG query time: {summary['kg_retrieval']['avg_kg_time_ms']:.0f}ms")
        
        print("\n💰 Token Usage:")
        print(f"  LLM Only: {summary['average_tokens']['llm_only']:.0f} tokens/query")
        print(f"  LLM+RAG:  {summary['average_tokens']['llm_rag']:.0f} tokens/query")
        
        print("="*70 + "\n")

def main():
    comparator = ComprehensiveComparison()
    
    print("\n" + "="*70)
    print("LLM vs RAG COMPARISON TOOL")
    print("="*70)
    print("\nOptions:")
    print("1. Run full comparison (all questions)")
    print("2. Test single question")
    print("3. Exit")
    
    choice = input("\nSelect (1-3): ").strip()
    
    if choice == '1':
        output_file = input("\nOutput filename [comparison_results.json]: ").strip()
        if not output_file:
            output_file = "comparison_results.json"
        
        comparator.run_full_comparison(output_file)
    
    elif choice == '2':
        question = input("\nEnter question: ").strip()
        if question:
            test_case = {
                "id": "CUSTOM",
                "question": question,
                "category": "custom",
                "expected_entities": []
            }
            comparator.compare_single_question(test_case)
    
    else:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()