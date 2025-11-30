"""
Restaurant Intelligence Agent - Enhanced Gradio 6 Interface
Professional UI with cards, plain English summaries, polished layout

Hackathon: Anthropic MCP 1st Birthday - Track 2 (Productivity)
Author: Tushar Pingle

VERSION 4.1 UPDATES:
1. NEW SENTIMENT SCALE:
   - 🟢 Positive: >= 0.6 (customers clearly enjoyed/praised)
   - 🟡 Neutral: 0 to 0.59 (mixed feelings, average, okay)
   - 🔴 Negative: < 0 (complaints, criticism, disappointment)

2. Updated all thresholds throughout the app for consistency
3. Improved Q&A prompt for balanced answers (pros AND cons)
4. Fixed PDF style conflicts with RIA prefix
5. Fixed Q&A "proxies" error with Anthropic SDK
6. Multi-platform support (OpenTable + Google Maps)
"""

import gradio as gr
import os
import ast
import re
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from typing import Optional, Tuple, List, Dict, Any
import tempfile
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================

MODAL_API_URL = os.getenv(
    "MODAL_API_URL",
    "https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run"
)

# Email configuration (set these as environment variables)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Restaurant Intelligence Agent <noreply@example.com>")


# ============================================================================
# URL DETECTION
# ============================================================================

def detect_platform(url: str) -> str:
    """Detect which platform the URL is from."""
    if not url:
        return "unknown"
    
    url_lower = url.lower()
    
    if 'opentable' in url_lower:
        return "opentable"
    elif any(x in url_lower for x in ['google.com/maps', 'goo.gl/maps', 'maps.google', 'maps.app.goo.gl']):
        return "google_maps"
    else:
        return "unknown"


def get_platform_emoji(platform: str) -> str:
    """Get emoji for platform."""
    return "🍽️" if platform == "opentable" else "🗺️" if platform == "google_maps" else "❓"


# ============================================================================
# TREND CHART - Rating vs Sentiment Over Time
# ============================================================================

def parse_opentable_date(date_str: str) -> Optional[datetime]:
    """Parse date formats like 'Dined 1 day ago', '2 weeks ago', etc."""
    if not date_str:
        return None
    
    date_str = str(date_str).lower().strip()
    today = datetime.now()
    
    day_match = re.search(r'(\d+)\s*days?\s*ago', date_str)
    if day_match:
        return today - timedelta(days=int(day_match.group(1)))
    
    week_match = re.search(r'(\d+)\s*weeks?\s*ago', date_str)
    if week_match:
        return today - timedelta(weeks=int(week_match.group(1)))
    
    month_match = re.search(r'(\d+)\s*months?\s*ago', date_str)
    if month_match:
        return today - timedelta(days=int(month_match.group(1)) * 30)
    
    if 'yesterday' in date_str:
        return today - timedelta(days=1)
    if 'today' in date_str:
        return today
    
    simple_day = re.search(r'^(\d+)\s*day', date_str)
    if simple_day:
        return today - timedelta(days=int(simple_day.group(1)))
    
    simple_week = re.search(r'^(\d+)\s*week', date_str)
    if simple_week:
        return today - timedelta(weeks=int(simple_week.group(1)))
    
    return None


def calculate_review_sentiment(text: str) -> float:
    """
    Simple sentiment calculation from review text.
    Returns value from -1 (very negative) to +1 (very positive).
    
    NOTE: This matches the backend's calculate_sentiment() function.
    The backend pre-calculates sentiment in trend_data, but this is used
    as a fallback when text needs to be analyzed locally.
    """
    if not text:
        return 0.0
    text = str(text).lower()
    
    positive = ['amazing', 'excellent', 'fantastic', 'great', 'awesome', 'delicious', 
                'perfect', 'outstanding', 'loved', 'beautiful', 'fresh', 'friendly', 
                'best', 'wonderful', 'incredible', 'superb', 'exceptional', 'good',
                'nice', 'tasty', 'recommend', 'enjoy', 'impressed', 'favorite']
    negative = ['terrible', 'horrible', 'awful', 'bad', 'worst', 'disappointing', 
                'poor', 'overpriced', 'slow', 'rude', 'cold', 'bland', 'mediocre',
                'disgusting', 'inedible', 'undercooked', 'overcooked']
    
    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)
    
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


