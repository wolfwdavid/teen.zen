# print("Welcome to the Chatbot!")

#name = input("What is your name?\n")
#print(name)


welcome_prompt = "Welcome!, I am a chatbot. How can I assist you today?\n - To get started, please select an option:\n 1. Chat with me\n 2. Get information\n 3. Exit\n"

def get_user_name():
    print("Please enter your name:")
    user_name = input()
    print("Hello, {user_name}! How can I assist you today?")

def get_information():
    print("Please enter the information you need:")
    info_request = input()
    

def main():
   while(True):
    selection = input(welcome_prompt)
   if selection == '1':
       print("You have selected to chat with me.")
       get_user_name
       # Add chat functionality here
   elif selection == '2':
       print("You have selected to get information.")
       get_information
       # Add information functionality here
       
   elif selection == '3':
       print("Exiting the chatbot. Goodbye!")
   else:
       print("Invalid selection. Please try again.")
       return

main()