"""
PDF Report Generator for Restaurant Intelligence Agent

Generates professional PDF reports with:
- Executive Summary
- Menu Analysis with charts
- Aspect Analysis
- Chef & Manager Insights
- Trend Analysis
- Customer Feedback Highlights
"""

import os
import io
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, ListFlowable, ListItem
)
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import HorizontalBarChart


# Color scheme
COLORS = {
    'primary': colors.HexColor('#2196F3'),      # Blue
    'positive': colors.HexColor('#10b981'),     # Green
    'neutral': colors.HexColor('#f59e0b'),      # Amber
    'negative': colors.HexColor('#ef4444'),     # Red
    'text': colors.HexColor('#1f2937'),         # Dark gray
    'light_gray': colors.HexColor('#f3f4f6'),   # Light background
    'border': colors.HexColor('#e5e7eb'),       # Border
}


def get_sentiment_color(sentiment: float) -> colors.Color:
    """Get color based on sentiment score."""
    if sentiment > 0.3:
        return COLORS['positive']
    elif sentiment > -0.3:
        return COLORS['neutral']
    else:
        return COLORS['negative']


def create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=COLORS['primary'],
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=COLORS['primary'],
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    ))
    
    # Subsection header
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=COLORS['text'],
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLORS['text'],
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14
    ))
    
    # Highlight/quote text
    styles.add(ParagraphStyle(
        name='Quote',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4b5563'),
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10,
        fontName='Helvetica-Oblique',
        leading=14
    ))
    
    # Stat number
    styles.add(ParagraphStyle(
        name='StatNumber',
        parent=styles['Normal'],
        fontSize=24,
        textColor=COLORS['primary'],
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Stat label
    styles.add(ParagraphStyle(
        name='StatLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    ))
    
    return styles


def create_stat_box(value: str, label: str, styles) -> Table:
    """Create a statistics box."""
    data = [
        [Paragraph(str(value), styles['StatNumber'])],
        [Paragraph(label, styles['StatLabel'])]
    ]
    
    table = Table(data, colWidths=[1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLORS['light_gray']),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    
    return table


def create_sentiment_table(items: List[Dict], title: str, styles, max_items: int = 10) -> List:
    """Create a table showing items with sentiment scores."""
    elements = []
    
    elements.append(Paragraph(title, styles['SubsectionHeader']))
    
    if not items:
        elements.append(Paragraph("No data available.", styles['BodyText']))
        return elements
    
    # Sort by mentions and take top items
    sorted_items = sorted(items, key=lambda x: x.get('mention_count', 0), reverse=True)[:max_items]
    
    # Table header
    data = [['Item', 'Sentiment', 'Mentions', 'Status']]
    
    for item in sorted_items:
        name = item.get('name', 'Unknown')[:30]
        sentiment = item.get('sentiment', 0)
        mentions = item.get('mention_count', 0)
        
        # Status emoji based on sentiment
        if sentiment > 0.3:
            status = '✅ Positive'
        elif sentiment > -0.3:
            status = '🟡 Mixed'
        else:
            status = '⚠️ Needs Attention'
        
        data.append([name.title(), f'{sentiment:+.2f}', str(mentions), status])
    
    table = Table(data, colWidths=[2.5*inch, 1*inch, 0.8*inch, 1.5*inch])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light_gray']]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    return elements


def create_insights_section(insights: Dict, role: str, styles) -> List:
    """Create insights section for Chef or Manager."""
    elements = []
    
    role_title = "Chef" if role == "chef" else "Manager"
    emoji = "🍳" if role == "chef" else "📊"
    
    elements.append(Paragraph(f"{emoji} {role_title} Insights", styles['SectionHeader']))
    
    # Summary
    summary = insights.get('summary', 'No summary available.')
    elements.append(Paragraph(f"<b>Summary:</b> {summary}", styles['BodyText']))
    elements.append(Spacer(1, 10))
    
    # Strengths
    strengths = insights.get('strengths', [])
    if strengths:
        elements.append(Paragraph("✅ Strengths", styles['SubsectionHeader']))
        for s in strengths[:5]:
            if isinstance(s, dict):
                s = s.get('action', str(s))
            elements.append(Paragraph(f"• {s}", styles['BodyText']))
        elements.append(Spacer(1, 10))
    
    # Concerns
    concerns = insights.get('concerns', [])
    if concerns:
        elements.append(Paragraph("⚠️ Areas of Concern", styles['SubsectionHeader']))
        for c in concerns[:5]:
            if isinstance(c, dict):
                c = c.get('action', str(c))
            elements.append(Paragraph(f"• {c}", styles['BodyText']))
        elements.append(Spacer(1, 10))
    
    # Recommendations
    recommendations = insights.get('recommendations', [])
    if recommendations:
        elements.append(Paragraph("💡 Recommendations", styles['SubsectionHeader']))
        for r in recommendations[:5]:
            if isinstance(r, dict):
                priority = r.get('priority', '').upper()
                action = r.get('action', str(r))
                if priority:
                    elements.append(Paragraph(f"• <b>[{priority}]</b> {action}", styles['BodyText']))
                else:
                    elements.append(Paragraph(f"• {action}", styles['BodyText']))
            else:
                elements.append(Paragraph(f"• {r}", styles['BodyText']))
    
    return elements


def generate_pdf_report(
    analysis_data: Dict[str, Any],
    restaurant_name: str,
    output_path: Optional[str] = None
) -> str:
    """
    Generate a professional PDF report from analysis data.
    
    Args:
        analysis_data: Complete analysis results from the agent
        restaurant_name: Name of the restaurant
        output_path: Optional path to save PDF (if None, uses temp file)
    
    Returns:
        Path to generated PDF file
    """
    # Create output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = restaurant_name.lower().replace(" ", "_").replace("/", "_")
        output_path = os.path.join(tempfile.gettempdir(), f"{safe_name}_report_{timestamp}.pdf")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Get styles
    styles = create_styles()
    
    # Build document content
    elements = []
    
    # ========== COVER PAGE ==========
    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph("🍽️", styles['ReportTitle']))
    elements.append(Paragraph("Restaurant Intelligence Report", styles['ReportTitle']))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(restaurant_name, ParagraphStyle(
        'RestaurantName',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=COLORS['text'],
        alignment=TA_CENTER
    )))
    elements.append(Spacer(1, 0.5*inch))
    
    # Report metadata
    report_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated: {report_date}", ParagraphStyle(
        'ReportDate',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )))
    
    elements.append(Spacer(1, 1*inch))
    
    # Quick stats on cover
    menu = analysis_data.get('menu_analysis', {})
    aspects = analysis_data.get('aspect_analysis', {})
    raw_reviews = analysis_data.get('raw_reviews', [])
    
    food_items = menu.get('food_items', [])
    drinks = menu.get('drinks', [])
    aspect_list = aspects.get('aspects', [])
    
    stat_data = [
        [
            create_stat_box(str(len(raw_reviews)), "Reviews Analyzed", styles),
            create_stat_box(str(len(food_items) + len(drinks)), "Menu Items", styles),
            create_stat_box(str(len(aspect_list)), "Aspects Analyzed", styles)
        ]
    ]
    
    stat_table = Table(stat_data, colWidths=[2*inch, 2*inch, 2*inch])
    stat_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(stat_table)
    
    elements.append(PageBreak())
    
    # ========== EXECUTIVE SUMMARY ==========
    elements.append(Paragraph("📋 Executive Summary", styles['SectionHeader']))
    
    # Calculate overall sentiment
    all_items = food_items + drinks
    if all_items:
        avg_sentiment = sum(i.get('sentiment', 0) for i in all_items) / len(all_items)
        sentiment_text = "positive" if avg_sentiment > 0.3 else "mixed" if avg_sentiment > -0.3 else "concerning"
        elements.append(Paragraph(
            f"Based on analysis of <b>{len(raw_reviews)}</b> customer reviews, {restaurant_name} shows "
            f"<b>{sentiment_text}</b> overall sentiment (score: {avg_sentiment:+.2f}). "
            f"The analysis identified <b>{len(all_items)}</b> menu items and <b>{len(aspect_list)}</b> "
            f"customer experience aspects.",
            styles['BodyText']
        ))
    else:
        elements.append(Paragraph(
            f"Analysis of {len(raw_reviews)} customer reviews for {restaurant_name}.",
            styles['BodyText']
        ))
    
    elements.append(Spacer(1, 15))
    
    # Key highlights
    if all_items:
        top_items = sorted(all_items, key=lambda x: x.get('sentiment', 0), reverse=True)[:3]
        if top_items:
            elements.append(Paragraph("🌟 Top Performing Items", styles['SubsectionHeader']))
            for item in top_items:
                elements.append(Paragraph(
                    f"• <b>{item.get('name', '?').title()}</b> - Sentiment: {item.get('sentiment', 0):+.2f}",
                    styles['BodyText']
                ))
    
    elements.append(Spacer(1, 10))
    
    # Areas needing attention
    problem_items = [i for i in all_items if i.get('sentiment', 0) < -0.2]
    if problem_items:
        elements.append(Paragraph("⚠️ Items Needing Attention", styles['SubsectionHeader']))
        for item in problem_items[:3]:
            elements.append(Paragraph(
                f"• <b>{item.get('name', '?').title()}</b> - Sentiment: {item.get('sentiment', 0):+.2f}",
                styles['BodyText']
            ))
    
    elements.append(PageBreak())
    
    # ========== MENU ANALYSIS ==========
    elements.append(Paragraph("🍽️ Menu Performance Analysis", styles['SectionHeader']))
    
    elements.append(Paragraph(
        f"Analysis of {len(food_items)} food items and {len(drinks)} beverages mentioned in customer reviews.",
        styles['BodyText']
    ))
    
    # Food items table
    if food_items:
        elements.extend(create_sentiment_table(food_items, "Food Items", styles))
    
    # Drinks table
    if drinks:
        elements.extend(create_sentiment_table(drinks, "Beverages", styles))
    
    elements.append(PageBreak())
    
    # ========== ASPECT ANALYSIS ==========
    elements.append(Paragraph("📊 Customer Experience Aspects", styles['SectionHeader']))
    
    elements.append(Paragraph(
        "Analysis of key aspects that customers mentioned in their reviews.",
        styles['BodyText']
    ))
    
    if aspect_list:
        elements.extend(create_sentiment_table(aspect_list, "Aspects Overview", styles))
    
    elements.append(PageBreak())
    
    # ========== CHEF INSIGHTS ==========
    chef_insights = analysis_data.get('insights', {}).get('chef', {})
    if chef_insights:
        elements.extend(create_insights_section(chef_insights, 'chef', styles))
        elements.append(PageBreak())
    
    # ========== MANAGER INSIGHTS ==========
    manager_insights = analysis_data.get('insights', {}).get('manager', {})
    if manager_insights:
        elements.extend(create_insights_section(manager_insights, 'manager', styles))
        elements.append(PageBreak())
    
    # ========== CUSTOMER FEEDBACK HIGHLIGHTS ==========
    elements.append(Paragraph("💬 Customer Feedback Highlights", styles['SectionHeader']))
    
    # Get some sample reviews
    if raw_reviews:
        positive_reviews = [r for r in raw_reviews if r.get('rating', 0) >= 4][:3]
        
        if positive_reviews:
            elements.append(Paragraph("Positive Feedback", styles['SubsectionHeader']))
            for r in positive_reviews:
                text = r.get('text', r.get('review_text', ''))[:200]
                if text:
                    elements.append(Paragraph(f'"{text}..."', styles['Quote']))
    
    elements.append(Spacer(1, 20))
    
    # ========== FOOTER ==========
    elements.append(Paragraph(
        "Report generated by Restaurant Intelligence Agent | Powered by Claude AI",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#9ca3af'),
            alignment=TA_CENTER
        )
    ))
    
    # Build PDF
    doc.build(elements)
    
    print(f"✅ PDF Report generated: {output_path}")
    return output_path


