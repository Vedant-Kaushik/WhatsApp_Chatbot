# ============================================
# 1. IMPORTS & CONFIGURATION
# ============================================
from pywa import WhatsApp, types, filters
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage,RemoveMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.prompts import PromptTemplate
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START,END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import psycopg
import os,time
import shutil
import json
import PyPDF2
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

DB_URI="postgresql://postgres:postgres@localhost:5432/postgres"
conn = psycopg.connect(DB_URI, autocommit=True)
checkpoint = PostgresSaver(conn)
checkpoint.setup()

# ============================================
# 2. INITIALIZATION (App, LLM, DB)
# ============================================
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

with open("prompts.json", "r") as f:
    data = json.load(f)

class RouteDecision(BaseModel):
    requires_document: Literal["yes", "no"] = Field(description="Whether the question requires document lookup")

router_llm = llm.with_structured_output(RouteDecision)

# ============================================
# 3. HELPER FUNCTIONS (Utilities)
# ============================================

def delete_thread(thread_id: str, user_name: str):
    conn = psycopg.connect(DB_URI)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
    conn.commit()
    conn.close() 

    # Delete persistent vector store if it exists
    persist_directory = f"vector_stores/{user_name}'s_pdf"
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory) 
        time.sleep(0.1) # to avoid race condition

def format_docs (retrieved_docs) :
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return context_text

def get_input_text(context,query):
    prompt_template = PromptTemplate(
        template=data['pdf_prompt'],
        input_variables = ["context", "question"]
    )
    formatted_prompt = prompt_template.invoke({"context": context, "question": query})
    input_text = formatted_prompt.to_string()
    return input_text

def check_for_pdf_query(msg):
    persist_directory = f"vector_stores/{msg.from_user.name}'s_pdf"
    if os.path.exists(persist_directory):
        # Ask LLM: "Does this question need the PDF?"
        decision = router_llm.invoke([HumanMessage(content=msg.text)])
        # decision is striclty yes or no
        if decision.requires_document == "yes":
            # Load vector store and get context
            vector_store = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)
            context = get_pdf_context(vector_store, msg.text)
            # Inject context into the message
            input_text = get_input_text(context,msg.text) 
            return input_text

    return msg.text

def get_input_state(config, input_text):
    current_state = chat_bot.get_state(config)
    if not current_state.values.get("messages"):
        input_state = {
            "messages": [
                SystemMessage(content=data['system_prompt']),  # Use the correct prompt
                HumanMessage(content=input_text)
            ]
        }
    else:
        input_state = {"messages": [HumanMessage(content=input_text)]} # input_text = context + question
    return input_state

# ============================================
# 4. PDF PROCESSING (Vector Store)
# ============================================
def pdf_to_vector_store(filename,name_id):

    # read the file and extract text
    with open(filename, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text()

    # devine a splitter and devide text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1080, chunk_overlap=200)
    chunks = splitter.create_documents([extracted_text])

    # store chunks in vector form in vector store of chroma and save it to disk
    os.makedirs("vector_stores", exist_ok=True)
    persist_directory = f"vector_stores/{name_id}'s_pdf" # overwrrites if pdf is send by same user again
    vector_store = Chroma.from_documents(chunks, embedding_model, persist_directory=persist_directory)

    return vector_store

def get_pdf_context(vector_store, query: str):
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 20, "lambda_mult": 0.7}
    )
    docs = retriever.invoke(query)
    return format_docs(docs)

# ============================================
# 5. MESSAGE HANDLERS (WhatsApp)
# ============================================

# Global set to track processed messages (simple deduplication)
processed_messages = set()

# if user uplaods a document
@wa.on_message(filters.document)
def handle_pdf(_: WhatsApp, msg: types.Message):

    # Deduplicate: If we already processed this message ID, skip it
    if msg.id in processed_messages:
        return
    processed_messages.add(msg.id)

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
    new_path = f"temp_downloads/{msg.from_user.name}.pdf" # overwrrites if pdf is send by same user again
    os.rename(file_path, new_path)
    file_path = new_path

    # Keep the user engaged during processing
    msg.indicate_typing() 

    # 5. Vectorize the pdf and create a vector store
    # overwrrites if pdf is send by same user again
    persist_directory = f"vector_stores/{msg.from_user.name}'s_pdf" 
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory) 
        time.sleep(0.1) # to avoid race condition
    vector_store = pdf_to_vector_store(file_path,msg.from_user.name)
    
    # 6. Retrieve Context from the vector store
    
    msg.indicate_typing()
    query = msg.caption if msg.caption else "Summarize this document"
    context = get_pdf_context(vector_store, query)
    
    # 7. Construct a Composite Message
    input_text = get_input_text(context,query)
    
    # 8. in case of "clear" or new chat 
    input_state = get_input_state(config, input_text)
    
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
        delete_thread(thread_id, msg.from_user.name)
        msg.react("👍")
        return

    # get input text
    input_text = check_for_pdf_query(msg)
    
    # in case of "clear" or new chat 
    input_state = get_input_state(config,input_text)

    response = chat_bot.invoke(input_state, config=config)["messages"][-1].content

    msg.reply(response)


# ============================================
# 6. GRAPH COMPONENTS (LangGraph State)
# ============================================

# Now lets get responses with history from llm

class state_chatbot(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]

class summary_messages(state_chatbot): #inherits from state_chatbot
    summary:str


def chatbot(state:summary_messages):

    message=[] # temporary list to store messages it will be combined with summary and state['messages']

    if state.get('summary'):
        message.append(
            HumanMessage(content=f"converstaion summary \n{state['summary']}")
        )

    message.extend(state['messages'])
    response=llm.invoke(message) 
    return {'messages':[response]}
    
def summarize_conversation(state:summary_messages):

    exsisting_summary=state.get("summary")

    if exsisting_summary:

        prompt=f"exsisting_summary\n{exsisting_summary}\n\n extend the summary using new conversation above"

    else :
        prompt="suumarize the conversation"

    message_and_summary=state["messages"]+[HumanMessage(content=prompt)] # all messages + summary 

    new_summary=llm.invoke(message_and_summary)

    # all messages except last 2
    message_to_delete=state["messages"][:-2]

    return {
        "summary":new_summary.content,
        "messages":[RemoveMessage(id=m.id) for m in message_to_delete],
    }

def should_summarize(state:summary_messages):

    return len(state["messages"])>10 # consedering llm gives long answers

# ============================================
# 7. GRAPH SETUP & INITIALIZATION
# ============================================
def Chatflow():
    graph=StateGraph(summary_messages)

    graph.add_node('chatbot',chatbot)
    graph.add_node('summarize_conversation',summarize_conversation)

    graph.add_edge(START,'chatbot')
    graph.add_conditional_edges(
        'chatbot',
        should_summarize,
        {
            True:"summarize_conversation",
            False:END
        }
    )
    graph.add_edge('summarize_conversation',END)
    
    workflow = graph.compile(checkpointer=checkpoint)

    return workflow

chat_bot=Chatflow()

