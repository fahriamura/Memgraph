from neo4j import GraphDatabase
from typing import List, Dict, Optional

class MemgraphHandler:
    def __init__(self, host: str, port: int, username: str = "", password: str = ""):
        self.uri = f"bolt://{host}:{port}"
        self.username = username
        self.password = password
        self.driver = None
        
    def connect(self):
        try:
            auth = (self.username, self.password) if self.username else None
            self.driver = GraphDatabase.driver(self.uri, auth=auth)
            
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            print(f"✓ Connected to Memgraph at {self.uri}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Memgraph: {e}")
            print(f"  Make sure Memgraph is running on {self.uri}")
            return False
    
    def disconnect(self):
        if self.driver:
            self.driver.close()
            print("✓ Disconnected from Memgraph")
    
    def execute_query(self, query: str, parameters: Dict = None):
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return list(result)
        except Exception as e:
            print(f"✗ Query execution failed: {e}")
            print(f"  Query: {query}")
            print(f"  Params: {parameters}")
            return None
    
    def node_exists(self, node_id: str, node_type: str) -> bool:
        query = f"MATCH (n:{node_type} {{id: $node_id}}) RETURN count(n) as count"
        result = self.execute_query(query, {"node_id": node_id})
        return result and result[0]["count"] > 0
    
    def create_node(self, node_id: str, node_type: str, properties: Dict):
        """
        Create new node - FIXED VERSION with proper parameter binding
        """
        # Sanitize node_type
        node_type = node_type.replace(" ", "_").replace("-", "_")
        
        # Build parameters dict - start with id
        params = {"node_id": node_id}
        
        # Add other properties (exclude 'id' to avoid duplication)
        prop_assignments = ["id: $node_id"]  # Always set id first
        
        for key, value in properties.items():
            if key != 'id':  # Skip 'id' if present in properties
                # Create unique parameter name
                param_name = f"prop_{key}"
                params[param_name] = value
                prop_assignments.append(f"{key}: ${param_name}")
        
        # Build query
        props_str = ", ".join(prop_assignments)
        query = f"CREATE (n:{node_type} {{{props_str}}}) RETURN n"
        
        # Debug print (remove in production)
        # print(f"DEBUG Query: {query}")
        # print(f"DEBUG Params: {params}")
        
        result = self.execute_query(query, params)
        
        if result:
            print(f"✓ Created node: {node_id} (:{node_type})")
            return True
        return False

    def node_exists_any_label(self, node_id: str) -> bool:
        query = "MATCH (n {id: $node_id}) RETURN count(n) as count"
        result = self.execute_query(query, {"node_id": node_id})
        return result and result[0]["count"] > 0
    
    def relationship_exists(self, from_id: str, to_id: str, relation_type: str) -> bool:
        query = f"""
        MATCH (a {{id: $from_id}})-[r:{relation_type}]->(b {{id: $to_id}})
        RETURN count(r) as count
        """
        
        result = self.execute_query(query, {
            "from_id": from_id,
            "to_id": to_id
        })
        
        return result and result[0]["count"] > 0
    
    def create_relationship(self, from_id: str, to_id: str, 
                          relation_type: str, properties: Dict = None):
        """
        Create relationship - FIXED VERSION
        """
        params = {
            "from_id": from_id,
            "to_id": to_id
        }
        
        if properties:
            # Build property assignments with unique param names
            prop_assignments = []
            for key, value in properties.items():
                param_name = f"rel_{key}"
                params[param_name] = value
                prop_assignments.append(f"{key}: ${param_name}")
            
            props_str = "{" + ", ".join(prop_assignments) + "}"
            
            query = f"""
            MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
            CREATE (a)-[r:{relation_type} {props_str}]->(b)
            RETURN r
            """
        else:
            query = f"""
            MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
            CREATE (a)-[r:{relation_type}]->(b)
            RETURN r
            """
        
        result = self.execute_query(query, params)
        
        if result:
            print(f"✓ Created relationship: {from_id} -[{relation_type}]-> {to_id}")
            return True
        return False
    
    def insert_triplet(self, subject: str, subject_type: str,
                      relation: str, obj: str, obj_type: str,
                      source: str = None):
        """
        Insert triplet - FIXED VERSION
        """
        # Create subject if not exists
        if not self.node_exists(subject, subject_type):
            properties = {"source": source or "scraped"}
            # Don't add description = subject (that's the bug!)
            self.create_node(subject, subject_type, properties)
        
        # Create object if not exists
        if not self.node_exists(obj, obj_type):
            properties = {"source": source or "scraped"}
            # Don't add description = obj
            self.create_node(obj, obj_type, properties)
        
        # Create relationship
        query = f"""
        MATCH (a:{subject_type} {{id: $subject}}), (b:{obj_type} {{id: $obj}})
        MERGE (a)-[r:{relation}]->(b)
        SET r.source = $source
        RETURN r
        """
        
        result = self.execute_query(query, {
            "subject": subject,
            "obj": obj,
            "source": source or "scraped"
        })
        
        if result:
            print(f"✓ Triplet: ({subject}) -[{relation}]-> ({obj})")
            return True
        return False
    
    def get_all_nodes(self) -> List[Dict]:
        query = "MATCH (n) RETURN n"
        result = self.execute_query(query)
        
        nodes = []
        if result:
            for record in result:
                node = record["n"]
                nodes.append({
                    "id": node.get("id"),
                    "type": list(node.labels)[0] if node.labels else "Unknown",
                    "properties": dict(node)
                })
        return nodes
    
    def get_all_relationships(self) -> List[Dict]:
        query = "MATCH (a)-[r]->(b) RETURN a.id as from_id, type(r) as rel_type, b.id as to_id, properties(r) as props"
        result = self.execute_query(query)
        
        relationships = []
        if result:
            for record in result:
                relationships.append({
                    "from": record["from_id"],
                    "relation": record["rel_type"],
                    "to": record["to_id"],
                    "properties": dict(record["props"]) if record["props"] else {}
                })
        return relationships
    
    def search_node_by_text(self, text: str) -> List[Dict]:
        query = """
        MATCH (n)
        WHERE n.id CONTAINS $text OR n.description CONTAINS $text
        RETURN n
        """
        
        result = self.execute_query(query, {"text": text})
        
        nodes = []
        if result:
            for record in result:
                node = record["n"]
                nodes.append({
                    "id": node.get("id"),
                    "type": list(node.labels)[0] if node.labels else "Unknown",
                    "properties": dict(node)
                })
        return nodes
    
    def get_graph_statistics(self) -> Dict:
        stats = {
            "total_nodes": 0,
            "total_relationships": 0,
            "node_types": {},
            "relationship_types": {}
        }

        nodes = self.get_all_nodes()
        stats["total_nodes"] = len(nodes)
        
        for node in nodes:
            node_type = node["type"]
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
        
        relationships = self.get_all_relationships()
        stats["total_relationships"] = len(relationships)
        
        for rel in relationships:
            rel_type = rel["relation"]
            stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
        
        return stats


if __name__ == "__main__":
    handler = MemgraphHandler(host="localhost", port=7687)
    
    if handler.connect():
        print("\n✓ Connection test successful!")
        
        # Clean test
        print("\nCleaning old test data...")
        handler.execute_query("MATCH (n) WHERE n.source = 'test' DETACH DELETE n")
        
        # Test insert
        print("\nTesting insert...")
        handler.insert_triplet(
            subject="TestIrys",
            subject_type="Platform",
            relation="has_component",
            obj="TestIrysVM",
            obj_type="Component",
            source="test"
        )
        
        # Verify
        nodes = handler.get_all_nodes()
        test_nodes = [n for n in nodes if n['properties'].get('source') == 'test']
        
        print(f"\nCreated {len(test_nodes)} test nodes:")
        for node in test_nodes:
            print(f"\n  {node['id']} ({node['type']}):")
            for k, v in node['properties'].items():
                print(f"    {k}: {v}")
        
        # Cleanup
        print("\nCleaning up test data...")
        handler.execute_query("MATCH (n) WHERE n.source = 'test' DETACH DELETE n")
        
        handler.disconnect()
    else:
        print("\n✗ Connection test failed!")