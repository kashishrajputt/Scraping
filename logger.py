import logging
import os


LOG_DIR = os.path.join(os.getcwd(), 'proofs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)


LOG_PATH = os.path.join(LOG_DIR, 'scraper.log')


logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s',
handlers=[
logging.FileHandler(LOG_PATH),
logging.StreamHandler()
]
)


logger = logging.getLogger('eCourtsScraper')