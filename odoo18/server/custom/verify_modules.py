#!/usr/bin/env python
"""
Coconut Factory ERP - Module Verification Script
Run this to verify all modules are properly structured before installation.
"""

import os
import sys

BASE_DIR = r'C:\odoo\odoo18\server\custom'

MODULES = [
    'coconut_base',
    'coconut_supplier',
    'coconut_purchase',
    'coconut_inventory',
    'coconut_production',
    'coconut_notification',
    'coconut_dashboard',
]

REQUIRED_FILES = [
    '__manifest__.py',
    '__init__.py',
    'models/__init__.py',
    'security/ir.model.access.csv',
]

def check_module(module_name):
    """Check if module has all required files"""
    module_path = os.path.join(BASE_DIR, module_name)
    
    if not os.path.exists(module_path):
        print(f"[FAIL] {module_name}: Directory missing")
        return False
    
    all_good = True
    
    for req_file in REQUIRED_FILES:
        file_path = os.path.join(module_path, req_file)
        if os.path.exists(file_path):
            print(f"  [OK] {module_name}/{req_file}")
        else:
            print(f"  [MISSING] {module_name}/{req_file}")
            all_good = False
    
    # Check manifest can be parsed
    manifest_path = os.path.join(module_path, '__manifest__.py')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'name' in content and 'depends' in content:
                print(f"  [OK] {module_name}/__manifest__.py valid structure")
            else:
                print(f"  [ERROR] {module_name}/__manifest__.py missing required fields")
                all_good = False
    except Exception as e:
        print(f"  [ERROR] Error reading manifest: {e}")
        all_good = False
    
    return all_good

def main():
    print("=" * 60)
    print("Coconut Factory ERP - Module Verification")
    print("=" * 60)
    
    all_ok = True
    
    for module in MODULES:
        print(f"\nChecking {module}:")
        if check_module(module):
            print(f"[OK] {module} looks good")
        else:
            print(f"[FAIL] {module} has issues")
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("[OK] All modules verified successfully!")
        print("\nNext steps:")
        print("1. Verify odoo.conf has custom addons path")
        print("2. Restart Odoo service")
        print("3. Update Apps list in Odoo UI")
        print("4. Install modules in order:")
        for i, m in enumerate(MODULES, 1):
            print(f"   {i}. {m}")
    else:
        print("[FAIL] Some modules have missing files - check above")
        sys.exit(1)

if __name__ == '__main__':
    main()
