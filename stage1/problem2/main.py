import json
logList=[]

try:
    with open("mission_computer_main.log","r") as f :
        lines=f.readlines()[1:] 
        for line in lines:
            parts = line.split(",",2)
            logList.append(parts)
    logList.reverse()
    dictList=[]
    for parts in logList:
        dictList.append({
            "timestamp":parts[0],
            "event":parts[1],
            "message":parts[2].strip()
            })
   
    with open("mission_computer_main.json","w") as f:
        json.dump(dictList,f,indent=4)
except FileNotFoundError:
    print("File not found. Please ensure the file exists in the specified path.")
except UnicodeDecodeError:
    print("Error decoding the file. Please ensure the file is in the correct format.")  
