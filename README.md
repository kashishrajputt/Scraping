# eCourts High Court Case Status Scraper

A modular, asynchronous Python pipeline for scraping case status information from the eCourts High Court portal (https://hcservices.ecourts.gov.in/hcservices/main.php).

## Features

- **Asynchronous Web Scraping**: Built with Playwright for robust browser automation
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **High Court Enumeration**: Automatically discovers all available High Courts
- **Bench Discovery**: Enumerates benches for selected High Courts
- **Multiple Search Types**: Supports both Party Name and Case Number searches
- **CAPTCHA Handling**: Integrated CAPTCHA solving capabilities
- **Database Integration**: SQLite database for storing results
- **Error Handling**: Comprehensive retry mechanisms and error recovery
- **Logging**: Detailed logging for monitoring and debugging

## Project Structure

```
vakildesk/
├── main.py              # Main pipeline orchestrator
├── scapper.py           # Core scraping functions
├── database.py          # Database management
├── captcha_solver.py    # CAPTCHA solving module
├── config.py           # Configuration settings
├── logger.py           # Logging configuration
├── utils.py            # Utility functions
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
└── proofs/            # Logs and screenshots
```

## Installation

1. **Clone or download the project**
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

5. **Create environment file** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Configuration

### Environment Variables (.env file)

```env
# Database settings (optional - defaults to SQLite)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecourts
DB_USER=postgres
DB_PASS=your_password


# Browser settings
HEADLESS=false  # Set to true for headless mode

# Site configuration
BASE_URL=https://hcservices.ecourts.gov.in/hcservices/main.php
MAX_RESULTS=20
```

## Usage

### Basic Usage

Run the main scraper:

```bash
python main.py
```

