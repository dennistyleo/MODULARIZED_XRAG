# Frontend Component Rules

## No Hardcoded IDs
- Components must self-register

## Self-Registration Pattern
- registry.registerTab({id, label, order, component})

## Tab Lifecycle
- bind(element)
- onActivate()
- onDeactivate()
- onData(data)