def generate_trend_chart(trend_data: List[Dict], restaurant_name: str) -> Optional[str]:
    """
    Generate Rating vs Sentiment trend chart.
    
    UPDATED: Now uses pre-calculated trend_data from backend.
    Format: [{"date": "2 days ago", "rating": 4.5, "sentiment": 0.6}, ...]
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    if not trend_data or len(trend_data) < 3:
        return None
    
    dated_reviews = []
    for r in trend_data:
        if not isinstance(r, dict):
            continue
        date = parse_opentable_date(r.get('date', ''))
        if date:
            rating = float(r.get('rating', 0) or 0)
            sentiment = float(r.get('sentiment', 0) or 0)  # Already calculated!
            dated_reviews.append({
                'date': date,
                'rating': rating if rating > 0 else 3.5,
                'sentiment': sentiment
            })
    
    # Fallback: if no dates parsed, use sequential ordering
    if len(dated_reviews) < 3 and len(trend_data) >= 3:
        dated_reviews = []
        for i, r in enumerate(trend_data):
            if not isinstance(r, dict):
                continue
            rating = float(r.get('rating', 0) or 3.5)
            sentiment = float(r.get('sentiment', 0) or 0)
            dated_reviews.append({
                'date': datetime.now() - timedelta(days=i),
                'rating': rating if rating > 0 else 3.5,
                'sentiment': sentiment
            })
    
    if len(dated_reviews) < 3:
        return None
    
    dated_reviews.sort(key=lambda x: x['date'])
    weekly = {}
    for r in dated_reviews:
        week = r['date'] - timedelta(days=r['date'].weekday())
        key = week.strftime('%Y-%m-%d')
        if key not in weekly:
            weekly[key] = {'date': week, 'ratings': [], 'sentiments': []}
        weekly[key]['ratings'].append(r['rating'])
        weekly[key]['sentiments'].append(r['sentiment'])
    
    dates = []
    ratings = []
    sentiments = []
    for k in sorted(weekly.keys()):
        w = weekly[k]
        dates.append(w['date'])
        ratings.append(sum(w['ratings']) / len(w['ratings']))
        sentiments.append(sum(w['sentiments']) / len(w['sentiments']))
    
    if len(dates) < 2:
        return None
    
    BG = '#1f2937'
    TEXT = '#e5e7eb'
    GRID = '#374151'
    RATING_COLOR = '#f59e0b'
    SENTIMENT_COLOR = '#10b981'
    
    try:
        fig, ax1 = plt.subplots(figsize=(14, 6))
        fig.patch.set_facecolor(BG)
        ax1.set_facecolor(BG)
        
        ax1.plot(dates, ratings, color=RATING_COLOR, linewidth=2.5, marker='o', 
                 markersize=8, label='Avg Rating (Stars)')
        ax1.fill_between(dates, ratings, alpha=0.2, color=RATING_COLOR)
        ax1.set_ylabel('Rating (1-5)', fontsize=12, color=RATING_COLOR)
        ax1.tick_params(axis='y', labelcolor=RATING_COLOR, labelsize=10)
        ax1.tick_params(axis='x', colors=TEXT, labelsize=10)
        ax1.set_ylim(1, 5)
        
        ax2 = ax1.twinx()
        ax2.set_facecolor(BG)
        sent_scaled = [(s + 1) * 2 + 1 for s in sentiments]
        ax2.plot(dates, sent_scaled, color=SENTIMENT_COLOR, linewidth=2.5, 
                 marker='s', markersize=8, linestyle='--', label='Sentiment')
        ax2.fill_between(dates, sent_scaled, alpha=0.15, color=SENTIMENT_COLOR)
        ax2.set_ylabel('Sentiment', fontsize=12, color=SENTIMENT_COLOR)
        ax2.tick_params(axis='y', labelcolor=SENTIMENT_COLOR, labelsize=10)
        ax2.set_ylim(1, 5)
        
        ax1.set_title(f'Rating vs Sentiment Trend', fontsize=15, fontweight='bold', color=TEXT, pad=20)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', color=TEXT)
        ax1.grid(True, alpha=0.3, color=GRID)
        
        for spine in ax1.spines.values():
            spine.set_color(GRID)
        for spine in ax2.spines.values():
            spine.set_color(GRID)
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower left',
                   facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=10)
        
        plt.tight_layout(pad=2.0)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            plt.savefig(f.name, dpi=120, bbox_inches='tight', facecolor=BG)
            plt.close()
            return f.name
    except Exception as e:
        print(f"[TREND CHART] Error: {e}")
        return None


def generate_trend_insight(trend_data: List[Dict], restaurant_name: str) -> str:
    """
    Generate text insight from trend data.
    
    UPDATED: Now uses pre-calculated trend_data from backend.
    Format: [{"date": "...", "rating": 4.5, "sentiment": 0.6}, ...]
    """
    if not trend_data or len(trend_data) < 3:
        return "Not enough data to analyze trends (need 3+ reviews)."
    
    ratings = []
    sentiments = []
    for r in trend_data:
        if isinstance(r, dict):
            rating = float(r.get('rating', 0) or r.get('overall_rating', 0) or 0)
            if rating > 0:
                ratings.append(rating)
            # Use pre-calculated sentiment if available, otherwise calculate
            sentiment = r.get('sentiment')
            if sentiment is not None:
                sentiments.append(float(sentiment))
            else:
                text = r.get('text', '') or r.get('review_text', '')
                sentiments.append(calculate_review_sentiment(text))
    
    if not ratings:
        return "No rating data available."
    
    avg_rating = sum(ratings) / len(ratings)
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    
    insight = f"**{restaurant_name}** has an average rating of **{avg_rating:.1f} stars** "
    
    if avg_sentiment >= 0.6:
        insight += "with **positive sentiment**. "
        if avg_rating >= 4.0:
            insight += "✅ Ratings and sentiment are aligned!"
        else:
            insight += "🤔 Sentiment is positive but ratings are moderate."
    elif avg_sentiment < 0:
        insight += "but with **concerning sentiment**. "
        if avg_rating >= 4.0:
            insight += "⚠️ **Warning:** High ratings but negative sentiment detected."
        else:
            insight += "❌ Both ratings and sentiment suggest issues."
    else:
        insight += "with **neutral sentiment**. 📊 Reviews are mixed."
    
    return insight


# ============================================================================
# HELPER FUNCTIONS - IMPROVED SUMMARIES
# ============================================================================

def clean_insight_text(data) -> str:
    """Convert various formats to clean bullet points."""
    if not data:
        return "• No data available"
    
    if isinstance(data, str):
        try:
            parsed = ast.literal_eval(data)
            if isinstance(parsed, list):
                data = parsed
        except:
            return data
    
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                action = item.get('action', item.get('recommendation', str(item)))
                priority = item.get('priority', '')
                if priority:
                    lines.append(f"• **[{priority.upper()}]** {action}")
                else:
                    lines.append(f"• {action}")
            else:
                lines.append(f"• {item}")
        return "\n".join(lines) if lines else "• No data available"
    
    return str(data)


def format_insights(insights: dict, role: str) -> str:
    """Format insights for display."""
    if not insights:
        return f"*No {role} insights available yet.*"
    
    emoji = "🍳" if role == "chef" else "📊"
    title = "Chef" if role == "chef" else "Manager"
    
    summary = insights.get('summary', 'Analysis in progress...')
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


def translate_menu_performance(menu: dict, restaurant_name: str) -> str:
    """
    Create simple summary of menu performance.
    Keep it clean - detailed info is in the dropdown.
    """
    food_items = menu.get('food_items', [])
    drinks = menu.get('drinks', [])
    all_items = food_items + drinks
    
    if not all_items:
        return f"*No menu data available for {restaurant_name} yet.*"
    
    # Count categories - NEW thresholds: >= 0.6 positive, 0-0.59 neutral, < 0 negative
    stars = len([i for i in all_items if i.get('sentiment', 0) >= 0.6])
    good = len([i for i in all_items if 0 <= i.get('sentiment', 0) < 0.6])
    concerns = len([i for i in all_items if i.get('sentiment', 0) < 0])
    
    # Simple summary
    summary = f"""### 🍽️ Menu Overview for {restaurant_name}

**{len(all_items)} items analyzed** ({len(food_items)} food, {len(drinks)} drinks)

| Category | Count |
|----------|-------|
| 🟢 Positive (≥0.6) | {stars} |
| 🟡 Neutral (0 to 0.59) | {good} |
| 🔴 Negative (<0) | {concerns} |

👇 **Select an item from the dropdown below to see detailed customer feedback.**
"""
    return summary


def translate_aspect_performance(aspects: dict, restaurant_name: str) -> str:
    """
    Create simple summary of aspect performance.
    Keep it clean - detailed info is in the dropdown.
    """
    aspect_list = aspects.get('aspects', [])
    
    if not aspect_list:
        return f"*No aspect data available for {restaurant_name} yet.*"
    
    # Count categories - NEW thresholds: >= 0.6 positive, 0-0.59 neutral, < 0 negative
    strengths = len([a for a in aspect_list if a.get('sentiment', 0) >= 0.6])
    neutral = len([a for a in aspect_list if 0 <= a.get('sentiment', 0) < 0.6])
    weaknesses = len([a for a in aspect_list if a.get('sentiment', 0) < 0])
    
    # Simple summary
    summary = f"""### 📊 Customer Experience Overview for {restaurant_name}

**{len(aspect_list)} aspects analyzed**

| Category | Count |
|----------|-------|
| 🟢 Strengths (≥0.6) | {strengths} |
| 🟡 Neutral (0 to 0.59) | {neutral} |
| 🔴 Weaknesses (<0) | {weaknesses} |

