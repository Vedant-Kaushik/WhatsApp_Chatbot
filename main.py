from pywa import WhatsApp, types, filters
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START,END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import sqlite3
import os
import json
import PyPDF2

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

embedding_model = GoogleGenerativeAIEmbeddings(
    model="embedding-001"
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

    # mark as read and show typing indicator
    msg.mark_as_read()
    msg.indicate_typing()

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

def pdf_to_vector_store(filename):

    # read the file and extract text
    with open(filename, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        extracted_text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()

    # devine a splitter and devide text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1080, chunk_overlap=200)
    chunks = splitter.create_documents([extracted_text])

    # store chunks in vetor form in vector store of chroma
    vector_store = Chroma.from_documents(chunks,embedding_model)

    return vector_store

# # get vector stroe for that pdf
# vector_store=pdf_to_vector_store(filename)
# so this is the part thats gona go in the pywa pdf handler 

def format_docs (retrieved_docs) :
    context_text = "\n\n".join(doc. page_content for doc in retrieved_docs)
    return context_text


def RAG(filename,query:str):

    # for temp purpose keep it here
    vector_store=pdf_to_vector_store(filename)
    # make retriver out of this vector store
    retriver=vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 20, "lambda_mult": 0.7}
    )

    # make a temp prompt
    temp_prompt = PromptTemplate(
        template=data['pdf_prompt'],
        input_variables = ["context", "question"]
    )

    # from thsi we get context and quetion
    parallel_chain = RunnableParallel({
        'context': retriver | RunnableLambda(format_docs),
        'question': RunnablePassthrough()
    })

    parser = StrOutputParser()
    # make final prompt using main chain

    main_chain = parallel_chain | temp_prompt | llm | parser

    # return final answer
    return main_chain.invoke(query)

def Chatflow():
    graph=StateGraph(state_chatbot)

    graph.add_node('chatbot',chatbot)

    graph.add_edge(START,'chatbot')
    graph.add_edge('chatbot',END)
    
    workflow = graph.compile(checkpointer=chekpointer)
    return workflow

chat_bot=Chatflow()

