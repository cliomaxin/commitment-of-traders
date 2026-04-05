Project Overview

This Django-based web application processes, stores, and visualizes CFTC Commitment of Traders (COT) reports. These reports provide critical financial data regarding trader positioning in futures markets. The system is specifically optimized for 10 key instruments across forex, metals, and cryptocurrency markets.

Core Navigation & Features

Recent COT

    Live Market View: Displays the most recent CFTC Commitment of Traders data for all tracked instruments.

    Instrument Positioning: Shows detailed trader positioning data including Non-Commercial, Commercial, and Non-Reportable trader counts.

    Market Depth: Presents open interest, percentage breakdowns, and week-over-week changes at a glance.

Historical COT Tabled

    Date-Based Navigation: Browse through all historical COT report dates with record counts per week.

    Report Archives: Access complete historical data for any available reporting date.

    Trend Analysis: Compare positioning data across different time periods.

Recent COT Analysis

    Sentiment Signals: Automatically generates buy, sell, and neutral signals based on trader positioning patterns.

    Market Categorization: Separates analysis by asset class (Forex, Metals, Crypto).

    Signal Summary: Quick overview of bullish positions, confused markets, and bearish setups.

Historical COT Tree

    Analytical Timeline: View historical analysis signals across all reporting dates.

    Positioning Evolution: Track how market sentiment has changed over time.

    Pattern Recognition: Identify recurring trading patterns and positioning trends.

Import COT

    Upload Interface: Drag-and-drop file upload system for importing raw CFTC data.

    Format Support: Accepts HTML reports, Excel spreadsheets (.xls, .xlsx, .xlsb, .csv, .ods), and other data formats.

    Real-Time Feedback: Displays import progress with detailed success or error reporting.

Core Functionality
Data Processing Pipeline

    Automated Parsing: Downloads and parses CFTC reports in multiple formats:
        - HTML reports (current weekly data)
        - Excel spreadsheets (.xls, .xlsx, .xlsb, .csv, .ods for historical data)

    Targeted Instrument Extraction: Focuses on 10 specific instruments:

        Forex (7 majors): EUR/USD, GBP/USD, JPY/USD, CHF/USD, CAD/USD, AUD/USD, NZD/USD

        Metals (2): Gold, Silver

        Crypto (1): Bitcoin

    Data Normalization: Converts raw data into structured database records for consistency.

Data Storage & Management

    Comprehensive Database Schema: Stores 50+ data points per instrument per week, including:

        Trader positions (Non-Commercial, Commercial, Non-Reportable)

        Open interest and weekly changes

        Percentage breakdowns and trader counts by category

    Audit Trail: Maintains a full history of data changes to ensure data integrity.

    Import Logging: Tracks all data uploads with detailed success or failure statuses.

User Interfaces

    Recent COT Dashboard: Clean, professional display of current trader positioning data.

    Historical Navigation: Browse and compare data across any reporting date.

    Analysis Views: Automated market sentiment calculations with visual signal indicators.

    Search & Filter: Real-time search functionality across all tracked instruments.

Technical Architecture
Backend (Handle_Raw_COT App)

    Custom Parsers: 
        - HTML Parser: Specifically designed for the CFTC's unique fixed-width formatting
        - Excel Parser: Handles multiple spreadsheet formats for historical data import

    Django Models: Built with complex relationships, constraints, and optimized indexing.

    Upload API: Supports file-based data imports with comprehensive validation.

    Error Handling: Implements validation to prevent corrupted data entry.

Frontend (Display_Data App)

    Responsive Design: A modern web interface built for both desktop and mobile devices.

    Dynamic Functionality: Real-time search and filtering powered by vanilla JavaScript.

    Typography: Utilizes professional typography and custom CSS for high readability.

    Signal Visualization: Color-coded market signals for quick sentiment assessment.

Key Features
Market Intelligence

    Sentiment Analysis: Automatically calculates bullish and bearish positioning based on trader behavior patterns.

    Net Positioning: Tracks the delta between long and short positions across various trader types.

    Historical Trends: Provides week-over-week change tracking to identify market shifts.

    Market Context: Analyzes open interest and trader count for deeper volume insights.

Developer-Friendly Design

    Modular Architecture: Maintains a clean separation between data processing logic and display layers.

    Extensibility: The parser is designed to easily accommodate new instruments or alternative data sources.

    Multi-View System: Supports multiple visualization formats for different analysis workflows.

Production Standards

    Data Integrity: Strict database constraints prevent the entry of duplicate records.

    Performance: Optimized queries ensure the system handles large historical datasets efficiently.

    Error Reporting: Detailed logs for parsing errors to facilitate rapid troubleshooting.

Use Cases

    Trading Analysis: Gain deep insights into market sentiment and institutional positioning.

    Risk Management: Monitor the activity of large traders to identify potential market reversals.

    Market Research: Conduct historical analysis of trader behavior during specific economic cycles.


    Algorithmic Trading: Use structured positioning data as an input for quantitative trading models.

    Financial Reporting: Generate professional market intelligence reports for stakeholders.

Technology Stack
Component	Technology
Backend	Django 3.2, Python 3.7+
Database	SQLite (Development) / PostgreSQL (Production)
Frontend	HTML5, CSS3, Vanilla JavaScript
Styling	Custom CSS, Google Fonts
Deployment	Gunicorn + Nginx
Data Flow Process

    Source: Download CFTC HTML files from the official government portal.

    Upload: Submit files through the secure web interface.

    Parsing: Process the HTML using the custom-built fixed-width parser.

    Validation: Normalize data and verify against existing records.

    Persistence: Store data in the database with an associated audit trail.

    Visualization: Render data through the web interface for analysis.

    Insight: Generate actionable intelligence on positioning and sentiment.

This project transforms raw government financial data into actionable market intelligence, making complex trader positioning data accessible and understandable for traders, analysts, and researchers.
