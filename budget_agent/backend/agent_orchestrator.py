import ollama
import json
import os
from datetime import datetime
from pdf_service import pdf_store

# SIMPLIFIED SCHEMAS FOR 3B MODEL (Removed doc_id to prevent hallucinations)
tool_list_headings = {
    'type': 'function',
    'function': {
        'name': 'list_headings',
        'description': 'Get the table of contents.',
        'parameters': {
            'type': 'object',
            'properties': {},
        }
    }
}

tool_get_page = {
    'type': 'function',
    'function': {
        'name': 'get_page',
        'description': 'Get the full text content of a specific page.',
        'parameters': {
            'type': 'object',
            'properties': {
                'page_number': {'type': 'integer', 'description': 'The page number to read'}
            },
            'required': ['page_number']
        }
    }
}

tool_search_keyword = {
    'type': 'function',
    'function': {
        'name': 'search_keyword',
        'description': 'Search for highly specific keywords in the document to find page numbers. Provide an array of words.',
        'parameters': {
            'type': 'object',
            'properties': {
                'keywords': {
                    'type': 'array', 
                    'items': {'type': 'string'},
                    'description': 'An array of highly specific keywords to search for to narrow down results (e.g., ["conduct", "2024"]).'
                }
            },
            'required': ['keywords']
        }
    }
}

tools = [tool_list_headings, tool_get_page, tool_search_keyword]

def execute_tool(name: str, args: dict, current_doc_id: str):
    """Safely executes the tool and automatically injects the correct doc_id."""
    try:
        if name == 'list_headings':
            return pdf_store.list_headings(current_doc_id)
        elif name == 'get_page':
            return pdf_store.get_page(current_doc_id, args.get('page_number'))
        elif name == 'search_keyword':
            keys = args.get('keywords') or [args.get('keyword')]
            return pdf_store.search_keyword(current_doc_id, keys)
        return f"Error: Unknown tool {name}"
    except Exception as e:
        return f"Error executing tool: {str(e)}"

def run_agent(question: str, doc_id: str, model: str = 'qwen2.5:3b'):
    messages = [
        {
            "role": "system", 
            "content": (
                "You are an AI document reader. "
                "CRITICAL RULE: YOU MUST CALL A TOOL RIGHT NOW. Do not answer the question directly. "
                "If the user asks a question, your VERY FIRST step is to use the 'search_keyword' tool. "
                "CRITICAL: You MUST provide an array of the most rare and specific words from the question to narrow down the search. Do not search for generic topics. "
                "CRITICAL: Do NOT subtract 1 from page numbers. If search returns [8], you MUST call get_page with 8. "
                "After you get page numbers, you MUST use the 'get_page' tool to read the text. "
                "CRITICAL FALLBACK: If 'search_keyword' returns 'not found', you MUST immediately call 'search_keyword' again with DIFFERENT keywords. Do not ask the user for permission. "
                "Only after reading the page text should you provide the final answer. "
                "If the text does not contain the answer, say exactly: 'Insufficient information'."
            )
        },
        {"role": "user", "content": question}
    ]
    
    call_count = 0
    max_budget = 6 
    call_log = []
    
    while True:
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                tools=tools
            )
        except Exception as e:
            return {"answer": f"Failed to connect to Ollama: {str(e)}", "logs": call_log}
        
        msg = response.get('message', {})
        
        # If no tool calls, it's the final answer
        if not msg.get('tool_calls'):
            call_log.append({"type": "final_answer", "content": msg.get('content')})
            
            # Save the execution trace to a JSON file
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "answer": msg.get('content'),
                "total_tool_calls": call_count,
                "trace_logs": call_log
            }
            try:
                log_file = "trace_history.json"
                history = []
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        history = json.load(f)
                history.append(log_entry)
                with open(log_file, "w") as f:
                    json.dump(history, f, indent=4)
            except Exception as e:
                print(f"Error saving log: {e}")
                
            return {"answer": msg.get('content'), "logs": call_log}
            
        messages.append(msg) # Append the assistant's tool call request
        
        # Process Tool Calls
        for tool_call in msg.get('tool_calls', []):
            call_count += 1
            func = tool_call.get('function', {})
            func_name = func.get('name')
            func_args = func.get('arguments', {})
            
            if call_count > max_budget:
                 call_log.append({"type": "budget_exhausted", "content": f"Budget exhausted on {func_name}"})
                 messages.append({
                     "role": "tool",
                     "content": "Error: Budget exhausted. You must provide your final answer immediately using only the information you already have.",
                     "name": func_name
                 })
                 continue
                 
            call_log.append({"type": "tool_call", "name": func_name, "args": func_args})
            
            # Execute tool WITH the hidden doc_id injected safely by Python!
            result = execute_tool(func_name, func_args, doc_id)
            
            messages.append({
                "role": "tool",
                "content": str(result),
                "name": func_name
            })

    return {"answer": "Insufficient information. Loop exited unexpectedly.", "logs": call_log}
