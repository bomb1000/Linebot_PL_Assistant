from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')


def GPT_response(text):
    # 使用 chat/completions 端点
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # 确保使用正确的模型名称
        messages=[{"role": "system", "content": "我是您的助理，絕對只使用繁体中文回答您的问题。"} ,{"role": "user", "content": text}],
        temperature=0.5,
        max_tokens=500
    )
    print(response)
    # 重組回應
    answer = response['choices'][0]['message']['content'].replace('。','')
    return answer



# 監聽所有來自 /callback 的 Post Request
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
        abort(400)
    return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = GPT_response(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")  # 印出完整的錯誤堆棧
        error_message = '發生錯誤，請稍後再試。錯誤詳情：' + str(e)  # 顯示錯誤的具體訊息
        if 'quota' in str(e).lower():  # 檢查錯誤是否與額度有關
            error_message = '你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息。錯誤詳情：' + str(e)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(error_message))
       

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
