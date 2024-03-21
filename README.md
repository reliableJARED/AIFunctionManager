# AIFunctionManager
A python function management class that simplifies function with OpenAI ChatGPT and Anthropic Claude.  Specifically the class allows you to load functions in to an instance and easily provide function instructions, receive arguments, and format outputs back to either model with relative ease.  I made this for myself for a different project but figured I'd share since I found it useful.

#Create A Function with the Right Format
Example of how to setup a function that can be used by ChatGPT or Claude via AIFunctionManager:
```python

#Your function arguments, not the 'a' but the actual input, MUST always be in the form Name_of_Function(self,*args,return_instructions=False).
def write_and_save_file(self,*args,return_instructions=False):
        #Function DNA
        # D what does this function do
        d = "this function is used to create and save files to the system"

        # N what is the name of this function
        n = self.write_and_save_file.__name__

        # A what are the arguments to the function
        #each argument instruction is a dict and needs to have a name, type, description and if it's a required argument
        a = [{"name":"file_name","type":"string","description":"accepts a string input to be used as the file name.","required":True},
             {"name":"file_data", "type": "string","description": "accepts a string input that is either code or other file data","required":True},
             {"name":"directory","type": "string","description": "alternative directory location for file","required":False}]

        #the AIFunctionManager will call this function with return_instructions=True so that it knows how to inform the LLM how to use the function    
        if return_instructions:
          return d,n,a
        
        ###IMPORTANT###
        #the LLM can really only send args as json, string or xml.  If you want a callback or other specialized args they need to be injected ALONG with the call
        #this means the DNA for the function could be misleading for a HUMAN, specifically with callback functions in terms of a human reading the 'a' part.
        #it's best to state what additional *args will be so a human knows, in addition to the 'a' for the dna.

        #All of the args the LLM wants to send the function will always be contained in arg[0]
        LLM_arg = arg[0]

        #*args will also contain a callback function 'callback' as arg[1]
        callback = arg[1]
        callback("something to send to a callback function")

        #access the args from the LLM
        file_name = arg[0]['file_name'] #or: arg[0]a[0]['name']
        file_data = arg[0]['file_data'] #or: arg[0]a[1]['name']
        directory = arg[0]['directory'] #or: arg[0]a[2]['name']

        
        #some funciton logic - 
        with open(f'{directory}{file_name}', 'w') as file:
            file.write(file_data)

        #outputs based on the model
        return "File created and saved"
```
 the 'd' is always a string.
 the 'n' should always be ```self.Name_of_Function.__name__ ```
 the 'a' is always a list of dicts


#How to Use AIFunctionManager
First create an instance as either 'claude' or 'chatgpt'
```python
from AIFunctionManager import AIFunctionManager

#pass either 'claude' or 'chatgpt'
#additionally you can pass a debug flag
fm = AIFunctionManager('claude') # AIFunctionManager('claude',debug=True)
```
Then with the instance you can start to load functions.  

```python
#pass our write_and_save_file() function from above to load it in the AIFunctionManager
fm.load_tool(write_and_save_file)

```
Load as many functions as you want using this method, but know that Claude as of (March 20,2024) is best used with 5 or less functions

#ChatGPT Usage
```python
#now get the function instrcutions from all of our loaded functions
instructions = fm.getAllInstructions()
#basic prompt
message = [{"role": "user", "content": "please create a text file that says 'hello world' and save it."}]

chatgpt = OpenAI()
#passing the function instructions to ChatGPT
reqParams_chatgpt= {
            'temperature': 0.9,
            'n': 1,
            'messages':message,
            'tools':instructions,
            'tool_choice':"auto"
            #new
            #'response_format':{ "type": "json_object" },
        }
#request to the API
result_chatgpt = chatgpt.chat.completions.create(model="gpt-4-turbo-preview", **reqParams_chatgpt)
#does ChatGPT want to use a tool?
usetool = fm.was_tool_use_requested(result_chatgpt)
#ChatGPT can return a multi tool request, which is a bit different than Claude.
if usetool:
    for f in range(len(result_chatgpt.choices[0].message.tool_calls)):
        #call the function
        res = fm.use_tool(result_chatgpt.choices[0].message.tool_calls[f],conversation_hist=reqParams_chatgp['message'])
        #res = fm.use_tool(result_chatgpt.choices[0].message.tool_calls[f],IamCallBack)
#send it back to chatgpt
result_chatgpt2 = chatgpt.chat.completions.create(model="gpt-4-turbo-preview", **reqParams_chatgpt)

#... rest of code logic sending resutls back to modle 

```
#Claude Usage
```python
#now get the function instrcutions from all of our loaded functions
instructions = fm.getAllInstructions()

claude = Anthropic()
#basic prompt
message = [{"role": "user", "content": "please create a text file that says 'hello world' and save it."}]
#request to the API
result_claude = claude.messages.create(
    model="claude-3-sonnet-20240229", 
    max_tokens=1024,
    messages=message,
    system="You can use functions",
    stop_sequences=["</function_calls>"],
    temperature = 0.1
)

#does Claude want to use a tool?
usetool = fm.was_tool_use_requested(result_claude)
#Claude can't (as of March 20, 2024) return a multi tool request
if usetool:
    res = fm.use_tool(result_claude.content,IamCallBackFunction,conversation_hist=message)
    #res = fm.use_tool(result_claude.content,IamCallBackFunction) ->do this if you dont want auto formatting of response

#res is already formatted with xml per Claude docs to send the res straight back to claude
#but setting conversation_hist=message will make it so it already has everything needed to send the response back to claude
result_claude2 = claude.messages.create(
    model="claude-3-sonnet-20240229", 
    max_tokens=1024,
    messages=message,
    system="You can use functions",
    stop_sequences=["</function_calls>"],
    temperature = 0.1
)


#... rest of code logic sending resutls back to modle 

```
Above examples are not complete working examples.  It assumes you're familiar with putting model responses back in to the messages parameter and sending another request to ChatGPT or Claude.

The intent is to demonstrate that AIFunctionManager can help make it so without too much effor you can switch metween Claude and ChatGPT when functions are being used.