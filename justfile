registry := "ghcr.io/hardmcp"
image := "ndpsc-case-search-mcp"
port := "8000"

# List available recipes
default:
    @just --list

# Run the server locally with uv
dev:
    uv run ndpsc-case-search-mcp

# Build the Docker image
build:
    docker build -t {{image}} .

# Run the Docker container
run: build
    docker run --rm -p {{port}}:8000 {{image}}

# Build, tag, and push to GHCR
push: build
    docker tag {{image}} {{registry}}/{{image}}:latest
    docker push {{registry}}/{{image}}:latest

# Check server health
health:
    curl -s http://localhost:{{port}}/health | python3 -m json.tool

# Format code
fmt:
    uv run ruff format .
    uv run ruff check --select I --fix .
