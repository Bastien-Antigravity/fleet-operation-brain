VERSION ?= $(shell cat VERSION.txt 2>/dev/null || echo "0.0.1")

.PHONY: all build test race vet version clean

all: build

version:
	@echo $(VERSION)

build:
	@echo "Building repository (version $(VERSION))..."
	@if [ -f "go.mod" ]; then go build ./...; fi
	@if [ -f "Cargo.toml" ]; then cargo build --release; fi

test:
	@echo "Running tests (version $(VERSION))..."
	@if [ -f "go.mod" ]; then go test -v ./...; fi
	@if [ -f "Cargo.toml" ]; then cargo test; fi

race:
	@echo "Running race detector (version $(VERSION))..."
	@if [ -f "go.mod" ]; then go test -race ./...; fi

vet:
	@echo "Running go vet..."
	@if [ -f "go.mod" ]; then go vet ./...; fi

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist build *.egg-info target/ bin/
