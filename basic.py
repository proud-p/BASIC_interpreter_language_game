from utils.strings_with_arrows import string_with_arrows
import string

#################################################
# TOKENS
#################################################

# TT stands for Token Type
TT_INT = "TT_INT"
TT_FLOAT = "FLOAT"
TT_IDENTIFIER = "IDENTIFIER"
TT_KEYWORD = "KEYWORD"
TT_PLUS = "PLUS"
TT_MINUS = "MINUS"
TT_MUL = "MUL"
TT_DIV = "DIV"
TT_EQ = "EQ"
TT_LPAREN = "LPAREN"
TT_RPAREN  = "RPAREN"
TT_POWER = "POWER"
TT_EOF  = "EOF" # End of File token, used to indicate the end of the input text

class Token:
    def __init__(self,type_,value=None, pos_start = None,pos_end = None):
        self.type =  type_
        self.value = value
        
        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy().advance()
             
        if pos_end: 
            self.pos_end = pos_end
        
    def matches(self, type_, value):
        return self.type == type_ and self.value == value
    
    def __repr__(self): # representation method so it looks nice when printed out in the terminal window
        if self.value: return f"{self.type}:{self.value}"
        return f"{self.type}"
    
#################################################
# DIGITS CONSTNANTS
#################################################
    
DIGITS = "0123456789"
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + DIGITS

KEYWORDS = ["VAR"]

#################################################
# ERRORS
#################################################

class Error:
    def __init__(self,pos_start, pos_end, error_name, details):
        self.error_name = error_name
        self.details = details
        self.pos_start = pos_start
        self.pos_end = pos_end
    
    def as_string(self):
        result = f"{self.error_name}: {self.details}"
        result += f"\nFile {self.pos_start.fn}, line {self.pos_start.ln + 1}"
        result += f", column {self.pos_start.col + 1}"
        result += f" to {self.pos_end.ln + 1}, column {self.pos_end.col + 1}"
        result += "\n\n" + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return result
    
class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Illegal Character", details)
        
class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Invalid Syntax", details)
        
class RTError(Error):
    def __init__(self,pos_start,pos_end,details):
        super().__init__(pos_start, pos_end, "Runtime Error", details)
        
#################################################
# POSITION
#################################################

class Position:
    def __init__(self,idx, ln,col, fn, ftxt=None):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn #file name
        self.ftxt = ftxt #file text, not used in this lexer but could be useful for error messages
    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1
        
        if current_char == "\n":
            self.ln += 1
            self.col = 0
            
        return self
    
    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt) # return a copy of the position so we can save the position before we advance it
    

#################################################
# LEXER
#################################################

class Lexer:
    """A lexer is a class that takes a string of text and breaks it down into tokens.
It is the first step in the process of interpreting or compiling a programming language.
In this case, it will take a string of BASIC code and break it down into tokens that can be used by the parser.
    The lexer will ignore whitespace and comments, and will return a list of tokens that represent the code.
    Each token will have a type and a value. The type will be one of the token types defined above, and the value will be the actual value of the token.
    For example, the string "1 + 2" will be broken down into three tokens: an integer token with value 1, a plus token with no value, and an integer token with value 2.
    """
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1,0,-1,fn=fn,ftxt=text) # initialize the position with -1 index, 0 line number, and -1 column number, -1 column number so we can advance to the first character to 0
        self.current_char = None
        self.advance() # initialize the lexer by setting the text, position, and current character
        
    def advance(self, current_char=None):
        self.pos.advance(self.current_char) # advance the position by one character
        self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None #advance the position and set the current character to None if we are at the end of the text
        
    def make_tokens(self):
        tokens = []
        
        while self.current_char != None:
            if self.current_char in "\t\n\r ": # ignore whitespace characters
                self.advance()
            elif self.current_char in DIGITS:
                tokens.append(self.make_number())
            elif self.current_char in LETTERS:
                tokens.append(self.make_identifier())
            elif self.current_char == "+":
                tokens.append(Token(TT_PLUS, pos_start=self.pos))
                self.advance()
            elif self.current_char == "-":
                tokens.append(Token(TT_MINUS, pos_start=self.pos))
                self.advance()
            elif self.current_char == "*":
                tokens.append(Token(TT_MUL, pos_start=self.pos))
                self.advance()
            elif self.current_char == "/":
                tokens.append(Token(TT_DIV, pos_start=self.pos))
                self.advance()
            elif self.current_char == "^": # power operator
                tokens.append(Token(TT_POWER, pos_start=self.pos))
                self.advance()
            elif self.current_char == "=": # power operator
                tokens.append(Token(TT_EQ, pos_start=self.pos))
                self.advance()
            elif self.current_char == "(":
                tokens.append(Token(TT_LPAREN, pos_start=self.pos))
                self.advance()
            elif self.current_char == ")":
                tokens.append(Token(TT_RPAREN, pos_start=self.pos))
                self.advance()
            else:
                pos_start = self.pos.copy()# save the position before we advance
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, f"Error on {pos_start.idx} to {self.pos.idx} since '{char}' is not a valid token") # return no tokens and an error if we encounter an illegal character
          
        tokens.append(Token(TT_EOF, pos_start=self.pos)) # add an end of file token to the list of tokens
        self.advance() # advance the position to the end of the file
        return tokens, None # return the list of tokens and None for no error
    
    def make_number(self):
        num_str = ""
        dot_count = 0 #is it a float or an int?
        pos_start = self.pos.copy() # save the position before we advance
        
        while self.current_char != None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1: break # can't have more than one dot in a number
                
                dot_count += 1
                num_str += "."
            else:
                num_str += self.current_char
            self.advance()
            
        if dot_count == 0:
            return Token(TT_INT, int(num_str), pos_start=pos_start, pos_end=self.pos)
        else:
            return Token(TT_FLOAT, float(num_str),pos_start=pos_start, pos_end=self.pos)
        
    def make_identifier(self):
        id_str = ""
        pos_start = self.pos.copy()
        
        while self.current_char !=None and self.current_char in LETTERS_DIGITS + "_": #allow _
            id_str += self.current_char
            self.advance()
            
        tok_type = TT_KEYWORD if id_str in KEYWORDS else TT_IDENTIFIER #if string in keywords (like print) then keyword else identifier
        return Token(tok_type, id_str, pos_start, self.pos)
