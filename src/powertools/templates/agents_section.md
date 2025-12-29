## Powertools

This project uses [powertools](https://github.com/fincognition/powertools) for memory and task tracking.

### Setup

```bash
# Start services
docker compose -f .powertools/compose.yaml up -d

# Or with podman
podman-compose -f .powertools/compose.yaml up -d
```

### MCP Server

Connect your agent to the powertools MCP server:

- URL: `http://localhost:8765/sse`

### Available Tools

- `add_memory`, `search_memory`, `list_memories`, `delete_memory`
- `create_task`, `get_ready_tasks`, `get_task`, `update_task`, `add_dependency`, `list_tasks`
