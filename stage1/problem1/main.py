print("hello, Mars!")

try : 
    with open("mission_computer_main.log","r") as f:
        print(f.read())
except FileNotFoundError:
    print("File not found. Please check the file path and try again.")  
except UnicodeDecodeError:
    print("Error decoding the file. Please ensure the file is in the correct format.")
except Exception as e:
    print(f"An error occurred: {e}")


