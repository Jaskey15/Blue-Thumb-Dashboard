# Blue Thumb Water Quality Dashboard

## 🌊 Overview

This project transforms complex water quality datasets from Oklahoma's Blue Thumb volunteer monitoring program into accessible, interactive visualizations that help communicate stream health across Oklahoma's watersheds. With data from **370+ monitoring sites**, the dashboard provides comprehensive statewide coverage enhanced by AI-powered assistance and automated cloud processing.

### 🚀 Key Achievements

- **Interactive Statewide Monitoring**: Real-time visualization of all monitoring sites with parameter-based status indicators
- **AI Stream Health Assistant**: Intelligent chatbot powered by Google Vertex AI with specialized stream health knowledge
- **Automated Data Processing**: Cloud-based pipeline for processing new Survey123 submissions daily
- **Comprehensive Analysis**: Chemical, biological, and habitat assessment tools with educational content
- **Production-Ready Architecture**: Scalable cloud infrastructure with automated backups and monitoring

## 🛠️ Technology Stack

### Core Platform
- **Python 3.8+** - Data processing and analysis
- **Dash & Plotly** - Interactive web dashboard and visualizations  
- **SQLite** - Normalized database schema for comprehensive monitoring data
- **Pandas** - Data manipulation and analysis
- **Bootstrap** - Responsive UI components

### Google Cloud Integration
- **Vertex AI (Gemini 2.0)** - AI-powered stream health chatbot with document grounding
- **Cloud Functions** - Serverless data processing and synchronization
- **Cloud Storage** - Database hosting with automated backups
- **Cloud Scheduler** - Automated daily data updates
- **ArcGIS API** - Survey123 integration for real-time data collection

### AI & Machine Learning
- **Vertex AI Search** - Knowledge base grounding for accurate responses
- **Google Search Integration** - Fallback knowledge source for comprehensive answers
- **Natural Language Processing** - Context-aware stream health expertise

## ✨ Features

### 🤖 AI Stream Health Assistant
- **Expert Knowledge**: Trained on Blue Thumb documentation and stream health science
- **Context-Aware**: Provides tab-specific guidance and answers
- **Multi-Source**: Combines grounded knowledge with real-time search capabilities
- **Interactive Chat**: Available on every tab with persistent conversation history

### 🗺️ Interactive Statewide Site Map
- Real-time visualization of all 370+ monitoring sites across Oklahoma
- Parameter-based color coding for immediate status assessment  
- Active site filtering to focus on currently monitored locations
- Click-to-navigate functionality for detailed site analysis

### 🧪 Comprehensive Chemical Analysis
- Time series visualization of key water quality parameters
- Reference threshold highlighting (normal, caution, poor conditions)
- Multi-site comparison capabilities
- Seasonal filtering and trend analysis
- Parameter-specific educational explanations with AI assistance

### 🐟 Biological Community Assessment
- Fish community integrity scoring over time
- Macroinvertebrate bioassessment results statewide
- Species diversity metrics and trends
- Detailed biological metrics for scientific review
- Interactive species galleries with identification guides

### 🏞️ Habitat Assessment
- Physical stream condition scoring across Oklahoma watersheds
- Habitat quality trends over monitoring periods
- Component-level habitat metrics breakdown
- Watershed-scale habitat comparisons

### ☁️ Cloud-Powered Data Pipeline
- **Automated Daily Sync**: Processes new Survey123 submissions at 6 AM Central
- **Smart Data Processing**: Handles range-based measurements and validation
- **Backup Management**: Automatic database backups before each update
- **Error Handling**: Comprehensive logging and monitoring
- **Cost-Efficient**: <$1/year operational costs

## 🏗️ Project Structure

