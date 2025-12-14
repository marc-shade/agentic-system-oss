import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// Query: List all pending tasks (reactive)
export const listPending = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("tasks")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .collect();
  },
});

// Query: List tasks for a specific node
export const listForNode = query({
  args: { nodeId: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("tasks")
      .withIndex("by_assignedTo", (q) => q.eq("assignedTo", args.nodeId))
      .collect();
  },
});

// Query: Get next task (highest priority pending)
export const getNext = query({
  args: {},
  handler: async (ctx) => {
    const pending = await ctx.db
      .query("tasks")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .collect();

    if (pending.length === 0) return null;

    // Sort by priority (descending)
    return pending.sort((a, b) => b.priority - a.priority)[0];
  },
});

// Mutation: Create a new task
export const create = mutation({
  args: {
    title: v.string(),
    description: v.optional(v.string()),
    priority: v.number(),
    createdBy: v.string(),
  },
  handler: async (ctx, args) => {
    const taskId = await ctx.db.insert("tasks", {
      title: args.title,
      description: args.description,
      status: "pending",
      priority: args.priority,
      createdBy: args.createdBy,
      createdAt: Date.now(),
    });
    return { taskId };
  },
});

// Mutation: Claim a task (atomic assignment)
export const claim = mutation({
  args: {
    taskId: v.id("tasks"),
    nodeId: v.string(),
  },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);

    if (!task) {
      return { success: false, error: "Task not found" };
    }

    if (task.status !== "pending") {
      return { success: false, error: `Task already ${task.status}` };
    }

    // Atomically claim the task (OCC handles conflicts)
    await ctx.db.patch(args.taskId, {
      status: "assigned",
      assignedTo: args.nodeId,
    });

    return { success: true, task };
  },
});

// Mutation: Start working on a task
export const start = mutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);

    if (!task || task.status !== "assigned") {
      return { success: false, error: "Task not assigned" };
    }

    await ctx.db.patch(args.taskId, {
      status: "running",
      startedAt: Date.now(),
    });

    return { success: true };
  },
});

// Mutation: Complete a task
export const complete = mutation({
  args: {
    taskId: v.id("tasks"),
    result: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.taskId, {
      status: "completed",
      completedAt: Date.now(),
      result: args.result,
    });
    return { success: true };
  },
});

// Mutation: Fail a task
export const fail = mutation({
  args: {
    taskId: v.id("tasks"),
    error: v.string(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.taskId, {
      status: "failed",
      completedAt: Date.now(),
      error: args.error,
    });
    return { success: true };
  },
});
