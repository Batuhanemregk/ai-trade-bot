#!/usr/bin/env python3
"""
Configuration Validation Script
Validates policy.yaml against JSON schema and Pydantic models
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from infrastructure.bootstrap import load_policy
from configs.schemas import PolicyConfig, get_validation_errors


def validate_with_pydantic(policy):
    """Validate policy using Pydantic models."""
    print("\n[CHECK] Pydantic Model Validation")
    print("=" * 60)
    
    try:
        # Validate with Pydantic
        PolicyConfig(**policy)
        print("[OK] Pydantic validation passed")
        return True
        
    except Exception as e:
        print("[ERROR] Pydantic validation failed:")
        
        # Get detailed errors
        errors = get_validation_errors(policy)
        for error in errors:
            print(f"  - {error}")
        
        return False


def validate_with_json_schema(policy):
    """Validate policy using JSON schema."""
    print("\n[CHECK] JSON Schema Validation")
    print("=" * 60)
    
    try:
        import jsonschema
        
        # Load schema
        schema_path = Path(__file__).parent.parent / 'configs' / 'schema.json'
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Validate
        jsonschema.validate(policy, schema)
        print("[OK] JSON schema validation passed")
        return True
        
    except ImportError:
        print("[WARNING] jsonschema not installed, skipping")
        print("  Install: pip install jsonschema")
        return True  # Don't fail if jsonschema not available
        
    except jsonschema.ValidationError as e:
        print(f"[ERROR] JSON schema validation failed:")
        print(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        print(f"  Error: {e.message}")
        return False
        
    except Exception as e:
        print(f"[ERROR] JSON schema validation error: {e}")
        return False


def validate_business_rules(policy):
    """Validate business logic rules."""
    print("\n[CHECK] Business Rules Validation")
    print("=" * 60)
    
    errors = []
    
    # Check: Weights sum to 1.0
    try:
        scoring = policy['trading']['scoring']
        total = (scoring['ta_weight'] + scoring['ml_weight'] + 
                scoring['news_weight'] + scoring['risk_weight'])
        
        if abs(total - 1.0) > 0.01:
            errors.append(f"Scoring weights sum to {total:.3f}, must be 1.0 (±0.01)")
        else:
            print(f"  [OK] Weights sum: {total:.3f}")
    except KeyError as e:
        errors.append(f"Missing scoring weight: {e}")
    
    # Check: TP > SL
    try:
        risk = policy['trading']['risk']
        if risk['take_profit_pct'] <= risk['stop_loss_pct']:
            errors.append(
                f"TP ({risk['take_profit_pct']:.1%}) must be > SL ({risk['stop_loss_pct']:.1%})"
            )
        else:
            print(f"  [OK] TP ({risk['take_profit_pct']:.1%}) > SL ({risk['stop_loss_pct']:.1%})")
    except KeyError as e:
        errors.append(f"Missing risk config: {e}")
    
    # Check: Reasonable position size
    try:
        max_pos = policy['trading']['risk']['max_position_size']
        if max_pos > 0.3:
            errors.append(
                f"max_position_size too high ({max_pos:.1%}). "
                "Recommended: ≤20% for safety"
            )
        else:
            print(f"  [OK] Max position size: {max_pos:.1%}")
    except KeyError as e:
        errors.append(f"Missing max_position_size: {e}")
    
    # Check: Mode safety
    try:
        mode = policy['exchange']['mode']
        testnet = policy['exchange'].get('testnet', False)
        
        if mode == 'live' and not testnet:
            print(f"  [WARNING] Mode is LIVE (real trading enabled!)")
        else:
            print(f"  [OK] Mode: {mode}, Testnet: {testnet}")
    except KeyError as e:
        errors.append(f"Missing exchange config: {e}")
    
    # Check: Required environment variables reference
    try:
        token = policy['telegram'].get('token', '')
        if token and token.startswith('${') and token.endswith('}'):
            print(f"  [OK] Telegram token references environment variable")
        elif policy['telegram'].get('enabled', False) and not token:
            errors.append("Telegram enabled but token not configured")
    except:
        pass
    
    if errors:
        print(f"\n[ERROR] Business rule violations:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n[OK] All business rules passed")
        return True


def check_required_files():
    """Check if required files exist."""
    print("\n[CHECK] Required Files")
    print("=" * 60)
    
    required_files = [
        'configs/policy.yaml',
        'configs/schema.json',
        'configs/schemas.py',
        '.env'
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [ERROR] {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def main():
    """Run all configuration validations."""
    print("\n" + "=" * 60)
    print("CONFIGURATION VALIDATION")
    print("=" * 60)
    
    # Check files
    if not check_required_files():
        print("\n[ERROR] Required files missing")
        return 1
    
    # Load policy
    print("\n[CHECK] Loading Policy")
    print("=" * 60)
    
    try:
        policy = load_policy()
        print("[OK] Policy loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load policy: {e}")
        return 1
    
    # Run validations
    validations = [
        ("Pydantic Model", lambda: validate_with_pydantic(policy)),
        ("JSON Schema", lambda: validate_with_json_schema(policy)),
        ("Business Rules", lambda: validate_business_rules(policy)),
    ]
    
    results = []
    for name, validator in validations:
        result = validator()
        results.append((name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} validations passed")
    
    if passed == total:
        print("\n[SUCCESS] Configuration is valid!")
        print("\nYou can now safely run:")
        print("  python -m infrastructure.scheduler_runner")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} validation(s) failed")
        print("\nPlease fix the issues in configs/policy.yaml")
        return 1


if __name__ == "__main__":
    sys.exit(main())

