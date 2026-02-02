#!/bin/bash

echo "=========================================="
echo "MAScheaptalk - Setup and Run"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠ .env file not found!"
    echo ""
    echo "Creating .env file..."
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo ""
    echo "✅ Created .env file"
    echo "📝 Please edit .env and add your OpenAI API key:"
    echo "   OPENAI_API_KEY=sk-..."
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if API key is set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-api-key-here" ]; then
    echo "❌ OPENAI_API_KEY not configured in .env!"
    echo ""
    echo "Please edit .env file and add your API key:"
    echo "   OPENAI_API_KEY=sk-..."
    echo ""
    exit 1
fi

echo "✅ API key found"
echo ""

# Ask which milestone to run
echo "Which milestone do you want to run?"
echo "  1) Milestone 2: Deviation Suite"
echo "  2) Milestone 3: Baseline Comparison"
echo "  3) Milestone 4: Protocol Progression"
echo "  4) All Milestones"
echo ""
read -p "Enter choice (1-4): " choice

echo ""
echo "=========================================="
echo "Starting execution..."
echo "=========================================="
echo ""

case $choice in
    1)
        python run_milestone2_deviation.py
        ;;
    2)
        python run_milestone3_baselines.py
        ;;
    3)
        python run_milestone4_protocols.py
        ;;
    4)
        python run_all_milestones.py
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Execution complete!"
echo "=========================================="
echo ""
echo "📁 Results are in: results/"
echo "   - milestone2/deviation_suite_results.json"
echo "   - milestone3/baseline_comparison.json"
echo "   - milestone4/protocol_comparison.json"
