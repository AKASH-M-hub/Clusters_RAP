import ollama
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
        'description': 'Search for ONE specific keyword in the document to find page numbers.',
        'parameters': {
            'type': 'object',
            'properties': {
                'keyword': {'type': 'string', 'description': 'ONE exact single keyword to search for'}
            },
            'required': ['keyword']
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
            return pdf_store.search_keyword(current_doc_id, args.get('keyword'))
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
                "If the user asks a question, your VERY FIRST step is to use the 'search_keyword' tool with a SINGLE unique word from their question to find page numbers. "
                "After you get page numbers, you MUST use the 'get_page' tool to read the text. "
                "Only after reading the page text should you provide the final answer. "
                "If the text does not contain the answer, say exactly: 'Insufficient information'."
            )
        },
        {"role": "user", "content": question}
    ]
    
    call_count = 0
    max_budget = 5 
    call_log = []
    
    while call_count < max_budget:
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
            return {"answer": msg.get('content'), "logs": call_log}
            
        messages.append(msg) # Append the assistant's tool call request
        
        # Process Tool Calls
        for tool_call in msg.get('tool_calls', []):
            call_count += 1
            if call_count >= max_budget:
                 final_msg = "Insufficient information. Tool call budget exhausted."
                 call_log.append({"type": "budget_exhausted", "content": final_msg})
                 return {"answer": final_msg, "logs": call_log}
                 
            func = tool_call.get('function', {})
            func_name = func.get('name')
            func_args = func.get('arguments', {})
            
            call_log.append({"type": "tool_call", "name": func_name, "args": func_args})
            
            # Execute tool WITH the hidden doc_id injected safely by Python!
            result = execute_tool(func_name, func_args, doc_id)
            
            # Log the result
            call_log.append({"type": "tool_result", "result": str(result)[:300] + ("..." if len(str(result)) > 300 else "")})
            
            messages.append({
                "role": "tool",
                "content": str(result),
                "name": func_name
            })

    return {"answer": "Insufficient information. Loop exited unexpectedly.", "logs": call_log}
