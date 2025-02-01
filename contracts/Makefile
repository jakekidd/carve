# Makefile for setting up and testing the ESIMMarketplace project

.PHONY: all clean build test

# Install Foundry and dependencies
# @echo "Installing Foundry..."
# curl -L https://foundry.paradigm.xyz | bash
install:
	@echo "Installing dependencies..."
	forge install OpenZeppelin/openzeppelin-contracts --no-commit

# Build the project
build:
	@echo "Building the project..."
	forge build

# Run tests
test:
	@echo "Running tests..."
	forge test

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	forge clean

# Default target
all: install build test
