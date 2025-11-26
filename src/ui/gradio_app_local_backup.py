"""
Gradio 6 Interface for Restaurant Intelligence Agent
Hackathon Submission: MCP-1st-Birthday Track 2 - Productivity
"""

import gradio as gr
from gradio import State
import os
import sys
import json
import ast
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.scrapers.opentable_scraper import scrape_opentable
from src.data_processing import process_reviews, clean_reviews_for_ai
from src.agent.base_agent import RestaurantAnalysisAgent


def clean_insight_text(text):
    """
    Clean up insight text that may contain list formatting or JSON artifacts.
    Handles recommendations with priority/action/reason structure.
    
    Args:
        text: Raw text that might be a list or have brackets/quotes
        
    Returns:
        Clean, formatted text with bullet points
    """
    if isinstance(text, list):
        # Handle list of dicts (recommendations format)
        if text and isinstance(text[0], dict):
            cleaned_items = []
            for item in text:
                if 'action' in item:
                    cleaned_items.append(item['action'])
                else:
                    cleaned_items.append(str(item))
            return '\n\n'.join(f"• {item}" for item in cleaned_items)
        # Handle simple list
        return '\n\n'.join(f"• {item}" for item in text)
    
    elif isinstance(text, str):
        text = text.strip()
        
        # Handle [{'priority': 'high', 'action': '...'}] style formatting
        if text.startswith('[{') and text.endswith('}]'):
            try:
                # Try to parse as Python list of dicts
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    actions = [item.get('action', str(item)) for item in parsed]
                    return '\n\n'.join(f"• {action}" for action in actions)
            except:
                # If parsing fails, try regex extraction
                try:
                    actions = re.findall(r"'action':\s*'([^']+)'", text)
                    if actions:
                        return '\n\n'.join(f"• {action}" for action in actions)
                except:
                    pass
        
        # Handle simple list format
        if text.startswith('[') and text.endswith(']'):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    # Handle list of dicts
                    if parsed and isinstance(parsed[0], dict):
                        actions = [item.get('action', str(item)) for item in parsed]
                        return '\n\n'.join(f"• {action}" for action in actions)
                    # Handle simple list
                    return '\n\n'.join(f"• {item}" for item in parsed)
            except:
                # Remove brackets and continue processing
                text = text.strip('[]')
        
        # Clean up quotes and convert comma-separated to bullets
        text = text.replace('", "', '\n• ').replace("', '", '\n• ').strip('"\'')
        
        # If already has bullets, return as is
        if '\n• ' in text and not text.startswith('• '):
            text = '• ' + text
        
        return text
    
    return str(text)