#################################################
# NODES CLASSES
#################################################

class NumberNode:
    def __init__(self,token):
        self.tok = token
        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end
    def __repr__(self): #return a string containing a printable representation of an object
        return f"{self.tok}"
    
class BinOpNode:
    def __init__(self,left_node,op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node
        
        self.pos_start = self.left_node.pos_start
        self.pos_end = self.right_node.pos_end
        
    def __repr__(self):
        return f"({self.left_node}, {self.op_tok}, {self.right_node})"

class UnaryOpNode: # for unary operations like -5 or +5
    """Unary operations are operations that only have one operand, such as negation or positive sign"""
    def __init__(self,op_tok, node):
        self.op_tok = op_tok
        self.node = node
        
        self.pos_start = self.op_tok.pos_start
        self.pos_end = node.pos_end
        
    def __repr__(self):
        return f"({self.op_tok}, {self.node})"
    
class VarAccessNode:
    def __init__(self, var_name_tok):
        self.var_name_tok = var_name_tok
        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok.pos_end
        
class VarAssignNode:
    def __init__(self, var_name_tok, value_node):
        self.var_name_tok = var_name_tok
        self.value_node = value_node
        
        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok.pos_end
#################################################
# PARSE RESULT
#################################################
class ParseResult: 
    def __init__(self):
        self.error = None
        self.node = None
        
        
    def register(self, res):
        pass
    
    def register(self, res): # register a result from a function call
        if isinstance(res,ParseResult): #if res is a parse result class object
            if res.error: self.error = res.error
            return res.node
        
        
    def success(self, node): # if the result is successful
        self.node = node
        return self
    
    def failure(self, error): # if the result is a failure
        self.error = error
        return self



#################################################
# PARSER
#################################################

class Parser:
    def __init__(self,tokens):
        self.tok = tokens
        self.tok_idx = -1 #token index
        self.advance()
        
    def advance(self):
        self.tok_idx += 1
        if self.tok_idx < len(self.tok):
            self.current_tok = self.tok[self.tok_idx]
        return self.current_tok 
    
    def parse(self): #call expression - advance till find plus or minus
        res = self.expr()
        if not res.error and self.current_tok.type != TT_EOF:
            return res.failure(InvalidSyntaxError(self.current_tok.pos_start, self.current_tok.pos_end, "Expected '+', '-', '*', '/', '^' or EOF"))
        return res
    
    def power(self):
        return self.bin_op(self.atom, (TT_POWER,), self.factor)
    
    def atom(self):
        res = ParseResult() #create a parse result object
        tok = self.current_tok
        
        if tok.type == TT_IDENTIFIER:
            res.register(self.advance())
            return res.success(VarAccessNode(tok))
        
        #normal operations
        elif tok.type in (TT_INT, TT_FLOAT):
            res.register(self.advance()) #wrap the advance in a parse result object but not doing anything yet
            return res.success(NumberNode(tok)) #recursive functions since call eachother
        
        #if token is a left parenthesis, call expression and return the node
        elif tok.type == TT_LPAREN:
            res.register(self.advance()) #advance to the next token
            node = res.register(self.expr()) #call expression to get the next node
            if res.error: return res #if there is an error, return the error
            
            if self.current_tok.type == TT_RPAREN: #if the next token is not a right parenthesis, return an error
               res.register(self.advance()) #advance to the next token if right parenthesis is found
            else:
                return res.failure(InvalidSyntaxError(self.current_tok.pos_start, self.current_tok.pos_end, "Expected ')'"))
            return res.success(node) #return the node

        return res.failure(InvalidSyntaxError(tok.pos_start, tok.pos_end, "Expected int, float, + , - or ()")) #if not an int or float, return an error , + and - included b/c atom only called inside power which is called inside factor so has to include all the things in factor as well
        
    def factor(self): #if token is int or float advance and return number node class
        res = ParseResult() #create a parse result object
        tok = self.current_tok
        
        #unary operations
        if tok.type in (TT_PLUS,TT_MINUS): #if token is a plus sign, advance and return a unary operation node
            res.register(self.advance()) #advance to the next token
            node = res.register(self.factor()) #call factor again to get the next node
            if res.error: return res
            return res.success(UnaryOpNode(tok, node)) #return a unary operation node with the token and the node
        
        return self.power()
    
    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV, TT_POWER))
        
    
    def expr(self):
        res = ParseResult()
        
        if self.current_tok.matches(TT_KEYWORD, "VAR"):
            res.register(self.advance())
        
            if self.current_tok.type != TT_IDENTIFIER: #if not identifier error
                return res.failure(InvalidSyntaxError(self.current_tok.pos_start , self.current_tok.pos_end, "Expected Identifier"))
            
            var_name = self.current_tok #current token is var name
            res.register(self.advance())
            
            # now look for = to know when var name ends
            if self.current_tok.type != TT_EQ:
                return res.failure(InvalidSyntaxError(self.current_tok.pos_start , self.current_tok.pos_end, "Expected '='"))
            res.register(self.advance())
            expr = res.register(self.expr())
            if res.error: return res
            
            return res.success(VarAssignNode(var_name, expr))
            
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))
    
    
    def bin_op(self, func_a, ops, func_b=None): # pass in rule and accepted operations, func needs to be wrapped in ParseResult so we can register the result of the function call
        # since term and expression is basically the same with the difference being it's either doing the same operation on a factor or a term, we can create a code that can be used for both 
        #scenarios
        
        if func_b is None:
            func_b = func_a
        
        res = ParseResult() #create a parse result object
        left =  res.register(func_a()) #register will take in the parse result from the call to this function and return the node from the function call
        
        if res.error: return res # if there is an error, return the error
        
        while self.current_tok.type in ops: #if current tok is operation token
            op_tok = self.current_tok
            res.register(self.advance()) #advance to next
            right = res.register(func_b())
            
            if res.error: return res # if there is an error, return the error
            
            left = BinOpNode(left,op_tok,right)
            
        return res.success(left) #now a binary operation node because we re-assigned it - becomes a term
        