👇 **Select an aspect from the dropdown below to see detailed customer feedback.**
"""
    return summary


def generate_chart(items: list, title: str) -> Optional[str]:
    """Generate sentiment chart - top 10 by mentions, highest at TOP."""
    if not items:
        return None
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        BG_COLOR = '#1f2937'
        TEXT_COLOR = '#e5e7eb'
        GRID_COLOR = '#374151'
        POSITIVE = '#10b981'
        NEUTRAL = '#f59e0b'
        NEGATIVE = '#ef4444'
        
        # Sort by mention_count descending, then REVERSE for display
        # (so highest mentions appear at TOP of horizontal bar chart)
        sorted_items = sorted(items, key=lambda x: x.get('mention_count', 0), reverse=True)[:10]
        sorted_items = sorted_items[::-1]  # Reverse so highest is at top
        
        names = [f"{item.get('name', '?')[:18]} ({item.get('mention_count', 0)})" for item in sorted_items]
        sentiments = [item.get('sentiment', 0) for item in sorted_items]
        
        # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
        colors = [POSITIVE if s >= 0.6 else NEUTRAL if s >= 0 else NEGATIVE for s in sentiments]
        
        fig, ax = plt.subplots(figsize=(10, max(5, len(names) * 0.5)))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        y_pos = range(len(names))
        bars = ax.barh(y_pos, sentiments, color=colors, height=0.65, alpha=0.9)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=10, color=TEXT_COLOR, fontweight='medium')
        ax.set_xlabel('Sentiment Score', fontsize=11, color=TEXT_COLOR)
        ax.set_title(title, fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
        
        ax.axvline(x=0, color=GRID_COLOR, linestyle='-', linewidth=1.5, alpha=0.8)
        ax.set_xlim(-1, 1)
        
        for bar, sent in zip(bars, sentiments):
            label = f'{sent:+.2f}'
            x_pos = bar.get_width() + 0.05 if bar.get_width() >= 0 else bar.get_width() - 0.12
            ax.text(x_pos, bar.get_y() + bar.get_height()/2, label, 
                   va='center', ha='left' if bar.get_width() >= 0 else 'right',
                   fontsize=9, color=TEXT_COLOR, fontweight='bold')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        ax.xaxis.grid(True, color=GRID_COLOR, linestyle='-', linewidth=0.5, alpha=0.5)
        ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=9)
        ax.tick_params(axis='y', colors=TEXT_COLOR, left=False)
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=POSITIVE, label='Positive (>0.3)', alpha=0.9),
            Patch(facecolor=NEUTRAL, label='Mixed (-0.3 to 0.3)', alpha=0.9),
            Patch(facecolor=NEGATIVE, label='Negative (<-0.3)', alpha=0.9)
        ]
        ax.legend(handles=legend_elements, loc='lower left', fontsize=9,
                 facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
        
        plt.tight_layout()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            plt.savefig(f.name, dpi=120, bbox_inches='tight', facecolor=BG_COLOR)
            plt.close(fig)
            return f.name
    except Exception as e:
        print(f"Chart error: {e}")
        return None


def extract_restaurant_name(url: str) -> str:
    """Extract restaurant name from URL."""
    try:
        if 'opentable' in url.lower():
            path = url.split('?')[0].rstrip('/')
            return path.split('/')[-1].replace('-', ' ').title()
        elif 'google' in url.lower():
            if '/place/' in url:
                place = url.split('/place/')[1].split('/')[0]
                return place.replace('+', ' ').replace('%20', ' ').replace('%26', '&')
        return "Restaurant"
    except:
        return "Restaurant"


def get_item_detail(item_name: str, state: dict) -> str:
    """Get DETAILED feedback for a selected menu item."""
    if not item_name or not state:
        return "Select an item to see details."
    
    clean_name = item_name.split(' (')[0].strip().lower()
    menu = state.get('menu_analysis', {})
    all_items = menu.get('food_items', []) + menu.get('drinks', [])
    
    for item in all_items:
        if item.get('name', '').lower() == clean_name:
            sentiment = item.get('sentiment', 0)
            mentions = item.get('mention_count', 0)
            summary = item.get('summary', '')
            related_reviews = item.get('related_reviews', [])
            
            # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
            emoji = "🟢" if sentiment >= 0.6 else "🟡" if sentiment >= 0 else "🔴"
            
            detail = f"""### {clean_name.title()}

{emoji} **Sentiment Score:** {sentiment:+.2f} | **Total Mentions:** {mentions}

---

**📝 What Customers Are Saying:**

{summary if summary else 'No detailed summary available.'}

"""
            # Add sample reviews if available
            if related_reviews:
                detail += "\n**💬 Sample Reviews:**\n\n"
                for i, review in enumerate(related_reviews[:3]):
                    if isinstance(review, dict):
                        text = review.get('review_text', str(review))
                    else:
                        text = str(review)
                    if text and len(text) > 20:
                        detail += f"> *\"{text[:200]}{'...' if len(text) > 200 else ''}\"*\n\n"
            
            # Add actionable insight - NEW thresholds
            detail += "\n**🎯 Recommended Action:**\n"
            if sentiment >= 0.6:
                detail += f"This is a **star performer**! Consider featuring {clean_name.title()} in promotions and training staff to recommend it."
            elif sentiment >= 0:
                detail += f"Customers have neutral/mixed feelings about {clean_name.title()}. Monitor feedback and look for improvement opportunities."
            else:
                detail += f"⚠️ **Attention Needed:** {clean_name.title()} has negative feedback. Review preparation process and address customer complaints."
            
            return detail
    
    return f"No details found for '{item_name}'."


def get_aspect_detail(aspect_name: str, state: dict) -> str:
    """Get DETAILED feedback for a selected aspect."""
    if not aspect_name or not state:
        return "Select an aspect to see details."
    
    clean_name = aspect_name.split(' (')[0].strip().lower()
    aspects = state.get('aspect_analysis', {}).get('aspects', [])
    
    for aspect in aspects:
        if aspect.get('name', '').lower() == clean_name:
            sentiment = aspect.get('sentiment', 0)
            mentions = aspect.get('mention_count', 0)
            summary = aspect.get('summary', '')
            related_reviews = aspect.get('related_reviews', [])
            
            # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
            emoji = "🟢" if sentiment >= 0.6 else "🟡" if sentiment >= 0 else "🔴"
            
            detail = f"""### {clean_name.title()}

{emoji} **Sentiment Score:** {sentiment:+.2f} | **Total Mentions:** {mentions}

---

**📝 Customer Feedback Summary:**

{summary if summary else 'No detailed summary available.'}

