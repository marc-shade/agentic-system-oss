import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// Query: Get all nodes (reactive - auto-updates when any node changes)
export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("nodes").collect();
  },
});

// Query: Get online nodes only
export const listOnline = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("nodes")
      .withIndex("by_status", (q) => q.eq("status", "online"))
      .collect();
  },
});

// Query: Get specific node by ID
export const get = query({
  args: { nodeId: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("nodes")
      .withIndex("by_nodeId", (q) => q.eq("nodeId", args.nodeId))
      .first();
  },
});

// Query: Get cluster health summary
export const clusterHealth = query({
  args: {},
  handler: async (ctx) => {
    const nodes = await ctx.db.query("nodes").collect();
    const now = Date.now();
    const staleThreshold = 30000; // 30 seconds

    const online = nodes.filter(n => n.status === "online" && (now - n.lastHeartbeat) < staleThreshold);
    const offline = nodes.filter(n => n.status === "offline" || (now - n.lastHeartbeat) >= staleThreshold);
    const busy = nodes.filter(n => n.status === "busy");

    return {
      totalNodes: nodes.length,
      onlineCount: online.length,
      offlineCount: offline.length,
      busyCount: busy.length,
      avgCpuUsage: online.reduce((sum, n) => sum + (n.cpuUsage || 0), 0) / Math.max(online.length, 1),
      avgMemoryUsage: online.reduce((sum, n) => sum + (n.memoryUsage || 0), 0) / Math.max(online.length, 1),
      lastUpdated: now,
    };
  },
});

// Mutation: Register or update node heartbeat
export const heartbeat = mutation({
  args: {
    nodeId: v.string(),
    hostname: v.string(),
    status: v.union(v.literal("online"), v.literal("offline"), v.literal("busy")),
    cpuUsage: v.optional(v.number()),
    memoryUsage: v.optional(v.number()),
    activeTask: v.optional(v.string()),
    capabilities: v.array(v.string()),
    version: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("nodes")
      .withIndex("by_nodeId", (q) => q.eq("nodeId", args.nodeId))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, {
        ...args,
        lastHeartbeat: Date.now(),
      });
      return { action: "updated", nodeId: args.nodeId };
    } else {
      await ctx.db.insert("nodes", {
        ...args,
        lastHeartbeat: Date.now(),
      });
      return { action: "registered", nodeId: args.nodeId };
    }
  },
});

// Mutation: Mark node as offline
export const markOffline = mutation({
  args: { nodeId: v.string() },
  handler: async (ctx, args) => {
    const node = await ctx.db
      .query("nodes")
      .withIndex("by_nodeId", (q) => q.eq("nodeId", args.nodeId))
      .first();

    if (node) {
      await ctx.db.patch(node._id, {
        status: "offline",
        lastHeartbeat: Date.now(),
        activeTask: undefined,
      });
      return { success: true };
    }
    return { success: false, error: "Node not found" };
  },
});

// Mutation: Set node status to busy with task
export const setBusy = mutation({
  args: {
    nodeId: v.string(),
    activeTask: v.string(),
  },
  handler: async (ctx, args) => {
    const node = await ctx.db
      .query("nodes")
      .withIndex("by_nodeId", (q) => q.eq("nodeId", args.nodeId))
      .first();

    if (node) {
      await ctx.db.patch(node._id, {
        status: "busy",
        activeTask: args.activeTask,
        lastHeartbeat: Date.now(),
      });
      return { success: true };
    }
    return { success: false, error: "Node not found" };
  },
});

// Mutation: Delete a node from the cluster
export const deleteNode = mutation({
  args: { nodeId: v.string() },
  handler: async (ctx, args) => {
    const node = await ctx.db
      .query("nodes")
      .withIndex("by_nodeId", (q) => q.eq("nodeId", args.nodeId))
      .first();

    if (node) {
      await ctx.db.delete(node._id);
      return { success: true, deleted: args.nodeId };
    }
    return { success: false, error: "Node not found" };
  },
});
