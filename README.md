# Blue Thumb Water Quality Dashboard

An interactive web dashboard for visualizing stream health data from Oklahoma's Blue Thumb volunteer monitoring program. This project transforms complex water quality datasets into accessible visualizations that help communicate stream health to the public.

## Overview

Blue Thumb volunteers collect water quality data from over 70 streams across Oklahoma. This dashboard focuses on Tenmile Creek data and provides:

- **Chemical water quality analysis** - pH, dissolved oxygen, nutrients, and pollutants
- **Biological community assessment** - fish and macroinvertebrate health indicators  
- **Physical habitat evaluation** - stream structure and ecosystem conditions
- **Interactive mapping** - spatial visualization of monitoring sites and conditions
- **Educational content** - explanations of what the data means for stream health

## Technologies Used

- **Python** - Data processing and analysis
- **Dash & Plotly** - Interactive web dashboard and visualizations
- **SQLite** - Database for processed monitoring data
- **Pandas** - Data manipulation and analysis
- **Bootstrap** - Responsive UI components

## Quick Start

### Prerequisites
- Python 3.8+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Blue-Thumb-Statewide-Data.git
   cd Blue-Thumb-Statewide-Data
   Create virtual environment


2. **Create virtual environment**
   ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. **Install dependencies**
   ```bash
    pip install -r requirements.txt

4. **Load the monitoring data**
   ```bash
    python -m database.reset_database

5. **Start the dashboard**
   ```bash
    python app.py

5. **Open your browser**
    Navigate to http://127.0.0.1:8050

## Project Structure

├── app.py                 # Main dashboard application
├── requirements.txt       # Python dependencies
├── database/             # Database schema and connection utilities
├── data_processing/      # Data cleaning and loading scripts
├── visualizations/       # Chart and map generation
├── layouts/             # Dashboard page layouts
├── callbacks.py         # Interactive dashboard logic
├── data/
│   ├── raw/            # Original CSV data files
│   └── processed/      # Cleaned data outputs
├── text/               # Educational content (markdown)
└── assets/             # Images, icons, and styling

## Features

### Interactive Chemical Analysis
- Time series visualization of key water quality parameters
- Reference threshold highlighting (normal, caution, poor conditions)
- Seasonal filtering and trend analysis
- Parameter-specific educational explanations

### Biological Community Health
- Fish community integrity scoring over time
- Macroinvertebrate bioassessment results
- Species galleries with identification information
- Detailed metrics tables for scientific review

### Habitat Assessment
- Physical stream condition scoring
- Habitat quality trends over monitoring period
- Component-level habitat metrics breakdown

### Geographic Visualization
- Interactive map of all monitoring sites
- Color-coded status indicators by parameter
- Site-specific data access through map interface

## Data Source

This dashboard uses data from the [Blue Thumb Volunteer Stream Monitoring Program](https://www.ok.gov/conservation/Agency_Divisions/Water_Division/Blue_Thumb/), administered by the Oklahoma Conservation Commission. Blue Thumb trains citizen volunteers to collect standardized water quality data, creating one of the most comprehensive stream monitoring datasets in Oklahoma.

## Development Notes

This project demonstrates:
- **Data pipeline architecture** - ETL processes for multiple data types
- **Database design** - Normalized schema for water quality monitoring data
- **Interactive visualization** - Complex dashboard with multiple linked components
- **Scientific communication** - Translating technical data for public understanding

## Future Enhancements

- [ ] Expand to include all Blue Thumb monitoring sites statewide
- [ ] Add data download functionality for researchers
- [ ] Implement automated data updates from new monitoring events
- [ ] Include weather data correlation analysis
- [ ] Add comparative watershed analysis tools

## Contributing

This project was developed to support Blue Thumb's mission of "stream protection through education." For questions about the monitoring program or data, contact the Oklahoma Conservation Commission.

## Acknowledgments

- **Blue Thumb Program** - Oklahoma Conservation Commission
- **Volunteer Monitors** - Citizens collecting the water quality data
- **Jacob Askey** - Dashboard development and data analysis