"""
            # Add sample reviews if available
            if related_reviews:
                detail += "\n**💬 What Customers Said:**\n\n"
                for i, review in enumerate(related_reviews[:3]):
                    if isinstance(review, dict):
                        text = review.get('review_text', str(review))
                    else:
                        text = str(review)
                    if text and len(text) > 20:
                        detail += f"> *\"{text[:200]}{'...' if len(text) > 200 else ''}\"*\n\n"
            
            # Add actionable insight - NEW thresholds
            detail += "\n**🎯 Recommended Action:**\n"
            if sentiment >= 0.6:
                detail += f"**{clean_name.title()}** is a major strength! Maintain current standards and use in marketing."
            elif sentiment >= 0:
                detail += f"**{clean_name.title()}** has neutral/mixed reviews. Identify specific areas to improve and make it exceptional."
            else:
                detail += f"⚠️ **Priority Issue:** **{clean_name.title()}** needs attention. Address customer complaints and consider staff training or process changes."
            
            return detail
    
    return f"No details found for '{aspect_name}'."


# ============================================================================
# PDF GENERATION - FIXED
# ============================================================================

def generate_pdf_report(state: dict) -> Optional[str]:
    """
    Generate professional PDF report from analysis state.
    Uses ReportLab with custom styling for a polished output.
    """
    if not state:
        print("[PDF] No state provided")
        return None
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Color scheme
        PRIMARY = HexColor('#2563eb')
        PRIMARY_LIGHT = HexColor('#dbeafe')
        POSITIVE = HexColor('#10b981')
        POSITIVE_LIGHT = HexColor('#d1fae5')
        WARNING = HexColor('#f59e0b')
        WARNING_LIGHT = HexColor('#fef3c7')
        NEGATIVE = HexColor('#ef4444')
        NEGATIVE_LIGHT = HexColor('#fee2e2')
        TEXT_DARK = HexColor('#1f2937')
        TEXT_LIGHT = HexColor('#6b7280')
        BACKGROUND = HexColor('#f9fafb')
        BORDER = HexColor('#e5e7eb')
        
        # Extract data
        restaurant_name = state.get('restaurant_name', 'Restaurant')
        source = state.get('source', 'unknown').replace('_', ' ').title()
        menu = state.get('menu_analysis', {})
        aspects = state.get('aspect_analysis', {})
        insights = state.get('insights', {})
        # Use trend_data (slim) or fall back to raw_reviews for backward compatibility
        trend_data = state.get('trend_data', state.get('raw_reviews', []))
        
        food_items = menu.get('food_items', [])
        drinks = menu.get('drinks', [])
        all_menu = food_items + drinks
        aspect_list = aspects.get('aspects', [])
        
        # Create file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = restaurant_name.lower().replace(" ", "_").replace("/", "_").replace("&", "and")[:30]
        output_path = os.path.join(tempfile.gettempdir(), f"{safe_name}_report_{timestamp}.pdf")
        
        print(f"[PDF] Generating professional report for {restaurant_name}")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles - ALL use unique names to avoid conflicts with ReportLab defaults
        # ReportLab defaults include: Normal, BodyText, Italic, Heading1-6, Title, Bullet, Definition, Code
        
        styles.add(ParagraphStyle('RIACoverTitle', parent=styles['Heading1'],
                                 fontSize=32, textColor=PRIMARY, alignment=TA_CENTER,
                                 spaceAfter=10, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIACoverSubtitle', parent=styles['Normal'],
                                 fontSize=16, textColor=TEXT_LIGHT, alignment=TA_CENTER,
                                 spaceAfter=30, fontName='Helvetica'))
        
        styles.add(ParagraphStyle('RIACoverRestaurant', parent=styles['Heading1'],
                                 fontSize=24, textColor=TEXT_DARK, alignment=TA_CENTER,
                                 spaceAfter=15, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIASectionHeader', parent=styles['Heading1'],
                                 fontSize=18, textColor=PRIMARY, spaceBefore=20,
                                 spaceAfter=12, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIASubHeader', parent=styles['Heading2'],
                                 fontSize=14, textColor=TEXT_DARK, spaceBefore=15,
                                 spaceAfter=8, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIABody', parent=styles['Normal'],
                                 fontSize=10, textColor=TEXT_DARK, spaceAfter=8,
                                 leading=14, fontName='Helvetica'))
        
        styles.add(ParagraphStyle('RIABullet', parent=styles['Normal'],
                                 fontSize=10, textColor=TEXT_DARK, leftIndent=20,
                                 spaceAfter=5, fontName='Helvetica'))
        
        styles.add(ParagraphStyle('RIAQuote', parent=styles['Normal'],
                                 fontSize=10, textColor=TEXT_LIGHT, leftIndent=20,
                                 rightIndent=20, spaceAfter=10, fontName='Helvetica-Oblique'))
        
        styles.add(ParagraphStyle('RIAFooter', parent=styles['Normal'],
                                 fontSize=8, textColor=TEXT_LIGHT, alignment=TA_CENTER))
        
        styles.add(ParagraphStyle('RIAPriorityHigh', parent=styles['Normal'],
                                 fontSize=10, textColor=NEGATIVE, leftIndent=20,
                                 spaceAfter=5, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIAPriorityMedium', parent=styles['Normal'],
                                 fontSize=10, textColor=WARNING, leftIndent=20,
                                 spaceAfter=5, fontName='Helvetica-Bold'))
        
        styles.add(ParagraphStyle('RIAPriorityLow', parent=styles['Normal'],
                                 fontSize=10, textColor=POSITIVE, leftIndent=20,
                                 spaceAfter=5, fontName='Helvetica-Bold'))
        
        elements = []
        
        # ==================== COVER PAGE ====================
        elements.append(Spacer(1, 1.5*inch))
        elements.append(Paragraph("RESTAURANT", styles['RIACoverTitle']))
        elements.append(Paragraph("INTELLIGENCE REPORT", styles['RIACoverTitle']))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("AI-Powered Customer Review Analysis", styles['RIACoverSubtitle']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=10, spaceAfter=10))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(restaurant_name, styles['RIACoverRestaurant']))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"Data Source: {source}", styles['RIAFooter']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Stats boxes
        stats_data = [[
            str(len(trend_data)), str(len(all_menu)), str(len(aspect_list))
        ], [
            "Reviews", "Menu Items", "Aspects"
        ]]
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BACKGROUND),
            ('TEXTCOLOR', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 1), (-1, 1), TEXT_LIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 24),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['RIAFooter']))
        elements.append(Paragraph("Powered by Claude AI • Restaurant Intelligence Agent", styles['RIAFooter']))
        elements.append(PageBreak())
        
        # ==================== EXECUTIVE SUMMARY ====================
        elements.append(Paragraph("Executive Summary", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        # Calculate sentiment
        all_sentiments = [item.get('sentiment', 0) for item in all_menu]
        avg_sentiment = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0
        
        # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
        sent_label = "Excellent" if avg_sentiment >= 0.8 else "Positive" if avg_sentiment >= 0.6 else "Neutral" if avg_sentiment >= 0 else "Needs Attention"
        sent_color = POSITIVE if avg_sentiment >= 0.6 else WARNING if avg_sentiment >= 0 else NEGATIVE
        sent_bg = POSITIVE_LIGHT if avg_sentiment >= 0.6 else WARNING_LIGHT if avg_sentiment >= 0 else NEGATIVE_LIGHT
        
        # Sentiment box
        sent_data = [[f"Overall Sentiment: {avg_sentiment:+.2f}", sent_label]]
        sent_table = Table(sent_data, colWidths=[3.5*inch, 2*inch])
        sent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), sent_bg),
            ('TEXTCOLOR', (0, 0), (-1, -1), sent_color),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 2, sent_color),
        ]))
        elements.append(sent_table)
        elements.append(Spacer(1, 15))
        
        # Key highlights
        elements.append(Paragraph("Key Highlights", styles['RIASubHeader']))
        top_items = sorted(all_menu, key=lambda x: x.get('sentiment', 0), reverse=True)[:3]
        if top_items:
            elements.append(Paragraph("✅ <b>Top Performing Items:</b>", styles['RIABody']))
            for item in top_items:
                elements.append(Paragraph(f"    • {item.get('name', '?').title()} (sentiment: {item.get('sentiment', 0):+.2f})", styles['RIABullet']))
        
        # NEW threshold: < 0 for concerns
        concern_items = [i for i in all_menu if i.get('sentiment', 0) < 0]
        if concern_items:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("⚠️ <b>Items Needing Attention:</b>", styles['RIABody']))
            for item in sorted(concern_items, key=lambda x: x.get('sentiment', 0))[:3]:
                elements.append(Paragraph(f"    • {item.get('name', '?').title()} (sentiment: {item.get('sentiment', 0):+.2f})", styles['RIABullet']))
        
        elements.append(Spacer(1, 15))
        
        # Summary stats - NEW thresholds
        positive = len([i for i in all_menu if i.get('sentiment', 0) >= 0.6])
        neutral = len([i for i in all_menu if 0 <= i.get('sentiment', 0) < 0.6])
        negative = len([i for i in all_menu if i.get('sentiment', 0) < 0])
        
        summary_data = [
            ['Metric', 'Value', 'Details'],
            ['Reviews Analyzed', str(len(trend_data)), f'From {source}'],
            ['Menu Items', str(len(all_menu)), f'{len(food_items)} food, {len(drinks)} drinks'],
            ['🟢 Positive', str(positive), 'Sentiment ≥ 0.6'],
            ['🟡 Neutral', str(neutral), 'Sentiment 0 to 0.59'],
            ['🔴 Negative', str(negative), 'Sentiment < 0'],
        ]
        summary_table = Table(summary_data, colWidths=[2*inch, 1.3*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BACKGROUND]),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        elements.append(summary_table)
        elements.append(PageBreak())
        
        # ==================== MENU ANALYSIS ====================
        elements.append(Paragraph("Menu Performance Analysis", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        if all_menu:
            elements.append(Paragraph(
                f"Analysis of <b>{len(all_menu)}</b> menu items ({len(food_items)} food, {len(drinks)} drinks) based on {len(trend_data)} customer reviews.",
                styles['RIABody']
            ))
            elements.append(Spacer(1, 10))
            
            sorted_menu = sorted(all_menu, key=lambda x: x.get('mention_count', 0), reverse=True)[:20]
            menu_data = [['#', 'Item', 'Sentiment', 'Mentions', 'Status']]
            for i, item in enumerate(sorted_menu, 1):
                sentiment = item.get('sentiment', 0)
                # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
                status = '✓ Positive' if sentiment >= 0.6 else '~ Neutral' if sentiment >= 0 else '✗ Negative'
                menu_data.append([str(i), item.get('name', '?').title()[:22], f"{sentiment:+.2f}", str(item.get('mention_count', 0)), status])
            
            menu_table = Table(menu_data, colWidths=[0.4*inch, 2.2*inch, 1*inch, 0.9*inch, 1.1*inch])
            menu_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), POSITIVE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BACKGROUND]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ]))
            elements.append(menu_table)
        elements.append(Spacer(1, 20))
        
        # ==================== ASPECT ANALYSIS ====================
        elements.append(Paragraph("Customer Experience Aspects", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        if aspect_list:
            sorted_aspects = sorted(aspect_list, key=lambda x: x.get('mention_count', 0), reverse=True)[:20]
            aspect_data = [['#', 'Aspect', 'Sentiment', 'Mentions', 'Status']]
            for i, aspect in enumerate(sorted_aspects, 1):
                sentiment = aspect.get('sentiment', 0)
                # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
                status = '✓ Strength' if sentiment >= 0.6 else '~ Neutral' if sentiment >= 0 else '✗ Weakness'
                aspect_data.append([str(i), aspect.get('name', '?').title()[:22], f"{sentiment:+.2f}", str(aspect.get('mention_count', 0)), status])
            
            aspect_table = Table(aspect_data, colWidths=[0.4*inch, 2.2*inch, 1*inch, 0.9*inch, 1.1*inch])
            aspect_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), WARNING),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BACKGROUND]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ]))
            elements.append(aspect_table)
        elements.append(PageBreak())
        
        # ==================== CHEF INSIGHTS ====================
        elements.append(Paragraph("🍳 Chef Insights", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        chef_data = insights.get('chef', {})
        if chef_data:
            if chef_data.get('summary'):
                elements.append(Paragraph("Summary", styles['RIASubHeader']))
                elements.append(Paragraph(str(chef_data['summary']), styles['RIABody']))
            
            if chef_data.get('strengths'):
                elements.append(Paragraph("✅ Strengths", styles['RIASubHeader']))
                strengths = chef_data['strengths']
                if isinstance(strengths, list):
                    for s in strengths[:8]:  # Show up to 8 strengths
                        text = s.get('action', str(s)) if isinstance(s, dict) else str(s)
                        elements.append(Paragraph(f"• {text}", styles['RIABullet']))
            
            if chef_data.get('concerns'):
                elements.append(Paragraph("⚠️ Areas of Concern", styles['RIASubHeader']))
                concerns = chef_data['concerns']
                if isinstance(concerns, list):
                    for c in concerns[:5]:  # Show up to 5 concerns
                        text = c.get('action', str(c)) if isinstance(c, dict) else str(c)
                        elements.append(Paragraph(f"• {text}", styles['RIABullet']))
            
            if chef_data.get('recommendations'):
                elements.append(Paragraph("💡 Recommendations", styles['RIASubHeader']))
                recs = chef_data['recommendations']
                if isinstance(recs, list):
                    for r in recs[:8]:  # Show up to 8 recommendations
                        if isinstance(r, dict):
                            priority = r.get('priority', 'medium').lower()
                            action = r.get('action', str(r))
                            style_name = 'RIAPriorityHigh' if priority == 'high' else 'RIAPriorityMedium' if priority == 'medium' else 'RIAPriorityLow'
                            elements.append(Paragraph(f"[{priority.upper()}] {action}", styles[style_name]))
                        else:
                            elements.append(Paragraph(f"• {r}", styles['RIABullet']))
        else:
            elements.append(Paragraph("Chef insights will be available after full analysis.", styles['RIABody']))
        
        elements.append(Spacer(1, 20))
        
        # ==================== MANAGER INSIGHTS ====================
        elements.append(Paragraph("📊 Manager Insights", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        manager_data = insights.get('manager', {})
        if manager_data:
            if manager_data.get('summary'):
                elements.append(Paragraph("Summary", styles['RIASubHeader']))
                elements.append(Paragraph(str(manager_data['summary']), styles['RIABody']))
            
            if manager_data.get('strengths'):
                elements.append(Paragraph("✅ Operational Strengths", styles['RIASubHeader']))
                strengths = manager_data['strengths']
                if isinstance(strengths, list):
                    for s in strengths[:8]:  # Show up to 8 strengths
                        text = s.get('action', str(s)) if isinstance(s, dict) else str(s)
                        elements.append(Paragraph(f"• {text}", styles['RIABullet']))
            
            if manager_data.get('concerns'):
                elements.append(Paragraph("⚠️ Operational Concerns", styles['RIASubHeader']))
                concerns = manager_data['concerns']
                if isinstance(concerns, list):
                    for c in concerns[:5]:  # Show up to 5 concerns
                        text = c.get('action', str(c)) if isinstance(c, dict) else str(c)
                        elements.append(Paragraph(f"• {text}", styles['RIABullet']))
            
            if manager_data.get('recommendations'):
                elements.append(Paragraph("💡 Action Items", styles['RIASubHeader']))
                recs = manager_data['recommendations']
                if isinstance(recs, list):
                    for r in recs[:8]:  # Show up to 8 recommendations
                        if isinstance(r, dict):
                            priority = r.get('priority', 'medium').lower()
                            action = r.get('action', str(r))
                            style_name = 'RIAPriorityHigh' if priority == 'high' else 'RIAPriorityMedium' if priority == 'medium' else 'RIAPriorityLow'
                            elements.append(Paragraph(f"[{priority.upper()}] {action}", styles[style_name]))
                        else:
                            elements.append(Paragraph(f"• {r}", styles['RIABullet']))
        else:
            elements.append(Paragraph("Manager insights will be available after full analysis.", styles['RIABody']))
        
        elements.append(PageBreak())
        
        # ==================== CUSTOMER FEEDBACK HIGHLIGHTS ====================
        elements.append(Paragraph("Customer Feedback Highlights", styles['RIASectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=5, spaceAfter=15))
        
        positive_reviews = []
        negative_reviews = []
        
        # Extract sample reviews from menu items and aspects (they have related_reviews with text)
        all_related_reviews = []
        
        # Get reviews from menu items
        for item in all_menu:
            for r in item.get('related_reviews', [])[:2]:
                if isinstance(r, dict):
                    text = r.get('review_text', r.get('text', ''))
                else:
                    text = str(r)
                if text and len(text) > 30:
                    sentiment = item.get('sentiment', 0)
                    all_related_reviews.append({'text': text, 'sentiment': sentiment})
        
        # Get reviews from aspects
        for aspect in aspect_list:
            for r in aspect.get('related_reviews', [])[:2]:
                if isinstance(r, dict):
                    text = r.get('review_text', r.get('text', ''))
                else:
                    text = str(r)
                if text and len(text) > 30:
                    sentiment = aspect.get('sentiment', 0)
                    all_related_reviews.append({'text': text, 'sentiment': sentiment})
        
        # Sort by sentiment to get best positive and worst negative
        for review in sorted(all_related_reviews, key=lambda x: x['sentiment'], reverse=True):
            text = review['text']
            # NEW thresholds: >= 0.6 for positive, < 0 for negative
            if review['sentiment'] >= 0.6 and len(positive_reviews) < 3:
                positive_reviews.append(text[:180])
            elif review['sentiment'] < 0 and len(negative_reviews) < 3:
                negative_reviews.append(text[:180])
        
        elements.append(Paragraph("✅ Positive Feedback", styles['RIASubHeader']))
        if positive_reviews:
            for review in positive_reviews:
                elements.append(Paragraph(f'"{review}..."', styles['RIAQuote']))
        else:
            elements.append(Paragraph("Detailed positive feedback samples not available.", styles['RIABody']))
        
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("⚠️ Critical Feedback", styles['RIASubHeader']))
        if negative_reviews:
            for review in negative_reviews:
                elements.append(Paragraph(f'"{review}..."', styles['RIAQuote']))
        else:
            elements.append(Paragraph("No significant negative feedback identified. Great job!", styles['RIABody']))
        
        # ==================== FOOTER ====================
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=10, spaceAfter=10))
        elements.append(Paragraph(f"Report generated for {restaurant_name}", styles['RIAFooter']))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['RIAFooter']))
        elements.append(Paragraph("Restaurant Intelligence Agent • Powered by Claude AI", styles['RIAFooter']))
        elements.append(Paragraph("© 2025 - Built for Anthropic MCP Hackathon", styles['RIAFooter']))
        
        # Build PDF
        doc.build(elements)
        print(f"[PDF] Successfully generated professional report: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[PDF] Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_pdf(state: dict) -> Optional[str]:
    """Generate PDF and return path for download."""
    if not state:
        print("[PDF] No state for download")
        return None
    
    pdf_path = generate_pdf_report(state)
    print(f"[PDF] Download path: {pdf_path}")
    return pdf_path


def send_email_report(email: str, state: dict) -> str:
    """Send PDF report via email."""
    if not state:
        return "❌ No analysis data available. Please run analysis first."
    
    if not email or '@' not in email:
        return "❌ Please enter a valid email address."
    
    if not SMTP_USER or not SMTP_PASSWORD:
        return "⚠️ Email sending is not configured. Please download the PDF instead."
    
    try:
        pdf_path = generate_pdf_report(state)
        if not pdf_path:
            return "❌ Failed to generate PDF report."
        
        restaurant_name = state.get('restaurant_name', 'Restaurant')
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = f"Restaurant Intelligence Report - {restaurant_name}"
        
        body = f"""
