from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import openai
import traceback
from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from langchain.embeddings import OpenAIEmbeddings
import rag_module  # Import the RAG module

# Initialize Flask app
app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Set Linebot and OpenAI configuration
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize SQLAlchemy
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}
connection_string = f"postgresql+psycopg2://{postgresql_config['user']}:{postgresql_config['password']}@" \
                    f"{postgresql_config['host']}/{postgresql_config['database']}"
engine = create_engine(connection_string)
Base = declarative_base()

# Define document table
class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    embedding = Column('embedding', VECTOR(1536))

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Retrieve relevant documents from database
def get_relevant_documents(query, top_n=5):
    embeddings = OpenAIEmbeddings(openai_api_key=openai.api_key)
    query_embedding = embeddings.embed_query(query)
    result = session.query(Document).order_by(func.l2_distance(Document.embedding, query_embedding)).limit(top_n).all()
    return [doc.content for doc in result]

# Listen for all incoming POST requests from /callback
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Handle messages
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        # Generate response using RAG module
        response = rag_module.generate_response(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(response))
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        error_message = '發生錯誤，請稍後再試。錯誤詳情：' + str(e)
        if 'quota' in str(e).lower():
            error_message = '你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息。錯誤詳情：' + str(e)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(error_message))

@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
