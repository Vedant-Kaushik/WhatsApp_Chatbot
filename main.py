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
from langchain.tools import tool
from typing import TypedDict, Annotated
import psycopg
import os,time
import shutil
import json
import PyPDF2
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from typing import Literal
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langgraph.store.postgres import PostgresStore
from langchain_tavily import TavilySearch

load_dotenv()

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
conn = psycopg.connect(DB_URI, autocommit=True)
checkpoint = PostgresSaver(conn)
checkpoint.setup()

conn_ltm = psycopg.connect(DB_URI, autocommit=True)
store = PostgresStore(conn_ltm)
store.setup()

# ============================================
# 2. INITIALIZATION (App, LLM, DB)
# ============================================
app = FastAPI()

wa = WhatsApp(
    phone_id=os.getenv("PHONE_ID"),
    token=os.getenv("WHATSAPP_TOKEN"),
    server=app,
    verify_token=os.getenv("VERIFY_TOKEN"),
    app_id=int(os.getenv("APP_ID")),
    app_secret=os.getenv("APP_SECRET"),
    webhook_endpoint="/webhook/meta", 
    filter_updates=False,
    validate_updates=False,
    continue_handling=True,
)

embedding_model = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001"
)

llm=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)

with open("prompts.json", "r") as f:
    data = json.load(f)

class RouteDecision(BaseModel):
    requires_document: Literal["yes", "no"] = Field(description="Whether the question requires document lookup")

router_llm = llm.with_structured_output(RouteDecision)

class MemoryItem(BaseModel):
    text: str = Field(description="Atomic user memory")
    is_new: bool = Field(description="True if new, false if duplicate")

class MemoryDecision(BaseModel):
    should_write: bool
    memories: List[MemoryItem] = Field(default_factory=list)

memory_extractor = llm.with_structured_output(MemoryDecision)

MEMORY_PROMPT = data['memory_prompt']

search_tool = TavilySearch(
    max_results=3,
    topic="general",
    include_images=False,
    include_image_descriptions=False,
)
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

    ns = ("user", thread_id, "details")
    items = store.search(ns)
    for item in items:
        store.delete(ns, item.key)

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

def get_input_state(config, input_text, msg_id: str):
    current_state = chat_bot.get_state(config)
    
    # We leave the user details injection for the chatbot node to handle dynamically
    if not current_state.values.get("messages"):
        input_state = {
            "messages": [
                HumanMessage(content=input_text)
            ],
            "msg_id": msg_id
        }
    else:
        input_state = {"messages": [HumanMessage(content=input_text)],"msg_id":msg_id} # input_text = context + question
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

    # Check if the PDF had any readable text
    if not extracted_text.strip():
        return None

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

@wa.on_message(filters.image)
def handle_image(client: WhatsApp, msg: types.Message):
    """Handle incoming image messages — no disk storage needed."""
    
    thread_id=f"whatsapp_{msg.from_user.wa_id}_{msg.from_user.name}"
    config = {"configurable": {"thread_id": thread_id}}

    # Download image bytes directly into memory
    image_bytes = msg.image.download(in_memory=True)
    
    import base64
    image_data = base64.b64encode(image_bytes).decode()
    mime = msg.image.mime_type or "image/jpeg"
    
    # Pass to Gemini 2.5 Flash as multimodal message
    human_msg = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_data}"}
        },
        {
            "type": "text",
            "text": msg.caption or "Analyse this image and describe what you see."
        }
    ])
    
    result = chat_bot.invoke({"messages": [human_msg]}, config=config)
    reply = result["messages"][-1].content
    
    if(type(reply)==str): 
        msg.reply(reply)
    else:
        msg.reply(reply[0]['text'])

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
    try:
        msg.mark_as_read()
    except Exception:
        pass  # Gracefully handle DNS failures on HF
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
    
    if not vector_store:
        msg.reply("I couldn't read any text from that PDF. It might be an image-based scan or completely empty!")
        return
    
    # 6. Retrieve Context from the vector store
    
    msg.indicate_typing()
    query = msg.caption if msg.caption else "Summarize this document"
    context = get_pdf_context(vector_store, query)
    
    # 7. Construct a Composite Message
    input_text = get_input_text(context,query)
    
    # 8. in case of "clear" or new chat 
    input_state = get_input_state(config, input_text,msg.id)
    
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
    try:
        msg.mark_as_read()
    except Exception:
        pass  # Gracefully handle DNS failures on HF
    msg.indicate_typing()

    if msg.text == "clear":
        delete_thread(thread_id, msg.from_user.name)
        msg.react("👍")
        return

    # get input text
    input_text = check_for_pdf_query(msg)
    
    # in case of "clear" or new chat 
    input_state = get_input_state(config,input_text,msg.id)

    # i need to pass meesage i here for remember node name space
    response = chat_bot.invoke(input_state, config=config)["messages"][-1].content

    if(type(response)==str): 
        msg.reply(response)
    else:
        msg.reply(response[0]['text'])


