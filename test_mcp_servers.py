"""
Test all MCP servers
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=" * 70)
print("Testing MCP Servers")
print("=" * 70 + "\n")

# Test 1: save_report
print("Test 1: Testing save_report MCP server")
print("-" * 70)

from src.mcp_integrations.save_report import save_json_report, list_saved_reports

test_data = {
    "restaurant": "Test Restaurant",
    "sentiment": 0.85,
    "menu_items": ["salmon sushi", "miso soup"],
    "aspects": ["food quality", "service speed"]
}

saved_path = save_json_report("Test Restaurant", test_data, "reports")
print(f"✅ Report saved to: {saved_path}")

reports = list_saved_reports("reports")
print(f"✅ Found {len(reports)} reports")
if reports:
    print(f"   Latest: {reports[0]}")

# Test 2: query_reviews
print("\n" + "=" * 70)
print("Test 2: Testing query_reviews MCP server")
print("-" * 70)

from src.mcp_integrations.query_reviews import index_reviews, query_reviews, get_indexed_restaurants

test_reviews = [
    "The salmon sushi was incredible! So fresh.",
    "Service was slow - waited 25 minutes.",
    "Food quality is amazing but pricey.",
    "Presentation is stunning!",
]

result = index_reviews("Test Restaurant", test_reviews)
print(f"✅ {result}")

restaurants = get_indexed_restaurants()
print(f"✅ Indexed restaurants: {restaurants}")

answer = query_reviews("Test Restaurant", "What do customers say about the salmon sushi?")
print(f"\n📋 Q&A Test:")
print(f"   Question: What do customers say about the salmon sushi?")
print(f"   Answer: {answer[:200]}...")

# Test 3: generate_chart
print("\n" + "=" * 70)
print("Test 3: Testing generate_chart MCP server")
print("-" * 70)

from src.mcp_integrations.generate_chart import generate_sentiment_chart, generate_comparison_chart

test_items = [
    {"name": "salmon sushi", "sentiment": 0.89},
    {"name": "miso soup", "sentiment": 0.72},
    {"name": "tempura", "sentiment": 0.45},
]

chart_path = generate_sentiment_chart(test_items, "outputs/test_sentiment.png")
print(f"✅ Sentiment chart saved to: {chart_path}")

comparison_data = {
    "food quality": 0.88,
    "service speed": 0.52,
    "presentation": 0.91,
}

comparison_path = generate_comparison_chart(
    comparison_data, 
    "outputs/test_comparison.png",
    "Aspect Comparison"
)
print(f"✅ Comparison chart saved to: {comparison_path}")

print("\n" + "=" * 70)
print("🎉 All MCP servers tested successfully!")
print("=" * 70)
print("\n✅ save_report: Working")
print("✅ query_reviews: Working")
print("✅ generate_chart: Working")
print("\nMCP servers are ready for agent integration!")
