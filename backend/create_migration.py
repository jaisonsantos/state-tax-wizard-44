#!/usr/bin/env python3
"""
Script to create initial migration
"""
import subprocess
import sys

def main():
    try:
        # Create initial migration
        result = subprocess.run([
            sys.executable, "-m", "alembic", "revision", "--autogenerate", 
            "-m", "Initial migration"
        ], cwd="backend", capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error creating migration: {result.stderr}")
            return 1
            
        print("Migration created successfully!")
        print(result.stdout)
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())