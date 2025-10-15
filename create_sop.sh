#!/bin/bash

###############################################################################
# Confluence SOP Creator - Shell Wrapper
#
# This script provides a convenient way to run the Python SOP creator
# with proper error handling and environment setup.
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Please install Python 3.7 or higher"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_info "Using Python $PYTHON_VERSION"
}

# Check if requests library is installed
check_dependencies() {
    if ! python3 -c "import requests" &> /dev/null; then
        print_warning "The 'requests' library is not installed"
        echo ""
        read -p "Would you like to install it now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Installing requests..."
            pip3 install requests
            print_success "Requests library installed"
        else
            print_error "Cannot continue without 'requests' library"
            echo "Please run: pip3 install requests"
            exit 1
        fi
    fi
}

# Show banner
show_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Confluence SOP Page Creator                            ║"
    echo "║     Create professional SOPs with ease                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Check if config file exists
check_config() {
    if [ -f ".env" ]; then
        print_info "Loading configuration from .env file"
        source .env
        export CONFLUENCE_URL
        export CONFLUENCE_EMAIL
        export CONFLUENCE_API_TOKEN
    fi
}

# Show quick help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -i, --interactive       Run in interactive mode (default)
    -j, --json FILE         Create SOP from JSON file
    -t, --template          Show template structure
    -v, --version           Show version information

Environment Variables:
    CONFLUENCE_URL          Your Confluence instance URL
    CONFLUENCE_EMAIL        Your Atlassian email
    CONFLUENCE_API_TOKEN    Your API token

Examples:
    $0                      # Interactive mode
    $0 -j my_sop.json       # Create from JSON
    $0 --template           # Show template

For more information, see: SOP_CREATOR_README.md
EOF
}

# Show template info
show_template() {
    print_info "SOP Template Structure"
    echo ""
    cat << EOF
A complete SOP includes:

1. Document Control Information
   - Document ID, Version, Dates, Owner, Department

2. Purpose
   - Why this SOP exists

3. Scope
   - What it covers and doesn't cover

4. Definitions and Acronyms
   - Terms used in the document

5. Roles and Responsibilities
   - Who does what

6. Procedure (Core Section)
   - Step-by-step instructions
   - Substeps for details
   - Notes and warnings

7. Related Documents
   - Links to other SOPs and references

8. Revision History
   - Track changes over time

See sop_template.json for a complete example.
EOF
}

# Main script
main() {
    show_banner

    # Parse command line arguments
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--template)
            show_template
            exit 0
            ;;
        -v|--version)
            echo "Confluence SOP Creator v1.0.0"
            exit 0
            ;;
    esac

    # Check prerequisites
    print_info "Checking prerequisites..."
    check_python
    check_dependencies
    check_config
    print_success "All prerequisites met"
    echo ""

    # Handle JSON file input
    if [ "$1" = "-j" ] || [ "$1" = "--json" ]; then
        if [ -z "$2" ]; then
            print_error "Please specify a JSON file"
            echo "Usage: $0 -j <filename.json>"
            exit 1
        fi

        if [ ! -f "$2" ]; then
            print_error "File not found: $2"
            exit 1
        fi

        print_info "Creating SOP from: $2"
        # Auto-input for JSON mode
        python3 create_confluence_page.py << EOF
2
$2
MDS

EOF
    else
        # Interactive mode (default)
        print_info "Starting interactive mode..."
        echo ""
        python3 create_confluence_page.py
    fi
}

# Run main function
main "$@"
