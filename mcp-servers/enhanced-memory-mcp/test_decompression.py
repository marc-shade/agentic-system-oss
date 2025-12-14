#!/usr/bin/env python3
"""
Test script to examine compressed data format in SQLite database
"""
import sqlite3
import zlib
import pickle
import json

DB_PATH = "/Users/marc/.claude/enhanced_memories/memory.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Test entity 184 (one that failed)
print("=" * 70)
print("TESTING ENTITY 184 DATA FORMAT")
print("=" * 70)

cursor.execute("SELECT id, name, compressed_data FROM entities WHERE id=184")
entity = cursor.fetchone()

if entity:
    entity_id, name, compressed_data = entity
    print(f"\nEntity ID: {entity_id}")
    print(f"Entity Name: {name}")
    print(f"Compressed data type: {type(compressed_data)}")
    print(f"Compressed data length: {len(compressed_data) if compressed_data else 0}")

    if compressed_data:
        # Examine first 20 bytes
        print(f"\nFirst 20 bytes (hex): {compressed_data[:20].hex()}")

        # Try zlib decompression
        try:
            decompressed = zlib.decompress(compressed_data)
            print(f"\n✅ Zlib decompression successful!")
            print(f"Decompressed type: {type(decompressed)}")
            print(f"Decompressed length: {len(decompressed)}")
            print(f"\nFirst 200 bytes of decompressed data:")
            print(decompressed[:200])

            # Try different deserialization methods
            print("\n" + "-" * 70)
            print("TESTING DESERIALIZATION METHODS")
            print("-" * 70)

            # Method 1: UTF-8 decode + JSON
            try:
                decoded = decompressed.decode('utf-8')
                print(f"\n1. UTF-8 decode: ✅ Success")
                print(f"   Decoded length: {len(decoded)}")
                try:
                    data = json.loads(decoded)
                    print(f"   JSON parse: ✅ Success")
                    print(f"   Data type: {type(data)}")
                    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    print(f"   Sample: {str(data)[:200]}")
                except json.JSONDecodeError as e:
                    print(f"   JSON parse: ❌ Failed - {e}")
            except UnicodeDecodeError as e:
                print(f"\n1. UTF-8 decode: ❌ Failed - {e}")

            # Method 2: Pickle
            try:
                data = pickle.loads(decompressed)
                print(f"\n2. Pickle loads: ✅ Success")
                print(f"   Data type: {type(data)}")
                print(f"   Sample: {str(data)[:200]}")
            except Exception as e:
                print(f"\n2. Pickle loads: ❌ Failed - {e}")

        except zlib.error as e:
            print(f"\n❌ Zlib decompression failed: {e}")
    else:
        print("\n❌ No compressed data (NULL)")

# Test a few more entities
print("\n" + "=" * 70)
print("TESTING SAMPLE OF OTHER ENTITIES")
print("=" * 70)

cursor.execute("SELECT id, name, compressed_data FROM entities LIMIT 5")
for entity in cursor.fetchall():
    entity_id, name, compressed_data = entity
    status = "NULL" if compressed_data is None else f"{len(compressed_data)} bytes"
    print(f"\nEntity {entity_id} ({name}): {status}")

    if compressed_data:
        try:
            decompressed = zlib.decompress(compressed_data)
            try:
                decoded = decompressed.decode('utf-8')
                data = json.loads(decoded)
                print(f"  ✅ UTF-8 + JSON successful")
            except:
                print(f"  ❌ UTF-8 + JSON failed")
        except:
            print(f"  ❌ Decompression failed")

conn.close()
