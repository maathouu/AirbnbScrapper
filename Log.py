import time
import os

def SayDict(Var):
    Result = []
    Id = 1
    MaxLent = 0

    for item in Var:
        if len(item) > MaxLent:MaxLent = len(item)

    for item in Var:
        Signe1 = "└" if len(Var) == Id else "├"
        Signe2 = " " if len(Var) == Id else "│"

        if type(Var[item]) == dict: 
            Result.append(f"{Signe1}─ {item}\n")
            Temp = SayDict(Var[item])
            for SubItem in Temp:
                Result.append(f"{Signe2}  {SubItem}")
        else:
            Result.append(f"{Signe1}─ {item:<{MaxLent}} : {Var[item]}\n")
        Id += 1
    return Result


class ConsoleColor:
    HEADER = '\033[95m'
    
    CYAN = '\033[96m'                   # Finished function
    GREEN = '\033[92m'                  # Actual category
    RED = '\033[31m'                    # Error
    YELLOW = '\033[33m'                 # Warning / import info
    BLUE = '\033[34m'                   # Starting new function
    PURPLE = '\033[35m'                 # User Settings
    PINK = '\033[38;2;255;105;180m'     # Global Settings
    ORANGE = '\033[38;2;255;165;0m'     # Value calculated by the function ( like time )
 
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class LogManager:
    def __init__(self,mode="normal",save="console"):
        
        self.Version = "16-07-2026.0"
        self.Save = save
        self.Category = "None"
        self.ErrorCategory = "None"
        
        if self.Save in ("file","both"):
            if not os.path.isdir("Log"):
                os.makedirs("Log")
            if mode == "normal":
                self.File = f"{time.strftime('%Y-%m-%d_%H:%M', time.localtime())}.log"
            elif mode == "test":
                self.File = "Log/Test.log"
            with open(self.File,"w") as TempFile:
                TempFile.write("")

        self.Say(f"Log module loaded with version : {self.Version}")

    def Changecategory(self,Com):
        self.Category = Com

    def Say(self,*Message,PrefixTime=True,PrefixCategory=True,StartSpace=0,Format=0):
        
        if PrefixTime:Prefix =  ((f"[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}]",ConsoleColor.BOLD),)
        else:Prefix = ()

        if PrefixCategory:Prefix += (" | ",(self.Category,ConsoleColor.GREEN)," | : ")

        if StartSpace > 0 :Prefix = ("\n"*StartSpace,)+Prefix   

        if Format == 1:
            Message = tuple([Mess for List in Message for Mess in List])

        if self.Save in ("file","both"):
            RawMessage = ""
            for word in Prefix+Message:
                
                if type(word) == str:RawMessage += word
                else:RawMessage += word[0]

            with open(self.File, "a",encoding="utf-8") as File:
                File.write(RawMessage+"\n")    

        if self.Save in ("console","both"):
            for word in Prefix+Message:
                if type(word) != str:
                    print(word[1]+word[0]+ConsoleColor.END,end="")
                else:
                    print(word,end="")
            print()

    def SayError(self,Var):
        RawData = {key:value for key,value in vars(Var).items()}
        NewData = {"Context":{key:value for key,value in RawData.items() if key in ("GlobalContext","Context","DetailedContext")},
                   "Parameters":{key:value for key,value in RawData.items() if key not in ("GlobalContext","Context","DetailedContext")}}
        self.Say(("╔═══════════════════════════════════════════════════════════════╗\n║                             ERROR                             ║\n╚═══════════════════════════════════════════════════════════════╝",ConsoleColor.RED),PrefixTime=False,PrefixCategory=False)

        Display = SayDict(NewData)
        self.Say(Display,PrefixTime=False,PrefixCategory=False,Format=1)