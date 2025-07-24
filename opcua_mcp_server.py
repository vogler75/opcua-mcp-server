#!/usr/bin/env python3
"""
OPC UA MCP Server
Connects to an OPC UA server and exposes it via MCP (Model Context Protocol)
"""

import argparse
import asyncio
import json
import fnmatch
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from opcua import Client, ua
from opcua.ua import NodeClass
from fastmcp import FastMCP


@dataclass
class NodeInfo:
    """Information about an OPC UA node"""
    node_id: str
    browse_name: str
    display_name: str
    node_class: str
    children: List['NodeInfo'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class OPCUAMCPServer:
    def __init__(self, opcua_url: str, start_node: str = "i=85", 
                 username: Optional[str] = None, password: Optional[str] = None):
        self.opcua_url = opcua_url
        self.start_node = start_node
        self.username = username
        self.password = password
        self.client = None
        self.node_tree = None
        self.flat_nodes = {}  # node_id -> NodeInfo mapping for quick lookup
        
    def connect(self):
        """Connect to OPC UA server"""
        self.client = Client(self.opcua_url)
        
        if self.username and self.password:
            self.client.set_user(self.username)
            self.client.set_password(self.password)
            
        self.client.connect()
        print(f"Connected to OPC UA server: {self.opcua_url}")
        
    def disconnect(self):
        """Disconnect from OPC UA server"""
        if self.client:
            self.client.disconnect()
            print("Disconnected from OPC UA server")
            
    def browse_node(self, node, visited=None) -> NodeInfo:
        """Recursively browse a node and its children using proper OPC UA browsing"""
        if visited is None:
            visited = set()
            
        try:
            # Format the NodeId properly as a string
            node_id = node.nodeid.to_string()
            
            # Avoid infinite loops by checking if we've already visited this node
            if node_id in visited:
                return None
            visited.add(node_id)
            
            # Get node information
            browse_name = node.get_browse_name()
            display_name = node.get_display_name()
            node_class = node.get_node_class()
            
            node_info = NodeInfo(
                node_id=node_id,
                browse_name=browse_name.Name,
                display_name=display_name.Text or "",
                node_class=node_class.name
            )
            
            # Store in flat structure for quick lookup
            self.flat_nodes[node_info.node_id] = node_info
            
            # Browse all hierarchical references from this node
            try:
                # Use get_children_descriptions to get all references
                references = node.get_children_descriptions()
                
                if references:
                    for ref in references:
                        try:
                            # Get the target node
                            target_node = self.client.get_node(ref.NodeId)
                            
                            # Recursively browse the target node
                            child_info = self.browse_node(target_node, visited.copy())
                            if child_info:
                                node_info.children.append(child_info)
                                
                        except Exception as e:
                            print(f"Error browsing reference target {ref.NodeId}: {e}")
                            continue
                            
            except Exception as e:
                print(f"Error getting children descriptions for node {node}: {e}")
                # Fallback to simple get_children
                try:
                    children = node.get_children()
                    for child in children:
                        child_info = self.browse_node(child, visited.copy())
                        if child_info:
                            node_info.children.append(child_info)
                except Exception as e2:
                    print(f"Error with fallback get_children for node {node}: {e2}")
                    
            return node_info
            
        except Exception as e:
            print(f"Error browsing node {node}: {e}")
            return None
            
    def browse_tree(self):
        """Browse the entire node tree starting from the configured node"""
        if not self.client:
            raise Exception("Not connected to OPC UA server")
            
        # Get starting node
        start_node = self.client.get_node(self.start_node)
        print(f"Starting browse from node: {self.start_node}")
        
        # Browse recursively
        self.node_tree = self.browse_node(start_node)
        print(f"Browsing complete. Found {len(self.flat_nodes)} nodes")
        
    def read_node_value(self, node_id: str) -> Any:
        """Read the value of a single node"""
        if not self.client:
            raise Exception("Not connected to OPC UA server")
            
        try:
            node = self.client.get_node(node_id)
            value = node.get_value()
            return value
        except Exception as e:
            raise Exception(f"Error reading node {node_id}: {e}")
            
    def read_multiple_values(self, node_ids: List[str]) -> Dict[str, Any]:
        """Read values of multiple nodes"""
        results = {}
        for node_id in node_ids:
            try:
                results[node_id] = self.read_node_value(node_id)
            except Exception as e:
                results[node_id] = {"error": str(e)}
        return results
        
    def find_by_display_name(self, pattern: str) -> List[NodeInfo]:
        """Find nodes by display name using wildcards"""
        matches = []
        for node_id, node_info in self.flat_nodes.items():
            if fnmatch.fnmatch(node_info.display_name.lower(), pattern.lower()):
                matches.append(node_info)
        return matches
        
    def find_by_browse_name(self, pattern: str) -> List[NodeInfo]:
        """Find nodes by browse name using wildcards"""
        matches = []
        for node_id, node_info in self.flat_nodes.items():
            if fnmatch.fnmatch(node_info.browse_name.lower(), pattern.lower()):
                matches.append(node_info)
        return matches


# Global variable to store the OPC UA server instance
opcua_server = None


def main():
    global opcua_server
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='OPC UA MCP Server')
    parser.add_argument('opcua_url', help='OPC UA server URL (e.g., opc.tcp://localhost:4840)')
    parser.add_argument('--start-node', default='i=85', help='Starting node ID for browsing (default: i=85)')
    parser.add_argument('--username', help='Username for OPC UA authentication')
    parser.add_argument('--password', help='Password for OPC UA authentication')
    parser.add_argument('--transport', choices=['stdio', 'http'], default='http', 
                       help='MCP transport method (default: http)')
    parser.add_argument('--http-port', type=int, default=3000, 
                       help='Port for HTTP transport (default: 3000)')
    
    args = parser.parse_args()
    
    # Create OPC UA client
    opcua_server = OPCUAMCPServer(
        args.opcua_url,
        args.start_node,
        args.username,
        args.password
    )
    
    # Connect and browse
    try:
        opcua_server.connect()
        opcua_server.browse_tree()
    except Exception as e:
        print(f"Failed to connect or browse OPC UA server: {e}")
        return
    
    # Create MCP server
    mcp = FastMCP("opcua-mcp-server")
    
    
    # Define tools
    @mcp.tool()
    async def read_value(node_ids: List[str]) -> Dict[str, Any]:
        """Read the current value of one or more OPC UA nodes"""
        return {"values": opcua_server.read_multiple_values(node_ids)}
    
    @mcp.tool()
    async def find_by_display_name(pattern: str) -> Dict[str, List[Dict]]:
        """Find nodes by display name pattern (supports wildcards)"""
        matches = opcua_server.find_by_display_name(pattern)
        return {
            "matches": [
                {
                    "node_id": m.node_id,
                    "display_name": m.display_name,
                    "browse_name": m.browse_name,
                    "node_class": m.node_class
                }
                for m in matches
            ]
        }
    
    @mcp.tool()
    async def find_by_browse_name(pattern: str) -> Dict[str, List[Dict]]:
        """Find nodes by browse name pattern (supports wildcards)"""
        matches = opcua_server.find_by_browse_name(pattern)
        return {
            "matches": [
                {
                    "node_id": m.node_id,
                    "display_name": m.display_name,
                    "browse_name": m.browse_name,
                    "node_class": m.node_class
                }
                for m in matches
            ]
        }
    
    # Run the MCP server
    try:
        if args.transport == "stdio":
            # For stdio, run the default way
            mcp.run()
        else:  # HTTP
            # For HTTP transport, we need to create a web server
            # FastMCP should handle this internally
            mcp.run(transport="http", port=args.http_port)
                
    finally:
        if opcua_server:
            opcua_server.disconnect()


if __name__ == "__main__":
    main()