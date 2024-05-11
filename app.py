# configuration = Configuration(access_token='vbe05kdIZq9OHDPEYphwEiWWeceVm+9ONTcxVC1bkchDji4oWPfQxL8jdEv4sLo72lMz0udPy42qi2ZjA1asKBNrwelxDCI1ih1sK9gjDFLooEHRpn+fyA5yOZ/YUozTCnHPgoippjkrMs3LrfcPFwdB04t89/1O/w1cDnyilFU=')
# handler = WebhookHandler('6caabad552d4be95d53916288baa3d1e')

from flask import Flask, request, abort
import openai
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

app = Flask(__name__)

# Set your LINE and OpenAI credentials here
configuration = Configuration(access_token='vbe05kdIZq9OHDPEYphwEiWWeceVm+9ONTcxVC1bkchDji4oWPfQxL8jdEv4sLo72lMz0udPy42qi2ZjA1asKBNrwelxDCI1ih1sK9gjDFLooEHRpn+fyA5yOZ/YUozTCnHPgoippjkrMs3LrfcPFwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('6caabad552d4be95d53916288baa3d1e')
openai.api_key = 'sk-proj-Dp7vuumKPJGQ2LnUcdjyT3BlbkFJg4msj26G1U8jheUUGsaA'

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
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",  # You can change the model as needed
        prompt=user_message,
        max_tokens=150
    )
    response_text = response.choices[0].text.strip()

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
