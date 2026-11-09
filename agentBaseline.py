from random import random

import agent
import subprocess
import re
import requests
import json
import os
from time import sleep

class AgentAIBaseline(agent.AgentAI):
    '''This class is an agent that uses the Ollama server to generate C code.
    It is a subclass of the AgentAI class.
    It is used to generate C code and compile it using gcc.
    It uses the requests library to communicate with the server.
    It uses the subprocess library to compile the code using gcc.
    It uses the re library to extract the code from the markdown code block.
    It uses the json library to parse the response from the server.
    It uses the tqdm library to show the progress of the iterations.
    
    This class has two pipelines when talking to the model: 
    1. The first one is the main conversation between the model and the user.
    2. The second one is the conversation between the model and the user that is aimed to solve compilation errors.'''

    def __init__(self, server_address, model_name, my_role, language, max_tokens=16000, api_key=""):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.url = self.server_address                # chat API endpoint
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc
        self.language = language                # programming language
        self.max_tokens = max_tokens            # maximum number of tokens to generate
        self.api_key = api_key                  # API key for authentication (if needed)
        self.temp_dir = "temp"                      # temporary directory to store the code files
        
        # the main conversation between the model
        self.messages = [                   
            {"role": "system",
             "content": my_role 
            }
        ] 

        # initial compile messages queue
        self.__initial_compile_messages = [
            {"role": "system",
             "content": my_role
            }
        ]

        # the conversation between the model and the user
        # that is aimed to solve compilation errors
        self.__compile_messages = self.__initial_compile_messages

    def get_response(self, prompt):
        '''This method gets the response from the model.
        It sends the prompt to the model and returns the response.'''
        # send a request to the ollama server
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False,
            "temperature": 0.5,
            "max_completion_tokens": self.max_tokens,             # adjust this parameter to control the length of the output
        }
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        retries = 3
        sleep_time = 60  # seconds
        for attempt in range(retries):
            try:
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=2000*retries)

                if response.status_code == 200:
                    # get the response from the server
                    response_dict = json.loads(response.text)
                    # since the response contains a lot of other things, we need to extract the content
 
                    response_raw = response_dict['choices'][0]['message']['content']                 

                    # this is the difference to the parent class
                    # we do NOT add the response to the messages list
                    return response_raw
                else:
                    # on error, we print the error message
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.Timeout:
                
                time_s = sleep_time * (attempt + 1)
                print(f"Timeout occurred. Waiting for {time_s} seconds before retrying...")
                sleep(time_s) 
                print(f"Retrying {attempt + 1}/{retries}...")
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    return None

    def __get_response_compilation(self, prompt: str) -> str:
        '''This method gets the response from the model. 
        It sends the prompt to the model and returns the response.'''

        
        data = {
            "model": self.model_name,
            "messages": self.__compile_messages,
            "stream": False,
            "temperature": 0.5,
            "max_completion_tokens": self.max_tokens,             # adjust this parameter to control the length of the output
        }
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        # we use three retries just in case the server is busy
        # or there is a timeout
        retries = 3     

        for attempt in range(retries):
            try:
                # communicate with the server
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=2000)

                if response.status_code == 200:
                    # get the response from the server
                    response_dict = json.loads(response.text)

                    # since the response contains a lot of other things, we need to extract the content
                    response_raw = response_dict['choices'][0]['message']['content']  

                    return response_raw
                else:
                    # on error, we print the error message
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.Timeout:
                print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
            return None


    def __extract_c_code(self, markdown):
        '''This function extracts the C code from a markdown string.'''
        try: 
            pattern1 = r"```(c\+\+|c|python|java|ada|Ada|Python|Java|C\+\+|cpp|Cpp|CPP|C|JAVA|PYTHON|ADA)(.*?)```"
            pattern2 = r"```(.*?)```"
            pattern3 = r"```(.*?)$"
            match1 = re.search(pattern1, markdown, re.DOTALL)
            match2 = re.search(pattern2, markdown, re.DOTALL)
            match3 = re.search(pattern3, markdown, re.DOTALL)
            if match1:
                return match1.group(2).strip()
            elif match2:
                return match2.group(1).strip()
            elif match3:
                return match3.group(1).strip()
            else:
                return markdown
        except:
            pass
        return ""
    

    def remove_leading_language_token(self,text: str) -> str:
        """
        Remove the first word only if it is one of:
        ada, rust, haskell, java, c, pthon (case-insensitive).

        Keeps any leading whitespace/newlines intact.
        Only removes the token if it's the first non-whitespace word.
        """
        languages = {"c", "C", "python", "Python", "py", "PYTHON", "java", "Java", "JAVA", "Haskell", "haskell", "HASKELL", "hs", "lhs", "Ada", "ADA", "ada", "adb", "ads", "Rust", "rust", "rs"}

        # Match: leading whitespace (kept), then the first word, then optional spaces/tabs, and an optional single newline.
        m = re.match(r"^(\s*)([A-Za-z]+)([ \t]*\r?\n?)", text)
        if not m:
            return text

        leading_ws, first_word, following = m.groups()

        if first_word.casefold() in languages:
            return leading_ws + text[m.end():]  # remove the first word + the immediate spacing/newline captured
        return text

    def __get_code(self, code: str) -> str:
        '''This method gets the program code generated by the prompt. 
        The generation often results in a markdown code block. 
        This method extracts the code from the markdown block and returns it as a string.
        Line by line, with line breaks.'''
        
        # extract only the block that is between the ```c and ``` lines
        self.code = self.__extract_c_code(code)

        self.code = self.remove_leading_language_token(self.code)
        
        if code != "":
            # remove the first and the last line
            self.code = self.code.split('\n')
            #mdCode = mdCode[1:-1]
            self.code = '\n'.join(self.code)
        
        return self.code
    
    # compile the code using gcc
    def __compile_code(self, code: str) -> str:
        '''This method compiles the code using gcc.
        It returns the result of the compilation.'''

        if self.__code != "":

            temp_file_name = "code_temp"

            #temp_cod_file_path = f'temp/code_temp'
            temp_file = f'task_file.exe'

            random_string = ''.join(str(random.randint(0, 9)) for _ in range(5))

            temp_folder = f"{self.temp_dir}/{self.language}_{random_string}"

            os.makedirs(temp_folder, exist_ok=True)

            if code != "":
                if self.language == "C":
                    with open(f'{temp_folder}/{temp_file_name}.c', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['gcc', '-w', f'{temp_file_name}.c', '-o', temp_file, '-lm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                    exe_file_name = f"./{temp_file}"
                elif self.language == "C++":
                    with open(f'{temp_folder}/{temp_file_name}.cpp', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['g++', '-w', f'{temp_file_name}.cpp', '-o', temp_file, '-lm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                    exe_file_name = f"./{temp_file}"
                elif self.language == "Java":
                    suggested_file_name_java = self.suggest_java_filename(code)
                    with open(f'{temp_folder}/{suggested_file_name_java}.java', 'w+') as f:
                        f.write(code)   
                    result = subprocess.run(['javac', f'{suggested_file_name_java}.java'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                    exe_file_name = suggested_file_name_java
                    #os.remove(f'{temp_folder}/{suggested_file_name_java}.java')
                elif self.language == "Python":
                    with open(f'{temp_folder}/{temp_file_name}.py', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['python3', '-m', 'py_compile', f'{temp_file_name}.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                    exe_file_name = f'{temp_file_name}.py'
                elif self.language == "Ada":
                    with open(f'{temp_folder}/{temp_file_name}.adb', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['gnatmake', f'{temp_file_name}.adb'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,cwd=temp_folder) 
                    #print("RESULT: ", result)
                    exe_file_name = f"./{temp_file_name}"
                elif self.language == "Rust":
                    with open(f'{temp_folder}/{temp_file_name}.rs', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['rustc', f'{temp_file_name}.rs', '-o', temp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder) 
                    exe_file_name = f"./{temp_file}"
                elif self.language == "Haskell":
                    with open(f'{temp_folder}/{temp_file_name}.hs', 'w+') as f:
                        f.write(code)
                    result = subprocess.run(['ghc', f'{temp_file_name}.hs', '-o', temp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                    exe_file_name = f"./{temp_file}"
 


            # check if the output of the compilation contains the word "error"
            if b'error' in result.stderr:
                self.__compile_result = f"Compilation error: {result.stderr.decode()}"
            else:
                self.__compile_result = "Compilation successful"
        else:
            self.__compile_result = "No code found"   

        return self.__compile_result
    


            # Strip comments and string/char literals to avoid false positives
    def _strip_comments_and_strings(self, s: str) -> str:
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)               # block comments
        s = re.sub(r'//.*?$', '', s, flags=re.MULTILINE)               # line comments
        s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)                      # string literals
        s = re.sub(r"'(?:\\.|[^'\\])'", "''", s)                       # char literals
        return s


    def suggest_java_filename(self, source: str, include_package_path: bool = False, sep: str = "/") -> str:
        """
        Return the filename a Java source should have based on its package and top-level type.

        - Prefers a *public* top-level declaration (class/interface/enum/record/@interface).
        - Falls back to the first top-level declaration if no public one exists.
        - If include_package_path=True and a package is present, returns "<pkg/dirs>/<Type>.java".

        Raises:
            ValueError: if no top-level type is found.

        Example:
            name = suggest_java_filename(java_code)                       # "Hello.java"
            path = suggest_java_filename(java_code, True, sep="/")        # "com/example/Hello.java"
        """

        PACKAGE_RE = re.compile(r'(?m)^\s*package\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;')
        PUBLIC_TOP_RE = re.compile(
            r'(?m)^\s*public\s+(?:\w+\s+)*'
            r'(class|interface|enum|record|@interface)\s+([A-Za-z_]\w*)\b'
        )
        ANY_TOP_RE = re.compile(
            r'(?m)^\s*(?:\w+\s+)*'
            r'(class|interface|enum|record|@interface)\s+([A-Za-z_]\w*)\b'
        )

        cleaned = self._strip_comments_and_strings(source)

        # Helper to ensure we only consider top-level (brace depth 0)
        def _is_top_level(idx: int) -> bool:
            pre = cleaned[:idx]
            return pre.count("{") - pre.count("}") == 0

        # Package (if any)
        pkg_match = PACKAGE_RE.search(cleaned)
        pkg = pkg_match.group(1) if pkg_match else None

        # Prefer public top-level declaration
        name = None
        for m in PUBLIC_TOP_RE.finditer(cleaned):
            if _is_top_level(m.start()):
                name = m.group(2)
                break

        # Fallback: first top-level declaration of any visibility
        if not name:
            for m in ANY_TOP_RE.finditer(cleaned):
                if _is_top_level(m.start()):
                    name = m.group(2)
                    break

        if not name:
            filename = "code_temp"

        filename = f"{name}"
        if include_package_path and pkg:
            return f"{pkg.replace('.', sep)}{sep}{filename}"
        return filename


    def __solve_problem(self) -> str:
        '''This method solves the compilation problems using the model.
        It sends the prompt to the model and returns the response.'''     

        strPrompt = f'Ensure the following code is syntactically correct and compiles without errors: {self.__code}'
        
        # please note that we use the __compile_messages list to store the conversation
        # between the model and the user
        self.__compile_messages.append({"role": "user", "content": strPrompt})
        
        # get the response from the model
        strResult = self.__get_response_compilation(strPrompt)
        return strResult
    

    def start(self, tries: int, prompt: str) -> str:
        '''This method starts the agent. 
        It talks to the model and tries to fix problems if there are any.
        It sends the prompt to the model and returns the response.'''
        
        attempt = 0
        __strResult = ""
        
        # get the response from the server

        self.__response = self.get_response(prompt)
        self.__mdCode = self.__get_code(self.__response)
        self.__code = self.__mdCode
        
        # compile the code
        #self.__compile_result = self.__compile_code(self.__code)
        #__strResult = self.__code

        self.messages.append({"role": "assistant", "content": self.__response, "clean_code": self.__code, "attempt": attempt})
        
        while attempt < tries -1:
            # solve the problem
            __strResult = self.__solve_problem()

            # compile the result
            self.__code = self.__get_code(__strResult)
            
            # checking the compilation result of the code
            #self.__compile_result = self.__compile_code(self.__code)

            # if the compilation was successful, we break the loop
            # if the compilation was not successful, we try again

            attempt += 1
            #print(f"Attempt {attempt}: {__strResult}")
            self.messages.append({"role": "assistant", "content": __strResult, "clean_code": self.__code, "attempt": attempt})
        
        strResult = __strResult

        # add this to the messages in the main conversation
        self.messages.append({"role": "assistant", "content": strResult})

        # and clean up the compile messages
        # it is important because the next time we need to solve a problem
        # it is a different problem and the situation must start from scratch
        self.__compile_messages = self.__initial_compile_messages

        # return the result
        return strResult, attempt
