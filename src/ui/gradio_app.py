"""
Restaurant Intelligence Agent - Enhanced Gradio 6 Interface
Professional UI with cards, plain English summaries, polished layout

Hackathon: Anthropic MCP 1st Birthday - Track 2 (Productivity)
Author: Tushar Pingle
"""

import gradio as gr
import os
import ast
import requests
from typing import Optional, Tuple, List
import tempfile

# ============================================================================
# CONFIGURATION
# ============================================================================

MODAL_API_URL = os.getenv(
    "MODAL_API_URL",
    "https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run"
)

# ============================================================================
# SENTIMENT TRANSLATOR - Plain English Summaries
# ============================================================================

def translate_menu_performance(menu_data: dict, restaurant_name: str) -> str:
    """Convert menu analysis into plain English summary."""
    food_items = menu_data.get('food_items', [])
    drinks = menu_data.get('drinks', [])
    all_items = food_items + drinks
    
    if not all_items:
        return "No menu items were identified in the reviews."
    
    total = len(all_items)
    positive = [i for i in all_items if i.get('sentiment', 0) > 0.3]
    neutral = [i for i in all_items if -0.3 <= i.get('sentiment', 0) <= 0.3]
    negative = [i for i in all_items if i.get('sentiment', 0) < -0.3]
    
    pos_pct = round((len(positive) / total) * 100)
    neu_pct = round((len(neutral) / total) * 100)
    neg_pct = round((len(negative) / total) * 100)
    
    # Top performers and concerns
    sorted_items = sorted(all_items, key=lambda x: x.get('sentiment', 0), reverse=True)
    top_3 = [i.get('name', 'Unknown') for i in sorted_items[:3]]
    bottom_3 = [i.get('name', 'Unknown') for i in sorted_items[-3:] if i.get('sentiment', 0) < 0.3]
    
    summary = f"""**📊 Menu Performance Overview for {restaurant_name}**

Customers mentioned **{total} menu items** ({len(food_items)} food, {len(drinks)} drinks).

**Sentiment Breakdown:**
- 🟢 **{pos_pct}%** received positive feedback ({len(positive)} items)
- 🟡 **{neu_pct}%** received mixed feedback ({len(neutral)} items)
- 🔴 **{neg_pct}%** received negative feedback ({len(negative)} items)

**⭐ Top Performers:** {', '.join(top_3) if top_3 else 'N/A'}
"""
    
    if bottom_3:
        summary += f"\n**⚠️ Needs Attention:** {', '.join(bottom_3)}"
    
    summary += "\n\n💡 *Select a menu item from the dropdown below for detailed customer feedback.*"
    
    return summary


