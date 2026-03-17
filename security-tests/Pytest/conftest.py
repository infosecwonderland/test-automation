import os
import sys

# Make the repo root importable so both test suites share utils/contract_loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
