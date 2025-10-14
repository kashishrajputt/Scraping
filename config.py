from dotenv import load_dotenv
import os


load_dotenv()


# PostgreSQL database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'ecourts')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', '')


HEADLESS = os.getenv('HEADLESS', 'true').lower() in ('1','true','yes')


# site
BASE_URL = 'https://hcservices.ecourts.gov.in/hcservices/main.php'


# limits
MAX_RESULTS = 20