def translate_aspect_performance(aspect_data: dict, restaurant_name: str) -> str:
    """Convert aspect analysis into plain English summary."""
    aspects = aspect_data.get('aspects', [])
    
    if not aspects:
        return "No aspects were identified in the reviews."
    
    total = len(aspects)
    positive = [a for a in aspects if a.get('sentiment', 0) > 0.3]
    neutral = [a for a in aspects if -0.3 <= a.get('sentiment', 0) <= 0.3]
    negative = [a for a in aspects if a.get('sentiment', 0) < -0.3]
    
    pos_pct = round((len(positive) / total) * 100)
    neu_pct = round((len(neutral) / total) * 100)
    neg_pct = round((len(negative) / total) * 100)
    
    sorted_aspects = sorted(aspects, key=lambda x: x.get('sentiment', 0), reverse=True)
    strengths = [a.get('name', 'Unknown') for a in sorted_aspects[:3]]
    concerns = [a.get('name', 'Unknown') for a in sorted_aspects[-3:] if a.get('sentiment', 0) < 0.3]
    
    summary = f"""**📊 Operations & Service Overview for {restaurant_name}**

Customers discussed **{total} different aspects** of their experience.

**Sentiment Breakdown:**
- 🟢 **{pos_pct}%** positive feedback ({len(positive)} aspects)
- 🟡 **{neu_pct}%** mixed feedback ({len(neutral)} aspects)
- 🔴 **{neg_pct}%** negative feedback ({len(negative)} aspects)

**💪 Strengths:** {', '.join(strengths) if strengths else 'N/A'}
"""
    
    if concerns:
        summary += f"\n**⚠️ Areas for Improvement:** {', '.join(concerns)}"
    
    summary += "\n\n💡 *Select an aspect from the dropdown below for detailed analysis.*"
    
    return summary


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_insight_text(text) -> str:
    """Clean up insight text."""
    if text is None:
        return "No data available"
    
    if isinstance(text, list):
        if text and isinstance(text[0], dict):
            items = [item.get('action', str(item)) for item in text]
            return '\n'.join(f"• {item}" for item in items)
        return '\n'.join(f"• {str(item)}" for item in text)
    
    if isinstance(text, dict):
        return f"• {text.get('action', str(text))}"
    
    if isinstance(text, str):
        text = text.strip()
        if text.startswith('[') or text.startswith('{'):
            try:
                parsed = ast.literal_eval(text)
                return clean_insight_text(parsed)
            except:
                pass
        return text.strip('"\'[]')
    
    return str(text)


def format_insights(insights: dict, role: str) -> str:
    """Format insights into clean markdown."""
    if not isinstance(insights, dict):
        return str(insights)
    
    emoji = "🍳" if role == "chef" else "👔"
    title = "Kitchen & Menu" if role == "chef" else "Operations & Service"
    
    summary = insights.get('summary', 'Analysis complete.')
    strengths = clean_insight_text(insights.get('strengths', []))
    concerns = clean_insight_text(insights.get('concerns', []))
    recommendations = clean_insight_text(insights.get('recommendations', []))
    
    return f"""### {emoji} {title} Insights

**Summary:** {summary}

**✅ Strengths:**
{strengths}

**⚠️ Concerns:**
{concerns}

**💡 Recommendations:**
{recommendations}
"""


