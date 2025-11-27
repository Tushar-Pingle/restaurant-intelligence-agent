"""
Restaurant Intelligence Agent - Enhanced Gradio 6 Interface
Professional UI with cards, plain English summaries, polished layout

Hackathon: Anthropic MCP 1st Birthday - Track 2 (Productivity)
Author: Tushar Pingle

VERSION 3.0 FEATURES:
1. Multi-platform support (OpenTable + Google Maps)
2. PDF Report Export (download + email)
3. All previous fixes and refinements
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
    
    # "Dined X day(s) ago" or "X day(s) ago"
    day_match = re.search(r'(\d+)\s*days?\s*ago', date_str)
    if day_match:
        return today - timedelta(days=int(day_match.group(1)))
    
    # "X week(s) ago"
    week_match = re.search(r'(\d+)\s*weeks?\s*ago', date_str)
    if week_match:
        return today - timedelta(weeks=int(week_match.group(1)))
    
    # "X month(s) ago"
    month_match = re.search(r'(\d+)\s*months?\s*ago', date_str)
    if month_match:
        return today - timedelta(days=int(month_match.group(1)) * 30)
    
    if 'yesterday' in date_str:
        return today - timedelta(days=1)
    if 'today' in date_str:
        return today
    
    # Simple formats
    simple_day = re.search(r'^(\d+)\s*day', date_str)
    if simple_day:
        return today - timedelta(days=int(simple_day.group(1)))
    
    simple_week = re.search(r'^(\d+)\s*week', date_str)
    if simple_week:
        return today - timedelta(weeks=int(simple_week.group(1)))
    
    return None


def calculate_review_sentiment(text: str) -> float:
    """Simple sentiment calculation from review text."""
    if not text:
        return 0.0
    text = str(text).lower()
    
    positive = ['amazing', 'excellent', 'fantastic', 'great', 'awesome', 'delicious', 
                'perfect', 'outstanding', 'loved', 'beautiful', 'fresh', 'friendly', 
                'best', 'wonderful', 'incredible', 'superb', 'exceptional']
    negative = ['terrible', 'horrible', 'awful', 'bad', 'worst', 'disappointing', 
                'poor', 'overpriced', 'slow', 'rude', 'cold', 'bland', 'mediocre',
                'disgusting', 'inedible', 'undercooked', 'overcooked']
    
    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)
    
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


def generate_trend_chart(raw_reviews: List[Dict], restaurant_name: str) -> Optional[str]:
    """Generate Rating vs Sentiment trend chart."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    if not raw_reviews or len(raw_reviews) < 3:
        return None
    
    # Parse and prepare data
    dated_reviews = []
    for r in raw_reviews:
        if not isinstance(r, dict):
            continue
        date = parse_opentable_date(r.get('date', ''))
        if date:
            rating = float(r.get('rating', 0) or r.get('overall_rating', 0) or 0)
            text = r.get('text', '') or r.get('review_text', '')
            dated_reviews.append({
                'date': date,
                'rating': rating if rating > 0 else 3.5,
                'sentiment': calculate_review_sentiment(text)
            })
    
    # Fallback: synthetic dates
    if len(dated_reviews) < 3 and len(raw_reviews) >= 3:
        dated_reviews = []
        for i, r in enumerate(raw_reviews):
            if not isinstance(r, dict):
                continue
            rating = float(r.get('rating', 0) or r.get('overall_rating', 0) or 3.5)
            text = r.get('text', '') or r.get('review_text', '')
            dated_reviews.append({
                'date': datetime.now() - timedelta(days=i),
                'rating': rating if rating > 0 else 3.5,
                'sentiment': calculate_review_sentiment(text)
            })
    
    if len(dated_reviews) < 3:
        return None
    
    # Sort and group by week
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
    
    # Dark theme
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
        
        ax1.set_title(f'📊 Rating vs Sentiment Trend', fontsize=15, fontweight='bold', color=TEXT, pad=20)
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


