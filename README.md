# Blue Thumb Water Quality Dashboard

An interactive web dashboard for visualizing stream health data from Oklahoma's Blue Thumb volunteer monitoring program. This project transforms complex water quality datasets into accessible visualizations that help communicate stream health to the public across Oklahoma's watersheds.

## Overview

Blue Thumb volunteers collect water quality data from over 370 sites across Oklahoma. This dashboard provides comprehensive statewide coverage with:

- **Interactive site monitoring map** - Real-time status visualization of all monitoring locations with parameter-based color coding
- **Chemical water quality analysis** - pH, dissolved oxygen, nutrients, and pollutants across all sites
- **Biological community assessment** - Fish and macroinvertebrate health indicators statewide
- **Physical habitat evaluation** - Stream structure and ecosystem conditions
- **Educational content** - Explanations of what the data means for stream health
- **Advanced filtering** - Site-specific analysis and active monitoring location filtering

## Technologies Used

- **Python** - Data processing and analysis
- **Dash & Plotly** - Interactive web dashboard and visualizations
- **SQLite** - Normalized database schema for comprehensive monitoring data
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
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Load the monitoring data**
   ```bash
   python -m database.reset_database
   ```

5. **Start the dashboard**
   ```bash
   python app.py
   ```

6. **Open your browser**
   Navigate to http://127.0.0.1:8050

## Project Structure

```
├── app.py                 # Main dashboard application
├── requirements.txt       # Python dependencies
├── database/             # Database schema and connection utilities
│   ├── db_schema.py      # Normalized schema for all data types
│   └── reset_database.py # Database initialization and loading
├── data_processing/      # Comprehensive data cleaning and processing pipeline
│   ├── data_loader.py    # Core data loading utilities
│   ├── site_processing.py # Site consolidation and validation
│   ├── chemical_processing.py # Chemical data processing
│   ├── fish_processing.py # Fish community data processing
│   ├── macro_processing.py # Macroinvertebrate data processing
│   └── habitat_processing.py # Habitat assessment processing
├── visualizations/       # Chart and map generation
├── layouts/             # Modular dashboard layouts
│   └── tabs/            # Individual tab components
├── callbacks/           # Interactive dashboard logic
├── data/
│   ├── raw/            # Original CSV data files
│   ├── interim/        # Cleaned and validated data
│   └── processed/      # Database-ready outputs
├── text/               # Educational content (markdown)
└── assets/             # Images, icons, and styling
```

## Features

### Interactive Statewide Site Map
- Real-time visualization of all 340+ monitoring sites across Oklahoma
- Parameter-based color coding for immediate status assessment
- Active site filtering to focus on currently monitored locations
- Click-to-navigate functionality for detailed site analysis

### Comprehensive Chemical Analysis
- Time series visualization of key water quality parameters across all sites
- Reference threshold highlighting (normal, caution, poor conditions)
- Multi-site comparison capabilities
- Seasonal filtering and trend analysis
- Parameter-specific educational explanations

### Biological Community Assessment
- Fish community integrity scoring over time for all monitored sites
- Macroinvertebrate bioassessment results statewide
- Species diversity metrics and trends
- Detailed biological metrics for scientific review

### Habitat Assessment
- Physical stream condition scoring across Oklahoma watersheds
- Habitat quality trends over monitoring periods
- Component-level habitat metrics breakdown
- Watershed-scale habitat comparisons

### Advanced Data Processing Pipeline
- Automated data cleaning and validation
- Site name standardization and conflict resolution
- Duplicate detection and handling
- Multi-source data integration
- Database normalization and optimization

## Data Source

This dashboard uses data from the [Blue Thumb Volunteer Stream Monitoring Program](https://www.ok.gov/conservation/Agency_Divisions/Water_Division/Blue_Thumb/), administered by the Oklahoma Conservation Commission. Blue Thumb trains citizen volunteers to collect standardized water quality data, creating one of the most comprehensive stream monitoring datasets in Oklahoma with over 340 active and historical monitoring sites.

## Development Notes

This project demonstrates:
- **Comprehensive data pipeline architecture** - ETL processes for multiple data types across 340+ sites
- **Scalable database design** - Normalized schema handling chemical, biological, and habitat data
- **Advanced interactive visualization** - Multi-tab dashboard with linked components and real-time mapping
- **Scientific communication** - Translating complex statewide data for public understanding
- **Production deployment** - Robust architecture suitable for public use

### Code Standards

- **Comment Style Guide** - See [`docs/COMMENT_STYLE_GUIDE.md`](docs/COMMENT_STYLE_GUIDE.md) for consistent commenting standards across the codebase
- **Testing Framework** - Comprehensive test suite with 456+ tests ensuring reliability across all components

## Future Enhancements

- [ ] Automated data updates from new monitoring events
- [ ] Advanced statistical analysis and trend detection
- [ ] Weather data correlation analysis
- [ ] Watershed-scale comparative analysis tools
- [ ] Data download functionality for researchers
- [ ] Mobile-responsive design optimization

## Contributing

This project was developed to support Blue Thumb's mission of "stream protection through education" by making statewide water quality data accessible to the public. For questions about the monitoring program or data, contact the Oklahoma Conservation Commission.

## Acknowledgments

- **Blue Thumb Program** - Oklahoma Conservation Commission
- **Volunteer Monitors** - Citizens collecting water quality data across 340+ sites statewide
- **Jacob Askey** - Dashboard development and comprehensive data analysis


