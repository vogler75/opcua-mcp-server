# OPC UA MCP Server

A Python application that connects to an OPC UA server and exposes it via MCP (Model Context Protocol) using FastMCP.

## Features

- Connect to any OPC UA server with optional authentication
- Browse the complete node tree from a configurable starting node
- Expose the OPC UA node tree as MCP resources
- Read values from OPC UA nodes
- Search nodes by display name or browse name with wildcard support
- Support for both stdio and SSE (Server-Sent Events) transport methods

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic usage with HTTP transport (default):

```bash
python opcua_mcp_server.py opc.tcp://localhost:4840
```

### With authentication:

```bash
python opcua_mcp_server.py opc.tcp://localhost:4840 --username myuser --password mypass
```

### Using stdio transport:

```bash
python opcua_mcp_server.py opc.tcp://localhost:4840 --transport stdio
```

### With custom starting node and HTTP port:

```bash
python opcua_mcp_server.py opc.tcp://localhost:4840 --start-node "i=84" --http-port 8080
```

## Command Line Arguments

- `opcua_url` (required): OPC UA server URL (e.g., opc.tcp://localhost:4840)
- `--start-node`: Starting node ID for browsing (default: i=85)
- `--username`: Username for OPC UA authentication
- `--password`: Password for OPC UA authentication
- `--transport`: MCP transport method - 'stdio' or 'http' (default: http)
- `--http-port`: Port for HTTP transport (default: 3000)

## MCP Tools

The server provides the following tools:

### read-value
Read the current value of one or more OPC UA nodes.

**Parameters:**
- `node_ids`: List of node IDs to read

**Example:**
```json
{
  "node_ids": ["ns=2;s=MyVariable", "ns=2;s=Temperature"]
}
```

### find-by-display-name
Find nodes by display name pattern (supports wildcards).

**Parameters:**
- `pattern`: Display name pattern with wildcards (e.g., *Temperature*)

**Example:**
```json
{
  "pattern": "*Temperature*"
}
```

### find-by-browse-name
Find nodes by browse name pattern (supports wildcards).

**Parameters:**
- `pattern`: Browse name pattern with wildcards (e.g., *Sensor*)

**Example:**
```json
{
  "pattern": "*Sensor*"
}
```

## Node Information

Each node in the tree contains:
- `node_id`: The OPC UA node identifier
- `browse_name`: The browse name of the node
- `display_name`: The human-readable display name
- `node_class`: The type of node (e.g., Object, Variable, Method, etc.)
- `children`: List of child nodes (only for non-leaf nodes)

## Example

1. Start an OPC UA server (e.g., using `opcua-asyncio` example server)
2. Run the MCP server:
   ```bash
   python opcua_mcp_server.py opc.tcp://localhost:4840
   ```
3. The MCP server will connect to the OPC UA server, browse the node tree, and expose it via MCP
4. You can now use any MCP client to interact with the OPC UA data

## Error Handling

- The server will exit if it cannot connect to the OPC UA server
- Individual node read errors are returned in the response
- The server properly disconnects from the OPC UA server on shutdown