from app.models.knowledge import KnowledgeObject
class MemoryKnowledgeRepository:
    def __init__(self): self.items: dict[str, KnowledgeObject] = {}
    async def add(self,item): self.items[item.id]=item; return item
    async def save(self,item): self.items[item.id]=item; return item
    async def list(self): return list(self.items.values())
    async def get(self,item_id): return self.items.get(item_id)
    async def by_key(self,canonical_key): return [x for x in self.items.values() if x.canonical_key==canonical_key]
    async def clear(self): self.items.clear()
repository = MemoryKnowledgeRepository()
