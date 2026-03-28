#!/usr/bin/env python3
"""
Test script for skills module imports
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing skills imports...")
print(f"Python path: {sys.path[:3]}")

try:
    from wanclaw.backend.skills import get_skill_manager
    print("Successfully imported get_skill_manager")
    
    skill_manager = get_skill_manager()
    print(f"Skill manager created: {skill_manager}")
    
    # List skills
    skills = skill_manager.list_skills()
    print(f"Available skills: {len(skills)}")
    for skill in skills:
        print(f"  - {skill.get('name')}: {skill.get('description')}")
        
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Other error: {e}")
    import traceback
    traceback.print_exc()