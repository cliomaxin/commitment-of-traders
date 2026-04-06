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

Historical URL Extrapolation

    Generate URLs: Automatically generates CFTC report URLs for Currencies, Metals, and Bitcoin from 2005 onwards.

    Fill Gaps: Click the "Fill Gaps to Latest" button to automatically generate missing report URLs up to the current week.

    URL Management: Stores all generated URLs in the database for easy reference and scraping.

    Batch Updates: Handles multiple time-gaps at once (weeks, months, or years of missing reports).

Scrape Stored Report URLs

    URL-Based Scraping: Fetch live data from all stored CFTC report URLs in the database.

    Automated Parsing: Scrapes HTML from each URL and extracts COT data without manual downloads.

    Bulk Processing: Process all stored URLs with a single click.

    Separate Storage: Saves scraped data to a dedicated ScrapedCotReport model for distinction from manually imported data.

    Error Tracking: Detailed reporting on successful, failed, and partially processed URLs.

Core Functionality
Data Sourcing Pipeline

    URL Generation: Automatically generates CFTC report URLs based on COT release schedule (weekly Tuesdays).

    Fill-Gaps Feature: Intelligently detects missing report dates and backfills URLs to the current week.

    Web Scraping: Fetches live HTML reports from generated URLs without requiring manual downloads.

    Multi-Source Support: Supports three categories:
        - Currencies and Bitcoin (deacmesf.htm)
        - Metals (deacmxsf.htm)

Data Processing Pipeline

    Automated Parsing: Downloads and parses CFTC reports in multiple formats:
        - HTML reports (current weekly data and web-scraped historical data)
        - Excel spreadsheets (.xls, .xlsx, .xlsb, .csv, .ods for historical data)
        - Directly scraped from CFTC website via stored report URLs

    Targeted Instrument Extraction: Focuses on 10 specific instruments:

        Forex (7 majors): EUR/USD, GBP/USD, JPY/USD, CHF/USD, CAD/USD, AUD/USD, NZD/USD

        Metals (2): Gold, Silver

        Crypto (1): Bitcoin

    Data Normalization: Converts raw data into structured database records for consistency.

    Dual-Model Storage: Stores data in both CotReport (for manually imported data) and ScrapedCotReport (for web-scraped data).

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
Backend (Get_Data App)

    URL Generation: Automatically generates CFTC report URLs based on the COT release schedule (seven-day intervals on Tuesdays).

    Gap Detection: Identifies missing report dates between the last stored record and the current date.

    Batch URL Generation: Fills multiple gaps at once, supporting weeks, months, or years of missing data.

    Category Support: Generates URLs for Currencies, Metals, and Cryptocurrency categories independently.

    URL Storage: Maintains a persistent database of all generated and extrapolated URLs for reference and scraping.

Backend (Handle_Raw_COT App)

    Custom Parsers: 
        - HTML Parser: Specifically designed for the CFTC's unique fixed-width formatting
        - Excel Parser: Handles multiple spreadsheet formats for historical data import

    Web Scraper: Fetches live HTML reports from CFTC website using stored URLs with proper user-agent headers.

    Django Models: Built with complex relationships, constraints, and optimized indexing.
        - CotReport: For manually uploaded data
        - ScrapedCotReport: For web-scraped data (separate model for data source distinction)

    Dual Import Pipeline:
        - File Upload API: Supports file-based data imports with comprehensive validation.
        - URL Scraping API: Fetches and parses live HTML from stored CFTC report URLs.

    Error Handling: Implements validation to prevent corrupted data entry, with detailed logging for each source URL.

Frontend (Display_Data App)

    Responsive Design: A modern web interface built for both desktop and mobile devices.

    Dynamic Functionality: Real-time search and filtering powered by vanilla JavaScript.

    Typography: Utilizes professional typography and custom CSS for high readability.

    Signal Visualization: Color-coded market signals for quick sentiment assessment.

Key Features
Automated Data Sourcing

    URL Extrapolation: Generates historical CFTC report URLs based on the seven-day release schedule.

    Intelligent Gap Filling: Detects missing report dates and automatically generates URLs to the current week.

    Web Scraping: Fetches and parses live HTML data directly from CFTC website without manual downloads.

    Dual-Source Storage: Maintains separate records for manually imported and web-scraped data.

Market Intelligence

    Sentiment Analysis: Automatically calculates bullish and bearish positioning based on trader behavior patterns.

    Net Positioning: Tracks the delta between long and short positions across various trader types.

    Historical Trends: Provides week-over-week change tracking to identify market shifts.

    Market Context: Analyzes open interest and trader count for deeper volume insights.

Developer-Friendly Design

    Modular Architecture: Maintains a clean separation between data processing logic and display layers.

    Extensibility: The parser and scraper are designed to easily accommodate new instruments or alternative data sources.

    Multi-View System: Supports multiple visualization formats for different analysis workflows.

    Multiple Data Pipelines: Supports file uploads, URL-based scraping, and historical data generation.

Production Standards

    Data Integrity: Strict database constraints prevent the entry of duplicate records.

    Performance: Optimized queries ensure the system handles large historical datasets efficiently.

    Error Reporting: Detailed logs for parsing errors, scraping failures, and URL generation issues.

    Audit Trail: Full history of data changes and import sources for data lineage tracking.

Use Cases

    Trading Analysis: Gain deep insights into market sentiment and institutional positioning using automated data feeds.

    Risk Management: Monitor the activity of large traders to identify potential market reversals with continuously updated data.

    Market Research: Conduct historical analysis of trader behavior during specific economic cycles without manual data collection.

    Algorithmic Trading: Use structured positioning data from multiple sources as input for quantitative trading models.

    Financial Reporting: Generate professional market intelligence reports for stakeholders with up-to-date information.

    Fully Automated Pipeline: Set up once and run continuously to maintain the complete historical database automatically.

Technology Stack
Component	Technology
Backend	Django 3.2, Python 3.7+
Database	SQLite (Development) / PostgreSQL (Production)
Frontend	HTML5, CSS3, Vanilla JavaScript
Styling	Custom CSS, Google Fonts
Deployment	Gunicorn + Nginx
Data Flow Process

Three complementary data pipelines are supported:

**Pipeline 1: Manual File Upload**
    - Source: Download CFTC HTML/Excel files from the official government portal.
    - Upload: Submit files through the secure web interface.
    - Parsing: Process the files using custom-built parsers.
    - Storage: Save to CotReport model with import audit trail.

**Pipeline 2: Automated URL Generation & Scraping**
    - Generate: Automatically create CFTC report URLs based on 7-day release schedule.
    - Fill Gaps: Click "Fill Gaps to Latest" to backfill missing report dates.
    - Scrape: Click "Scrape stored report URLs" to fetch and parse live HTML.
    - Storage: Save to ScrapedCotReport model for source distinction.

**Pipeline 3: Historical Data Backfill**
    - Generate: Create URLs for years of historical data automatically.
    - Batch Scrape: Process hundreds of URLs in a single operation.
    - Validation: Normalize data and verify against existing records.
    - Persistence: Store data with complete audit trail and source attribution.

**Common Processing Steps (All Pipelines)**
    - Parsing: Extract data using HTML or Excel parser.
    - Validation: Normalize data and verify against existing records.
    - Persistence: Store data in the database with associated audit trail.
    - Visualization: Render data through the web interface for analysis.
    - Insight: Generate actionable intelligence on positioning and sentiment.

This project transforms raw government financial data into actionable market intelligence, making complex trader positioning data accessible and understandable for traders, analysts, and researchers.
