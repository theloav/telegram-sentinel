import logging
import os
from telethon import TelegramClient, events
import asyncio
import re
from transformers import pipeline
from dotenv import load_dotenv  # Import dotenv package

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()  # Load environment variables from .env file

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
developer_id = os.getenv('DEVELOPER_ID')

# Check for required environment variables
if not all([api_id, api_hash, bot_token, developer_id]):
    logger.error("Missing one or more required environment variables: API_ID, API_HASH, BOT_TOKEN, DEVELOPER_ID")
    raise ValueError("Missing one or more required environment variables.")

# Initialize Telegram Client for Bot
client = TelegramClient('bot', api_id, api_hash)

# Suspicious Keywords
suspicious_keywords = [
    'ICO', 'pump and dump', 'get rich quick', 'phishing',  # General keywords
    'double your money', 'high returns', 'guaranteed profit',  # Investment scams
    'crypto mining', 'investment opportunity', 'binary options', 'no risk'
]

urgency_keywords = ['act now', 'limited time', 'urgent', 'only today']

# Load Pre-trained NLP Models
sentiment_analyzer = pipeline("sentiment-analysis")
text_classifier = pipeline(
    "text-classification",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# AI-Powered Scam Detector
def analyze_message_with_ai(message):
    """Use AI model to classify message content."""
    result = text_classifier(message)
    return result[0]['label'], result[0]['score']  # Label and confidence score

def find_trigger_keywords(message, keywords):
    """Find keywords that triggered detection."""
    return [kw for kw in keywords if kw.lower() in message.lower()]

def extract_monetary_values(message):
    """Extract monetary values mentioned in the message."""
    return re.findall(r'\$\d+|\d+ USD|\u20b9\d+|\d+ INR', message)

def analyze_sentiment(message):
    """Analyze sentiment of the message."""
    result = sentiment_analyzer(message)[0]
    return result['label'], result['score']

async def process_message(chat, sender, message):
    """Check and report suspicious messages."""
    if not message:  # Handle non-text messages
        logger.debug(f"Non-text message received in {chat.title} by {sender}. Skipping analysis.")
        return

    logger.info(f"Processing message in {chat.title} from @{sender}: {message}")
    triggered_keywords = find_trigger_keywords(message, suspicious_keywords)
    monetary_values = extract_monetary_values(message)
    triggered_urgency = find_trigger_keywords(message, urgency_keywords)

    # AI-Powered Analysis
    sentiment_label, sentiment_score = analyze_sentiment(message)
    classification_label, classification_score = analyze_message_with_ai(message)

    logger.debug(f"Analysis results: Sentiment={sentiment_label}, Classification={classification_label}")

    # Determine if the message is suspicious
    if (triggered_keywords or monetary_values or triggered_urgency or 
        classification_label.lower() == 'scam' or classification_score > 0.8):
        logger.warning(f"Suspicious message detected in {chat.title} by @{sender}")
        await report_suspicious_activity(
            chat, sender, message, triggered_keywords, monetary_values, triggered_urgency,
            sentiment_label, sentiment_score, classification_label, classification_score
        )

@client.on(events.NewMessage)
async def handler(event):
    """Handle new messages in real-time."""
    chat = await event.get_chat()
    sender = await event.get_sender()
    message = event.message.message  # Text content of the message

    sender_username = sender.username if sender and sender.username else 'Unknown'

    logger.info(f"New message in {chat.title} by @{sender_username}")
    await process_message(chat, sender_username, message)

async def report_suspicious_activity(chat, sender, message, keywords, monetary_values, urgency, 
                                     sentiment_label, sentiment_score, classification_label, classification_score):
    """Report suspicious activity to the developer."""
    keywords_list = ', '.join(keywords) if keywords else 'None'
    monetary_list = ', '.join(monetary_values) if monetary_values else 'None'
    urgency_list = ', '.join(urgency) if urgency else 'None'

    alert_message = f"""
    🚨 **Suspicious Activity Alert** 🚨
    **Channel**: {chat.title}
    **Sender**: @{sender}
    **Message**: {message}
    **Detected Keywords**: {keywords_list}
    **Monetary Values**: {monetary_list}
    **Urgency Indicators**: {urgency_list}
    **Sentiment Analysis**: {sentiment_label} (Score: {sentiment_score:.2f})
    **AI Classification**: {classification_label} (Confidence: {classification_score:.2f})
    """
    logger.info(f"Reporting suspicious message to developer: {developer_id}")
    await client.send_message(developer_id, alert_message)

async def main():
    """Main function to start the bot and schedule tasks."""
    await client.start(bot_token=bot_token)
    logger.info("Bot is running...")
    await client.run_until_disconnected()

# Run the Bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

