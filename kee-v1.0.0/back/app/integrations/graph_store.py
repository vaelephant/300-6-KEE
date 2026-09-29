from app.core.config import settings
class GraphStore:
    def sync(self,obj):
        if not (settings.enable_neo4j_sync and settings.neo4j_uri): return {"enabled":False}
        from neo4j import GraphDatabase
        driver=GraphDatabase.driver(settings.neo4j_uri,auth=(settings.neo4j_user,settings.neo4j_password))
        with driver.session() as s:
            s.run("MERGE (k:Knowledge {id:$id}) SET k.content=$content,k.status=$status,k.version=$version,k.confidence=$confidence",id=obj.id,content=obj.content,status=obj.status,version=obj.version,confidence=obj.confidence)
            for ent in obj.entities:
                s.run("MATCH (k:Knowledge {id:$kid}) MERGE (e:Entity {name:$name}) MERGE (k)-[:MENTIONS]->(e)",kid=obj.id,name=ent)
            for rel in obj.relations:
                a=rel.get('source') or rel.get('from'); b=rel.get('target') or rel.get('to'); typ=rel.get('type','RELATED_TO')
                if a and b: s.run("MERGE (a:Entity {name:$a}) MERGE (b:Entity {name:$b}) MERGE (a)-[r:RELATED_TO]->(b) SET r.kind=$kind",a=a,b=b,kind=typ)
        driver.close(); return {"enabled":True}
graph_store=GraphStore()
