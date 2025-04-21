class VM:
    def __init__(self, memory: int):
        self.memory = memory

    def __repr__(self):
        return f"VM({self.memory})"

    def size(self):
        return self.memory