def generate_chart(items: list, title: str) -> Optional[str]:
    """Generate professional dark-themed sentiment chart."""
    if not items:
        return None
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        # Dark theme colors (matching Gradio dark mode)
        BG_COLOR = '#1f2937'       # Dark background
        TEXT_COLOR = '#e5e7eb'     # Light gray text
        GRID_COLOR = '#374151'     # Subtle grid
        POSITIVE = '#10b981'       # Green
        NEUTRAL = '#f59e0b'        # Amber/Orange
        NEGATIVE = '#ef4444'       # Red
        
        # Sort and limit
        sorted_items = sorted(items, key=lambda x: x.get('sentiment', 0), reverse=True)[:10]
        
        names = [item.get('name', '?')[:20] for item in sorted_items]
        sentiments = [item.get('sentiment', 0) for item in sorted_items]
        mentions = [item.get('mention_count', 1) for item in sorted_items]
        
        # Colors based on sentiment
        colors = [POSITIVE if s > 0.3 else NEUTRAL if s > -0.3 else NEGATIVE for s in sentiments]
        
        # Create figure with dark background
        fig, ax = plt.subplots(figsize=(8, max(4, len(names) * 0.45)))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        y_pos = range(len(names))
        
        # Create horizontal bars with rounded edges effect
        bars = ax.barh(y_pos, sentiments, color=colors, height=0.65, 
                      edgecolor=BG_COLOR, linewidth=1, alpha=0.9)
        
        # Style axes
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=10, color=TEXT_COLOR, fontweight='medium')
        ax.set_xlabel('Sentiment Score', fontsize=10, color=TEXT_COLOR, fontweight='medium')
        ax.set_title(title, fontsize=13, fontweight='bold', color=TEXT_COLOR, pad=15)
        
        # Zero line
        ax.axvline(x=0, color=GRID_COLOR, linestyle='-', linewidth=1.5, alpha=0.8)
        ax.set_xlim(-1, 1)
        
        # Value labels with background
        for bar, sent, mention in zip(bars, sentiments, mentions):
            label = f'{sent:+.2f}'
            x_pos = bar.get_width() + 0.05 if bar.get_width() >= 0 else bar.get_width() - 0.12
            ax.text(x_pos, bar.get_y() + bar.get_height()/2, label, 
                   va='center', ha='left' if bar.get_width() >= 0 else 'right',
                   fontsize=9, color=TEXT_COLOR, fontweight='bold')
            
            # Mention count on the left
            ax.text(-0.95, bar.get_y() + bar.get_height()/2, f'({mention})', 
                   va='center', ha='left', fontsize=8, color='#9ca3af', alpha=0.8)
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Subtle grid
        ax.xaxis.grid(True, color=GRID_COLOR, linestyle='-', linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)
        
        # X-axis ticks
        ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=9)
        ax.tick_params(axis='y', colors=TEXT_COLOR, left=False)
        
        # Legend with dark background
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=POSITIVE, label='Positive', alpha=0.9),
            Patch(facecolor=NEUTRAL, label='Mixed', alpha=0.9),
            Patch(facecolor=NEGATIVE, label='Negative', alpha=0.9)
        ]
        legend = ax.legend(handles=legend_elements, loc='lower right', fontsize=8,
                          facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
        
        plt.tight_layout()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            plt.savefig(f.name, dpi=120, bbox_inches='tight', 
                       facecolor=BG_COLOR, edgecolor='none')
            plt.close(fig)
            return f.name
        
    except Exception as e:
        print(f"Chart error: {e}")
        return None


def extract_restaurant_name(url: str) -> str:
    """Extract restaurant name from URL."""
    try:
        path = url.split('?')[0].rstrip('/')
        return path.split('/')[-1].replace('-', ' ').title()
    except:
        return "Restaurant"


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_restaurant(url: str, review_count: int):
    """Main analysis - calls Modal API."""
    
    empty = {}
    default_summary = "Run analysis to see performance overview."
    default_insight = "Run analysis to see insights."
    default_detail = "Select an item to see details."
    empty_dropdown = gr.update(choices=[], value=None)
    
    # Validation
    if not url or not url.strip():
        return (
            "❌ **Error:** Please enter an OpenTable restaurant URL.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    
    url = url.strip()
    if "opentable" not in url.lower():
        return (
            "❌ **Error:** URL must be from OpenTable (e.g., opentable.com/r/restaurant-name)",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    
    restaurant_name = extract_restaurant_name(url)
    
    try:
        # Call Modal
        response = requests.post(
            f"{MODAL_API_URL}/analyze",
            json={"url": url, "max_reviews": review_count},
            timeout=1800
        )
        
        if response.status_code != 200:
            return (
                f"❌ **API Error ({response.status_code}):** {response.text[:200]}",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        data = response.json()
        
        if not data.get("success"):
            return (
                f"❌ **Analysis Failed:** {data.get('error', 'Unknown error')}",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        # Extract data
        menu = data.get('menu_analysis', {})
        aspects = data.get('aspect_analysis', {})
        insights = data.get('insights', {})
        
        food_items = menu.get('food_items', [])
        drinks = menu.get('drinks', [])
        aspect_list = aspects.get('aspects', [])
        all_menu = food_items + drinks
        
        # State
        state = {
            "menu_analysis": menu,
            "aspect_analysis": aspects,
            "insights": insights,
            "restaurant_name": restaurant_name
        }
        
        # Plain English Summaries
        menu_summary = translate_menu_performance(menu, restaurant_name)
        aspect_summary = translate_aspect_performance(aspects, restaurant_name)
        
        # Insights
        chef_insights = format_insights(insights.get('chef', {}), 'chef')
        manager_insights = format_insights(insights.get('manager', {}), 'manager')
        
        # Charts
        chef_chart = generate_chart(all_menu, f"Menu Item Sentiment")
        manager_chart = generate_chart(aspect_list, f"Aspect Sentiment")
        
        # Dropdowns - use gr.update() for Gradio 6
        chef_choices = [i.get('name', '?') for i in all_menu]
        manager_choices = [a.get('name', '?') for a in aspect_list]
        
        chef_dropdown_update = gr.update(choices=chef_choices, value=None)
        manager_dropdown_update = gr.update(choices=manager_choices, value=None)
        
        # Status
        status = f"""✅ **Analysis Complete for {restaurant_name}!**

**📊 Summary:**
• Reviews analyzed: **{review_count}**
• Menu items found: **{len(all_menu)}** ({len(food_items)} food, {len(drinks)} drinks)
• Aspects discovered: **{len(aspect_list)}**

👇 **Explore the tabs below for detailed insights!**
"""
        
        return (
            status,
            menu_summary, chef_chart, chef_insights, chef_dropdown_update, default_detail,
            aspect_summary, manager_chart, manager_insights, manager_dropdown_update, default_detail,
            state
        )
        
    except requests.exceptions.Timeout:
        return (
            "❌ **Timeout:** Request took too long. Try with fewer reviews (20-50).",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    except Exception as e:
        return (
            f"❌ **Error:** {str(e)}",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )


# ============================================================================
# DRILL-DOWN FUNCTIONS
# ============================================================================

def get_item_detail(item_name: str, state: dict) -> str:
    if not item_name:
        return "👆 **Select a menu item** from the dropdown to see detailed customer feedback."
    if not state:
        return "⚠️ Please analyze a restaurant first."
    
    menu = state.get("menu_analysis", {})
    for item in menu.get('food_items', []) + menu.get('drinks', []):
        if item.get('name', '').lower() == item_name.lower():
            s = item.get('sentiment', 0)
            emoji = "🟢" if s > 0.3 else "🟡" if s > -0.3 else "🔴"
            label = "Positive" if s > 0.3 else "Mixed" if s > -0.3 else "Negative"
            
            result = f"""### {item_name.title()} {emoji}

**Sentiment:** {s:+.2f} ({label}) | **Mentions:** {item.get('mention_count', 0)}

---

**What customers say:**
{item.get('summary', 'No summary available.')}

---

**Sample reviews:**
"""
            for i, r in enumerate(item.get('related_reviews', [])[:3], 1):
                text = r.get('review_text', str(r))[:180] if isinstance(r, dict) else str(r)[:180]
                result += f"\n> {i}. \"{text}...\"\n"
            return result
    
    return f"No data found for '{item_name}'"


def get_aspect_detail(aspect_name: str, state: dict) -> str:
    if not aspect_name:
        return "👆 **Select an aspect** from the dropdown to see detailed analysis."
    if not state:
        return "⚠️ Please analyze a restaurant first."
    
    aspects = state.get("aspect_analysis", {}).get('aspects', [])
    for aspect in aspects:
        if aspect.get('name', '').lower() == aspect_name.lower():
            s = aspect.get('sentiment', 0)
            emoji = "🟢" if s > 0.3 else "🟡" if s > -0.3 else "🔴"
            label = "Positive" if s > 0.3 else "Mixed" if s > -0.3 else "Negative"
            
            result = f"""### {aspect_name.title()} {emoji}

**Sentiment:** {s:+.2f} ({label}) | **Mentions:** {aspect.get('mention_count', 0)}

---

**What customers say:**
{aspect.get('summary', 'No summary available.')}

---

**Sample reviews:**
"""
            for i, r in enumerate(aspect.get('related_reviews', [])[:3], 1):
                text = r.get('review_text', str(r))[:180] if isinstance(r, dict) else str(r)[:180]
                result += f"\n> {i}. \"{text}...\"\n"
            return result
    
    return f"No data found for '{aspect_name}'"


def answer_question(question: str, state: dict) -> str:
    if not question or not question.strip():
        return "❓ Please type a question above."
    if not state:
        return "⚠️ Please analyze a restaurant first."
    
    restaurant = state.get("restaurant_name", "the restaurant")
    menu = state.get("menu_analysis", {})
    aspects = state.get("aspect_analysis", {})
    
    q = question.lower()
    matches = []
    
    for item in menu.get('food_items', []) + menu.get('drinks', []):
        name = item.get('name', '').lower()
        if name in q or any(w in name for w in q.split() if len(w) > 3):
            matches.append(item)
    
    for aspect in aspects.get('aspects', []):
        name = aspect.get('name', '').lower()
        if name in q or any(w in name for w in q.split() if len(w) > 3):
            matches.append(aspect)
    
    if matches:
        answer = f"**Based on reviews of {restaurant}:**\n\n"
        for m in matches[:3]:
            s = m.get('sentiment', 0)
            emoji = "🟢" if s > 0.3 else "🟡" if s > -0.3 else "🔴"
            answer += f"**{m.get('name', '?').title()}** {emoji} (sentiment: {s:+.2f})\n"
            answer += f"{m.get('summary', '')[:250]}...\n\n"
        return f"**Q:** {question}\n\n{answer}"
    
    return f"""**Q:** {question}

**A:** I couldn't find specific information about that topic.

💡 **Try asking about:**
• Specific dishes (e.g., "How is the salmon?")
• Service quality (e.g., "What do people say about service?")
• Ambiance (e.g., "Is it good for dates?")
• Value (e.g., "Is it worth the price?")
"""


# ============================================================================
# EXAMPLE QUESTIONS
# ============================================================================

EXAMPLE_QUESTIONS = [
    "What are the best dishes to order?",
    "How is the service quality?",
    "Is this restaurant good for a date?",
    "What do people say about the ambiance?",
    "Is the food worth the price?",
    "Any complaints about wait times?",
]

def use_example_question(example: str) -> str:
    return example


# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_app() -> gr.Blocks:
    """Create enhanced Gradio interface."""
    
    with gr.Blocks(title="Restaurant Intelligence Agent") as app:
        
        # ==================== HEADER ====================
        gr.Markdown("""
# 🍽️ Restaurant Intelligence Agent

**AI-Powered Review Analysis for Restaurant Owners, Chefs & Managers**

*Uncover what customers really think — beyond star ratings.*
        """)
        
        gr.Markdown("---")
        
        # ==================== INPUT SECTION ====================
        gr.Markdown("### 📍 Enter Restaurant Details")
        
        with gr.Row():
            with gr.Column(scale=5):
                url_input = gr.Textbox(
                    label="OpenTable URL",
                    placeholder="https://www.opentable.com/r/restaurant-name",
                    info="Paste the full URL from OpenTable",
                    max_lines=1
                )
            with gr.Column(scale=1):
                review_count = gr.Dropdown(
                    choices=[20, 50, 100, 200],
                    value=50,
                    label="Reviews",
                    info="More = better insights"
                )
            with gr.Column(scale=1):
                analyze_btn = gr.Button("🚀 Analyze", variant="primary", size="lg")
        
        # ==================== STATUS ====================
        status_box = gr.Markdown(
            value="*Enter a restaurant URL above and click **Analyze** to start. Analysis takes 3-8 minutes.*"
        )
        
        # Hidden state
        analysis_state = gr.State(value={})
        
        gr.Markdown("---")
        
        # ==================== RESULTS TABS ====================
        with gr.Tabs():
            
            # ========== CHEF TAB ==========
            with gr.Tab("🍳 Chef Insights"):
                
                # Plain English Summary
                chef_summary = gr.Markdown(
                    value="*Run analysis to see menu performance overview.*"
                )
                
                gr.Markdown("---")
                
                # Chart + Insights side by side
                with gr.Row():
                    with gr.Column(scale=1):
                        chef_chart = gr.Image(label="Menu Sentiment Chart", height=380)
                    with gr.Column(scale=1):
                        chef_insights = gr.Markdown(value="*AI-generated insights will appear here.*")
                
                gr.Markdown("---")
                
                # Drill-down
                gr.Markdown("#### 🔍 Explore Menu Items")
                chef_dropdown = gr.Dropdown(label="Select a menu item", choices=[], interactive=True)
                chef_detail = gr.Markdown(value="*Select an item above to see what customers say about it.*")
            
            # ========== MANAGER TAB ==========
            with gr.Tab("👔 Manager Insights"):
                
                # Plain English Summary
                manager_summary = gr.Markdown(
                    value="*Run analysis to see operations & service overview.*"
                )
                
                gr.Markdown("---")
                
                # Chart + Insights
                with gr.Row():
                    with gr.Column(scale=1):
                        manager_chart = gr.Image(label="Aspect Sentiment Chart", height=380)
                    with gr.Column(scale=1):
                        manager_insights = gr.Markdown(value="*AI-generated insights will appear here.*")
                
                gr.Markdown("---")
                
                # Drill-down
                gr.Markdown("#### 🔍 Explore Service Aspects")
                manager_dropdown = gr.Dropdown(label="Select an aspect", choices=[], interactive=True)
                manager_detail = gr.Markdown(value="*Select an aspect above to see detailed feedback.*")
            
            # ========== Q&A TAB ==========
            with gr.Tab("💬 Ask Questions"):
                
                gr.Markdown("""
### Ask anything about the reviews

Get instant answers based on customer feedback. Try asking about specific dishes, 
service quality, ambiance, value, or any other aspect of the dining experience.
                """)
                
                # Example questions
                gr.Markdown("**💡 Try these example questions:**")
                with gr.Row():
                    for i, q in enumerate(EXAMPLE_QUESTIONS[:3]):
                        gr.Button(q, size="sm").click(
                            fn=lambda x=q: x,
                            outputs=gr.Textbox(visible=False)
                        )
                
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., What do customers think about the pasta dishes?",
                    lines=2
                )
                
                with gr.Row():
                    ask_btn = gr.Button("🔍 Ask", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
                
                answer_output = gr.Markdown(
                    value="*Analyze a restaurant first, then ask questions about the reviews.*"
                )
                
                clear_btn.click(fn=lambda: ("", ""), outputs=[question_input, answer_output])
        
        # ==================== FOOTER ====================
        gr.Markdown("---")
        
        gr.Markdown("""
<center>

**Built for** [Anthropic MCP 1st Birthday Hackathon](https://huggingface.co/MCP-1st-Birthday) 🎂 | 
**Track:** Productivity | **By:** Tushar Pingle

*Powered by Claude AI • Modal Cloud • MCP Integration*

</center>
        """)
        
        # ==================== EVENT HANDLERS ====================
        analyze_btn.click(
            fn=analyze_restaurant,
            inputs=[url_input, review_count],
            outputs=[
                status_box,
                chef_summary, chef_chart, chef_insights, chef_dropdown, chef_detail,
                manager_summary, manager_chart, manager_insights, manager_dropdown, manager_detail,
                analysis_state
            ]
        )
        
        chef_dropdown.change(
            fn=get_item_detail,
            inputs=[chef_dropdown, analysis_state],
            outputs=chef_detail
        )
        
        manager_dropdown.change(
            fn=get_aspect_detail,
            inputs=[manager_dropdown, analysis_state],
            outputs=manager_detail
        )
        
        ask_btn.click(
            fn=answer_question,
            inputs=[question_input, analysis_state],
            outputs=answer_output
        )
    
    return app


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        theme=gr.themes.Soft(primary_hue="orange", secondary_hue="slate")
    )