def generate_pdf_bytes(analysis_data: Dict[str, Any], restaurant_name: str) -> bytes:
    """
    Generate PDF report and return as bytes (for direct download).
    
    Args:
        analysis_data: Complete analysis results
        restaurant_name: Name of the restaurant
    
    Returns:
        PDF file as bytes
    """
    # Generate to temp file
    pdf_path = generate_pdf_report(analysis_data, restaurant_name)
    
    # Read bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Clean up temp file
    try:
        os.remove(pdf_path)
    except:
        pass
    
    return pdf_bytes


if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        'menu_analysis': {
            'food_items': [
                {'name': 'salmon sushi', 'sentiment': 0.85, 'mention_count': 12},
                {'name': 'miso soup', 'sentiment': 0.72, 'mention_count': 8},
                {'name': 'tempura', 'sentiment': -0.15, 'mention_count': 5},
            ],
            'drinks': [
                {'name': 'sake', 'sentiment': 0.65, 'mention_count': 6},
                {'name': 'green tea', 'sentiment': 0.90, 'mention_count': 4},
            ]
        },
        'aspect_analysis': {
            'aspects': [
                {'name': 'service', 'sentiment': 0.75, 'mention_count': 25},
                {'name': 'ambiance', 'sentiment': 0.82, 'mention_count': 18},
                {'name': 'wait time', 'sentiment': -0.30, 'mention_count': 10},
            ]
        },
        'insights': {
            'chef': {
                'summary': 'Overall positive feedback on sushi quality.',
                'strengths': ['Fresh ingredients', 'Beautiful presentation'],
                'concerns': ['Tempura can be inconsistent'],
                'recommendations': [
                    {'priority': 'high', 'action': 'Review tempura preparation process'}
                ]
            },
            'manager': {
                'summary': 'Service is a strong point, wait times need attention.',
                'strengths': ['Friendly staff', 'Attentive service'],
                'concerns': ['Long wait times during peak hours'],
                'recommendations': [
                    {'priority': 'medium', 'action': 'Consider reservation system improvements'}
                ]
            }
        },
        'raw_reviews': [
            {'rating': 5, 'text': 'Amazing sushi, best in the city!'},
            {'rating': 4, 'text': 'Great food but had to wait 30 minutes.'},
        ]
    }
    
    output = generate_pdf_report(sample_data, "Test Restaurant", "test_report.pdf")
    print(f"Test report saved to: {output}")