#################################################
# Runtime Result
#################################################

class RTResult:
    def __init__(self):
        self.value = None
        self.error = None
    
    def register(self,res):
        if res.error: self.error = res.error
        return res.value
    
    def success(self,value):
        self.value = value
        return self

    def failure(self, error):
        self.error = error
        return self


#################################################
# Values
#################################################

class Number: #class to store number and operating on them with other numbers
    def __init__(self, value):
        self.value = value #python number
        self.set_pos()
        self.set_context() #set context to None by default, can be set later when we assign a variable
        
    def set_pos(self, pos_start =None, pos_end = None): #position in case there are errors
        self.pos_start = pos_start
        self.pos_end = pos_end
        
        return self
    
    def set_context(self, context =None):
        # context is used to store the context of the variable, e.g. global or local
        # context None means no context, e.g. when we create a number in the interpreter
        self.context = context
        return self
    
    def added_to(self,other):
        if isinstance(other,Number): #check if value we are operating on is another number
            return Number(self.value + other.value).set_context(self.context) , None # add our value to the other value
            
        
    def subbed_by(self,other):
        if isinstance(other,Number): #check if value we are operating on is another number
            return Number(self.value - other.value).set_context(self.context), None # subtract our value to the other value
        
    def multed_by(self,other):
        if isinstance(other,Number): #check if value we are operating on is another number
            return Number(self.value * other.value).set_context(self.context),None # * our value to the other value
    
    def dived_by(self,other):        
        if isinstance(other,Number): #check if value we are operating on is another number
            if other.value ==0:
                return None, RTError(other.pos_start , other.pos_end, "Division by zero", self.context) 
            return Number(self.value / other.value).set_context(self.context), None # / our value to the other value
        
    def power_by(self, other):
        if isinstance(other, Number):
            return Number(self.value ** other.value).set_context(self.context), None