def generate_trend_insight(raw_reviews: List[Dict], restaurant_name: str) -> str:
    """Generate text insight from trend data."""
    if not raw_reviews or len(raw_reviews) < 3:
        return "Not enough data to analyze trends (need 3+ reviews)."
    
    ratings = []
    sentiments = []
    for r in raw_reviews:
        if isinstance(r, dict):
            rating = float(r.get('rating', 0) or r.get('overall_rating', 0) or 0)
            if rating > 0:
                ratings.append(rating)
            text = r.get('text', '') or r.get('review_text', '')
            sentiments.append(calculate_review_sentiment(text))
    
    if not ratings:
        return "No rating data available."
    
    avg_rating = sum(ratings) / len(ratings)
    avg_sentiment = sum(sentiments) / len(sentiments)
    
    insight = f"**{restaurant_name}** has an average rating of **{avg_rating:.1f} stars** "
    
    if avg_sentiment > 0.3:
        insight += "with **positive sentiment**. "
        if avg_rating >= 4.0:
            insight += "✅ Ratings and sentiment are aligned!"
        else:
            insight += "🤔 Sentiment is positive but ratings are moderate."
    elif avg_sentiment < -0.1:
        insight += "but with **concerning sentiment**. "
        if avg_rating >= 4.0:
            insight += "⚠️ **Warning:** High ratings but negative sentiment detected."
        else:
            insight += "❌ Both ratings and sentiment suggest issues."
    else:
        insight += "with **neutral sentiment**. 📊 Reviews are mixed."
    
    return insight


# ============================================================================
# HELPER FUNCTIONS
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
    """Create plain English summary of menu performance."""
    food_items = menu.get('food_items', [])
    drinks = menu.get('drinks', [])
    all_items = food_items + drinks
    
    if not all_items:
        return f"*No menu data available for {restaurant_name} yet.*"
    
    stars = [i for i in all_items if i.get('sentiment', 0) > 0.5]
    concerns = [i for i in all_items if i.get('sentiment', 0) < -0.2]
    
    summary = f"**{restaurant_name}** has **{len(all_items)}** menu items analyzed "
    summary += f"({len(food_items)} food, {len(drinks)} drinks).\n\n"
    
    if stars:
        top = sorted(stars, key=lambda x: x.get('sentiment', 0), reverse=True)[:3]
        summary += "🌟 **Customer Favorites:** " + ", ".join([i.get('name', '?') for i in top]) + "\n\n"
    
    if concerns:
        summary += "⚠️ **Needs Attention:** " + ", ".join([i.get('name', '?') for i in concerns[:3]]) + "\n"
    
    return summary


def translate_aspect_performance(aspects: dict, restaurant_name: str) -> str:
    """Create plain English summary of aspect performance."""
    aspect_list = aspects.get('aspects', [])
    
    if not aspect_list:
        return f"*No aspect data available for {restaurant_name} yet.*"
    
    strengths = [a for a in aspect_list if a.get('sentiment', 0) > 0.3]
    weaknesses = [a for a in aspect_list if a.get('sentiment', 0) < -0.1]
    
    summary = f"**{restaurant_name}** was evaluated on **{len(aspect_list)}** aspects.\n\n"
    
    if strengths:
        top = sorted(strengths, key=lambda x: x.get('sentiment', 0), reverse=True)[:3]
        summary += "💪 **Strengths:** " + ", ".join([a.get('name', '?').title() for a in top]) + "\n\n"
    
    if weaknesses:
        summary += "📉 **Areas to Improve:** " + ", ".join([a.get('name', '?').title() for a in weaknesses[:3]]) + "\n"
    
    return summary


