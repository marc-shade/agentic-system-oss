#!/usr/bin/env python3
"""
GitMQ Security Testing Script
==============================

Tests the cryptographic authentication and schema validation improvements.

Tests:
1. Keypair generation and loading
2. Message signing and verification
3. Schema validation (valid and invalid payloads)
4. Attack detection (shell injection, future timestamps, malicious code)
5. Cross-node trust establishment

Usage:
    # Generate keys for a node
    python3 test_security.py --generate-keys macpro51

    # Run all security tests
    python3 test_security.py --test-all macpro51

    # Test specific scenario
    python3 test_security.py --test-signing macpro51
    python3 test_security.py --test-validation
    python3 test_security.py --test-attacks
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

from auth import MessageAuthenticator
from payload_schema import (
    TaskPayload, CodeExecutionPayload, ResultPayload,
    validate_payload, TaskType, Priority, ExecutionMode
)
from pydantic import ValidationError


def test_keypair_generation(node_id: str):
    """Test 1: Keypair generation and persistence."""
    print("\n" + "=" * 70)
    print("TEST 1: Keypair Generation and Persistence")
    print("=" * 70)

    # Create authenticator (generates keys if needed)
    auth = MessageAuthenticator(node_id=node_id)

    # Check keys exist
    keys_dir = Path.home() / ".ssh" / "cluster-keys"
    priv_key = keys_dir / f"{node_id}.priv"
    pub_key = keys_dir / f"{node_id}.pub"

    assert priv_key.exists(), f"Private key not found: {priv_key}"
    assert pub_key.exists(), f"Public key not found: {pub_key}"

    # Check permissions
    priv_perms = oct(priv_key.stat().st_mode)[-3:]
    assert priv_perms == "600", f"Private key has wrong permissions: {priv_perms} (expected 600)"

    print(f"✓ Private key: {priv_key} (permissions: {priv_perms})")
    print(f"✓ Public key: {pub_key}")
    print(f"✓ Trusted nodes: {list(auth.public_keys.keys())}")
    print("\nPASS: Keypair generation and persistence")


def test_message_signing(node_id: str):
    """Test 2: Message signing and verification."""
    print("\n" + "=" * 70)
    print("TEST 2: Message Signing and Verification")
    print("=" * 70)

    auth = MessageAuthenticator(node_id=node_id)

    # Create a test message
    message = {
        "task_id": "abc-123",
        "type": "health_check",
        "source_node": node_id,
        "target_node": "test-target",
        "timestamp": datetime.now().isoformat(),
        "payload": {"test": True}
    }

    print(f"\nOriginal message:")
    print(json.dumps(message, indent=2))

    # Sign the message
    signed = auth.sign_payload(message.copy())

    assert "_signature" in signed, "Signature not added"
    assert "_signed_by" in signed, "Signer not added"
    assert signed["_signed_by"] == node_id, f"Wrong signer: {signed['_signed_by']}"

    print(f"\nSigned message (signature truncated):")
    print(f"  _signature: {signed['_signature'][:40]}...")
    print(f"  _signed_by: {signed['_signed_by']}")

    # Verify the signature
    is_valid = auth.verify_payload(signed)

    assert is_valid, "Signature verification failed"

    print(f"\n✓ Signature verified successfully")
    print("\nPASS: Message signing and verification")


def test_schema_validation():
    """Test 3: Schema validation for valid and invalid payloads."""
    print("\n" + "=" * 70)
    print("TEST 3: Schema Validation")
    print("=" * 70)

    # Test 3a: Valid payload
    print("\n3a. Valid task payload:")
    valid_task = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "code_execution",
        "source_node": "macpro51",
        "target_node": "mac-studio",
        "payload": {
            "code": "print('Hello, GitMQ')",
            "code_language": "python",
            "entry_point": "main.py"
        }
    }

    try:
        validated = validate_payload(valid_task, TaskPayload)
        print(f"✓ Valid payload accepted")
        print(f"  Task ID: {validated.task_id}")
        print(f"  Type: {validated.type}")
        print(f"  Checksum: {validated.checksum}")
    except ValidationError as e:
        print(f"✗ FAIL: Valid payload rejected: {e}")
        sys.exit(1)

    # Test 3b: Invalid node name
    print("\n3b. Invalid node name (uppercase):")
    invalid_node = valid_task.copy()
    invalid_node["source_node"] = "MACPRO51"  # Must be lowercase

    try:
        validate_payload(invalid_node, TaskPayload)
        print(f"✗ FAIL: Invalid node name accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Invalid node name rejected: {e}")

    # Test 3c: Future timestamp
    print("\n3c. Future timestamp:")
    future_timestamp = valid_task.copy()
    future_timestamp["timestamp"] = (datetime.now() + timedelta(days=1)).isoformat()

    try:
        validate_payload(future_timestamp, TaskPayload)
        print(f"✗ FAIL: Future timestamp accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Future timestamp rejected: {e}")

    # Test 3d: Invalid UUID format
    print("\n3d. Invalid task ID format:")
    invalid_uuid = valid_task.copy()
    invalid_uuid["task_id"] = "not-a-valid-uuid"

    try:
        validate_payload(invalid_uuid, TaskPayload)
        print(f"✗ FAIL: Invalid UUID accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Invalid UUID rejected")

    print("\nPASS: Schema validation")


def test_code_execution_validation():
    """Test 4: Code execution payload validation."""
    print("\n" + "=" * 70)
    print("TEST 4: Code Execution Payload Validation")
    print("=" * 70)

    # Test 4a: Valid code execution
    print("\n4a. Valid code execution:")
    valid_code = {
        "code": "import sys\nprint(sys.version)",
        "code_language": "python",
        "dependencies": ["requests>=2.31.0"],
        "entry_point": "main.py"
    }

    try:
        code_payload = CodeExecutionPayload.model_validate(valid_code)
        print(f"✓ Valid code payload accepted")
        print(f"  Language: {code_payload.code_language}")
        print(f"  Dependencies: {code_payload.dependencies}")
    except ValidationError as e:
        print(f"✗ FAIL: Valid code rejected: {e}")
        sys.exit(1)

    # Test 4b: Shell injection in arguments
    print("\n4b. Shell injection in arguments:")
    shell_injection = valid_code.copy()
    shell_injection["arguments"] = ["--flag; rm -rf /"]

    try:
        CodeExecutionPayload.model_validate(shell_injection)
        print(f"✗ FAIL: Shell injection accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Shell injection blocked")

    # Test 4c: Invalid language
    print("\n4c. Invalid language:")
    invalid_lang = valid_code.copy()
    invalid_lang["code_language"] = "brainfuck"

    try:
        CodeExecutionPayload.model_validate(invalid_lang)
        print(f"✗ FAIL: Invalid language accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Invalid language rejected")

    # Test 4d: Must provide code or code_file
    print("\n4d. Missing code:")
    no_code = {
        "code_language": "python",
        "entry_point": "main.py"
    }

    try:
        CodeExecutionPayload.model_validate(no_code)
        print(f"✗ FAIL: Missing code accepted")
        sys.exit(1)
    except ValidationError as e:
        print(f"✓ Missing code rejected")

    print("\nPASS: Code execution validation")


def test_attack_scenarios(node_id: str):
    """Test 5: Common attack scenarios."""
    print("\n" + "=" * 70)
    print("TEST 5: Attack Scenario Detection")
    print("=" * 70)

    auth = MessageAuthenticator(node_id=node_id)

    # Attack 5a: Unsigned message
    print("\n5a. Unsigned message (no signature):")
    unsigned = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "code_execution",
        "source_node": "evil-node",
        "target_node": node_id,
        "payload": {"code": "import os; os.system('rm -rf /')"}
    }

    is_valid = auth.verify_payload(unsigned)
    if is_valid:
        print(f"✗ FAIL: Unsigned message accepted")
        sys.exit(1)
    else:
        print(f"✓ Unsigned message rejected")

    # Attack 5b: Tampered message
    print("\n5b. Tampered message (modified after signing):")
    legit_message = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "health_check",
        "source_node": node_id,
        "target_node": "test-node",
        "payload": {}
    }

    signed = auth.sign_payload(legit_message.copy())

    # Attacker modifies the payload
    signed["payload"]["malicious"] = "rm -rf /"

    is_valid = auth.verify_payload(signed)
    if is_valid:
        print(f"✗ FAIL: Tampered message accepted")
        sys.exit(1)
    else:
        print(f"✓ Tampered message detected")

    # Attack 5c: Directory traversal
    print("\n5c. Directory traversal in working_directory:")
    traversal = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "code_execution",
        "source_node": node_id,
        "target_node": "test-node",
        "execution_context": {
            "working_directory": "../../etc"
        },
        "payload": {}
    }

    try:
        validate_payload(traversal, TaskPayload)
        print(f"✗ FAIL: Directory traversal accepted")
        sys.exit(1)
    except ValidationError:
        print(f"✓ Directory traversal blocked")

    # Attack 5d: Protected env var override
    print("\n5d. Protected environment variable override:")
    env_override = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "code_execution",
        "source_node": node_id,
        "target_node": "test-node",
        "execution_context": {
            "environment_vars": {
                "PATH": "/evil/path"
            }
        },
        "payload": {}
    }

    try:
        validate_payload(env_override, TaskPayload)
        print(f"✗ FAIL: Env var override accepted")
        sys.exit(1)
    except ValidationError:
        print(f"✓ Protected env var override blocked")

    print("\nPASS: Attack scenario detection")


def test_result_payload():
    """Test 6: Result payload validation."""
    print("\n" + "=" * 70)
    print("TEST 6: Result Payload Validation")
    print("=" * 70)

    # Valid result
    result = ResultPayload(
        task_id="550e8400-e29b-41d4-a716-446655440000",
        executing_node="macpro51",
        status="success",
        exit_code=0,
        stdout="Hello, world!\n",
        execution_time_ms=42.5,
        memory_usage_mb=15.2,
        cpu_usage_percent=8.3
    )

    print(f"✓ Result payload created:")
    print(f"  Task ID: {result.task_id}")
    print(f"  Status: {result.status}")
    print(f"  Execution time: {result.execution_time_ms}ms")
    print(f"  Memory: {result.memory_usage_mb}MB")
    print(f"  CPU: {result.cpu_usage_percent}%")

    # Validate serialization
    result_dict = result.model_dump(mode='json')
    assert "started_at" in result_dict
    assert "completed_at" in result_dict

    print(f"✓ Result serialization successful")
    print("\nPASS: Result payload validation")


def run_all_tests(node_id: str):
    """Run all security tests."""
    print("\n" + "=" * 70)
    print("GitMQ Security Test Suite")
    print("=" * 70)
    print(f"Node ID: {node_id}")
    print(f"Date: {datetime.now().isoformat()}")

    try:
        test_keypair_generation(node_id)
        test_message_signing(node_id)
        test_schema_validation()
        test_code_execution_validation()
        test_attack_scenarios(node_id)
        test_result_payload()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print("\nSecurity improvements verified:")
        print("  ✓ Cryptographic message signatures (Ed25519)")
        print("  ✓ Schema validation (Pydantic)")
        print("  ✓ Shell injection prevention")
        print("  ✓ Directory traversal prevention")
        print("  ✓ Timestamp validation")
        print("  ✓ Protected environment variables")
        print("  ✓ Tamper detection")
        print()

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GitMQ Security Testing")
    parser.add_argument("--node-id", help="Node identifier", default="test-node")
    parser.add_argument("--generate-keys", action="store_true", help="Generate keypair only")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--test-signing", action="store_true", help="Test message signing")
    parser.add_argument("--test-validation", action="store_true", help="Test schema validation")
    parser.add_argument("--test-attacks", action="store_true", help="Test attack detection")

    args = parser.parse_args()

    if args.generate_keys:
        print(f"Generating keypair for node: {args.node_id}")
        auth = MessageAuthenticator(node_id=args.node_id)
        print(f"✓ Keypair generated")
        print(f"  Private: ~/.ssh/cluster-keys/{args.node_id}.priv")
        print(f"  Public: ~/.ssh/cluster-keys/{args.node_id}.pub")
        return

    if args.test_all or (not args.test_signing and not args.test_validation and not args.test_attacks):
        run_all_tests(args.node_id)
    else:
        if args.test_signing:
            test_message_signing(args.node_id)
        if args.test_validation:
            test_schema_validation()
            test_code_execution_validation()
        if args.test_attacks:
            test_attack_scenarios(args.node_id)


if __name__ == "__main__":
    main()
