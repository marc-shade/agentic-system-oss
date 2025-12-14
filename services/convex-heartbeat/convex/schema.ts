import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Node status - reactive subscriptions for cluster coordination
  nodes: defineTable({
    nodeId: v.string(),           // e.g., "orchestrator", "builder", "researcher"
    hostname: v.string(),         // e.g., "mac-studio", "macpro51"
    status: v.union(v.literal("online"), v.literal("offline"), v.literal("busy")),
    lastHeartbeat: v.number(),    // Unix timestamp
    cpuUsage: v.optional(v.number()),
    memoryUsage: v.optional(v.number()),
    activeTask: v.optional(v.string()),
    capabilities: v.array(v.string()),
    version: v.optional(v.string()),
  })
    .index("by_nodeId", ["nodeId"])
    .index("by_status", ["status"]),

  // Task queue - ACID transactions for coordination
  tasks: defineTable({
    title: v.string(),
    description: v.optional(v.string()),
    status: v.union(
      v.literal("pending"),
      v.literal("assigned"),
      v.literal("running"),
      v.literal("completed"),
      v.literal("failed")
    ),
    priority: v.number(),         // 1-10, higher = more urgent
    assignedTo: v.optional(v.string()),  // nodeId
    createdBy: v.string(),        // nodeId that created the task
    createdAt: v.number(),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
    result: v.optional(v.string()),
    error: v.optional(v.string()),
  })
    .index("by_status", ["status"])
    .index("by_assignedTo", ["assignedTo"])
    .index("by_priority", ["priority"]),

  // Inter-node messages - reactive chat
  messages: defineTable({
    fromNode: v.string(),
    toNode: v.optional(v.string()),  // null = broadcast
    content: v.string(),
    messageType: v.union(
      v.literal("chat"),
      v.literal("command"),
      v.literal("status"),
      v.literal("alert")
    ),
    timestamp: v.number(),
    read: v.boolean(),
  })
    .index("by_toNode", ["toNode"])
    .index("by_timestamp", ["timestamp"]),
});