def generate_chart(items: list, title: str) -> Optional[str]:
    """Generate sentiment chart - top 10 by mentions."""
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
        
        sorted_items = sorted(items, key=lambda x: x.get('mention_count', 0), reverse=True)[:10]
        
        names = [f"{item.get('name', '?')[:18]} ({item.get('mention_count', 0)})" for item in sorted_items]
        sentiments = [item.get('sentiment', 0) for item in sorted_items]
        
        colors = [POSITIVE if s > 0.3 else NEUTRAL if s > -0.3 else NEGATIVE for s in sentiments]
        
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
            # Try to extract from Google Maps URL
            if '/place/' in url:
                place = url.split('/place/')[1].split('/')[0]
                return place.replace('+', ' ').replace('%20', ' ')
        return "Restaurant"
    except:
        return "Restaurant"


def get_item_detail(item_name: str, state: dict) -> str:
    """Get details for a selected menu item."""
    if not item_name or not state:
        return "Select an item to see details."
    
    clean_name = item_name.split(' (')[0].strip().lower()
    menu = state.get('menu_analysis', {})
    all_items = menu.get('food_items', []) + menu.get('drinks', [])
    
    for item in all_items:
        if item.get('name', '').lower() == clean_name:
            sentiment = item.get('sentiment', 0)
            mentions = item.get('mention_count', 0)
            summary = item.get('summary', 'No detailed summary available.')
            
            emoji = "🟢" if sentiment > 0.3 else "🟡" if sentiment > -0.3 else "🔴"
            
            return f"""### {clean_name.title()}

{emoji} **Sentiment:** {sentiment:+.2f} | **Mentions:** {mentions}

**Customer Feedback:**
{summary}
"""
    return f"No details found for '{item_name}'."


def get_aspect_detail(aspect_name: str, state: dict) -> str:
    """Get details for a selected aspect."""
    if not aspect_name or not state:
        return "Select an aspect to see details."
    
    clean_name = aspect_name.split(' (')[0].strip().lower()
    aspects = state.get('aspect_analysis', {}).get('aspects', [])
    
    for aspect in aspects:
        if aspect.get('name', '').lower() == clean_name:
            sentiment = aspect.get('sentiment', 0)
            mentions = aspect.get('mention_count', 0)
            summary = aspect.get('summary', 'No detailed summary available.')
            
            emoji = "🟢" if sentiment > 0.3 else "🟡" if sentiment > -0.3 else "🔴"
            
            return f"""### {clean_name.title()}

{emoji} **Sentiment:** {sentiment:+.2f} | **Mentions:** {mentions}

**Customer Feedback:**
{summary}
"""
    return f"No details found for '{aspect_name}'."


# ============================================================================
# PDF GENERATION
# ============================================================================

def generate_pdf_report(state: dict) -> Optional[str]:
    """Generate PDF report from analysis state."""
    if not state:
        return None
    
    try:
        from src.reports.pdf_generator import generate_pdf_report as gen_pdf
        
        restaurant_name = state.get('restaurant_name', 'Restaurant')
        
        # Create report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = restaurant_name.lower().replace(" ", "_").replace("/", "_")[:30]
        output_path = os.path.join(tempfile.gettempdir(), f"{safe_name}_report_{timestamp}.pdf")
        
        pdf_path = gen_pdf(state, restaurant_name, output_path)
        return pdf_path
    
    except ImportError:
        # Fallback: simple text-based PDF
        return generate_simple_pdf(state)
    except Exception as e:
        print(f"PDF generation error: {e}")
        return None


