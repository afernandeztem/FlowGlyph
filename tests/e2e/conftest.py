import os

# Rich reads the width when the CLI's consoles are created, at import time.
os.environ["COLUMNS"] = "200"
