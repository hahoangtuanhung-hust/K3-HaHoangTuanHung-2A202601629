import sys
import os

# Set up paths for Vercel serverless environment
root_dir = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.app import app