def analyze_restaurant_interface(
    url: str,
    review_count: int,
    progress=gr.Progress()
):
    """
    Main analysis function called by Gradio interface.
    
    Yields progress updates and final results.
    """
    try:
        # Validate URL
        if not url or "opentable" not in url.lower():
            return (
                "❌ Error: Please enter a valid OpenTable URL",
                None, "Run analysis to see chef insights", [], 
                None, "Run analysis to see manager insights", [], 
                "❌ Invalid URL", ""
            )
        
        # Phase 1: Scraping
        progress(0.1, desc="📥 Scraping reviews from OpenTable...")
        yield (
            "📥 Scraping reviews from OpenTable...",
            None, "Run analysis to see chef insights", [], 
            None, "Run analysis to see manager insights", [], 
            "⏳ In progress...", ""
        )
        
        result = scrape_opentable(url=url, max_reviews=review_count, headless=True)
        
        if not result['success']:
            error_msg = f"❌ Scraping failed: {result.get('error')}"
            yield (error_msg, None, "", [], None, "", [], error_msg, "")
            return
        
        progress(0.2, desc=f"✅ Scraped {result['total_reviews']} reviews")
        yield (
            f"✅ Scraped {result['total_reviews']} reviews\n\n⚙️ Processing data...",
            None, "Run analysis to see chef insights", [], 
            None, "Run analysis to see manager insights", [],
            "⏳ In progress...", ""
        )
        
        # Phase 2: Data Processing
        df = process_reviews(result)
        review_texts = df['review_text'].dropna().tolist()
        review_texts = clean_reviews_for_ai(review_texts, verbose=False)
        
        progress(0.3, desc="✅ Data cleaned and ready")
        yield (
            f"✅ Scraped {result['total_reviews']} reviews\n✅ Data cleaned and ready\n\n🤖 Running AI analysis...",
            None, "Run analysis to see chef insights", [], 
            None, "Run analysis to see manager insights", [],
            "⏳ In progress...", ""
        )
        
        # Phase 3: AI Analysis
        # Extract restaurant name from URL more reliably
        restaurant_name = url.split('/')[-1].split('?')[0].replace('-', ' ').title()
        
        print(f"DEBUG: Restaurant name extracted: '{restaurant_name}'")
        
        agent = RestaurantAnalysisAgent()
        
        progress(0.4, desc="🤖 Analyzing menu items and aspects...")
        
        analysis = agent.analyze_restaurant(
            restaurant_url=url,
            restaurant_name=restaurant_name,
            reviews=review_texts
        )
        
        if not analysis['success']:
            error_msg = f"❌ Analysis failed: {analysis.get('error')}"
            yield (error_msg, None, "", [], None, "", [], error_msg, "")
            return
        
        progress(0.8, desc="✅ Analysis complete! Preparing results...")
        
        # Extract results
        menu_data = analysis['menu_analysis']
        aspect_data = analysis['aspect_analysis']
        insights = analysis['insights']
        
        # Prepare chef data
        food_items = menu_data.get('food_items', [])
        drinks = menu_data.get('drinks', [])
        all_menu_items = food_items + drinks
        
        chef_dropdown_choices = [item['name'] for item in all_menu_items]
        
        # Format chef insights with cleaned text
        chef_insights_data = insights.get('chef', {})
        if isinstance(chef_insights_data, dict):
            summary = clean_insight_text(chef_insights_data.get('summary', 'No summary available'))
            strengths = clean_insight_text(chef_insights_data.get('strengths', 'No strengths identified'))
            concerns = clean_insight_text(chef_insights_data.get('concerns', 'No concerns identified'))
            recommendations = clean_insight_text(chef_insights_data.get('recommendations', 'No recommendations available'))
            
            chef_insights_text = f"""## 🍳 Chef Insights

### Summary:
{summary}

### ✅ Strengths:
{strengths}

### ⚠️ Concerns:
{concerns}

### 💡 Recommendations:
{recommendations}"""
        else:
            chef_insights_text = clean_insight_text(str(chef_insights_data))
        
        # Prepare manager data
        aspects = aspect_data.get('aspects', [])
        manager_dropdown_choices = [aspect['name'] for aspect in aspects]
        
        # Format manager insights with cleaned text
        manager_insights_data = insights.get('manager', {})
        if isinstance(manager_insights_data, dict):
            summary = clean_insight_text(manager_insights_data.get('summary', 'No summary available'))
            strengths = clean_insight_text(manager_insights_data.get('strengths', 'No strengths identified'))
            concerns = clean_insight_text(manager_insights_data.get('concerns', 'No concerns identified'))
            recommendations = clean_insight_text(manager_insights_data.get('recommendations', 'No recommendations available'))
            
            manager_insights_text = f"""## 👔 Manager Insights

### Summary:
{summary}

### ✅ Strengths:
{strengths}

### ⚠️ Concerns:
{concerns}

### 💡 Recommendations:
{recommendations}"""
        else:
            manager_insights_text = clean_insight_text(str(manager_insights_data))
        
        # Get chart paths
        chef_chart_path = "outputs/menu_sentiment.png" if os.path.exists("outputs/menu_sentiment.png") else None
        manager_chart_path = "outputs/aspect_comparison.png" if os.path.exists("outputs/aspect_comparison.png") else None
        
        progress(1.0, desc="✅ Complete!")
        
        final_progress = f"""✅ Analysis Complete!

📊 Results:
- Menu items found: {len(all_menu_items)}
- Aspects discovered: {len(aspects)}
- Chef insights: ✅
- Manager insights: ✅

👉 Check the tabs below for detailed results!"""
        
        # Ensure restaurant_name is a clean string for Q&A context
        restaurant_context_value = str(restaurant_name).strip()
        
        print(f"DEBUG: About to yield restaurant_context: '{restaurant_context_value}'")
        
        yield (
            final_progress,
            chef_chart_path,
            chef_insights_text,
            gr.update(choices=chef_dropdown_choices, value=None),
            manager_chart_path,
            manager_insights_text,
            gr.update(choices=manager_dropdown_choices, value=None),
            "✅ Analysis complete!",
            restaurant_context_value  # Clean string for Q&A
        )
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        import traceback
        print(f"DEBUG: Exception occurred:")
        print(traceback.format_exc())
        yield (error_msg, None, "", [], None, "", [], error_msg, "")


