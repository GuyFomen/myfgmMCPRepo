# ════════════════════════════════════════════════════════════════════════════
# Makefile — myfgmmcpforsqlserver
# ════════════════════════════════════════════════════════════════════════════

PYTHON  = .venv/Scripts/python.exe
UV      = uv
SERVER  = myfgm_sql_mcp_server.py
TESTS   = tests/test_server.py

.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "  make install      Install all dependencies"
	@echo "  make test         Run full test suite"
	@echo "  make test-v       Run tests with verbose output"
	@echo "  make test-fast    Run tests stopping at first failure"
	@echo "  make server       Start the MCP server"
	@echo "  make clean        Remove cache and temp files"
	@echo ""

install:
	$(UV) sync

test:
	$(UV) run pytest $(TESTS)

test-v:
	$(UV) run pytest $(TESTS) -v

test-fast:
	$(UV) run pytest $(TESTS) -v -x

server:
	$(UV) run python $(SERVER)

clean:
	$(UV) run python -c "import shutil, os; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', 'tests/__pycache__', '__pycache__']]"
	@echo "Cleaned."