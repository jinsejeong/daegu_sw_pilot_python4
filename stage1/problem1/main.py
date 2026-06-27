print("hello, Mars!")

try : 
    with open("mission_computer_main.log","r") as f:
        print(f.read())
except FileNotFoundError:
    print("File not found. Please ensure the file exists in the specified path.")  
except UnicodeDecodeError:
    print("Error decoding the file. Please ensure the file is in the correct format.")
except Exception as e:
    print(f"An error occurred: {e}")


