---
name: frontend-tab-generator
description: Generates self-registering tab components.
---

# Frontend Tab Generator Skill

## Four Tabs
- Core (core, order 1)
- GNN (gnn, order 2)
- World Model (world_model, order 3)
- Causal Matrix (causal_matrix, order 4)

## Self-Registration Pattern
export function register(registry) {
    const component = new TabName();
    registry.registerTab({id, label, order, component});
    return component;
}
