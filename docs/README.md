# Knowledge Manager Documentation

Welcome to the Knowledge Manager documentation! This directory contains comprehensive guides for using, deploying, and extending the Knowledge Manager.

## 📖 Documentation Index

### Getting Started

- **[Main README](../README.md)** - Quick start guide, installation, and basic usage
- **[MCP Integration Guide](MCP_INTEGRATION.md)** - Integrate with AI agents via Model Context Protocol

### Technical Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - System design, components, and data flow
- **[API Reference](API_REFERENCE.md)** - Complete REST API and MCP endpoint reference

## 📚 Documentation Overview

### [Architecture Guide](ARCHITECTURE.md)

Comprehensive overview of the Knowledge Manager's architecture and design.

**Topics Covered:**
- System architecture with component diagrams
- Architecture layers (Presentation, API, Business Logic, Data)
- Component details (Authentication, Ingestion, Vector Operations)
- Data flow diagrams (Upload, Query, MCP)
- Security architecture and threat model
- Scalability considerations and optimization strategies
- Technology stack and design decisions

**Read this if you want to:**
- Understand how the system works internally
- Learn about data flow and component interactions
- Explore security mechanisms
- Plan for scaling or extending the system
- Understand design trade-offs

---

### [API Reference](API_REFERENCE.md)

Complete API documentation for all REST and MCP endpoints.

**Topics Covered:**
- User management (registration, login, API keys)
- Document management (upload, index, query, delete)
- Corpus management (create, upload, query, permissions)
- Admin operations (approve/revoke corpuses)
- MCP protocol (JSON-RPC 2.0 implementation)
- Error codes and handling
- Rate limiting policies

**Read this if you want to:**
- Integrate with the Knowledge Manager programmatically
- Understand API request/response formats
- Learn about available endpoints and parameters
- Implement error handling and retry logic
- Configure rate limits

---

### [MCP Integration Guide](MCP_INTEGRATION.md)

Guide for integrating AI agents with Knowledge Manager via the Model Context Protocol.

**Topics Covered:**
- What is MCP and how it works
- Quick start with curl examples
- Available tools (query_knowledge, query_corpus, list_collections, list_corpuses)
- Available resources (corpus metadata)
- Streaming queries via Server-Sent Events
- Error handling with structured error codes
- Rate limiting for MCP endpoints
- Python client examples
- Claude Desktop integration

**Read this if you want to:**
- Enable AI agents to search your knowledge base
- Use Knowledge Manager with Claude or other AI assistants
- Implement streaming queries for progressive results
- Build custom MCP clients
- Integrate with Claude Desktop

---

## 🚀 Quick Start Paths

### For Users

1. Start with the **[Main README](../README.md)** for installation
2. Follow the setup instructions to get the server running
3. Use the Streamlit UI for basic operations
4. Check **[API Reference](API_REFERENCE.md)** for programmatic access

### For AI Integration

1. Read **[MCP Integration Guide](MCP_INTEGRATION.md)** for overview
2. Try the **[Python Client Example](../examples/mcp/python_client.py)**
3. Explore streaming with **[Streaming Client](../examples/mcp/streaming_client.py)**
4. Configure **[Claude Desktop](../examples/mcp/claude_desktop_config.json)** for direct integration

### For Developers

1. Review **[Architecture Guide](ARCHITECTURE.md)** to understand the system
2. Read **[API Reference](API_REFERENCE.md)** for endpoint details
3. Check the codebase structure in the main README
4. Explore **[MCP Integration](MCP_INTEGRATION.md)** for MCP implementation details

### For System Administrators

1. Review **[Architecture Guide](ARCHITECTURE.md)** for security and scalability
2. Check **[API Reference](API_REFERENCE.md)** for rate limiting configuration
3. Set up environment variables per the main README
4. Monitor logs and configure rate limits as needed

---

## 📂 Additional Resources

### Code Examples

- **[Python MCP Client](../examples/mcp/python_client.py)** - Complete MCP client implementation
- **[Streaming Client](../examples/mcp/streaming_client.py)** - SSE streaming example
- **[Claude Desktop Config](../examples/mcp/claude_desktop_config.json)** - Claude integration

### Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Configuration Files

- **[.env.example](../.env.example)** - Environment variables reference
- **[requirements.txt](../requirements.txt)** - Python dependencies

---

## 🔧 Environment Configuration

All configuration is managed via environment variables. See `.env.example` for a complete reference.

**Key Settings:**

```bash
# Required
OPENAI_API_KEY=sk-your-api-key

# Optional (with defaults)
VECTOR_DB_PATH=./data/vector_index
USER_DB_PATH=./users.db
MAX_FILE_SIZE_MB=25
API_KEY_TTL_DAYS=90

# Rate Limiting
QUERY_RATE_LIMIT=60/minute
UPLOAD_RATE_LIMIT=10/minute

# MCP-specific
MCP_QUERY_RATE_LIMIT=30/minute
MCP_LIST_RATE_LIMIT=60/minute
```

---

## 🆘 Getting Help

### Common Issues

1. **Import Errors:** Run `pip install -r requirements.txt`
2. **OpenAI API Errors:** Check `OPENAI_API_KEY` in `.env`
3. **Database Errors:** Ensure write permissions on `VECTOR_DB_PATH`
4. **Rate Limit Errors:** Adjust rate limits in `.env`

### Documentation Feedback

If you find issues with the documentation or have suggestions:

1. Open an issue on GitHub
2. Submit a pull request with improvements
3. Contact the maintainers

---

## 📝 Documentation Updates

**Last Updated:** Phase 6 - MCP Integration Complete

**Version:** 1.0.0

**Contributors:** Knowledge Manager Development Team

---

## 📄 License

This documentation is part of the Knowledge Manager project and is licensed under the MIT License.
