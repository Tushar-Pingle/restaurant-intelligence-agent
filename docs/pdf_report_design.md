# PDF Report Design Specification

## Overview
Professional, structured PDF report for restaurant intelligence analysis.

## Structure

### 1. Cover Page
- Restaurant name (large, bold)
- Report generation date
- Analysis period
- Company logo/branding (optional)

### 2. Executive Summary (1 page)
- Overall sentiment score (large visual indicator)
- Key highlights (3-5 bullet points)
- Critical issues requiring immediate attention
- Quick stats: # reviews analyzed, # menu items, # aspects

### 3. Menu Analysis (2-3 pages)
- **Section Header:** "Menu Performance Analysis"
- Embedded chart: Menu sentiment visualization (PNG)
- Table: Top performing items
  - Item name
  - Sentiment score
  - Mention count
  - Key feedback
- Table: Items needing attention
  - Item name
  - Issues identified
  - Recommendations

### 4. Aspect Analysis (2-3 pages)
- **Section Header:** "Customer Experience Aspects"
- Embedded chart: Aspect comparison (PNG)
- For each major aspect:
  - Aspect name
  - Sentiment score (visual indicator)
  - Customer feedback summary
  - Trends

### 5. Chef Insights (1-2 pages)
- **Section Header:** "Recommendations for Kitchen Team"
- Menu item recommendations
- Quality concerns
- Customer preferences
- Actionable next steps

### 6. Manager Insights (1-2 pages)
- **Section Header:** "Operational Recommendations"
- Service improvements
- Training needs
- Staffing recommendations
- Customer experience enhancements

### 7. Customer Feedback Highlights (1 page)
- Top 5 positive reviews (quotes)
- Top 5 critical reviews (quotes)
- Trending topics

### 8. Appendix (optional)
- Detailed data tables
- Methodology
- Data sources

## Design Elements

### Colors
- Primary: Professional blue (#2196F3)
- Positive: Green (#4CAF50)
- Warning: Orange (#FF9800)
- Critical: Red (#F44336)
- Neutral: Gray (#757575)

### Typography
- Headers: Bold, 16-18pt
- Subheaders: Bold, 14pt
- Body: Regular, 11pt
- Captions: Regular, 9pt

### Layout
- Margins: 1 inch all sides
- Two-column layout for data-heavy sections
- White space for readability
- Page numbers in footer
- Restaurant name in header (after cover)

## Technical Implementation

### Libraries to Use
- **ReportLab** or **WeasyPrint** for PDF generation
- **Pillow** for image embedding
- **matplotlib** charts already generated

### File Size Target
- Keep under 5MB for easy sharing
- Compress images if needed
- Optimize charts for print quality (300 DPI)

## Export Button in Gradio
- Prominent "Download PDF Report" button
- Show generation progress
- Auto-download when ready
- Save copy to reports/ folder

## Future Enhancements (Post-Hackathon)
- Custom branding (restaurant logo)
- Multi-language support
- Email delivery option
- Comparison reports (month-over-month)

---

**Build Date:** Days 14-15  
**Priority:** HIGH (required for demo)  
**Estimated Time:** 4-6 hours