#################################################
# CONTEXT
#################################################

class Context:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent #parent context, e.g. if we are in a function, the parent context is the global context
        self.parent_entry_pos = parent_entry_pos #position in the parent context where we entered this context, used for error messages
        self.symbol_table = None #symbol table for this context, used to store variables and their values
  

#################################################
# SYMBOL TABLE
#################################################
# keep reference of all var names and values

class SymbolTable:
    def __init__(self):
        self.symbols = {}
        self.parent = None #like function parent for local vars, for global vars will be global symbol table with no parent
        
    def get(self, name):
        value = self.symbols.get(name, None) #none is var default value
        if value == None and self.parent: #if var referenced is not assigned in current scope get from parent
            return self.parent.get(name) #if no var in scope check parent 
        
        return value
    
    def set(self, name, value):
        self.symbols[name] = value
        
    def remove(self,name):
        del self.symbols[name]
        
        
        
        

#################################################
# INTERPRETER
#################################################
class Interpreter:
    def visit(self, node,context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name,self.no_visit_method) #default method, getattr will return the method with the name visit_{node type} if it exists, otherwise it will return no_visit_method
        return method(node,context)
        
    def no_visit_method(self,node,context):
        raise Exception(f"No visit_{type(node).__name__} method defined")
    
    def visit_NumberNode(self, node, context):
        print("Found number node!")
        return RTResult().success(Number(node.tok.value).set_context(context).set_pos(node.pos_start, node.pos_end)) # can't be unsuccessful since no operations happening
    
    def visit_VarAccessNode(self, node, context):
        print("Found VarAccessNode!")
        res = RTResult()
        var_name = node.var_name_tok.value
        
        value = context.symbol_table.get(var_name)
        
        if not value:
            return res.failure(RTError(node.pos_start, node.pos_end, f"'{var_name}' is not defined", self.context))
        
        return res.success(value.set_pos(node.pos_start, node.pos_end)) #return the value of the variable
    
    def visit_VarAssignNode(self, node, context):
        print("Found VarAssignNode!")
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(self.visit(node.value_node, context)) #visit the value node to get the value of the variable
        
        if res.error: return res #if there is an error, return the error
        
        context.symbol_table.set(var_name, value) #set the value of the variable in the symbol table if no error 
        return res.success(value) #return the value of the variable
        
    
    def visit_BinOpNode(self, node, context):
        print("Found bin op node!")
        res = RTResult()
        
        left = res.register(self.visit(node.left_node, context)) #visit child node
        if res.error: return res
        right = res.register(self.visit(node.right_node, context)) #visit child node
        if res.error: return res
        
        error = None
        
        if node.op_tok.type == TT_PLUS:
            result,error = left.added_to(right)
        elif node.op_tok.type == TT_MINUS:
            result,error = left.subbed_by(right)
        elif node.op_tok.type == TT_MUL:
            result,error = left.multed_by(right)
        elif node.op_tok.type == TT_DIV:
            result,error = left.dived_by(right)
        elif node.op_tok.type == TT_POWER:
            result, error = left.power_by(right)
        else:
            raise Exception("Not a BinOp found: ",node.op_tok.type)
        
        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))
        
    def visit_UnaryOpNode(self, node, context):
        print("Found UnaryOpNode") #e.g. like -5
        res = RTResult()
        
        number = res.register(self.visit(node.node, context))
        
        if res.error: return res
        
        error = None
        
        if node.op_tok.type == TT_MINUS:
            number, error = number.multed_by(Number(-1))
            
        
        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))


        
#################################################
# RUN
#################################################

global_symbol_table = SymbolTable() #global symbol table for all variables, used to store variables and their values
global_symbol_table.set("null", Number(0)) #set a null variable to 0, used to represent no value

def run(fn,text):
    lexer = Lexer(fn,text)
    tokens, error = lexer.make_tokens()
    
    if error: return None, error
    
    # Generate Abstract Syntax Tree
    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error: return None, ast.error
    
    #Run Program
    interpreter = Interpreter()
    context = Context("<program>") #create a context for the program
    context.symbol_table = global_symbol_table #set the symbol table to the global symbol table
    result = interpreter.visit(ast.node, context)
    
    return result.value.value, result.error