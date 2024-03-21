import types
import re

class AIFunctionManager():
    '''
    This class is used to manage functions for openai chatgpt and anthropic claude based on the API for tool use/function calling of both.
    This enables rapid testing of either model by simply instansiating the class as a chatgpt or claude type.
    '''
    def __init__(self, model,debug=False):
        self.model = model
        self.chatgpt = 'chatgpt'
        self.claude = 'claude'
        self.debug = debug
        try:
          if self.model != self.chatgpt and self.model != self.claude:
            raise ValueError(f'AIFunctionManager can\'t be created with: \'{self.model}\'. Initialize with \'chatgpt\' or \'claude\'')
        except ValueError as e:
          self.printDebug(e)
        
        #container for gpt model instructions
        self.AllToolInstructions = {}

    def callFunctionByName(self, func_name, *args, **kwargs):
        self.printDebug(f"callFunctionByName({func_name, args, kwargs})")
        #This method is how the model accesses the functions
        func = getattr(self, func_name)
        self.printDebug(f"callFunctionByNam:return->({func})")
        return func(*args, **kwargs)

    def claude_construct_tool_prompt(self, name, description, formatted_parameters):
        self.printDebug(f"claude_construct_tool_prompt({name} {description} {formatted_parameters})")
        #package the tool instructions into full description of the tool for Claude using the XML struct
        constructed_prompt =f"<tool_description><tool_name>{name}</tool_name>\n<description>\n{description}\n</description>\n<parameters>\n{formatted_parameters}\n</parameters>\n</tool_description>"
        self.printDebug(f"claude_construct_tool_prompt:return->{constructed_prompt}")
        return constructed_prompt

    def claude_construct_format_parameters_prompt(self, instructions):
        self.printDebug(f"claude_construct_format_parameters_prompt({instructions})")
        #empty string for the XML structures
        formatted_instructions =""
        #generate XML structure for the claude tool
        for i in range(0,len(instructions)):
          formatted_instructions += f"<parameter>\n<name>{instructions[i]['name']}</name>\n<type>{instructions[i]['type']}</type>\n<description>{instructions[i]['description']}</description>\n</parameter>"
        self.printDebug(f"claude_construct_format_parameters_prompt:return->{formatted_instructions}")
        #return XML strut for the tool
        return formatted_instructions
    
    def claude_construct_function_result(self,name,result):
        self.printDebug(f"claude_construct_function_result({name}{result})")
        #format our function output for Claude
        constructed_result_prompt = f"<function_results>\n<result>\n<tool_name>{name}</tool_name>\n<stdout>\n{result}\n</stdout>\n</result>\n</function_results>"
        self.printDebug(f"claude_construct_function_result:return->{constructed_result_prompt}")
        return constructed_result_prompt
    
    def getAllInstructions(self):
        self.printDebug(f"getAllInstructions()")
        #anthropic needs the instructions back as a single string XML format
        if self.model == self.claude:
          instructions = ''.join(str(value) for value in self.AllToolInstructions.values())
          self.printDebug(f"getAllInstructions: return->{instructions}")
        #openai needs the instructions back as a list of dict
        if self.model == self.chatgpt:
          instructions = [value for value in self.AllToolInstructions.values()]
          self.printDebug(f"getAllInstructions: return->{instructions}")
        return instructions
    
    def extract_tool_info(self,model_response):
       self.printDebug(f"extract_tool_info({model_response})")
       ''' CLAUDE - model_response
       Message(id='msg_01S3gfzN39VyYcFVTnxJzzey', content=[ContentBlock(text='Here is how we can create a text file with the contents "hello world" and save it:\n\n<function_calls>\n<invoke>\n<tool_name>write_and_save_file</tool_name>\n<parameters>\n<file_name>hello.txt</file_name>\n<file_data>hello world</file_data>\n</parameters>\n</invoke>\n', type='text')], model='claude-3-sonnet-20240229', role='assistant', stop_reason='stop_sequence', stop_sequence='</function_calls>', type='message', usage=Usage(input_tokens=303, output_tokens=93))
       '''
       '''CHATGPT - model_response
       ChatCompletionMessageToolCall(id='call_cLKvC9aDcgX9xJhXoHvmyipT', function=Function(arguments='{"file_data":"hello world","file_name":"hello_world.txt"}', name='write_and_save_file'), type='function')
       '''
       tool_args = {} #container
       func_name = None #string name of the tool
       if self.model == self.claude:
          #isolate the response
          xml = model_response[0].text
          # tool string name
          func_name = self.extract_value_from_xml_tag('tool_name',xml)
          #get the args
          tool_args = self.claude_tool_arg_extractor(func_name,xml)
       if self.model == self.chatgpt:
          #args
          tool_args = model_response.function.arguments
          #string name
          func_name = model_response.function.name

       self.printDebug(f"extract_tool_info:return->{tool_args, func_name}") 
       return tool_args, func_name

    def create_tool_use_response_prompt(self,model_response,func_name,arguments,results,msg_hist_list):
        ''' CLAUDE - model_response
        Message(id='msg_01S3gfzN39VyYcFVTnxJzzey', content=[ContentBlock(text='Here is how we can create a text file with the contents "hello world" and save it:\n\n<function_calls>\n<invoke>\n<tool_name>write_and_save_file</tool_name>\n<parameters>\n<file_name>hello.txt</file_name>\n<file_data>hello world</file_data>\n</parameters>\n</invoke>\n', type='text')], model='claude-3-sonnet-20240229', role='assistant', stop_reason='stop_sequence', stop_sequence='</function_calls>', type='message', usage=Usage(input_tokens=303, output_tokens=93))
        '''
        '''CHATGPT - model_response
        ChatCompletionMessageToolCall(id='call_cLKvC9aDcgX9xJhXoHvmyipT', function=Function(arguments='{"file_data":"hello world","file_name":"hello_world.txt"}', name='write_and_save_file'), type='function')
        '''
        #TODO: take the current msg history list, add the formatted function results and  put them in the list and return the message history list
        if self.model == self.chatgpt:
          msg_hist_list.append({"role": "assistant", "content": "null","function_call":{"name":func_name,"arguments":arguments}})
          #TODO: maksure that results are safe to return
          msg_hist_list.append({"role":"function","name":func_name,"content":results})
          return msg_hist_list
          
        if self.model == self.claude:
          #TODO: maksure that results are safe to return
          resp_string = self.get_response_content(model_response)
          func_call_msg = self.extract_value_from_xml_tag('invoke',resp_string)
          result_message = "</function_calls>" + func_call_msg + "</function_calls>" + results
          final = {"role": "assistant","content": result_message}
          msg_hist_list.append(final)
          return msg_hist_list

    def get_response_content(self,model_output):
       if self.model == self.chatgpt:
          return model_output.choices[0].message.content
       if self.model == self.claude:
          return model_output[0].text
    
    def use_tool(self,model_response,*additional_arguments_not_from_model,conversation_hist=False):
        #model_response is in  an OpenAI ChatCompletionMessageToolCall or Anthropic Message object
        self.printDebug(f"use_tool({model_response,*additional_arguments_not_from_model})")

        #additional_arguments_not_from_model is typically a callback function
        ''' CLAUDE - model_response
        Message(id='msg_01S3gfzN39VyYcFVTnxJzzey', content=[ContentBlock(text='Here is how we can create a text file with the contents "hello world" and save it:\n\n<function_calls>\n<invoke>\n<tool_name>write_and_save_file</tool_name>\n<parameters>\n<file_name>hello.txt</file_name>\n<file_data>hello world</file_data>\n</parameters>\n</invoke>\n', type='text')], model='claude-3-sonnet-20240229', role='assistant', stop_reason='stop_sequence', stop_sequence='</function_calls>', type='message', usage=Usage(input_tokens=303, output_tokens=93))
        '''
        '''CHATGPT - model_response
        ChatCompletionMessageToolCall(id='call_cLKvC9aDcgX9xJhXoHvmyipT', function=Function(arguments='{"file_data":"hello world","file_name":"hello_world.txt"}', name='write_and_save_file'), type='function')
        '''
        try:
          #takes an OpenAI ChatCompletionMessageToolCall or Anthropic Message object
          argDict,funcName = self.extract_tool_info(model_response)
          #TODO: make sure that the arg structure matches the function dna
          func = getattr(self,funcName)
          #run the function
          results = func(argDict,*additional_arguments_not_from_model)
          #TODO: this assumes a safe string return for results.  However that may not be the case. Add json safe or other checks here
          if self.model == self.claude:
             results = self.claude_construct_function_result(funcName,results)
          self.printDebug(f"use_tool():return->{results}")
          
          if conversation_hist is False:
            print("No convo history")
            return results
          else:
             print("Yes Convo History")
             response = self.create_tool_use_response_prompt(model_response,funcName,argDict,results,conversation_hist)
             return response
        except Exception as e:
            self.printDebug(f"use_tool()->{e}")
    
    def claude_tool_arg_extractor(self,method_string_name,model_args_xml):
      #get the dna from the model again
      func = getattr(self, method_string_name)
      #we only actually need the 'a' argument list from the dna
      d,n,a = func(False,return_instructions=True)
      #get the values as a list, ordered 1,2,3... in terms of positions relative
      #container to repack the args as a dict
      args = {}
      for i in range(0,len(a)):
        #get the tag name that should be in the xml for this argument
        xmlArgTag = a[i]['name']
        #see if the xml had the tag, if not arg_value will be False.  This will happen if there are optional args
        arg_val = self.extract_value_from_xml_tag(xmlArgTag,model_args_xml)
        #if the model did provide an argument for this arg name, pack it
        if arg_val:
          args[xmlArgTag] = arg_val
      return args

    def extract_value_from_xml_tag(self,tag_name,xml_data):
        #create the search pattern using the tag
        pattern = r'<{}>(.+?)</{}>'.format(tag_name, tag_name)
        self.printDebug(f"extract_value_from_xml_tag:pattern->{pattern}") 
        #xtract the value between tags, if tag was found
        matches = re.findall(pattern, xml_data, re.DOTALL)
        #return the value
        if matches:
            #only return the first match, there should also only be 1
            self.printDebug(f"extract_value_from_xml_tag:return->{matches[0]}") 
            return matches[0]
        else:
            return False
        
    def tool_use_system_prompt(self,msg=" "):
        #generate basic system prompt for tool use
        if self.model == self.claude:
          claude_sys_prompt = self.claude_construct_tool_use_system_prompt(msg)
          return claude_sys_prompt
        if self.model == self.chatgpt:
          chatgpt_sys_prompt = self.chagpt_construct_tool_use_system_prompt(msg)
          return chatgpt_sys_prompt

    def chagpt_construct_tool_use_system_prompt(self,msg):
       #this is not a good method. gpt is setup so the sytem prompt is much closer tied to the tool use and no special formatting is needed
       return {"role": "system", "content": f"{msg}. In this environment you have access to a set of tools you can use to answer the user's question"}
    
    def claude_construct_tool_use_system_prompt(self,msg):
        tool_use_system_prompt = (
            msg+"In this environment you have access to a set of tools you can use to answer the user's question.\n"
            "\n"
            "You may call them like this:\n"
            "<function_calls>\n"
            "<invoke>\n"
            "<tool_name>$TOOL_NAME</tool_name>\n"
            "<parameters>\n"
            "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
            "...\n"
            "</parameters>\n"
            "</invoke>\n"
            "</function_calls>\n"
            "\n"
            "Here are the tools available:\n"
            +self.getAllInstructions()
        )
        return tool_use_system_prompt

    def load_tool(self,method):
        self.printDebug(f"load_tool({method})")
        #name for the method
        method_name = method.__name__
        #load the method in to AIFunctionManager instance
        try:
          #bind the method to the instance of self
          bound_method = types.MethodType(method, self)
          #bind the method to the instance as an attribute
          setattr(self, method.__name__, bound_method)
          #create the instruction package that is used by the LLM to know how to use the function
          instructions_for_model = self.create_instruction_pkg(bound_method)
          #add the instruction set to all other LLM method instructions
          self.AllToolInstructions[method_name]=instructions_for_model
          
          #else:
            #raise ValueError('function name must start with gpt_ for it to be loaded.  Please append gpt_ to your function name')
        except Exception as e:
            self.printDebug(f"load_tool->{e}")

    def was_tool_use_requested(self,model_output):
        self.printDebug(f"was_tool_use_requested({model_output})")
        #review the output to see if tool use was requested
        #NOTE - as of March 20,2024 Claude won't send a multi/serial tool use response but ChatGPT will
        if self.model == self.chatgpt:
          if self.get_finish_sequence(model_output) == "tool_calls":
             return True
          else:
             return False
        if self.model == self.claude:
          if self.get_finish_sequence(model_output) == "</function_calls>":
             return True
          else:
             return False
          
    def get_finish_sequence(self,model_output):
       if self.model == self.chatgpt:
          return model_output.choices[0].finish_reason
       if self.model == self.claude:
          return model_output.stop_sequence   

    def create_instruction_pkg(self, method):
        self.printDebug(f"create_instruction_pkg({method})")
        #gather the tool instructions, 'False' is passed to satisfy the *args position. 
        d,n,a = method(False,return_instructions=True)
        #properties required to be in each 'a', argument for the function
        required_keys_in_a = ["name","type","description","required"]
        #check formats of the dna-r
        try:
          if type(d) != str:
              raise ValueError('create_instruction_pkg():function description must be type str')
          if type(n) != str:
              raise ValueError('create_instruction_pkg():function name must be type str')
          if type(a) != list:
              raise ValueError('create_instruction_pkg():function arguments must be type list, function expects a list of dict objects')
          #confirm that each 'a' has the required properties
          for i in range(0,len(a)):
            #review the key of this a
            for key in a[i].keys():
              #missing required key
              if key not in required_keys_in_a:
                  raise ValueError(f"create_instruction_pkg():function arguments missing key:{key}")
        except ValueError as e:
          self.printDebug(f"{e}")

        if self.model == self.claude:
          LLM_instructions = self.mk_anthropic_instruction(d,n,a)
          self.printDebug(f"create_instruction_pkg():return->{LLM_instructions})")
          return LLM_instructions
        if self.model == self.chatgpt:
          LLM_instructions = self.mk_openai_instruction(d,n,a)
          self.printDebug(f"create_instruction_pkg():return->{LLM_instructions})")
          return LLM_instructions    
    
    def mk_anthropic_instruction(self,d,n,a):
        self.printDebug(f"mk_anthropic_instruction({d,n,a})")
        #format the instructions about arguments for the method
        formatted_parameters = self.claude_construct_format_parameters_prompt(a)
        #set what the method is called and how to use it then add to our list of tools
        LLM_instruction_set = self.claude_construct_tool_prompt(n, d, formatted_parameters)
        #return the instruction set
        self.printDebug(f"mk_anthropic_instruction():return->{LLM_instruction_set}")
        return LLM_instruction_set
    
    def mk_openai_instruction(self,d,n,a):
        self.printDebug(f"mk_openai_instruction({d,n,a})")
        #format the instructions about arguments for the method
        args = {}
        required_args = []
        #reformat the 'a' dict to remove the required key, and put those keys in a list for chatgpt
        for i in range(0,len(a)):
          #check if this is a required key
          required = a[i].pop('required')
          if required:
            #put the value of the arg name in the required list of arggs
            required_args.append(a[i]['name'])
        #package each function argument
        for i in range(0,len(a)):
           args[a[i]['name']] = {"type": f"{a[i]['type']}","description": f"{a[i]['description']}"}
        
        #create instruction set
        LLM_instruction_set = {"type": "function",
                              "function": {"name": f"{n}",
                              "description": f"{d}",
                              "parameters":
                                  {"type": "object",
                                   "properties":args,
                                   "required":required_args}}}
        self.printDebug(f"mk_openai_instruction():return->{LLM_instruction_set}")
        return LLM_instruction_set

    #debug printer
    def printDebug(self,message):
      PURPLE = '\033[94m'
      ENDCOLOR = '\033[0m'
      if self.debug:
        print(f"{PURPLE}Debug {self}:{ENDCOLOR}{message}")