Hello,

Please find attached your Restaurant Intelligence Report for {restaurant_name}.

This report includes:
- Executive Summary
- Menu Performance Analysis
- Customer Experience Aspects
- Chef & Manager Insights

Generated by Restaurant Intelligence Agent
Powered by Claude AI
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{restaurant_name}_report.pdf"')
        msg.attach(part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        try:
            os.remove(pdf_path)
        except:
            pass
        
        return f"✅ Report sent successfully to **{email}**!"
    
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


# ============================================================================
# RAG Q&A FUNCTIONS - FIXED PROXIES ERROR
# ============================================================================

FOOD_WORDS = {'food', 'dish', 'dishes', 'menu', 'eat', 'taste', 'flavor', 'best', 'try', 'order', 'recommend'}
SERVICE_WORDS = {'service', 'staff', 'waiter', 'server', 'waitress', 'attentive', 'friendly', 'rude', 'slow'}
AMBIANCE_WORDS = {'ambiance', 'atmosphere', 'vibe', 'decor', 'noise', 'loud', 'quiet', 'romantic', 'cozy'}


def find_relevant_reviews(question: str, state: dict, top_k: int = 8) -> List[str]:
    """Find relevant reviews for the question using menu/aspect related_reviews."""
    if not state:
        return []
    
    q = question.lower()
    q_words = set(q.split())
    
    menu = state.get('menu_analysis', {})
    aspects = state.get('aspect_analysis', {})
    
    all_items = menu.get('food_items', []) + menu.get('drinks', [])
    all_aspects = aspects.get('aspects', [])
    
    relevant_reviews = []
    
    # Search in menu items
    for item in all_items:
        name = item.get('name', '').lower()
        if name in q or any(w in name for w in q_words):
            for r in item.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text not in relevant_reviews and len(text) > 20:
                    relevant_reviews.append(text)
    
    # Search in aspects
    for aspect in all_aspects:
        name = aspect.get('name', '').lower()
        if name in q or any(w in name for w in q_words):
            for r in aspect.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text not in relevant_reviews and len(text) > 20:
                    relevant_reviews.append(text)
    
    # Category-based search
    if q_words & SERVICE_WORDS:
        for aspect in all_aspects:
            if any(w in aspect.get('name', '').lower() for w in ['service', 'staff', 'wait']):
                for r in aspect.get('related_reviews', [])[:2]:
                    text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                    if text not in relevant_reviews:
                        relevant_reviews.append(text)
    
    if q_words & FOOD_WORDS:
        sorted_items = sorted(all_items, key=lambda x: x.get('sentiment', 0), reverse=True)
        for item in sorted_items[:3]:
            for r in item.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text not in relevant_reviews:
                    relevant_reviews.append(text)
    
    # Fallback: if still no reviews, gather from all items/aspects
    if not relevant_reviews:
        # Collect from top items by mentions
        sorted_items = sorted(all_items, key=lambda x: x.get('mention_count', 0), reverse=True)
        for item in sorted_items[:5]:
            for r in item.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text and len(text) > 20 and text not in relevant_reviews:
                    relevant_reviews.append(text)
        
        # Also from top aspects
        sorted_aspects = sorted(all_aspects, key=lambda x: x.get('mention_count', 0), reverse=True)
        for aspect in sorted_aspects[:5]:
            for r in aspect.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text and len(text) > 20 and text not in relevant_reviews:
                    relevant_reviews.append(text)
    
    return relevant_reviews[:top_k]


def generate_answer_with_claude(question: str, reviews: list, restaurant_name: str) -> str:
    """
    Generate answer using Claude - FIXED PROXIES ERROR.
    Uses direct HTTP request as fallback.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ API key not configured for AI-powered answers."
    
    reviews_text = ""
    for i, review in enumerate(reviews[:8], 1):
        text = str(review)[:300] + "..." if len(str(review)) > 300 else str(review)
        reviews_text += f"\n[Review {i}]: {text}\n"
    
    prompt = f"""You are a helpful assistant answering questions about {restaurant_name} based on customer reviews.

CUSTOMER REVIEWS:
{reviews_text}

QUESTION: {question}

Instructions:
- Answer based ONLY on the reviews provided above
- Be specific - mention actual dishes, staff behavior, or details from the reviews
- If reviews mention specific examples, include them
- Keep your answer helpful and concise (3-5 sentences)
- If the reviews don't contain relevant information, say so honestly
- Provide BALANCED answers - mention both pros AND cons when relevant
- If customers have mixed opinions, acknowledge both positive and negative feedback
- Don't oversell or undersell - be honest about what customers actually said

Answer:"""

    # Try Anthropic SDK first
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except TypeError as e:
        if 'proxies' in str(e):
            print("[RAG] Anthropic SDK proxies error, using HTTP fallback...")
            # Fallback to direct HTTP request
            try:
                import httpx
                
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 400,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['content'][0]['text']
                else:
                    return f"⚠️ API error: {response.status_code}"
            except Exception as http_e:
                return f"⚠️ Could not generate answer: {str(http_e)}"
        else:
            return f"⚠️ Could not generate answer: {str(e)}"
    except Exception as e:
        return f"⚠️ Could not generate answer: {str(e)}"


def answer_question(question: str, state: dict) -> str:
    """RAG Q&A function."""
    if not question or not question.strip():
        return "❓ Please type a question above."
    if not state:
        return "⚠️ Please analyze a restaurant first."
    
    restaurant = state.get("restaurant_name", "the restaurant")
    relevant_reviews = find_relevant_reviews(question, state, top_k=8)
    
    if not relevant_reviews:
        return f"""**Q:** {question}

**A:** I couldn't find relevant reviews to answer this question.

💡 **Try asking:**
• "What are the best dishes?"
• "How is the service?"
• "Is it good for a date?"
• "What do customers like most?"
"""
    
    answer = generate_answer_with_claude(question, relevant_reviews, restaurant)
    
    return f"""**Q:** {question}

**A:** {answer}

---
*🤖 Based on {len(relevant_reviews)} customer reviews*"""


EXAMPLE_QUESTIONS = [
    "What are the best dishes to order?",
    "How is the service quality?",
    "Is this restaurant good for a date?",
    "What do people say about the ambiance?",
    "Is the food worth the price?",
    "Any complaints about wait times?",
]


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_restaurant(url: str, review_count: int):
    """Main analysis function - calls Modal API with robust error handling."""
    
    empty = {}
    default_summary = "Run analysis to see performance overview."
    default_insight = "Run analysis to see insights."
    default_detail = "Select an item to see details."
    empty_dropdown = gr.update(choices=[], value=None)
    
    if not url or not url.strip():
        return (
            "❌ **Error:** Please enter a restaurant URL.",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    
    url = url.strip()
    platform = detect_platform(url)
    
    if platform == "unknown":
        return (
            "❌ **Error:** URL not recognized. Please use OpenTable or Google Maps URL.",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    
    restaurant_name = extract_restaurant_name(url)
    platform_emoji = get_platform_emoji(platform)
    
    try:
        print(f"[ANALYZE] {platform_emoji} Analyzing {restaurant_name} from {platform}...")
        print(f"[ANALYZE] Calling Modal API: {MODAL_API_URL}/analyze")
        
        # Use a session with retry logic
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST"]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        # Make request with streaming disabled for stability
        response = session.post(
            f"{MODAL_API_URL}/analyze",
            json={"url": url, "max_reviews": review_count},
            timeout=(30, 2100),  # 30s connect, 600s read (10 min)
            headers={"Connection": "keep-alive"}
        )
        
        print(f"[ANALYZE] Response status: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text[:500] if response.text else "No error details"
            print(f"[ANALYZE] Error response: {error_text}")
            return (
                f"❌ **API Error ({response.status_code}):** {error_text[:200]}",
                None, "No trend data available.",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        # Parse response
        try:
            data = response.json()
            print(f"[ANALYZE] Response received, success={data.get('success')}")
        except Exception as json_err:
            print(f"[ANALYZE] JSON parse error: {json_err}")
            return (
                f"❌ **Parse Error:** Could not parse API response. Try again.",
                None, "No trend data available.",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        if not data.get("success"):
            return (
                f"❌ **Analysis Failed:** {data.get('error', 'Unknown error')}",
                None, "No trend data available.",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        menu = data.get('menu_analysis', {})
        aspects = data.get('aspect_analysis', {})
        insights = data.get('insights', {})
        
        # Use slim trend_data (pre-calculated sentiment, no text)
        # Falls back to raw_reviews for backward compatibility
        trend_data = data.get('trend_data', data.get('raw_reviews', []))
        
        food_items = menu.get('food_items', [])
        drinks = menu.get('drinks', [])
        aspect_list = aspects.get('aspects', [])
        all_menu = food_items + drinks
        
        print(f"[ANALYZE] Data extracted: {len(all_menu)} menu items, {len(aspect_list)} aspects, {len(trend_data)} trend points")
        
        state = {
            "menu_analysis": menu,
            "aspect_analysis": aspects,
            "insights": insights,
            "restaurant_name": restaurant_name,
            "trend_data": trend_data,  # Store for PDF if needed
            "source": platform
        }
        
        trend_chart = generate_trend_chart(trend_data, restaurant_name)
        trend_insight = generate_trend_insight(trend_data, restaurant_name)
        
        # Use improved detailed summaries
        menu_summary = translate_menu_performance(menu, restaurant_name)
        aspect_summary = translate_aspect_performance(aspects, restaurant_name)
        
        chef_insights = format_insights(insights.get('chef', {}), 'chef')
        manager_insights = format_insights(insights.get('manager', {}), 'manager')
        
        chef_chart = generate_chart(all_menu, f"Menu Item Sentiment (Top 10 by Mentions)")
        manager_chart = generate_chart(aspect_list, f"Aspect Sentiment (Top 10 by Mentions)")
        
        chef_sorted = sorted(all_menu, key=lambda x: x.get('mention_count', 0), reverse=True)
        manager_sorted = sorted(aspect_list, key=lambda x: x.get('mention_count', 0), reverse=True)
        
        chef_choices = [f"{i.get('name', '?')} ({i.get('mention_count', 0)})" for i in chef_sorted]
        manager_choices = [f"{a.get('name', '?')} ({a.get('mention_count', 0)})" for a in manager_sorted]
        
        chef_dropdown_update = gr.update(choices=chef_choices, value=None)
        manager_dropdown_update = gr.update(choices=manager_choices, value=None)
        
        status = f"""✅ **Analysis Complete for {restaurant_name}!** {platform_emoji}

**📊 Summary:**
• Source: **{platform.replace('_', ' ').title()}**
• Reviews analyzed: **{len(trend_data)}**
• Menu items found: **{len(all_menu)}** ({len(food_items)} food, {len(drinks)} drinks)
• Aspects discovered: **{len(aspect_list)}**

👇 **Explore the tabs below for detailed insights!**
"""
        
        print(f"[ANALYZE] ✅ Analysis complete for {restaurant_name}")
        
        return (
            status,
            trend_chart, trend_insight,
            menu_summary, chef_chart, chef_insights, chef_dropdown_update, default_detail,
            aspect_summary, manager_chart, manager_insights, manager_dropdown_update, default_detail,
            state
        )
        
    except requests.exceptions.Timeout:
        print("[ANALYZE] ❌ Timeout error")
        return (
            "❌ **Timeout:** Request took too long. Try with fewer reviews (50-100).",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    except requests.exceptions.ConnectionError as ce:
        print(f"[ANALYZE] ❌ Connection error: {ce}")
        return (
            "❌ **Connection Error:** Could not reach analysis server. Please try again in a moment.",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ANALYZE] ❌ Exception: {e}")
        return (
            f"❌ **Error:** {str(e)[:200]}",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )


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

**Supported Platforms:** 🍽️ OpenTable | 🗺️ Google Maps
        """)
        
        gr.Markdown("---")
        
        # ==================== INPUT SECTION ====================
        gr.Markdown("### 📍 Enter Restaurant Details")
        
        with gr.Row():
            with gr.Column(scale=5):
                url_input = gr.Textbox(
                    label="Restaurant URL",
                    placeholder="Paste OpenTable or Google Maps URL",
                    info="Supports: opentable.com, google.com/maps",
                    max_lines=1
                )
            with gr.Column(scale=1):
                review_count = gr.Dropdown(
                    choices=[50, 100, 200, 500, 1000],
                    value=100,
                    label="Reviews",
                    info="More = better insights"
                )
            with gr.Column(scale=1):
                analyze_btn = gr.Button("🚀 Analyze", variant="primary", size="lg")
        
        status_box = gr.Markdown(
            value="*Enter a restaurant URL above and click **Analyze** to start.*"
        )
        
        analysis_state = gr.State(value={})
        
        gr.Markdown("---")
        
        # ==================== RESULTS TABS ====================
        with gr.Tabs():
            
            # ========== TRENDS TAB ==========
            with gr.Tab("📈 Trends"):
                gr.Markdown("""
### Rating vs Sentiment Over Time

This chart reveals the **disconnect** between what customers **rate** (stars) 
vs what they **say** (sentiment).
                """)
                trend_chart = gr.Image(label="Rating vs Sentiment Trend", height=450)
                gr.Markdown("---")
                trend_insight = gr.Markdown(value="*Run analysis to see trend insights.*")
            
            # ========== CHEF TAB ==========
            with gr.Tab("🍳 Chef Insights"):
                chef_summary = gr.Markdown(value="*Run analysis to see menu performance overview.*")
                gr.Markdown("---")
                with gr.Row():
                    with gr.Column(scale=1):
                        chef_chart = gr.Image(label="Menu Sentiment Chart", height=420)
                    with gr.Column(scale=1):
                        chef_insights = gr.Markdown(value="*AI-generated insights will appear here.*")
                gr.Markdown("---")
                gr.Markdown("**🔍 Drill Down:** Select a menu item to see detailed feedback")
                chef_dropdown = gr.Dropdown(choices=[], label="Select Menu Item", interactive=True)
                chef_detail = gr.Markdown(value="*Select an item above to see detailed feedback.*")
            
            # ========== MANAGER TAB ==========
            with gr.Tab("📊 Manager Insights"):
                manager_summary = gr.Markdown(value="*Run analysis to see aspect performance overview.*")
                gr.Markdown("---")
                with gr.Row():
                    with gr.Column(scale=1):
                        manager_chart = gr.Image(label="Aspect Sentiment Chart", height=420)
                    with gr.Column(scale=1):
                        manager_insights = gr.Markdown(value="*AI-generated insights will appear here.*")
                gr.Markdown("---")
                gr.Markdown("**🔍 Drill Down:** Select an aspect to see detailed feedback")
                manager_dropdown = gr.Dropdown(choices=[], label="Select Aspect", interactive=True)
                manager_detail = gr.Markdown(value="*Select an aspect above to see detailed feedback.*")
            
            # ========== Q&A TAB ==========
            with gr.Tab("💬 Ask Questions"):
                gr.Markdown("""
### Ask Questions About the Reviews

Get AI-powered answers based on actual customer feedback.
                """)
                gr.Markdown("**💡 Try these example questions:**")
                with gr.Row():
                    for q in EXAMPLE_QUESTIONS[:3]:
                        gr.Button(q, size="sm")
                
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., What do customers think about the pasta dishes?",
                    lines=2
                )
                with gr.Row():
                    ask_btn = gr.Button("🔍 Ask", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
                answer_output = gr.Markdown(value="*Analyze a restaurant first, then ask questions.*")
                clear_btn.click(fn=lambda: ("", "*Ask a question above.*"), outputs=[question_input, answer_output])
            
            # ========== EXPORT TAB ==========
            with gr.Tab("📤 Export Report"):
                gr.Markdown("""
### Export Your Analysis

Download a comprehensive PDF report or have it emailed directly to you.
                """)
                
                gr.Markdown("---")
                
                gr.Markdown("#### 📥 Download PDF Report")
                gr.Markdown("Get a professional PDF with all analysis results, charts, and recommendations.")
                
                with gr.Row():
                    download_btn = gr.Button("📄 Generate & Download PDF", variant="primary", size="lg")
                
                pdf_output = gr.File(label="Download Your Report", visible=True)
                download_status = gr.Markdown(value="")
                
                gr.Markdown("---")
                
                gr.Markdown("#### 📧 Email Report")
                gr.Markdown("Enter your email address to receive the PDF report directly in your inbox.")
                
                with gr.Row():
                    email_input = gr.Textbox(
                        label="Email Address",
                        placeholder="your@email.com",
                        max_lines=1,
                        scale=3
                    )
                    send_btn = gr.Button("📨 Send Report", variant="secondary", scale=1)
                
                email_status = gr.Markdown(value="")
        
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
                trend_chart, trend_insight,
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
        
        download_btn.click(
            fn=download_pdf,
            inputs=[analysis_state],
            outputs=pdf_output
        )
        
        send_btn.click(
            fn=send_email_report,
            inputs=[email_input, analysis_state],
            outputs=email_status
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