def generate_simple_pdf(state: dict) -> Optional[str]:
    """Fallback: Generate simple PDF using basic reportlab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        restaurant_name = state.get('restaurant_name', 'Restaurant')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(tempfile.gettempdir(), f"report_{timestamp}.pdf")
        
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height - inch, "Restaurant Intelligence Report")
        
        c.setFont("Helvetica", 16)
        c.drawCentredString(width/2, height - 1.5*inch, restaurant_name)
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 2*inch, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        
        # Stats
        menu = state.get('menu_analysis', {})
        aspects = state.get('aspect_analysis', {})
        raw_reviews = state.get('raw_reviews', [])
        
        y = height - 3*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, y, "Summary Statistics:")
        
        y -= 0.3*inch
        c.setFont("Helvetica", 10)
        c.drawString(inch, y, f"• Reviews Analyzed: {len(raw_reviews)}")
        
        y -= 0.25*inch
        food_items = menu.get('food_items', [])
        drinks = menu.get('drinks', [])
        c.drawString(inch, y, f"• Menu Items: {len(food_items) + len(drinks)}")
        
        y -= 0.25*inch
        c.drawString(inch, y, f"• Aspects Analyzed: {len(aspects.get('aspects', []))}")
        
        c.save()
        return output_path
    except Exception as e:
        print(f"Simple PDF error: {e}")
        return None


def download_pdf(state: dict) -> Optional[str]:
    """Generate PDF and return path for download."""
    if not state:
        return None
    return generate_pdf_report(state)


def send_email_report(email: str, state: dict) -> str:
    """Send PDF report via email."""
    if not state:
        return "❌ No analysis data available. Please run analysis first."
    
    if not email or '@' not in email:
        return "❌ Please enter a valid email address."
    
    # Check if email is configured
    if not SMTP_USER or not SMTP_PASSWORD:
        return "⚠️ Email sending is not configured. Please download the PDF instead."
    
    try:
        # Generate PDF
        pdf_path = generate_pdf_report(state)
        if not pdf_path:
            return "❌ Failed to generate PDF report."
        
        restaurant_name = state.get('restaurant_name', 'Restaurant')
        
        # Create email
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
- Trend Analysis

Generated by Restaurant Intelligence Agent
Powered by Claude AI

Best regards,
Restaurant Intelligence Agent
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{restaurant_name}_report.pdf"')
        msg.attach(part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        # Clean up temp file
        try:
            os.remove(pdf_path)
        except:
            pass
        
        return f"✅ Report sent successfully to **{email}**!"
    
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


# ============================================================================
# RAG Q&A FUNCTIONS
# ============================================================================

FOOD_WORDS = {'food', 'dish', 'dishes', 'menu', 'eat', 'taste', 'flavor', 'best', 'try', 'order', 'recommend'}
SERVICE_WORDS = {'service', 'staff', 'waiter', 'server', 'waitress', 'attentive', 'friendly', 'rude', 'slow'}
AMBIANCE_WORDS = {'ambiance', 'atmosphere', 'vibe', 'decor', 'noise', 'loud', 'quiet', 'romantic', 'cozy'}


def find_relevant_reviews(question: str, state: dict, top_k: int = 6) -> List[str]:
    """Find relevant reviews for the question."""
    if not state:
        return []
    
    q = question.lower()
    q_words = set(q.split())
    
    menu = state.get('menu_analysis', {})
    aspects = state.get('aspect_analysis', {})
    
    all_items = menu.get('food_items', []) + menu.get('drinks', [])
    all_aspects = aspects.get('aspects', [])
    
    relevant_reviews = []
    
    for item in all_items:
        name = item.get('name', '').lower()
        if name in q or any(w in name for w in q_words):
            for r in item.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text not in relevant_reviews and len(text) > 20:
                    relevant_reviews.append(text)
    
    for aspect in all_aspects:
        name = aspect.get('name', '').lower()
        if name in q or any(w in name for w in q_words):
            for r in aspect.get('related_reviews', [])[:2]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if text not in relevant_reviews and len(text) > 20:
                    relevant_reviews.append(text)
    
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
    
    if not relevant_reviews:
        for item in all_items[:5]:
            for r in item.get('related_reviews', [])[:1]:
                text = r.get('review_text', str(r)) if isinstance(r, dict) else str(r)
                if len(text) > 20:
                    relevant_reviews.append(text)
    
    return relevant_reviews[:top_k]


def generate_answer_with_claude(question: str, reviews: list, restaurant_name: str) -> str:
    """Generate answer using Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ API key not configured."
    
    reviews_text = ""
    for i, review in enumerate(reviews[:6], 1):
        text = str(review)[:250] + "..." if len(str(review)) > 250 else str(review)
        reviews_text += f"\n[Review {i}]: {text}\n"
    
    prompt = f"""Answer about {restaurant_name} based on these reviews:

REVIEWS:
{reviews_text}

QUESTION: {question}

Answer concisely (2-4 sentences) based ONLY on the reviews above."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"⚠️ Could not generate answer: {str(e)}"


def answer_question(question: str, state: dict) -> str:
    """RAG Q&A function."""
    if not question or not question.strip():
        return "❓ Please type a question above."
    if not state:
        return "⚠️ Please analyze a restaurant first."
    
    restaurant = state.get("restaurant_name", "the restaurant")
    relevant_reviews = find_relevant_reviews(question, state, top_k=6)
    
    if not relevant_reviews:
        return f"""**Q:** {question}

