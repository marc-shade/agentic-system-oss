-- Migration: Add always_include flag for user profile pattern (Zep-inspired)
-- Date: 2025-11-12
-- Purpose: Enable "always-include" facts that appear in every search result

-- Add always_include column to entities table
ALTER TABLE entities ADD COLUMN always_include BOOLEAN DEFAULT 0;

-- Create index for fast filtering
CREATE INDEX IF NOT EXISTS idx_entities_always_include ON entities(always_include);

-- Add comments for documentation
-- always_include = 1: Entity is automatically included in every search result
-- always_include = 0: Entity is retrieved only when semantically relevant

-- Example usage:
-- User profile facts: always_include = 1 (budget, preferences, requirements)
-- Historical data: always_include = 0 (normal semantic retrieval)
