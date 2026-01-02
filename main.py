from pywa import WhatsApp, types, filters
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START,END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import os
load_dotenv()

app = FastAPI()
wa = WhatsApp(
    phone_id=os.getenv("PHONE_ID"),
    token=os.getenv("WHATSAPP_TOKEN"),
    server=app,
    callback_url=os.getenv("CALLBACK_URL"),
    verify_token=os.getenv("VERIFY_TOKEN"),
    app_id=int(os.getenv("APP_ID")),
    app_secret=os.getenv("APP_SECRET"),
    webhook_endpoint="/webhook/meta", 
    filter_updates=False,
    validate_updates=False,
    continue_handling=True,
)
llm=ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)

current_state = {
    "messages": [SystemMessage(content="you are a helpful assistant working on gemini 3 pro")]
}

@wa.on_message(filters.text)
def Chatting(_: WhatsApp, msg: types.Message):
    global current_state
    if msg.text == "clear": 
        current_state = {
            "messages": [
                SystemMessage(content="you are a helpful assistant working on gemini 3 pro")
            ]
        }
        msg.react("👍")
        return
    
    current_state['messages'].append(HumanMessage(content=msg.text))

    response=chat_bot.invoke(current_state)['messages'][-1].content
    
    msg.reply(response) 


# Now lets get responses with history from llm

def chatbot(state_chatbot):
    message=state_chatbot['messages']
    # meesages contains full history 
    response=llm.invoke(message) 
    return {'messages':[response]}
    
class state_chatbot(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]

def Chatflow():
    graph=StateGraph(state_chatbot)

    graph.add_node('chatbot',chatbot)

    graph.add_edge(START,'chatbot')
    graph.add_edge('chatbot',END)

    workflow=graph.compile()
    return workflow

chat_bot=Chatflow()

