from pywa import WhatsApp, types, filters
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
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

# if user uplaods a document
@wa.on_message(filters.document)
def handle_pdf(_: WhatsApp, msg: types.Message):

    # 1. Get the thread_id for memory
    thread_id = f"whatsapp_{msg.from_user.wa_id}_{msg.from_user.name}"
    config = {"configurable": {"thread_id": thread_id}}

    # 2. Check if it's actually a PDF
    doc = msg.document
    if doc.mime_type != "application/pdf":
        msg.reply("Please send a valid PDF file.")
        return

    # 3. Mark read & Type
    msg.mark_as_read()
    msg.indicate_typing()
    msg.reply("I received your document! Analyzing it now...")
    
    # 4. Download and Vectorize
    os.makedirs("temp_downloads", exist_ok=True)
    file_path = doc.download(path="temp_downloads")
    
    # rename file for readability
    new_path = f"temp_downloads/{msg.from_user.name}.pdf"
    os.rename(file_path, new_path)
    file_path = new_path

    # Keep the user engaged during processing
    msg.indicate_typing() 

    # 5. Vectorize the pdf and create a vector store
    vector_store = pdf_to_vector_store(file_path)
    
    # 6. Retrieve Context from the vector store
    
    msg.indicate_typing()
    query = msg.caption if msg.caption else "Summarize this document"
    context = get_pdf_context(vector_store, query)
    
    # 7. Construct a Composite Message
    prompt_template = PromptTemplate(
        template=data['pdf_prompt'],
        input_variables = ["context", "question"]
    )
    formatted_prompt = prompt_template.invoke({"context": context, "question": query})
    input_text = formatted_prompt.to_string()
    
    # 8. in case of "clear" or new chat 
    current_state = chat_bot.get_state(config)
    if not current_state.values.get("messages"):
        input_state = {
            "messages": [
                SystemMessage(content=data['backup']),
                HumanMessage(content=input_text) # here input text contains context + question
            ]
        }
    else:
        input_state = {"messages": [HumanMessage(content=input_text)]}
    
    # Final type before generation
    msg.indicate_typing() 
    response = chat_bot.invoke(input_state, config=config)["messages"][-1].content
    msg.reply(response)


# if user sends text message
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
        input_state = {
            "messages": [
                SystemMessage(content=data['system_prompt']),
                HumanMessage(content=msg.text)
            ]
        }
    else:
        input_state = {"messages": [HumanMessage(content=msg.text)]}

    response = chat_bot.invoke(input_state, config=config)["messages"][-1].content

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
            extracted_text += page.extract_text()

    # devine a splitter and devide text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1080, chunk_overlap=200)
    chunks = splitter.create_documents([extracted_text])

    # store chunks in vector form in vector store of chroma
    vector_store = Chroma.from_documents(chunks,embedding_model)

    return vector_store



def format_docs (retrieved_docs) :
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return context_text


# New Helper: Just gets the text, doesn't use LLM
def get_pdf_context(vector_store, query: str):
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 20, "lambda_mult": 0.7}
    )
    docs = retriever.invoke(query)
    return format_docs(docs)

def Chatflow():
    graph=StateGraph(state_chatbot)

    graph.add_node('chatbot',chatbot)

    graph.add_edge(START,'chatbot')
    graph.add_edge('chatbot',END)
    
    workflow = graph.compile(checkpointer=chekpointer)
    return workflow

chat_bot=Chatflow()

