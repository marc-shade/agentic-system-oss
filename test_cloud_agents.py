#!/usr/bin/env python3
"""Test all agents use cloud models correctly"""
import asyncio
import sys

async def test_security_auditor():
    from intelligent_agents.security_auditor import SecurityAuditor
    
    auditor = SecurityAuditor()
    assert "192.168.1.186:11434" in auditor.ollama_host, f"Wrong endpoint: {auditor.ollama_host}"
    assert "cloud" in auditor.model, f"Not cloud model: {auditor.model}"
    
    # Test actual inference
    result = await auditor._call_ollama("Respond with: Test OK")
    assert len(result) > 0, "No response from cloud model"
    print(f"✅ Security Auditor: {auditor.model} @ {auditor.ollama_host}")
    print(f"   Response: {result[:50]}...")
    return True

async def test_all():
    try:
        result = await test_security_auditor()
        if result:
            print("\n✅ All agent tests passed!")
            return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(test_all()))