```
├── app.py                 # Main dashboard application
├── requirements.txt       # Python dependencies
├── cloud_functions/       # Google Cloud serverless functions
│   └── survey123_sync/    # Automated data synchronization
│       ├── main.py        # Cloud Function entry point
│       ├── chemical_processor.py # Data processing logic
│       ├── deploy.sh      # Deployment automation
│       └── requirements.txt
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
├── callbacks/           # Interactive dashboard logic
│   ├── chatbot_callbacks.py # AI assistant integration
│   ├── chemical_callbacks.py
│   ├── biological_callbacks.py
│   └── habitat_callbacks.py
├── layouts/             # Modular dashboard layouts
│   ├── components/      # Reusable UI components
│   │   └── chatbot.py   # Floating AI assistant widget
│   └── tabs/            # Individual tab components
├── visualizations/       # Chart and map generation
├── data/
│   ├── raw/            # Original CSV data files
│   ├── interim/        # Cleaned and validated data
│   └── processed/      # Database-ready outputs
│       └── chatbot_data/ # AI knowledge base content
├── text/               # Educational content (markdown)
└── assets/             # Images, icons, and styling
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Git
- Google Cloud SDK (for cloud features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Blue-Thumb-Dashboard.git
   cd Blue-Thumb-Dashboard
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

### Cloud Deployment (Optional)

For full AI and automated processing features:

1. **Set up Google Cloud Project**
   ```bash
   gcloud auth login
   gcloud config set project your-project-id
   ```

2. **Deploy Cloud Functions**
   ```bash
   cd cloud_functions/survey123_sync
   ./deploy.sh
   ```

3. **Configure Environment Variables**
   ```bash
   # Set ArcGIS credentials for Survey123 integration
   gcloud functions deploy survey123-daily-sync \
       --update-env-vars ARCGIS_CLIENT_ID="your_client_id" \
       --update-env-vars ARCGIS_CLIENT_SECRET="your_client_secret" \
       --update-env-vars SURVEY123_FORM_ID="your_form_id"
   ```

## 📊 Data Source

This dashboard uses data from the [Blue Thumb Volunteer Stream Monitoring Program](https://www.ok.gov/conservation/Agency_Divisions/Water_Division/Blue_Thumb/), administered by the Oklahoma Conservation Commission. Blue Thumb trains citizen volunteers to collect standardized water quality data, creating one of the most comprehensive stream monitoring datasets in Oklahoma with over 370 active and historical monitoring sites.

## 🔬 Technical Highlights

### Advanced Data Processing Pipeline
- **ETL Architecture**: Comprehensive processes for multiple data types across 370+ sites
- **Real-time Integration**: Automated Survey123 form processing with ArcGIS API
- **Data Validation**: Advanced duplicate detection and quality assurance
- **Scalable Design**: Cloud-native architecture for production deployment

### AI-Powered User Experience  
- **Contextual Assistance**: Tab-aware chatbot providing relevant stream health guidance
- **Knowledge Grounding**: Responses based on authoritative Blue Thumb documentation
- **Intelligent Fallback**: Google Search integration for comprehensive coverage
- **Natural Interaction**: Conversational interface with typing indicators and message history

### Production-Grade Infrastructure
- **Serverless Computing**: Cost-effective Cloud Functions with automatic scaling
- **Automated Backups**: Database versioning with timestamp-based backup system
- **Monitoring & Logging**: Comprehensive error tracking and performance monitoring
- **Security**: Environment-based credential management and HTTPS-only communication

## 📈 Impact & Results

- **370+ Monitoring Sites**: Comprehensive statewide water quality coverage
- **Multi-Parameter Analysis**: Chemical, biological, and habitat assessment integration
- **Educational Outreach**: Public-facing dashboard promoting stream health awareness
- **Automated Processing**: Daily data updates reducing manual intervention by 100%
- **AI Enhancement**: Intelligent assistance improving user engagement and understanding

## 🔮 Future Enhancements

- [ ] **Real-time Webhooks**: Immediate processing of new submissions
- [ ] **Advanced Analytics**: Machine learning for trend prediction and anomaly detection
- [ ] **Mobile Optimization**: Progressive web app capabilities
- [ ] **Multi-State Expansion**: Framework for other volunteer monitoring programs
- [ ] **Weather Integration**: Precipitation correlation analysis
- [ ] **API Development**: Public API for researchers and third-party applications

## 🧪 Testing & Quality Assurance

- **Comprehensive Test Suite**: 700+ tests ensuring reliability across all components
- **Automated CI/CD**: Continuous integration with quality checks
- **Data Validation**: Multi-layer validation ensuring data integrity
- **Performance Monitoring**: Real-time tracking of system performance

## 🤝 Contributing

This project was developed to support Blue Thumb's mission of "stream protection through education" by making statewide water quality data accessible to the public. For questions about the monitoring program or data, contact the Oklahoma Conservation Commission.

## 📄 License

This project is developed for educational and public service purposes. Please respect the data sources and maintain attribution to the Blue Thumb Program and Oklahoma Conservation Commission.

## 🙏 Acknowledgments

- **Blue Thumb Program** - Oklahoma Conservation Commission
- **Volunteer Monitors** - Citizens collecting water quality data across 370+ sites statewide  
- **Google Cloud Platform** - Providing AI and cloud infrastructure capabilities
- **Open Source Community** - Supporting libraries and frameworks that made this project possible

---

*Built with ❤️ for Oklahoma's streams and the volunteers who protect them*


