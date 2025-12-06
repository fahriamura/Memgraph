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
            
            # Test connection
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
        """
        Disconnect from Memgraph
        """
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
            return None
    
    def node_exists(self, node_id: str, node_type: str) -> bool:
        query = f"MATCH (n:{node_type} {{id: $node_id}}) RETURN count(n) as count"
        result = self.execute_query(query, {"node_id": node_id})
        return result and result[0]["count"] > 0
    
    def create_node(self, node_id: str, node_type: str, properties: Dict):
        """
        Create new node with specific label
        """
        # Sanitize node_type (remove spaces, special chars)
        node_type = node_type.replace(" ", "_").replace("-", "_")
        
        props_list = [f"{k}: ${k}" for k in properties.keys()]
        props_str = ", ".join(props_list)
        
        query = f"CREATE (n:{node_type} {{id: $id, {props_str}}}) RETURN n"
        params = {"id": node_id, **properties}
        
        result = self.execute_query(query, params)
        if result:
            print(f"✓ Created node: {node_id} (:{node_type})")
            return True
        return False

    def node_exists_any_label(self, node_id: str) -> bool:
        """
        Check if node exists with ANY label
        """
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
        props_str = ""
        params = {
            "from_id": from_id,
            "to_id": to_id
        }
        
        if properties:
            props_list = [f"{k}: ${k}" for k in properties.keys()]
            props_str = "{" + ", ".join(props_list) + "}"
            params.update(properties)
        
        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        CREATE (a)-[r:{relation_type} {props_str}]->(b)
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
        if not self.node_exists(subject, subject_type):
            self.create_node(subject, subject_type, {
                "description": subject,
                "source": source or "scraped"
            })
        
        if not self.node_exists(obj, obj_type):
            self.create_node(obj, obj_type, {
                "description": obj,
                "source": source or "scraped"
            })
        
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
        """
        Get all nodes
        """
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
        """
        Get all relationships from graph
        """
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
        
        handler.insert_triplet(
            subject="Irys",
            subject_type="Platform",
            relation="has_component",
            obj="IrysVM",
            obj_type="Platform",
            source="test"
        )
        
        nodes = handler.get_all_nodes()
        print(f"\nTotal nodes in graph: {len(nodes)}")
        
        relationships = handler.get_all_relationships()
        print(f"Total relationships in graph: {len(relationships)}")

        stats = handler.get_graph_statistics()
        print(f"\nGraph Statistics:")
        print(f"  Nodes: {stats['total_nodes']}")
        print(f"  Relationships: {stats['total_relationships']}")
        
        handler.disconnect()
    else:
        print("\n✗ Connection test failed!")
        print("\nMake sure Memgraph is running:")
        print("  docker run -p 7687:7687 memgraph/memgraph")