**A:** I couldn't find relevant reviews.

💡 **Try asking:**
• "What are the best dishes?"
• "How is the service?"
• "Is it good for a date?"
"""
    
    answer = generate_answer_with_claude(question, relevant_reviews, restaurant)
    
    return f"""**Q:** {question}

**A:** {answer}

---
*🤖 AI-generated answer based on {len(relevant_reviews)} reviews*"""


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
    """Main analysis function - calls Modal API."""
    
    empty = {}
    default_summary = "Run analysis to see performance overview."
    default_insight = "Run analysis to see insights."
    default_detail = "Select an item to see details."
    empty_dropdown = gr.update(choices=[], value=None)
    
    # Validation
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
        
        response = requests.post(
            f"{MODAL_API_URL}/analyze",
            json={"url": url, "max_reviews": review_count},
            timeout=1800
        )
        
        if response.status_code != 200:
            return (
                f"❌ **API Error ({response.status_code}):** {response.text[:200]}",
                None, "No trend data available.",
                default_summary, None, default_insight, empty_dropdown, default_detail,
                default_summary, None, default_insight, empty_dropdown, default_detail,
                empty
            )
        
        data = response.json()
        
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
        raw_reviews = data.get('raw_reviews', [])
        
        food_items = menu.get('food_items', [])
        drinks = menu.get('drinks', [])
        aspect_list = aspects.get('aspects', [])
        all_menu = food_items + drinks
        
        state = {
            "menu_analysis": menu,
            "aspect_analysis": aspects,
            "insights": insights,
            "restaurant_name": restaurant_name,
            "raw_reviews": raw_reviews,
            "source": platform
        }
        
        trend_chart = generate_trend_chart(raw_reviews, restaurant_name)
        trend_insight = generate_trend_insight(raw_reviews, restaurant_name)
        
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
• Reviews analyzed: **{review_count}**
• Menu items found: **{len(all_menu)}** ({len(food_items)} food, {len(drinks)} drinks)
• Aspects discovered: **{len(aspect_list)}**

👇 **Explore the tabs below for detailed insights!**
"""
        
        return (
            status,
            trend_chart, trend_insight,
            menu_summary, chef_chart, chef_insights, chef_dropdown_update, default_detail,
            aspect_summary, manager_chart, manager_insights, manager_dropdown_update, default_detail,
            state
        )
        
    except requests.exceptions.Timeout:
        return (
            "❌ **Timeout:** Request took too long. Try with fewer reviews (50-100).",
            None, "No trend data available.",
            default_summary, None, default_insight, empty_dropdown, default_detail,
            default_summary, None, default_insight, empty_dropdown, default_detail,
            empty
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            f"❌ **Error:** {str(e)}",
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
                
                # Download Section
                gr.Markdown("#### 📥 Download PDF Report")
                gr.Markdown("Get a professional PDF with all analysis results, charts, and recommendations.")
                
                with gr.Row():
                    download_btn = gr.Button("📄 Generate & Download PDF", variant="primary", size="lg")
                
                pdf_output = gr.File(label="Download Your Report", visible=True)
                
                gr.Markdown("---")
                
                # Email Section
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