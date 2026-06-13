tools/
├── __init__.py       — exports: TOOL_REGISTRY, tool, register_tool, get_tool_schema
├── models.py         — ToolDef, ToolResult, ToolContext, ToolCall
├── executor.py       — ToolDispatcher (async execution, result formatting)
└── registry.py       — @tool decorator, JSON schema builder, enum enrichment
└── sigma/
    ├── __init__.py   — auto-register all tools
    └── tools.py      — search_sigma, explain, filter, filter_metadata, coverage_analysis, summarize