# ============================================
# 6. GRAPH COMPONENTS (LangGraph State)
# ============================================

# Now lets get responses with history from llm

class state_chatbot(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]
    msg_id:str

class summary_messages(state_chatbot): #inherits from state_chatbot
    summary:str

@tool
def web_search(query:str):
    """Search the web for information. Ensure you use reputed and authoritative sources."""
    results= search_tool.invoke({"query": query})
    best_result = max(results['results'], key=lambda x: x['score'])
    return f"for title: {best_result['title']} \n\n from source: {best_result['url']} \n\n the content is: {best_result['content']}"

llm = llm.bind_tools([web_search])

def chatbot(state:summary_messages,config :RunnableConfig,store:BaseStore):

    message=[] # temporary list to store messages it will be combined with summary and state['messages']

    user_id = config["configurable"]["thread_id"]
    ns = ("user", user_id, "details") # name space for LTM
    
    items = store.search(ns)
    user_details = "\n".join(it.value.get("data", "") for it in items) if items else ""

    # Inject LTM context into the unified system prompt from prompts.json
    system_msg = SystemMessage(
        content=data["system_prompt"].format(
            user_details_content=user_details or "(empty)",
            current_time=datetime.now().strftime('%Y-%m-%d %I:%M:%S %p'),
        )
    )

    if state.get('summary'):
        message.append(
            HumanMessage(content=f"converstaion summary \n{state['summary']}")
        )

    message.extend(state['messages'])
    response=llm.invoke([system_msg] + message) 
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


def search_summarizer_checker(state:summary_messages):
    last_message = state["messages"][-1]
    # Check 1: Does the LLM want to call a tool?
    if last_message.tool_calls:
        return "tools"
    # Check 2: Should we summarize?
    if len(state["messages"]) > 10:
        return "summarize"
    return "end"


def remember_node(state: summary_messages, config: RunnableConfig,  store: BaseStore):

    user_id = config["configurable"]["thread_id"]
    ns = ("user", user_id, "details")

    # existing memory (all items under namespace)
    items = store.search(ns)
    existing = "\n".join(it.value.get("data", "") for it in items) if items else "(empty)"

    # latest user message
    last_text = state["messages"][-1].content

    decision: MemoryDecision = memory_extractor.invoke(
        [
            SystemMessage(content=MEMORY_PROMPT.format(user_details_content=existing)),
            HumanMessage(content=last_text),
        ]
    )
    
    if decision.should_write:
        for mem in decision.memories:
            if mem.is_new and mem.text.strip():
                # msg.id is used as key for memory
                store.put(ns, state["msg_id"], {"data": mem.text.strip()})

    return {}

# ============================================
# 7. GRAPH SETUP & INITIALIZATION
# ============================================
def Chatflow():
    graph=StateGraph(summary_messages)

    graph.add_node("remember", remember_node)
    graph.add_node('chatbot',chatbot)
    graph.add_node('summarize_conversation',summarize_conversation)
    graph.add_node("tools", ToolNode([web_search]))

    graph.add_edge(START,'remember')
    graph.add_edge("remember","chatbot")
    graph.add_conditional_edges(
        'chatbot',
        search_summarizer_checker,
        {
            "tools": "tools",
            "summarize": "summarize_conversation",
            "end": END
        }
    )
    graph.add_edge("tools", "chatbot")
    graph.add_edge('summarize_conversation',END)
    
    workflow = graph.compile(checkpointer=checkpoint,store=store)
    return workflow

chat_bot=Chatflow()

