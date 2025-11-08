"""
Guardian Validation Script

This script validates the Guardian system components without actually starting services.
It checks:
1. Guardian can import correctly
2. Configuration is valid
3. Port checking works
4. Service definitions are correct
"""

import sys
from pathlib import Path

# Add the Guardian module to path
guardian_path = Path(__file__).parent / "backend" / "services"
sys.path.insert(0, str(guardian_path))

def validate_imports():
    """Test that Guardian module imports correctly"""
    print("=" * 60)
    print("1. Testing Guardian Imports")
    print("=" * 60)
    
    try:
        from system_guardian import guardian
        print("✓ Guardian module imported successfully")
        
        # Check key components exist
        assert hasattr(guardian, 'ServiceManager'), "ServiceManager not found"
        print("✓ ServiceManager class found")
        
        assert hasattr(guardian, 'HealthMonitor'), "HealthMonitor not found"
        print("✓ HealthMonitor class found")
        
        assert hasattr(guardian, 'STARTUP_ORDER'), "STARTUP_ORDER not found"
        print("✓ STARTUP_ORDER configuration found")
        
        return guardian
    except ImportError as e:
        print(f"✗ Failed to import Guardian: {e}")
        return None
    except AssertionError as e:
        print(f"✗ Missing component: {e}")
        return None

def validate_configuration(guardian):
    """Validate the service configuration"""
    print("\n" + "=" * 60)
    print("2. Validating Service Configuration")
    print("=" * 60)
    
    try:
        startup_order = guardian.STARTUP_ORDER
        print(f"✓ Found {len(startup_order)} services configured")
        
        required_fields = ['name', 'port', 'path', 'health_endpoint']
        ports = set()
        
        for idx, service in enumerate(startup_order, 1):
            # Check required fields
            for field in required_fields:
                assert field in service, f"Service {idx} missing '{field}'"
            
            # Check port uniqueness
            port = service['port']
            assert port not in ports, f"Duplicate port {port}"
            ports.add(port)
            
            print(f"  {idx}. {service['name']:<25} Port: {port:<5} ✓")
        
        print(f"\n✓ All {len(startup_order)} service configurations are valid")
        return True
        
    except AssertionError as e:
        print(f"✗ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def validate_service_files(guardian):
    """Check that service files exist"""
    print("\n" + "=" * 60)
    print("3. Validating Service Files")
    print("=" * 60)
    
    root_path = Path(__file__).parent
    all_exist = True
    
    for service in guardian.STARTUP_ORDER:
        service_path = root_path / service['path']
        exists = service_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {service['name']}: {service_path}")
        
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n✓ All service files exist")
    else:
        print("\n✗ Some service files are missing")
    
    return all_exist

def validate_port_checking():
    """Test port checking functionality"""
    print("\n" + "=" * 60)
    print("4. Testing Port Checking")
    print("=" * 60)
    
    try:
        import psutil
        print("✓ psutil module available")
        
        # Test port checking (without Guardian instance)
        test_ports = [8001, 8002, 8003, 8004, 8005, 8006, 9000]
        
        for port in test_ports:
            in_use = any(
                conn.laddr.port == port and conn.status == 'LISTEN'
                for conn in psutil.net_connections()
            )
            status = "IN USE" if in_use else "AVAILABLE"
            print(f"  Port {port}: {status}")
        
        print("\n✓ Port checking functionality works")
        return True
        
    except ImportError:
        print("✗ psutil not available (required for port checking)")
        return False
    except Exception as e:
        print(f"✗ Port checking error: {e}")
        return False

def validate_dependencies():
    """Check that required dependencies are importable"""
    print("\n" + "=" * 60)
    print("5. Checking Dependencies")
    print("=" * 60)
    
    dependencies = {
        'asyncio': 'Async support',
        'logging': 'Logging',
        'psutil': 'Process/port monitoring',
        'aiohttp': 'HTTP client for health checks',
        'fastapi': 'Service framework',
        'uvicorn': 'ASGI server',
    }
    
    all_available = True
    for module_name, description in dependencies.items():
        try:
            __import__(module_name)
            print(f"  ✓ {module_name:<15} ({description})")
        except ImportError:
            print(f"  ✗ {module_name:<15} ({description}) - NOT INSTALLED")
            all_available = False
    
    if all_available:
        print("\n✓ All required dependencies are available")
    else:
        print("\n✗ Some dependencies are missing")
        print("  Run: pip install -r requirements.txt")
    
    return all_available

def main():
    """Run all validations"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Guardian System Validation" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # 1. Test imports
    guardian = validate_imports()
    results.append(guardian is not None)
    
    if guardian:
        # 2. Validate configuration
        results.append(validate_configuration(guardian))
        
        # 3. Validate service files
        results.append(validate_service_files(guardian))
    else:
        results.extend([False, False])
    
    # 4. Test port checking
    results.append(validate_port_checking())
    
    # 5. Check dependencies
    results.append(validate_dependencies())
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All validations passed! Guardian system is ready.")
        print("\nTo start the Guardian:")
        print("  .\\start_guardian.ps1")
        return 0
    else:
        print("\n✗ Some validations failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
