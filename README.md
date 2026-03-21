Project Overview
This is a Django-based web application that processes, stores, and visualizes CFTC Commitment of Traders (COT) reports - critical financial data showing trader positioning in futures markets. The system focuses on 10 key instruments across forex, metals, and cryptocurrency markets.
What the Project Does
🔄 Data Processing Pipeline
Automated HTML Parsing: Downloads and parses CFTC's fixed-width HTML reports from cftc.gov
Targeted Instrument Extraction: Focuses on 10 specific instruments:
oForex (7 majors): EUR/USD, GBP/USD, JPY/USD, CHF/USD, CAD/USD, AUD/USD, NZD/USD
oMetals (2): Gold, Silver
oCrypto (1): Bitcoin
Data Normalization: Converts raw HTML data into structured database records
📊 Data Storage & Management
Comprehensive Database Schema: Stores 50+ data points per instrument per week including:
oTrader positions (Non-Commercial, Commercial, Non-Reportable)
oOpen interest and weekly changes
oPercentage breakdowns
oTrader counts by category
Audit Trail: Maintains history of data changes for data integrity
Import Logging: Tracks all data uploads with success/failure status
🎨 User Interfaces
Upload Interface: Drag-and-drop file upload with real-time progress tracking
Admin Dashboard: Full Django admin interface for data management
Data Visualization: Clean, professional display of trader positioning data
Search & Filter: Live search functionality across instruments
🏗️ Technical Architecture
Backend (Handle_Raw_COT App):
Custom HTML parser for CFTC's unique fixed-width format
Django models with complex relationships and constraints
RESTful upload API with AJAX progress updates
Comprehensive error handling and data validation
Frontend (Display_Data App):
Responsive web interface with modern CSS design
Real-time search and filtering (vanilla JavaScript)
Professional typography and data visualization
Mobile-friendly responsive design
Key Features
📈 Market Intelligence
Sentiment Analysis: Calculates bullish/bearish positioning
Net Positioning: Tracks long vs short positions across trader types
Historical Trends: Week-over-week change tracking
Market Context: Open interest and trader count analytics
🔧 Developer-Friendly
Modular Design: Clean separation between data processing and display
Extensible Parser: Easy to add new instruments or data sources
API-Ready: Structured for integration with trading systems
Well-Documented: Comprehensive code comments and examples
🚀 Production-Ready
Error Handling: Robust parsing with detailed error reporting
Data Integrity: Database constraints prevent duplicates
Performance: Optimized queries and indexing
Scalable: Handles large datasets efficiently
Use Cases
1.Trading Analysis: Understand market sentiment and positioning
2.Risk Management: Monitor large trader activity
3.Market Research: Historical analysis of trader behavior
4.Algorithmic Trading: Feed positioning data into trading models
5.Financial Reporting: Generate market intelligence reports
Technology Stack
Backend: Django 3.2, Python 3.7+
Database: SQLite (development) / PostgreSQL (production)
Frontend: HTML5, CSS3, Vanilla JavaScript
Styling: Custom CSS with Google Fonts
Deployment: Django's built-in server (dev) / Gunicorn + Nginx (prod)
Data Flow
1.Download CFTC HTML files from cftc.gov
2.Upload files through web interface
3.Parse HTML using custom parser
4.Validate and normalize data
5.Store in database with audit trail
6.Display through clean web interface
7.Analyze positioning and sentiment
This project transforms raw government financial data into actionable market intelligence, making complex trader positioning data accessible and understandable for traders, analysts, and researchers.
