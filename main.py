from pywa import WhatsApp, types, filters
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START,END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import sqlite3
import os
import json

load_dotenv()
conn = sqlite3.connect("conversation.db", check_same_thread=False)
chekpointer = SqliteSaver(conn)

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

def delete_thread(thread_id: str):
    conn = sqlite3.connect("conversation.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close() 

with open("prompts.json", "r") as f:
    data = json.load(f)

@wa.on_message(filters.text)
def Chatting(_: WhatsApp, msg: types.Message):

    thread_id=f"whatsapp_{msg.from_user.wa_id}_{msg.from_user.name}"
    config={"configurable": {"thread_id": thread_id}}

    if msg.text == "clear":
        delete_thread(thread_id)
        msg.react("👍")
        return

    current_state = chat_bot.get_state(config)

    # in case of "clear" or new chat 
    if not current_state.values.get("messages"):
        initial_state = {
            "messages": [
                SystemMessage(content=data['system_prompt']),
                HumanMessage(content=msg.text)
            ]
        }
    else:
        initial_state = {"messages": [HumanMessage(content=msg.text)]}
    
    response = chat_bot.invoke(initial_state, config=config)["messages"][-1].content

    msg.reply(response) 


# Now lets get responses with history from llm

def chatbot(state_chatbot):
    message=state_chatbot['messages']
    response=llm.invoke(message) 
    return {'messages':[response]}
    
class state_chatbot(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]

def Chatflow():
    graph=StateGraph(state_chatbot)

    graph.add_node('chatbot',chatbot)

    graph.add_edge(START,'chatbot')
    graph.add_edge('chatbot',END)
    
    workflow = graph.compile(checkpointer=chekpointer)
    return workflow

chat_bot=Chatflow()

