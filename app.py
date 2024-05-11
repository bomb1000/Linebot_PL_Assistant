# configuration = Configuration(access_token='vbe05kdIZq9OHDPEYphwEiWWeceVm+9ONTcxVC1bkchDji4oWPfQxL8jdEv4sLo72lMz0udPy42qi2ZjA1asKBNrwelxDCI1ih1sK9gjDFLooEHRpn+fyA5yOZ/YUozTCnHPgoippjkrMs3LrfcPFwdB04t89/1O/w1cDnyilFU=')
# handler = WebhookHandler('6caabad552d4be95d53916288baa3d1e')

from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from transformers import pipeline

app = Flask(__name__)

# Set your LINE access token and Hugging Face model here
configuration = Configuration(access_token='YOUR_LINE_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_LINE_SECRET')
chat_pipeline = pipeline("text-generation", model="MediaTek-Research/Breeze-7B-Instruct-v1_0")

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    response_text = chat_pipeline(user_message, max_length=50)[0]['generated_text']

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response_text)]
            )
        )

if __name__ == "__main__":
    app.run()
