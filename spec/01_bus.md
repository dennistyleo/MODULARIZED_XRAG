# Sovereign BUS Specification

Message Format:
{
    "message_id": "MSG_XXXX",
    "timestamp": "ISO8601",
    "sender": "module_name",
    "recipient": "module_name or broadcast",
    "message_type": "EVENT_TYPE",
    "payload": {},
    "trace_id": "string",
    "reply_to": "MSG_XXXX"
}

Required Events:
- DATA_EXTRACTED (rag_module)
- ONTOLOGY_CLASSIFIED (stage_1)
- HYPOTHESIS_GENERATED (stage_2)
- PATHWAY_FILTERED (stage_3)
- RISK_ASSESSED (stage_4)
- REPORT_READY (stage_5)
- DRIFT_DETECTED (gnn_module)
- SHAPE_COMPARED (world_model)
- CAUSAL_MATRIX_READY (causal_matrix)
- HITL_REQUEST (any)
- HITL_RESPONSE (ui)
- ERROR (any)

Routing Rules:
- Direct: Send to specific module
- Broadcast: Send to all modules
- Reply: Send to message.sender
## Message ID Format
- Format: `MSG_{timestamp}_{random_4}`
- Example: `MSG_20260411_083000_A3F2`

## Event Priority
| Priority | Events |
|----------|--------|
| HIGH | DATA_EXTRACTED, HITL_REQUEST, HITL_RESPONSE, ERROR |
| MEDIUM | DRIFT_DETECTED, CAUSAL_MATRIX_READY, REPORT_READY |
| LOW | ONTOLOGY_CLASSIFIED, HYPOTHESIS_GENERATED, PATHWAY_FILTERED, RISK_ASSESSED, SHAPE_COMPARED |

## Timeout Handling
- Default timeout: 30 seconds
- On timeout: Return error E005 to sender
- Sender must implement retry logic per error code

## Error Handling
- Bus routing failure: Return E009 to sender
- Recipient not found: Log error, no delivery
- Malformed message: Reject with validation error

## Message Size Limit
- Maximum payload size: 10 MB
- Larger payloads must use chunking or reference storage