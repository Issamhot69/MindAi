from datetime import datetime

class AIMind:
    def __init__(self, user_id):
        self.user_id = user_id
        self.memory = {}
        self.version = "0.1.0"
        print(f"🧠 AI Mind actif — utilisateur : {user_id}")

    def remember(self, key, value):
        self.memory[key] = {"value": value, "date": datetime.now().isoformat()}
        print(f"✓ Mémorisé : {key} = {value}")

    def recall(self, key):
        item = self.memory.get(key)
        return item["value"] if item else None

    def status(self):
        print(f"""
┌─────────────────────────────┐
│       AI MIND  v{self.version}      │
├─────────────────────────────┤
│ Utilisateur : {self.user_id:<14}│
│ Mémoires    : {len(self.memory):<14}│
└─────────────────────────────┘""")

if __name__ == "__main__":
    brain = AIMind("ahmed")
    brain.remember("style", "cinématique réaliste")
    brain.remember("plateforme", "Instagram + TikTok")
    brain.status()
    print(f"\nStyle actif : {brain.recall('style')}")
