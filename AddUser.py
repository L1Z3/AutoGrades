from GraphUser import GraphUser

if __name__ == '__main__':
    key = input("Please enter an key to add. ")
    while True:
        publicString = input("Should the grades be public? Yes or no: ")
        if publicString.lower() == "yes":
            public = True
        elif publicString.lower() == "no":
            public = False
        else:
            print("Please enter yes or no.")
            continue
        break
    created_user = GraphUser.create_user(key, public)
    if created_user.is_public:
        print("Successfully created user " + created_user.name + " with ID " + str(created_user.id) + " and public grades.")
    else:
        print("Successfully created user " + created_user.name + " with ID " + str(created_user.id) + " and private grades.")