def get_menu_item_summary(item_name: str) -> str:
    """Get summary for selected menu item."""
    if not item_name:
        return "Please select a menu item"
    
    try:
        # Load menu data
        with open('outputs/menu_analysis.json', 'r') as f:
            menu_data = json.load(f)
        
        # Search in food items and drinks
        all_items = menu_data.get('food_items', []) + menu_data.get('drinks', [])
        
        for item in all_items:
            if item.get('name', '').lower() == item_name.lower():
                summary = item.get('summary', 'No summary available')
                sentiment = item.get('sentiment', 0)
                mentions = item.get('mention_count', 0)
                
                sentiment_emoji = "🟢" if sentiment > 0.3 else "🟡" if sentiment > -0.3 else "🔴"
                
                result = f"""## {item_name.title()}

{sentiment_emoji} **Sentiment:** {sentiment:+.2f} | **Mentions:** {mentions}

### Customer Feedback Summary:
{summary}

### Sample Reviews:
"""
                # Add sample reviews
                reviews = item.get('related_reviews', [])[:3]
                for i, review in enumerate(reviews, 1):
                    result += f"\n{i}. \"{review.get('review_text', '')[:200]}...\"\n"
                
                return result
        
        return f"No data found for '{item_name}'"
        
    except Exception as e:
        return f"Error loading summary: {str(e)}"


def get_aspect_summary(aspect_name: str) -> str:
    """Get summary for selected aspect."""
    if not aspect_name:
        return "Please select an aspect"
    
    try:
        # Load aspect data
        with open('outputs/aspect_analysis.json', 'r') as f:
            aspect_data = json.load(f)
        
        aspects = aspect_data.get('aspects', [])
        
        for aspect in aspects:
            if aspect.get('name', '').lower() == aspect_name.lower():
                summary = aspect.get('summary', 'No summary available')
                sentiment = aspect.get('sentiment', 0)
                mentions = aspect.get('mention_count', 0)
                
                sentiment_emoji = "🟢" if sentiment > 0.3 else "🟡" if sentiment > -0.3 else "🔴"
                
                result = f"""## {aspect_name.title()}

{sentiment_emoji} **Sentiment:** {sentiment:+.2f} | **Mentions:** {mentions}

### Customer Feedback Summary:
{summary}

### Sample Reviews:
"""
                # Add sample reviews
                reviews = aspect.get('related_reviews', [])[:3]
                for i, review in enumerate(reviews, 1):
                    result += f"\n{i}. \"{review.get('review_text', '')[:200]}...\"\n"
                
                return result
        
        return f"No data found for '{aspect_name}'"
        
    except Exception as e:
        return f"Error loading summary: {str(e)}"


