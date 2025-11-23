"""
Integration Script: Scraper → Agent → Analysis
Wires together the complete pipeline.
"""
import pandas as pd
from src.scrapers.opentable_scraper import scrape_opentable
from src.data_processing import process_reviews
from src.agent.base_agent import RestaurantAnalysisAgent

print("=" * 80)
print("🔥 COMPLETE PIPELINE: Scraper → Agent → Analysis")
print("=" * 80 + "\n")

# Step 1: Scrape reviews
print("📥 Step 1: Scraping OpenTable...")
url = "https://www.opentable.ca/r/miku-restaurant-vancouver"
restaurant_name = "Miku Restaurant"

scraper_result = scrape_opentable(url, max_reviews=50, headless=True)

if not scraper_result['success']:
    print(f"❌ Scraping failed: {scraper_result.get('error')}")
    exit(1)

print(f"✅ Scraped {scraper_result['total_reviews']} reviews\n")

# Step 2: Process to DataFrame
print("⚙️  Step 2: Processing data...")
df = process_reviews(scraper_result)
print(f"✅ Processed {len(df)} reviews into DataFrame\n")

# Step 3: Convert to format agents expect (List[str])
print("🔄 Step 3: Converting to agent format...")
review_texts = df['review_text'].dropna().tolist()  # ← Key conversion!
print(f"✅ Converted to {len(review_texts)} review texts\n")

# Step 4: Initialize agent
print("🤖 Step 4: Initializing Restaurant Analysis Agent...")
agent = RestaurantAnalysisAgent()
print("✅ Agent initialized with all sub-agents\n")

# Step 5: Run complete analysis
print("🚀 Step 5: Running complete analysis...")
print("-" * 80)

results = agent.analyze_restaurant(
    restaurant_url=url,
    restaurant_name=restaurant_name,
    reviews=review_texts,  # ← Pass list of strings
    review_count=str(len(review_texts))
)

print("\n" + "=" * 80)
print("📊 ANALYSIS RESULTS")
print("=" * 80 + "\n")

if results['success']:
    print(f"✅ Analysis completed successfully!\n")
    
    # Menu analysis
    menu_count = len(results['menu_analysis'].get('food_items', []))
    drink_count = len(results['menu_analysis'].get('drinks', []))
    print(f"🍽️  Menu Items Discovered: {menu_count} food + {drink_count} drinks")
    
    # Aspect analysis
    aspect_count = len(results['aspect_analysis'].get('aspects', []))
    print(f"🔍 Aspects Discovered: {aspect_count}")
    
    # Insights
    print(f"\n💡 Insights Generated:")
    print(f"   • Chef insights: {len(results['insights']['chef'].get('recommendations', []))} recommendations")
    print(f"   • Manager insights: {len(results['insights']['manager'].get('recommendations', []))} recommendations")
    
    # Step 6: Export everything
    print("\n" + "=" * 80)
    print("💾 Step 6: Exporting results...")
    print("=" * 80 + "\n")
    
    # Save raw data
    from src.data_processing import save_to_csv
    save_to_csv(df, 'data/raw/miku_reviews.csv')
    
    # Save analysis
    saved_files = agent.export_analysis('outputs')
    print("✅ Saved analysis files:")
    for key, path in saved_files.items():
        print(f"   • {key}: {path}")
    
    # Step 7: Test MCP tools
    print("\n" + "=" * 80)
    print("🔧 Step 7: Testing MCP Tools")
    print("=" * 80 + "\n")
    
    # Q&A
    print("🤔 Q&A Test:")
    question = "What do customers say about the sushi?"
    answer = agent.ask_question(question)
    print(f"   Q: {question}")
    print(f"   A: {answer[:200]}...\n")
    
    # Save report
    print("📄 Save Report Test:")
    report_path = agent.save_analysis_report('reports')
    print(f"   ✅ Report saved to: {report_path}\n")
    
    # Generate charts
    print("📊 Generate Charts Test:")
    charts = agent.generate_visualizations()
    for chart_type, path in charts.items():
        print(f"   ✅ {chart_type}: {path}")
    
else:
    print(f"❌ Analysis failed: {results.get('error')}")

print("\n" + "=" * 80)
print("🎉 COMPLETE PIPELINE TEST FINISHED!")
print("=" * 80)