def ask_question(question: str, restaurant_context: str) -> str:
    """Answer questions about the restaurant using RAG."""
    
    # Debug logging
    print(f"DEBUG: ask_question called")
    print(f"DEBUG: question = '{question}'")
    print(f"DEBUG: restaurant_context type = {type(restaurant_context)}")
    print(f"DEBUG: restaurant_context value = '{restaurant_context}'")
    print(f"DEBUG: restaurant_context repr = {repr(restaurant_context)}")
    
    if not question or question.strip() == "":
        return "❓ Please enter a question"
    
    # Check if context is valid
    if not restaurant_context or restaurant_context.strip() == "" or restaurant_context in ["⏳ In progress...", "❌ Invalid URL"]:
        return "⚠️ Please analyze a restaurant first before asking questions."
    
    try:
        from src.mcp_integrations.query_reviews import query_reviews_direct
        print(f"DEBUG: Calling query_reviews_direct with context: '{restaurant_context}'")
        answer = query_reviews_direct(restaurant_context, question)
        print(f"DEBUG: Got answer: {answer[:100]}...")
        return f"**Q:** {question}\n\n**A:** {answer}"
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(f"DEBUG: Error in ask_question: {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


def create_interface() -> gr.Blocks:
    """Create the Gradio interface."""
    
    with gr.Blocks(title="Restaurant Intelligence Agent") as demo:
        
        # Header
        gr.Markdown("""
        # 🍽️ Restaurant Intelligence Agent
        ### AI-Powered Restaurant Review Analysis
        
        Analyze customer reviews from OpenTable to get actionable insights for chefs and managers.
        Built with Claude AI + MCP + Gradio 6
        """)
        
        # Input Section
        with gr.Row():
            with gr.Column():
                url_input = gr.Textbox(
                    label="📍 OpenTable Restaurant URL",
                    placeholder="https://www.opentable.ca/r/restaurant-name",
                    info="Paste the full OpenTable URL of the restaurant"
                )
                
                review_count = gr.Dropdown(
                    choices=[20, 50, 100, 200, 300, 400, 500],
                    value=100,
                    label="📊 Number of Reviews to Analyze",
                    info="More reviews = better insights but longer processing time (recommended: 100)"
                )
                
                analyze_btn = gr.Button("🚀 Analyze Restaurant", variant="primary", size="lg")
        
        # Progress Section
        progress_box = gr.Textbox(
            label="📊 Analysis Progress",
            lines=6,
            interactive=False
        )
        
        status_text = gr.State("")  # Use State instead
        restaurant_context = gr.State("")  # Use State instead
        
        # Results Tabs
        with gr.Tabs():
            
            # Chef Tab
            with gr.Tab("🍳 Chef Insights"):
                gr.Markdown("### Kitchen Performance & Menu Analysis")
                
                chef_chart = gr.Image(label="Menu Sentiment Analysis", type="filepath")
                
                chef_insights = gr.Markdown("Run analysis to see chef insights")
                
                gr.Markdown("---")
                gr.Markdown("### 🔍 Drill Down: Select a Menu Item")
                
                chef_dropdown = gr.Dropdown(
                    choices=[],
                    label="Select Menu Item",
                    info="Choose a dish or drink to see detailed customer feedback"
                )
                
                chef_summary = gr.Markdown("Select a menu item above to see detailed feedback")
            
            # Manager Tab
            with gr.Tab("👔 Manager Insights"):
                gr.Markdown("### Operations & Service Analysis")
                
                manager_chart = gr.Image(label="Aspect Comparison", type="filepath")
                
                manager_insights = gr.Markdown("Run analysis to see manager insights")
                
                gr.Markdown("---")
                gr.Markdown("### 🔍 Drill Down: Select an Aspect")
                
                manager_dropdown = gr.Dropdown(
                    choices=[],
                    label="Select Aspect",
                    info="Choose an aspect (service, ambience, etc.) to see detailed feedback"
                )
                
                manager_summary = gr.Markdown("Select an aspect above to see detailed feedback")
            
            # Q&A Tab
            with gr.Tab("💬 Ask Questions"):
                gr.Markdown("""
                ### Ask questions about customer reviews
                
                Use the RAG-powered Q&A system to get specific answers from the review data.
                """)
                
                with gr.Row():
                    question_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., What do customers say about the atmosphere?",
                        lines=2
                    )
                
                ask_btn = gr.Button("Ask", variant="primary")
                
                answer_output = gr.Markdown("Answers will appear here after you analyze a restaurant and ask a question...")
        
        # Footer
        gr.Markdown("""
        ---
        **Built for:** Anthropic MCP 1st Birthday Hackathon 2025  
        **Track:** Track 2 - MCP in Action (Productivity)  
        **Tags:** `mcp-in-action-track-productivity`
        """)
        
        # Connect analyze button
        analyze_btn.click(
            fn=analyze_restaurant_interface,
            inputs=[url_input, review_count],
            outputs=[
                progress_box,
                chef_chart,
                chef_insights,
                chef_dropdown,
                manager_chart,
                manager_insights,
                manager_dropdown,
                status_text,
                restaurant_context
            ]
        )
        
        # Connect dropdowns
        chef_dropdown.change(
            fn=get_menu_item_summary,
            inputs=chef_dropdown,
            outputs=chef_summary
        )
        
        manager_dropdown.change(
            fn=get_aspect_summary,
            inputs=manager_dropdown,
            outputs=manager_summary
        )
        
        # Connect Q&A
        ask_btn.click(
            fn=ask_question,
            inputs=[question_input, restaurant_context],
            outputs=answer_output
        )
    
    return demo


def launch_app(share: bool = False):
    """Launch the Gradio app."""
    demo = create_interface()
    demo.launch(
        share=share,
        server_name="0.0.0.0",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
        )
    )


if __name__ == "__main__":
    launch_app(share=True)